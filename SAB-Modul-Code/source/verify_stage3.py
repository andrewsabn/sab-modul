"""Verify actual stage-3 cmap, widths, terminal edge alignment and OTS."""
import hashlib, json, unicodedata
from pathlib import Path
from fontTools.ttLib import TTFont
import ots
from verify_code import intersections
ROOT=Path(__file__).resolve().parents[1]
KEYS='⌘⌥⇧⌃⏎⌫␣'
MARKERS='✓✗•◦▪▫○●◆◇▶▼▲◀'
NAMED_MATH='≤≥≠≈∞√∑∆∂πµλ'
REQUIRED={
 'box':set(range(0x2500,0x2580)), 'blocks':set(range(0x2580,0x25A0)),
 'powerline':set(range(0xE0A0,0xE0A4))|set(range(0xE0B0,0xE0C9)),
 'arrows':set(range(0x2190,0x219A))|set(range(0x21D0,0x21DA)),
 'greek':set(range(0x3B1,0x3CA))|set(map(ord,'ΔΣΩΠΛΦΨ')),
 'keys':set(map(ord,KEYS)), 'markers':set(map(ord,MARKERS)),
 'named_math':set(map(ord,NAMED_MATH)),
}


def main(font_dir=ROOT/'source/stage3-masters', output=ROOT/'checks/stage3.json'):
 records=[]
 old=TTFont(ROOT/'source/code-masters/SABModulCode-Regular.ttf').getBestCmap()
 for path in sorted(font_dir.glob('*.ttf')):
  f=TTFont(path);cmap=f.getBestCmap();cp=set(cmap)
  missing={group:[f'U+{c:04X}' for c in sorted(req-cp)] for group,req in REQUIRED.items()}
  assert not any(missing.values()),(path.name,missing)
  assert set(old)<=cp,(path.name,'original coverage lost')
  mathset=sorted(cp&set(range(0x2200,0x2300)))
  assert len(mathset)>=40,(path.name,'math coverage',len(mathset))
  assert all(a in (0,600) for a,b in f['hmtx'].metrics.values())
  edge={}
  for char in '─━═':
   g=f['glyf'][cmap[ord(char)]];assert g.xMin==0 and g.xMax==600,(path.name,char,'horizontal edges')
   edge[char]=dict(xMin=g.xMin,xMax=g.xMax)
  for char in '│┃║':
   g=f['glyf'][cmap[ord(char)]];assert g.yMin<=-400 and g.yMax>=1100,(path.name,char,'vertical edges')
   edge[char]=dict(yMin=g.yMin,yMax=g.yMax)
  run=ots.sanitize(str(path),capture_output=True)
  stdout=run.stdout.decode(errors='replace') if isinstance(run.stdout,bytes) else run.stdout
  error=run.stderr.decode(errors='replace') if isinstance(run.stderr,bytes) else run.stderr
  assert run.returncode==0,(path.name,error)
  record=dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),cmap=len(cp),
    coverage={k:len(v) for k,v in REQUIRED.items()},missing=missing,math=[f'U+{c:04X} {unicodedata.name(chr(c))}' for c in mathset],
    terminal_edges=edge,ots=dict(exit=run.returncode,stdout=stdout,stderr=error),status='PASS')
  records.append(record);print(path.name,len(cp),'encoded',len(mathset),'math OTS PASS',flush=True)
 assert len(records)==10
 output.write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':
 import argparse
 parser=argparse.ArgumentParser();parser.add_argument('--font-dir',type=Path,default=ROOT/'source/stage3-masters');parser.add_argument('--output',type=Path,default=ROOT/'checks/stage3.json');args=parser.parse_args();main(args.font_dir,args.output)
