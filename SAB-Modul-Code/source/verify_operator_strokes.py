"""Measure local operator strokes by exact quadratic intersections, away from joins."""
import argparse,hashlib,json,math
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from verify_code import bbox,intersections
from code_symbols import STEMS
SAMPLES={'+':[((300,120),(0,1)),((140,270),(1,0))],'−':[((300,270),(1,0))],'=':[((300,380),(1,0)),((300,160),(1,0))],'/':[((300,330),(290,860))],'\\':[((300,330),(290,-860))],'<':[((385,442.5),(-340,-230)),((385,97.5),(340,-230))],'>':[((215,442.5),(340,-230)),((215,97.5),(-340,-230))],'×':[((219,351),(270,-270)),((219,189),(270,270))],'^':[((188,449),(160,330)),((412,449),(-160,330))],'#':[((185,0),(0,1)),((415,540),(0,1)),((300,150),(1,0)),((300,390),(1,0))],'~':[((300,270),(390,-180*math.pi))]}
for k in range(5):
 a=-math.pi/2+k*2*math.pi/5;SAMPLES.setdefault('*',[]).append(((300+170*math.cos(a),270+170*math.sin(a)),(math.cos(a),math.sin(a))))

for char,point in [('!',(300,400)),('?',(300,300)),('¦',(300,100))]:SAMPLES[char]=[(point,(0,1))]
SAMPLES['%']=[((300,350),(380,610))]
SAMPLES["'"]=[((300,600),(0,1))]
SAMPLES['"']=[((200,600),(0,1)),((400,600),(0,1))]
SAMPLES['`']=[((300,600),(-210,-260))]
def normal(font,name,point,tangent):
 tx,ty=tangent; length=math.hypot(tx,ty);tx/=length;ty/=length
 xp=ty*point[0]-tx*point[1];yp=tx*point[0]+ty*point[1]
 spans=intersections(font,name,yp,(ty,tx,-tx,ty,0,0))
 left,right=min(spans,key=lambda ab:abs(sum(ab)/2-xp))
 return right-left

def measure(font,weight):
 cm=font.getBestCmap();it=bool(font['post'].italicAngle);slope=math.tan(math.radians(10)) if it else 0
 lo=max(w for w in STEMS if w<=weight);hi=min(w for w in STEMS if w>=weight)
 stem=STEMS[lo] if lo==hi else STEMS[lo]+(STEMS[hi]-STEMS[lo])*(weight-lo)/(hi-lo)
 rows=[]
 for char,points in SAMPLES.items():
  b=bbox(font,cm[ord(char)]);shift=-slope*((b[1]+b[3])/2-270) if it else 0
  factor=1.2 if char in "'\"`!?¦" else 1.1
  for point,tangent in points:
   p=(point[0]+slope*(point[1]-270)+shift,point[1]);t=(tangent[0]+slope*tangent[1],tangent[1])
   value=normal(font,cm[ord(char)],p,t);target=stem*factor
   rows.append(dict(char=char,point=p,normal_width=value,target=target,pass_=abs(value-target)<=1))
 return rows

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--font-dir',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();records=[]
 for path in sorted(a.font_dir.glob('*.ttf')):
  f=TTFont(path);weights=list(range(300,701,50)) if 'fvar' in f else [f['OS/2'].usWeightClass]
  for w in weights:
   instance=instantiateVariableFont(f,{'wght':w},inplace=False) if 'fvar' in f else f
   rows=measure(instance,w);bad=[r for r in rows if not r['pass_']]
   records.append(dict(file=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),weight=w,samples=rows))
   print(path.name,w,'FAIL' if bad else 'PASS',[(r['char'],round(r['normal_width'],4),r['target']) for r in bad],flush=True)
 ok=bool(records) and all(r['pass_'] for row in records for r in row['samples'])
 a.output.write_text(json.dumps(dict(status='PASS' if ok else 'FAIL',tolerance=1,records=records),indent=2)+'\n')
 raise SystemExit(0 if ok else 1)
