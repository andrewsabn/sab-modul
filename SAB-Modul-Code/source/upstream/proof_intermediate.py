"""Compare actual variable instances with direct drawing at intermediate weights."""
from pathlib import Path
import hashlib,json,shutil,sys,tempfile
import numpy as np
import build
from proof import ROOT,Image,draw_text,ShapedFont,font

out=ROOT/'iterations'/sys.argv[1]
assert out.is_dir()
records=[];original_root=build.ROOT
try:
 with tempfile.TemporaryDirectory() as tmp:
  build.ROOT=Path(tmp)
  direct_fonts=out/'direct-fonts';direct_fonts.mkdir(exist_ok=True)
  for family in ['Sans','Mono']:
   for slant in ['', 'Oblique']:
    vf=ROOT/'VF'/('SABModul'+family+('-Italic' if slant else '')+'[wght].ttf')
    im=Image.new('RGB',(2400,1560),'white')
    for row,weight in enumerate([250,350,450,550,650,800]):
     thickness=float(np.interp(weight,[v[0] for v in build.WEIGHTS.values()],[v[1] for v in build.WEIGHTS.values()]))
     result=build.build('SAB Modul',family=='Mono','Regular',weight,thickness,bool(slant),('ttf',))
     direct=direct_fonts/(f'{family}{slant}-{weight}.ttf')
     shutil.copy2(Path(tmp)/'TTF'/(result['file']+'.ttf'),direct)
     for col,(path,label,variation) in enumerate([(direct,'Direct drawing',None),(vf,'Variable',{'wght':weight})]):
      x=25+1200*col;y=260*row
      draw_text(im,(x,y+38),label+' · '+family+' '+(slant or 'Roman')+' · '+str(weight),font('CoFo',25),fill='#777777')
      draw_text(im,(x,y+140),'0 9 ® § Юю Æ № e',ShapedFont(path,78,variation))
      draw_text(im,(x,y+206),'Технологии 2026. Release v0.8.0 © ®',ShapedFont(path,24,variation))
     records.append({'family':family,'style':slant or 'Roman','weight':weight,'stem_thickness':thickness,'direct_font':str(direct.relative_to(ROOT)),'direct_sha256':hashlib.sha256(direct.read_bytes()).hexdigest(),'variable_font':str(vf.relative_to(ROOT)),'variable_sha256':hashlib.sha256(vf.read_bytes()).hexdigest()})
    im.save(out/('intermediate-'+family+slant+'.png'))
finally:build.ROOT=original_root
(out/'intermediate.json').write_text(json.dumps({'sizes_px':[78,24],'engine':'HarfBuzz','records':records,'visual_acceptance':False},indent=2))
shutil.copy2(Path(__file__),out/'proof_intermediate.py')
print(out/'intermediate.json')
