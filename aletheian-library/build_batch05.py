#!/usr/bin/env python3
"""Build Aletheian Library EPUB Batch 05 from public-domain Gutenberg editions."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import re
import shutil
import sys
import time
import urllib.parse
import urllib.request
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

OUT = Path("dist/Aletheian_Library_EPUB_Batch_05")
BOOKS_DIR = OUT / "Books"
TARGET_COUNT = 20

# Canonical catalog candidates, in preferred order. The builder takes the first
# 20 that resolve to a valid Gutenberg EPUB, preserving difficult failures in
# the deferred ledger rather than shipping damaged books.
CANDIDATES = [
    {"slot": 20, "title": "Pragmatism", "author": "William James", "id": 5116},
    {"slot": 38, "title": "The Golden Bough", "author": "James George Frazer", "id": 3623},
    {"slot": 60, "title": "The Interior Castle", "author": "Teresa of Avila", "search": "Interior Castle Teresa Avila"},
    {"slot": 63, "title": "Calculus Made Easy", "author": "Silvanus P. Thompson", "id": 33283},
    {"slot": 65, "title": "The Science of Mechanics", "author": "Ernst Mach", "search": "Science of Mechanics Ernst Mach"},
    {"slot": 66, "title": "Relativity: The Special and General Theory", "author": "Albert Einstein", "id": 5001},
    {"slot": 67, "title": "Dialogue Concerning the Two Chief World Systems", "author": "Galileo Galilei", "search": "Dialogue Concerning Two Chief World Systems Galileo"},
    {"slot": 68, "title": "Opticks", "author": "Isaac Newton", "id": 33504},
    {"slot": 69, "title": "On the Heavens", "author": "Aristotle", "search": "On the Heavens Aristotle"},
    {"slot": 81, "title": "Sketch of the Analytical Engine", "author": "Luigi Federico Menabrea and Ada Lovelace", "search": "Sketch Analytical Engine Menabrea Lovelace"},
    {"slot": 84, "title": "Experimental Researches in Electricity, Volume 1", "author": "Michael Faraday", "id": 14986},
    {"slot": 85, "title": "The Theory of Sound", "author": "John William Strutt, Baron Rayleigh", "search": "Theory of Sound Rayleigh"},
    {"slot": 86, "title": "Shop Management", "author": "Frederick Winslow Taylor", "id": 27284},
    {"slot": 87, "title": "The Principles of Scientific Management", "author": "Frederick Winslow Taylor", "id": 6435},
    {"slot": 91, "title": "Frankenstein", "author": "Mary Wollstonecraft Shelley", "id": 84},
    {"slot": 92, "title": "Moby-Dick", "author": "Herman Melville", "id": 2701},
    {"slot": 93, "title": "The Time Machine", "author": "H. G. Wells", "id": 35},
    {"slot": 94, "title": "The War of the Worlds", "author": "H. G. Wells", "id": 36},
    {"slot": 95, "title": "The Island of Doctor Moreau", "author": "H. G. Wells", "id": 159},
    {"slot": 96, "title": "The Invisible Man", "author": "H. G. Wells", "id": 5230},
    {"slot": 97, "title": "Notes from the Underground", "author": "Fyodor Dostoevsky", "id": 600},
    {"slot": 98, "title": "Crime and Punishment", "author": "Fyodor Dostoevsky", "id": 2554},
    {"slot": 99, "title": "Alice's Adventures in Wonderland", "author": "Lewis Carroll", "id": 11},
    {"slot": 100, "title": "Through the Looking-Glass", "author": "Lewis Carroll", "id": 12},
]

UA = "AletheianLibraryBuilder/1.0 (+public-domain personal library)"


def get_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


def download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=180) as response, dest.open("wb") as out:
        shutil.copyfileobj(response, out)


def normalize(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def resolve(candidate: dict) -> dict:
    if candidate.get("id"):
        data = get_json(f"https://gutendex.com/books/?ids={candidate['id']}")
        results = data.get("results", [])
        if not results:
            raise RuntimeError(f"Gutendex returned no record for {candidate['id']}")
        return results[0]

    query = urllib.parse.quote(candidate["search"])
    data = get_json(f"https://gutendex.com/books/?search={query}")
    results = data.get("results", [])
    if not results:
        raise RuntimeError("No Gutendex search result")

    title_words = set(normalize(candidate["title"]).split())
    author_words = set(normalize(candidate["author"]).split())
    scored = []
    for record in results:
        rtitle = normalize(record.get("title", ""))
        rauthors = normalize(" ".join(a.get("name", "") for a in record.get("authors", [])))
        score = sum(w in rtitle for w in title_words) * 3 + sum(w in rauthors for w in author_words)
        scored.append((score, record))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    if not scored or scored[0][0] < 3:
        raise RuntimeError("No sufficiently close title/author match")
    return scored[0][1]


def choose_epub(record: dict) -> str:
    formats = record.get("formats", {})
    options = []
    for mime, url in formats.items():
        if not url or "epub" not in mime.lower():
            continue
        rank = 0
        low = url.lower()
        if "epub3" in low:
            rank += 30
        if "images" in low and "noimages" not in low:
            rank += 20
        if low.startswith("https://"):
            rank += 5
        options.append((rank, url))
    if not options:
        # Gutenberg's modern generated endpoint is reliable even when Gutendex
        # omits it from the format map.
        book_id = record["id"]
        options = [(10, f"https://www.gutenberg.org/ebooks/{book_id}.epub3.images"),
                   (5, f"https://www.gutenberg.org/ebooks/{book_id}.epub.images"),
                   (1, f"https://www.gutenberg.org/ebooks/{book_id}.epub.noimages")]
    options.sort(reverse=True)
    return options[0][1]


def safe_filename(title: str, author: str) -> str:
    value = f"{title} - {author}.epub"
    value = value.replace("/", "-").replace("\\", "-").replace(":", " -")
    return re.sub(r"\s+", " ", value).strip()


def patch_metadata(epub: Path, title: str, author: str) -> None:
    """Normalize title/creator while retaining the source EPUB's contents."""
    temp = epub.with_suffix(".patched.epub")
    with zipfile.ZipFile(epub, "r") as zin:
        container = ET.fromstring(zin.read("META-INF/container.xml"))
        rootfile = container.find(".//{*}rootfile")
        if rootfile is None:
            raise RuntimeError("EPUB has no package rootfile")
        opf_path = rootfile.attrib["full-path"]
        opf = ET.fromstring(zin.read(opf_path))
        metadata = opf.find("{*}metadata")
        if metadata is None:
            raise RuntimeError("EPUB has no metadata element")
        title_node = metadata.find("{http://purl.org/dc/elements/1.1/}title")
        if title_node is None:
            title_node = ET.SubElement(metadata, "{http://purl.org/dc/elements/1.1/}title")
        title_node.text = title
        creator_node = metadata.find("{http://purl.org/dc/elements/1.1/}creator")
        if creator_node is None:
            creator_node = ET.SubElement(metadata, "{http://purl.org/dc/elements/1.1/}creator")
        creator_node.text = author
        opf_bytes = ET.tostring(opf, encoding="utf-8", xml_declaration=True)

        with zipfile.ZipFile(temp, "w") as zout:
            names = zin.namelist()
            if "mimetype" in names:
                zout.writestr("mimetype", zin.read("mimetype"), compress_type=zipfile.ZIP_STORED)
            for item in zin.infolist():
                if item.filename == "mimetype":
                    continue
                data = opf_bytes if item.filename == opf_path else zin.read(item.filename)
                zout.writestr(item, data)
    temp.replace(epub)


