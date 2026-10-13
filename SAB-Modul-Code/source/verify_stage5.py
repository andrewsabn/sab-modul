"""Ensure the new italic base propagates to accents without cmap or glyph regressions."""
import hashlib,json,subprocess,unicodedata
from pathlib import Path
from fontTools.ttLib import TTFont
import ots
ROOT=Path(__file__).resolve().parents[1]


def main():
 records=[]
 for path in sorted((ROOT/'source/stage5-masters').glob('*.ttf')):
  f=TTFont(path);previous=TTFont(ROOT/'source/stage4-masters'/path.name);punctuation=TTFont(ROOT/'source/stage2-masters'/path.name)
  cmap=f.getBestCmap();assert cmap==previous.getBestCmap(),(path.name,'cmap changed')
  minus=cmap[0x2212]
  assert f['glyf'][minus].compile(f['glyf'])==punctuation['glyf'][minus].compile(punctuation['glyf']),(path.name,'minus not restored')
  changed={minus};accents=[]
  if f['post'].italicAngle:
   assert f['post'].italicAngle==-10
   a,b=[cmap[ord(ch)] for ch in 'aа'];changed.update([a,b])
   assert f['glyf'][a].compile(f['glyf'])==f['glyf'][b].compile(f['glyf'])
   assert f['glyf'][a].numberOfContours==2
   for cp,name in cmap.items():
    text=unicodedata.normalize('NFD',chr(cp))
    if len(text)>1 and text[0] in 'aа':
     changed.add(name);glyph=f['glyf'][name]
     assert glyph.isComposite() and glyph.components[0].glyphName==cmap[ord(text[0])],(path.name,chr(cp),'old base')
     outputs=[]
     for sample in [chr(cp),text]:
      run=subprocess.run(['hb-shape',str(path),'--text='+sample,'--output-format=json'],capture_output=True,text=True,check=True)
      shaped=json.loads(run.stdout);outputs.append([{k:v for k,v in item.items() if k!='cl'} for item in shaped])
     assert outputs[0]==outputs[1],(path.name,chr(cp),'NFC/NFD mismatch')
     accents.append(chr(cp))
   assert len(accents)==9
  unchanged=0
  for name in f.getGlyphOrder():
   if name not in changed:
    assert f['glyf'][name].compile(f['glyf'])==previous['glyf'][name].compile(previous['glyf']),(path.name,name,'unrelated glyph changed')
    unchanged+=1
  run=ots.sanitize(str(path),capture_output=True)
  row=dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),cmap=len(cmap),italicAngle=f['post'].italicAngle,
    accents=accents,unchanged_glyphs=unchanged,minus_restored=True,ots=dict(exit=run.returncode,stdout=run.stdout.decode(errors='replace'),stderr=run.stderr.decode(errors='replace')))
  assert run.returncode==0,(path.name,'OTS',row['ots'])
  records.append(row);print(path.name,'801 cmap; accents',len(accents),'OTS PASS',flush=True)
 assert len(records)==10
 (ROOT/'checks/stage5.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':main()
