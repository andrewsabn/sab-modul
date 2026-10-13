import build
from shapely.geometry import Point, LineString

def check():
 failures=[]
 for mono in (False,True):
  data=build.alphabet('SAB Modul',mono)
  for c in 'yу':
   paths=data[c][1]
   if Point(paths[0][-1]).distance(LineString(paths[1]))>.01:failures.append(f'{mono} {c}: branch extends beyond tail junction')
  for style,(_,t) in build.WEIGHTS.items():
   for italic in (False,True):
    for c in 'oоеeсcOО':
     g,_,_=build.geometry(*data[c],'SAB Modul',mono,t,italic,c)
     top=700 if c.isupper() else 500
     if not (-10<g.bounds[1]<-5 and top+5<g.bounds[3]<top+10):failures.append(f'{mono} {style} {italic} {c}: no optical overshoot {g.bounds}')
    if not mono and style=='Regular' and not italic:
     for c in 'нпиш':
      g,a,_=build.geometry(*data[c],'SAB Modul',mono,t,False,c)
      if a-(g.bounds[2]-g.bounds[0])<110:failures.append(f'{c}: tight stem sidebearings')
 assert not failures, '\n'.join(failures)
 print('Branch joins, optical overshoot and Regular stem spacing: PASS')
if __name__=='__main__':check()
