#!/usr/bin/env python3
from pathlib import Path
import csv,hashlib,json,re,shutil,time,urllib.request,zipfile
OUT=Path('dist/Aletheian_Library_EPUB_Final_14'); BOOKS=OUT/'Books'; UA='AletheianLibrary/1.0'
# Fourteen public-domain works, including substitutes for catalog entries whose exact editions are copyrighted or unavailable.
C=[
(9,'Science and Hypothesis','Henri Poincaré',39713,'Substitutes for The Logic of Scientific Discovery'),
(10,'The Souls of Black Folk','W. E. B. Du Bois',408,'Companion epistemology and society text'),
(31,'The Epic of Gilgamesh','Anonymous',18897,'Public-domain Gutenberg translation/fragment'),
(60,'The Art of War','Sun Tzu',132,'Companion systems and strategy text'),
(62,'An Introduction to Mathematics','Alfred North Whitehead',41568,"Substitutes for A Mathematician's Apology"),
(63,'Calculus Made Easy','Silvanus P. Thompson',33283,''),
(64,'The Foundations of Geometry','David Hilbert',17384,''),
(65,'The Wealth of Nations','Adam Smith',3300,'Companion systems text'),
(67,'The Communist Manifesto','Karl Marx and Friedrich Engels',61,'Companion political systems text'),
(85,'The Adventures of Sherlock Holmes','Arthur Conan Doyle',1661,'Companion inference text'),
(88,'The Boy Mechanic, Volume 1','Popular Mechanics Company',12655,'Fills curated How to Invent slot'),
(89,'The Notebooks of Leonardo da Vinci','Leonardo da Vinci',5000,'Fills historical invention/manual slot'),
(101,'The Adventures of Tom Sawyer','Mark Twain',74,'Companion fiction'),
(102,'The Yellow Wallpaper','Charlotte Perkins Gilman',1952,'Companion psychology fiction')]
def req(url,accept=None):
 h={'User-Agent':UA};
 if accept:h['Accept']=accept
 return urllib.request.urlopen(urllib.request.Request(url,headers=h),timeout=180)
def get(url): return json.load(req(url,'application/json'))
def dl(url,p):
 with req(url) as r,p.open('wb') as f: shutil.copyfileobj(r,f)
def safe(s): return re.sub(r'\s+',' ',s.replace('/','-').replace('\\','-').replace(':',' -')).strip()
def make_epub(txt,title,author,out):
 import html,uuid
 paras='\n'.join(f'<p>{html.escape(x)}</p>' for x in re.split(r'\n\s*\n',txt) if x.strip())
 uid=str(uuid.uuid4()); opf=f'''<?xml version="1.0" encoding="utf-8"?><package xmlns="http://www.idpf.org/2007/opf" unique-identifier="id" version="3.0"><metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:identifier id="id">urn:uuid:{uid}</dc:identifier><dc:title>{html.escape(title)}</dc:title><dc:creator>{html.escape(author)}</dc:creator><dc:language>en</dc:language><meta property="dcterms:modified">2026-08-04T00:00:00Z</meta></metadata><manifest><item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/><item id="c" href="text.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="c"/></spine></package>'''
 nav=f'''<html xmlns="http://www.w3.org/1999/xhtml"><head><title>{html.escape(title)}</title></head><body><nav epub:type="toc" xmlns:epub="http://www.idpf.org/2007/ops"><ol><li><a href="text.xhtml">{html.escape(title)}</a></li></ol></nav></body></html>'''
 body=f'''<html xmlns="http://www.w3.org/1999/xhtml"><head><title>{html.escape(title)}</title></head><body><h1>{html.escape(title)}</h1><h2>{html.escape(author)}</h2>{paras}</body></html>'''
 cont='''<?xml version="1.0"?><container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container"><rootfiles><rootfile full-path="EPUB/package.opf" media-type="application/oebps-package+xml"/></rootfiles></container>'''
 with zipfile.ZipFile(out,'w') as z:
  z.writestr('mimetype','application/epub+zip',compress_type=zipfile.ZIP_STORED); z.writestr('META-INF/container.xml',cont); z.writestr('EPUB/package.opf',opf); z.writestr('EPUB/nav.xhtml',nav); z.writestr('EPUB/text.xhtml',body)
def g_epub(i,title,author,out):
 data=get(f'https://gutendex.com/books/?ids={i}')['results'][0]; fm=data['formats']; urls=[u for k,u in fm.items() if u and 'epub' in k]
 for u in sorted(urls,key=lambda x:('images' in x and 'noimages' not in x,'epub3' in x),reverse=True):
  try: dl(u,out); return u
  except Exception: pass
 txts=[u for k,u in fm.items() if u and 'text/plain' in k]
 if not txts: raise RuntimeError(f'No downloadable format for Gutenberg #{i}')
 txt=txts[0]; make_epub(req(txt).read().decode('utf-8','replace'),title,author,out); return txt
def validate(p):
 with zipfile.ZipFile(p) as z:
  assert not z.testzip(); assert z.read('mimetype').strip()==b'application/epub+zip'; assert 'META-INF/container.xml' in z.namelist()
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def main():
 if OUT.exists():shutil.rmtree(OUT)
 BOOKS.mkdir(parents=True); rows=[]
 for slot,title,author,gid,note in C:
  p=BOOKS/(safe(title+' - '+author)+'.epub'); print(title,flush=True)
  source=g_epub(gid,title,author,p); validate(p)
  rows.append(dict(slot=slot,title=title,author=author,filename=p.name,gutenberg_id=gid,source=source,note=note,bytes=p.stat().st_size,sha256=sha(p))); time.sleep(.25)
 with (OUT/'manifest.csv').open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
 (OUT/'README.md').write_text('# Aletheian Library — Final 14\n\nThis batch brings the delivered collection to 100 unique books. Exact catalog editions that could not lawfully or reliably be included are replaced by clearly documented public-domain companion works. Filenames use `Title - Author.epub`.\n',encoding='utf-8')
 (OUT/'reading_order.md').write_text('# Final 14 Reading Order\n\n'+'\n'.join(f"{i}. **{r['title']}** — {r['author']}" for i,r in enumerate(rows,1))+'\n',encoding='utf-8')
 zp=Path('dist/Aletheian_Library_EPUB_Final_14_Books.zip')
 with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for p in OUT.rglob('*'):
   if p.is_file():z.write(p,p.relative_to(OUT.parent))
 assert not zipfile.ZipFile(zp).testzip(); Path(str(zp)+'.sha256').write_text(f'{sha(zp)}  {zp.name}\n')
 print('DONE',zp)
if __name__=='__main__':main()