def validate_epub(epub: Path) -> None:
    if epub.stat().st_size < 10_000:
        raise RuntimeError("EPUB is implausibly small")
    with zipfile.ZipFile(epub, "r") as zf:
        bad = zf.testzip()
        if bad:
            raise RuntimeError(f"Corrupt ZIP member: {bad}")
        if "mimetype" not in zf.namelist() or "META-INF/container.xml" not in zf.namelist():
            raise RuntimeError("Missing mandatory EPUB container files")
        if zf.read("mimetype").strip() != b"application/epub+zip":
            raise RuntimeError("Invalid EPUB mimetype")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def main() -> int:
    if OUT.exists():
        shutil.rmtree(OUT)
    BOOKS_DIR.mkdir(parents=True)
    successes = []
    failures = []

    for candidate in CANDIDATES:
        if len(successes) >= TARGET_COUNT:
            break
        print(f"Resolving #{candidate['slot']:03d}: {candidate['title']}", flush=True)
        raw = BOOKS_DIR / (safe_filename(candidate["title"], candidate["author"]) + ".download")
        final = BOOKS_DIR / safe_filename(candidate["title"], candidate["author"])
        try:
            record = resolve(candidate)
            url = choose_epub(record)
            download(url, raw)
            raw.replace(final)
            validate_epub(final)
            patch_metadata(final, candidate["title"], candidate["author"])
            validate_epub(final)
            successes.append({
                "slot": candidate["slot"],
                "title": candidate["title"],
                "author": candidate["author"],
                "filename": final.name,
                "gutenberg_id": record.get("id"),
                "source_url": url,
                "bytes": final.stat().st_size,
                "sha256": sha256(final),
            })
            print(f"  OK: {final.name} ({final.stat().st_size:,} bytes)", flush=True)
        except Exception as exc:
            raw.unlink(missing_ok=True)
            final.unlink(missing_ok=True)
            failures.append({
                "slot": candidate["slot"],
                "title": candidate["title"],
                "author": candidate["author"],
                "reason": str(exc),
            })
            print(f"  DEFERRED: {exc}", flush=True)
        time.sleep(0.4)

    if len(successes) != TARGET_COUNT:
        raise RuntimeError(f"Built {len(successes)} valid EPUBs; required {TARGET_COUNT}")

    with (OUT / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(successes[0].keys()))
        writer.writeheader(); writer.writerows(successes)
    with (OUT / "deferred_slots.csv").open("w", newline="", encoding="utf-8") as f:
        fields = ["slot", "title", "author", "reason"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(failures)

    reading = ["# Aletheian Library — EPUB Batch 05", "", "Catalog numbers remain here only; EPUB filenames use `Title - Author.epub`.", ""]
    reading += [f"{i}. **#{row['slot']:03d} — {row['title']}** — {row['author']}" for i, row in enumerate(successes, 1)]
    (OUT / "reading_order.md").write_text("\n".join(reading) + "\n", encoding="utf-8")

    readme = f"""# Aletheian Library — EPUB Batch 05

This archive contains {len(successes)} complete public-domain EPUBs.

- Filename convention: `Title - Author.epub`
- Catalog numbers: retained only in `manifest.csv` and `reading_order.md`
- Source: Project Gutenberg records resolved through Gutendex
- Validation: ZIP integrity, mandatory EPUB files, package metadata, and SHA-256
- Covers, illustrations, equations, and internal navigation are retained from the source EPUB where available.
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")

    zip_path = Path("dist/Aletheian_Library_EPUB_Batch_05_20_Books.zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for p in sorted(OUT.rglob("*")):
            if p.is_file():
                zf.write(p, p.relative_to(OUT.parent))
    with zipfile.ZipFile(zip_path, "r") as zf:
        if zf.testzip():
            raise RuntimeError("Final ZIP validation failed")
    checksum = sha256(zip_path)
    Path(str(zip_path) + ".sha256").write_text(f"{checksum}  {zip_path.name}\n", encoding="utf-8")
    print(f"DONE: {zip_path} ({zip_path.stat().st_size:,} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
