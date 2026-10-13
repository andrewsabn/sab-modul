from pathlib import Path
import json,sys
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
from shapely.geometry import LinearRing
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]
failures=[]
for folder in ['TTF','OTF','WOFF2']:
 for p in sorted((root/folder).glob('*.'+folder.lower())):
  f=TTFont(p);gs=f.getGlyphSet()
  for name in f.getGlyphOrder():
   pen=DecomposingRecordingPen(gs);gs[name].draw(pen);ring=[]
   for op,args in pen.value:
    if op=='moveTo':ring=[args[0]]
    elif op=='lineTo':ring.extend(args)
    elif op in ['closePath','endPath']:
     if len(ring)<3 or not LinearRing(ring).is_simple:failures.append([p.name,name])
     ring=[]
    else:raise AssertionError((p.name,name,op))
print(json.dumps(failures,indent=2))
assert not failures,'Quantized contours contain self intersections'
print('All exported contours are simple in TTF, OTF and WOFF2')
