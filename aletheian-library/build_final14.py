#!/usr/bin/env python3
from pathlib import Path
import csv,hashlib,json,re,shutil,time,urllib.parse,urllib.request,zipfile
from xml.etree import ElementTree as ET
OUT=Path('dist/Aletheian_Library_EPUB_Final_14'); BOOKS=OUT/'Books'; UA='AletheianLibrary/1.0'
# 13 unresolved catalog positions + 1 companion work. Two copyrighted slots use clearly labeled public-domain substitutes.
C=[
(9,'Science and Hypothesis','Henri Poincaré','g',39713,'Substitutes for The Logic of Scientific Discovery'),
(10,'The Grammar of Science','Karl Pearson','ia','grammarofscienc00pear',''),
(31,'The Epic of Gilgamish','R. Campbell Thompson','ia','epicofgilgamish00thom',''),
(60,'The Interior Castle','Teresa of Ávila','ia','interiorcastle00tere',''),
(62,'An Introduction to Mathematics','Alfred North Whitehead','g',41568,"Substitutes for A Mathematician's Apology"),
(63,'Calculus Made Easy','Silvanus P. Thompson','g',33283,''),
(64,'The Foundations of Geometry','David Hilbert','g',17384,''),
(65,'The Science of Mechanics','Ernst Mach','ia','scienceofmechani00mach',''),
(67,'Dialogue Concerning the Two Chief World Systems','Galileo Galilei','ia','dialogueconcern00gali',''),
(69,'On the Heavens','Aristotle','ia','worksofaristotle02arisuoft',''),
(85,'The Theory of Sound','John William Strutt, Baron Rayleigh','ia','theoryofsound01rayl',''),
(88,'The Boy Mechanic, Volume 1','Popular Mechanics Company','g',12655,'Fills curated How to Invent slot'),
(89,"Machinery's Handbook, First Edition",'Erik Oberg and Franklin D. Jones','ia','machineryshandbo00ober','Public-domain first edition'),
(101,'The Notebooks of Leonardo da Vinci','Leonardo da Vinci','g',5000,'Companion work completing 100 unique books')]
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
 if not urls:
  txt=[u for k,u in fm.items() if u and 'text/plain' in k][0]; make_epub(req(txt).read().decode('utf-8','replace'),title,author,out); return txt
 for u in sorted(urls,key=lambda x:('images' in x and 'noimages' not in x,'epub3' in x),reverse=True):
  try: dl(u,out); return u
  except: pass
 raise RuntimeError('No Gutenberg EPUB')
def ia_text(identifier):
 m=get(f'https://archive.org/metadata/{identifier}'); files=m.get('files',[])
 names=[f['name'] for f in files if f.get('name')]
 for suf in ('_djvu.txt','_text.pdf.txt','.txt'):
  cand=[n for n in names if n.endswith(suf)]
  if cand:
   n=max(cand,key=len); return req('https://archive.org/download/'+identifier+'/'+urllib.parse.quote(n)).read().decode('utf-8','replace'),'https://archive.org/details/'+identifier
 raise RuntimeError('No IA OCR text')
def validate(p):
 with zipfile.ZipFile(p) as z:
  assert not z.testzip(); assert z.read('mimetype').strip()==b'application/epub+zip'; assert 'META-INF/container.xml' in z.namelist()
def sha(p):
 h=hashlib.sha256();
 with p.open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
def main():
 if OUT.exists():shutil.rmtree(OUT)
 BOOKS.mkdir(parents=True); rows=[]
 for slot,title,author,kind,key,note in C:
  p=BOOKS/(safe(title+' - '+author)+'.epub'); print(title,flush=True)
  if kind=='g': source=g_epub(key,title,author,p)
  else:
   txt,source=ia_text(key); make_epub(txt,title,author,p)
  validate(p); rows.append(dict(slot=slot,title=title,author=author,filename=p.name,source=source,note=note,bytes=p.stat().st_size,sha256=sha(p))); time.sleep(.3)
 with (OUT/'manifest.csv').open('w',newline='',encoding='utf-8') as f:
  w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
 (OUT/'README.md').write_text('# Aletheian Library — Final 14\n\nThis batch closes the remaining catalog gaps and brings the delivered collection to 100 unique books. Two copyrighted catalog positions use clearly labeled public-domain substitutes; one companion title fills the arithmetic gap created by earlier duplicate seed titles. Filenames use `Title - Author.epub`.\n',encoding='utf-8')
 (OUT/'reading_order.md').write_text('# Final 14 Reading Order\n\n'+'\n'.join(f"{i}. **{r['title']}** — {r['author']}" for i,r in enumerate(rows,1))+'\n',encoding='utf-8')
 zp=Path('dist/Aletheian_Library_EPUB_Final_14_Books.zip')
 with zipfile.ZipFile(zp,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
  for p in OUT.rglob('*'):
   if p.is_file():z.write(p,p.relative_to(OUT.parent))
 assert not zipfile.ZipFile(zp).testzip(); Path(str(zp)+'.sha256').write_text(f'{sha(zp)}  {zp.name}\n')
 print('DONE',zp)
if __name__=='__main__':main()
