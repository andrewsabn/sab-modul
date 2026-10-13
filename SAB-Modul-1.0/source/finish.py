from pathlib import Path
import subprocess,shutil,tempfile
from fontTools.ttLib import TTFont

ROOT=Path(__file__).resolve().parents[1]
masters=ROOT/'source/masters';masters.mkdir(exist_ok=True)
for path in sorted((ROOT/'TTF').glob('*.ttf')):
 font=TTFont(path)
 if 'fpgm' not in font:
  master=masters/path.name;shutil.copy2(path,master)
  with tempfile.TemporaryDirectory() as tmp:
   hinted=Path(tmp)/path.name
   subprocess.run(['ttfautohint','-D','cyrl','-f','latn','-I',str(master),str(hinted)],check=True)
   check=TTFont(hinted)
   assert 'fpgm' in check and 'prep' in check
   assert check['hmtx'].metrics==font['hmtx'].metrics, path.name
   shutil.copy2(hinted,path)
 font=TTFont(path)
 font['head'].flags|=8
 font.save(path)
 font.flavor='woff2'
 (ROOT/'WOFF2').mkdir(exist_ok=True)
 font.save(ROOT/'WOFF2'/(path.stem+'.woff2'))
print('Hinted TTF and WOFF2:',len(list((ROOT/'TTF').glob('*.ttf'))))
