from pathlib import Path
from PIL import Image
from proof import ROOT,BASE,path,ShapedFont,font,draw_text,VARIABLE,variations
import sys,json,hashlib

out=ROOT/'iterations'/sys.argv[1]
assert out.is_dir()
assert json.loads((out/'measurements.json').read_text()).get('variable_candidate',False)==VARIABLE,'Proof mode differs from the main sheet'
lines=['i í ì î ï ĭ į ı j ĵ','і ї й ё Ї Й Ё','áéíóú ñüäö å ąęų','Ģģ Ķķ Ļļ Ņņ','Ŗŗ Ţţ Ųų Ąą Ęę','mínimo naïve','Київ їжак йод ёж','ď Ľ ľ ť  ďábel ľudia']
im=Image.new('RGB',(2400,3600),'white');records=[]
for section,(mono,style) in enumerate((m,s) for m in [False,True] for s in ['Regular','Bold','Black']):
 for col,kind in enumerate(['CoFo','Original','Current']):
  p=path(kind,style,mono)
  if kind=='Current':p=out/'fonts'/p.name
  f=ShapedFont(p,44,variations(kind,style));x=25+col*800;y=section*600
  draw_text(im,(x,y+40),kind+' · '+('Mono' if mono else 'Sans')+' · '+style,font('CoFo',24),fill='#777777')
  for i,text in enumerate(lines):draw_text(im,(x,y+110+i*62),text,f)
  records.append({'family':kind,'style':style,'mono':mono,'font':str(p),'variations':f.variations,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'widths_px':{text:round(f.getlength(text),3) for text in lines}})
im.save(out/'accents.png')
(out/'accents.json').write_text(json.dumps({'size_px':44,'engine':'HarfBuzz','records':records},ensure_ascii=False,indent=2))
print(out/'accents.png')
