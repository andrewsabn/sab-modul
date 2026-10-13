import sys,copy,json
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
sys.path.insert(0,'source');sys.path.append('source/upstream')
from package_web import make_subset,BOX
from verify_variable import boundary
from verify_operator_strokes import SAMPLES,measure
from verify_code_variable import contour_errors
styles={300:'Light',400:'Regular',500:'Medium',600:'SemiBold',700:'Bold'}
for italic in [False,True]:
 name='SABModulCode'+('-Italic' if italic else '')+'[wght]';base=Path('checks/fable/refit-VF')/(name+'.ttf');orig=TTFont(base);f=TTFont(base);cm=f.getBestCmap();preserve={cm[ord(c)] for c in 'Hlx'+''.join(SAMPLES)}|{n for n in f.getGlyphOrder() if n.startswith('code.op')}
 if italic:preserve.update({'uni0061','uni0430','uni02DB'})
 else:preserve.add('uni00B8')  # IUP creates rounded microloops at intermediate weights.
 eligible={n for n in f['gvar'].variations if n not in preserve and f['glyf'][n].numberOfContours>0}
 history=[]
 for tol in [2.0,1.5,1.0,0.5]:
  for n in eligible:
   f['gvar'].variations[n]=copy.deepcopy(orig['gvar'].variations[n])
   if tol==0.5:continue
   coords,control=f['glyf']._getCoordinatesAndControls(n,f['hmtx'].metrics)
   for v in f['gvar'].variations[n]:
    v.calcInferredDeltas(coords,control.endPts);v.roundDeltas();v.optimize(coords,control.endPts,tolerance=tol)
  temp=Path('checks/fable')/(name+'-iup-temp.ttf');f.save(temp);f=TTFont(temp);bad=set();worst={};crossings=[]
  for w in range(300,701,50):
   inst=instantiateVariableFont(f,{'wght':w});reference=TTFont('source/stage6-masters/SABModulCode-'+styles[w]+('Italic' if italic else '')+'.ttf') if w in styles else instantiateVariableFont(orig,{'wght':w})
   stroke_bad=[r for r in measure(inst,w) if not r['pass_']]
   assert not stroke_bad,(name,w,stroke_bad)
   for error in contour_errors(inst):
    bad.add(error['glyph']);crossings.append({'weight':w,**error})
   ga=reference.getGlyphSet();gb=inst.getGlyphSet()
   for n in reference.getGlyphOrder():
    a=boundary(ga,n);b=boundary(gb,n)
    if a.is_empty:assert b.is_empty;continue
    distance=a.hausdorff_distance(b)+0.01;worst[n]=max(worst.get(n,0),distance)
    if distance>2:bad.add(n)
  print(name,'IUP',tol,'geometry/contour failures',len(bad),flush=True)
  history.append(dict(iup_tolerance=tol,over_limit=sorted(bad),self_intersections=crossings,maximum=max(worst.values())))
  if not bad:break
  eligible=set(bad)
  for n in list(bad):
   g=f['glyf'][n]
   if g.isComposite():eligible.update(c.glyphName for c in g.components)
  eligible={n for n in eligible if f['glyf'][n].numberOfContours>0 and n not in preserve}
 assert not bad, sorted(bad)
 folder=Path('checks/fable/optimized-VF');folder.mkdir(exist_ok=True);p=folder/(name+'.ttf');f.save(p);f.flavor='woff2';f.save(p.with_suffix('.woff2'))
 o=folder/(name+'-main.woff2');make_subset(p,set(cm)-BOX,o,[cm[x]+'.pnum' for x in range(48,58)]);print('main_bytes',o.stat().st_size,flush=True)
 (folder/(name+'.json')).write_text(json.dumps({'history':history,'final_maximum':max(worst.values()),'bytes':o.stat().st_size},indent=2))
