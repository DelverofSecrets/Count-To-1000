#!/usr/bin/env python3
from pathlib import Path
import csv,hashlib,json,re,shutil,time,urllib.request,zipfile
OUT=Path('dist/Aletheian_Library_EPUB_Final_14'); BOOKS=OUT/'Books'; UA='AletheianLibrary/1.0'
C=[
('Science and Hypothesis','Henri Poincaré',39713,'Catalog replacement: scientific reasoning'),
('The Souls of Black Folk','W. E. B. Du Bois',408,'Catalog replacement: society and knowledge'),
('The Epic of Gilgamesh','Anonymous',18897,'Deferred catalog recovery; Gutenberg public-domain edition'),
('The Art of War','Sun Tzu',132,'Catalog companion: systems and strategy'),
('Pride and Prejudice','Jane Austen',1342,'Companion fiction'),
('War and Peace','Leo Tolstoy',2600,'Companion systems fiction'),
('A Tale of Two Cities','Charles Dickens',98,'Companion historical fiction'),
('A Christmas Carol','Charles Dickens',46,'Companion moral fiction'),
('Adventures of Huckleberry Finn','Mark Twain',76,'Companion American fiction'),
('Strange Case of Dr Jekyll and Mr Hyde','Robert Louis Stevenson',43,'Companion psychology fiction'),
('The Picture of Dorian Gray','Oscar Wilde',174,'Companion ethics fiction'),
('Dracula','Bram Stoker',345,'Companion symbolic fiction'),
('Metamorphosis','Franz Kafka',5200,'Companion transformation fiction'),
('The Importance of Being Earnest','Oscar Wilde',844,'Companion social satire')]
def req(url): return urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':UA}),timeout=180)
def dl(url,p):
 with req(url) as r,p.open('wb') as f: shutil.copyfileobj(r,f)
def safe(s): return re.sub(r'\s+',' ',s.replace('/','-').replace('\\','-').replace(':',' -')).strip()
def valid(p):
 with zipfile.ZipFile(p) as z:
  return not z.testzip() and z.read('mimetype').strip()==b'application/epub+zip' and 'META-INF/container.xml' in z.namelist()
def acquire(gid,p):
 urls=[f'https://www.gutenberg.org/ebooks/{gid}.epub3.images',f'https://www.gutenberg.org/ebooks/{gid}.epub.images',f'https://www.gutenberg.org/ebooks/{gid}.epub.noimages']
 for u in urls:
  try:
   dl(u,p)
   if valid(p): return u
  except Exception: pass
  p.unlink(missing_ok=True)
 raise RuntimeError(f'No valid EPUB for Gutenberg #{gid}')
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def main():
 if OUT.exists(): shutil.rmtree(OUT)
 BOOKS.mkdir(parents=True); rows=[]
 for i,(title,author,gid,note) in enumerate(C,1):
  p=BOOKS/(safe(title+' - '+author)+'.epub'); print(f'{i}/14 {title}',flush=True)
  source=acquire(gid,p); rows.append({'order':i,'title':title,'author':author,'filename':p.name,'gutenberg_id':gid,'source':source,'note':note,'bytes':p.stat().st_size,'sha256':sha(p)}); time.sleep(.25)
 with (OUT/'manifest.csv').open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=rows[0].keys()); w.writeheader(); w.writerows(rows)
 (OUT/'README.md').write_text('# Aletheian Library — Final 14\n\nThese fourteen validated public-domain EPUBs bring the delivered collection to 100 unique books. The original catalog contained several copyrighted, edition-sensitive, or unavailable slots; replacements are explicit in `manifest.csv`, never silently mislabeled. Filenames follow `Title - Author.epub`.\n',encoding='utf-8')
 (OUT/'reading_order.md').write_text('# Final 14 Reading Order\n\n'+'\n'.join(f"{r['order']}. **{r['title']}** — {r['author']}" for r in rows)+'\n',encoding='utf-8')
 zp=Path('dist/Aletheian_Library_EPUB_Final_14_Books.zip')
 with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for p in OUT.rglob('*'):
   if p.is_file(): z.write(p,p.relative_to(OUT.parent))
 assert not zipfile.ZipFile(zp).testzip(); Path(str(zp)+'.sha256').write_text(f'{sha(zp)}  {zp.name}\n')
 print('DONE',zp,zp.stat().st_size)
if __name__=='__main__': main()
