"""Render shipped static/variable numeric proofs; fonts are not modified."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.svgPathPen import SVGPathPen
import json,hashlib,tempfile
R=Path(__file__).resolve().parents[1];O=R/'checks/digits';O.mkdir(exist_ok=True)
label=ImageFont.truetype(str(R/'SAB-Modul-1.0/TTF/SABModulSans-Regular.ttf'),23)
records=[]
for family,folder in [('Sans','SAB-Modul-1.0'),('Mono','SAB-Modul-1.0'),('Code','SAB-Modul-Code')]:
 paths=sorted((R/folder/'TTF').glob('*'+family+'*.ttf'))
 small=Image.new('RGB',(1800,len(paths)*180+70),'white');d=ImageDraw.Draw(small)
 for i,p in enumerate(paths):
  im=Image.new('RGB',(2300,1190),'white');draw=ImageDraw.Draw(im);font=ImageFont.truetype(str(p),600)
  draw.text((25,15),p.stem+' | 300 pt at 144 dpi | shared baseline',font=label,fill='#657080')
  for row in range(2):
   baseline=530+row*565;draw.line((20,baseline,2270,baseline),fill='#d8dde2')
   draw.line((20,baseline-420,2270,baseline-420),fill='#d8dde2')
   for col in range(5):draw.text((col*450+25,baseline),'0123456789'[row*5+col],font=font,fill='#101820',anchor='ls')
  name=p.stem+'-300pt.png';im.save(O/name)
  d.text((20,i*180+10),p.stem,font=label,fill='#657080')
  for j,size in enumerate((14,16)):
   f=ImageFont.truetype(str(p),size*2)
   text='0123456789  2026-10-14  23:59  25 258 752  87,35%  0Oо 1Il 2Z 5S 3З 6б 8B'
   d.text((20,i*180+55+j*50),text,font=f,fill='#101820')
  records.append({'font':str(p.relative_to(R)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'large_proof':name,'small_sizes_pt':[14,16],'dpi':144})
 small.save(O/(family.lower()+'-small-all-styles.png'))
 for style in ('Regular','Bold'):
  p=R/folder/'TTF'/f'SABModul{family}-{style}.ttf';font=ImageFont.truetype(str(p),1200)
  im=Image.new('RGB',(2300,1120),'white');d=ImageDraw.Draw(im)
  for i,ch in enumerate('258'):
   d.text((i*760+20,20),family+' '+style+' '+ch+' | 600 pt',font=label,fill='#657080');d.text((i*760+10,1050),ch,font=font,fill='#101820',anchor='ls')
  im.save(O/(family.lower()+'-'+style.lower()+'-258-600pt.png'))
 # Additional weight interpolation proof, not substituted for master proofs.
 for p in (R/folder/'VF').glob('*'+family+'*.ttf'):
  f=TTFont(p);imin=int(f['fvar'].axes[0].minValue);imax=int(f['fvar'].axes[0].maxValue)
  im=Image.new('RGB',(1800,530),'white');d=ImageDraw.Draw(im)
  with tempfile.TemporaryDirectory() as tmp:
   for i,w in enumerate((imin,450.5,imax)):
    ins=instantiateVariableFont(f,{'wght':w},inplace=False);out=Path(tmp)/'instance.ttf';ins.save(out);pf=ImageFont.truetype(str(out),200)
    d.text((20,i*170+5),p.stem+' | wght '+str(w),font=label,fill='#657080');d.text((20,i*170+150),'0123456789',font=pf,fill='#101820',anchor='ls')
  im.save(O/(p.stem+'-interpolation.png'))
(O/'render-manifest.json').write_text(json.dumps({'static_styles':38,'records':records,'large_sizes_pt':[300,600],'small_sizes_pt':[14,16],'dpi':144},indent=2)+'\n')
html=['<!doctype html><meta charset="utf-8"><title>SAB Modul – digit repair proofs</title><style>body{font:16px system-ui;margin:24px;background:#f4f5f7}img{max-width:100%;background:white}section{background:white;padding:24px;margin:24px 0}.large{font-size:300pt;line-height:1.15;overflow:auto;white-space:nowrap}small{color:#657080}.small{margin:8px 0}.grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}</style><h1>SAB Modul – corrected digits</h1><p>All 38 styles. Actual shipped static WOFF2 fonts; 14/16pt reading, 300pt outlines. No synthetic bold or italic.</p>']
for i,rec in enumerate(records):
 p=Path(rec['font']);web=p.parent.parent/'WOFF2'/(p.stem+'.woff2');f=TTFont(R/p);weight=f['OS/2'].usWeightClass;italic=bool(f['post'].italicAngle)
 face='Proof'+str(i);url='../../'+str(web)
 html.append(f'<style>@font-face{{font-family:{face};src:url("{url}");font-weight:{weight};font-style:{"italic" if italic else "normal"}}}.f{i}{{font-family:{face};font-weight:{weight};font-style:{"italic" if italic else "normal"};font-synthesis:none}}</style>')
 html.append(f'<section><h2>{p.stem}</h2><div class="f{i}"><div class="small" style="font-size:14pt">0123456789 · 2026-10-14 · 23:59 · 25 258 752 · 0Oо 1Il 2Z 5S 3З 6б 8B · объем съешь подъезд ОБЪЕКТ</div><div class="small" style="font-size:16pt">0123456789 · $87,35 → $55,10 · 756 → 648 · 37% · релиз 2026.10.14</div><div class="large">0123456789</div></div><details><summary>300pt shared baseline raster proof</summary><img src="{rec["large_proof"]}"></details></section>')
html.append('<p>Technical reports and their retained exceptions are provided separately. These pages are visual proofs, not Google Fonts catalogue approval.</p>')
(O/'web-proof.html').write_text('\n'.join(html))
print('Proofs written:',len(records),'staticstyles;6VFpanels',flush=True)
