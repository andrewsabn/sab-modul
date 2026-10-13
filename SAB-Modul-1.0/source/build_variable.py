"""Fit corresponding quadratic contours to the seven original polygon masters."""
from pathlib import Path
import argparse,hashlib,itertools,json,math
import numpy as np
from fontTools.ttLib import TTFont,newTable
from fontTools.ttLib.tables.ttProgram import Program
from fontTools.misc.transform import Transform
from fontTools.otlLib.builder import buildStatTable
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.designspaceLib import DesignSpaceDocument,AxisDescriptor,SourceDescriptor,InstanceDescriptor
from fontTools.varLib import build as build_vf

ROOT=Path(__file__).resolve().parents[1]
STYLES={'Thin':200,'Light':300,'Regular':400,'Medium':500,'SemiBold':600,'Bold':700,'Black':900}
TOLERANCE=.8

def rings(glyph):
 result=[];start=0
 for end in glyph.endPtsOfContours:
  result.append(np.asarray(glyph.coordinates[start:end+1],dtype=float));start=end+1
 return result

def signature(points):
 nxt=np.roll(points,-1,axis=0)
 area=np.sum(points[:,0]*nxt[:,1]-points[:,1]*nxt[:,0])/2
 return np.r_[(np.min(points,axis=0)+np.max(points,axis=0))/2,np.ptp(points,axis=0),math.copysign(math.sqrt(abs(area)),area)]

class Ring:
 def __init__(self,points):
  self.points=np.vstack([points,points[0]])
  distances=np.linalg.norm(np.diff(self.points,axis=0),axis=1)
  assert np.all(distances>0),'Repeated polygon vertex'
  self.knots=np.r_[0,np.cumsum(distances)]/sum(distances)
  self.phase=0
  self.mapping=None
 def corners(self,legacy=False):
  p=self.points[:-1];a=p-np.roll(p,1,axis=0);b=np.roll(p,-1,axis=0)-p
  immediate=np.arctan2(a[:,0]*b[:,1]-a[:,1]*b[:,0],np.sum(a*b,axis=1))
  long_edges=(np.linalg.norm(a,axis=1)>=4)&(np.linalg.norm(b,axis=1)>=4)
  if legacy:
   self.turns=immediate
   return np.where(long_edges&(np.abs(immediate)>.55))[0]
  # Measure the turn over four units; tiny rounded polygon edges are not reliable tangents.
  dt=4/np.linalg.norm(np.diff(self.points,axis=0),axis=1).sum();t=self.knots[:-1]
  before=np.stack([np.interp((t-dt)%1,self.knots,self.points[:,i]) for i in [0,1]],axis=-1)
  after=np.stack([np.interp((t+dt)%1,self.knots,self.points[:,i]) for i in [0,1]],axis=-1)
  a=p-before;b=after-p
  self.turns=np.arctan2(a[:,0]*b[:,1]-a[:,1]*b[:,0],np.sum(a*b,axis=1))
  return np.where((long_edges|(np.abs(self.turns)>.7))&(np.abs(immediate)>.55))[0]
 def at(self,t):
  t=np.asarray(t)
  if self.mapping is not None:t=np.interp(t,*self.mapping)
  t=np.mod(t+self.phase,1)
  return np.stack([np.interp(t,self.knots,self.points[:,i]) for i in [0,1]],axis=-1)
 def vertices(self):
  t=np.mod(self.knots[:-1]-self.phase,1)
  if self.mapping is not None:t=np.interp(t,self.mapping[1],self.mapping[0])
  return t
 def normalized(self,t):
  return (self.at(t)-(np.min(self.points,axis=0)+np.max(self.points,axis=0))/2)/np.maximum(np.ptp(self.points,axis=0),1)
 def align(self,reference):
  ts=np.arange(256)/256;ref=reference.normalized(ts)
  samples=self.normalized(ts)
  best=min(range(256),key=lambda k:np.sum((np.roll(samples,-k,axis=0)-ref)**2))/256
  lo,hi=best-1/256,best+1/256
  for _ in range(18):
   a,b=(2*lo+hi)/3,(lo+2*hi)/3
   if np.sum((self.normalized(ts+a)-ref)**2)<np.sum((self.normalized(ts+b)-ref)**2):hi=b
   else:lo=a
  self.phase=(lo+hi)/2

def align_corners(group,legacy=False):
 corners=[r.corners(legacy) for r in group]
 if not all(len(c) for c in corners):return
 normalized=[(r.points[c]-(np.min(r.points,axis=0)+np.max(r.points,axis=0))/2)/np.maximum(np.ptp(r.points,axis=0),1) for r,c in zip(group,corners)]
 def anchor_cost(mi,i):
  r=group[mi];expected=(r.phase+group[2].knots[corners[2][i]])%1
  dt=np.abs(r.knots[corners[mi]]-expected);dt=np.minimum(dt,1-dt)
  wrong_turn=np.sign(r.turns[corners[mi]])!=np.sign(group[2].turns[corners[2][i]])
  return np.sum((normalized[mi]-normalized[2][i])**2,axis=1)+4*dt**2+wrong_turn
 anchor=min(range(len(corners[2])),key=lambda i:max(np.min(anchor_cost(mi,i)) for mi in range(len(group))))
 # An unmatched anchor can rotate a counter by half a turn. Keep arc alignment
 # when matching costs more than dropping both landmarks in the sequence fit.
 if max(np.min(anchor_cost(mi,anchor)) for mi in range(len(group)))>.08:return
 phases=[r.phase for r in group]
 def correspondence_error():
  samples=[r.normalized(np.linspace(0,1,257)) for r in group]
  return max(float(np.max(np.linalg.norm(a-b,axis=1))) for a,b in zip(samples,samples[1:]))
 baseline_error=correspondence_error()
 if not legacy and len(set(len(c) for c in corners))==1:
  reference=group[2];reference.phase=reference.knots[corners[2][0]]
  ts=np.r_[np.mod(reference.knots[corners[2]]-reference.phase,1),1]
  for mi,r in enumerate(group):
   shift=min(range(len(corners[mi])),key=lambda k:np.sum((np.roll(normalized[mi],-k,axis=0)-normalized[2])**2)+np.sum(np.sign(np.roll(r.turns[corners[mi]],-k))!=np.sign(reference.turns[corners[2]])))
   ordered=np.roll(corners[mi],-shift);r.phase=r.knots[ordered[0]]
   native=np.r_[np.mod(r.knots[ordered]-r.phase,1),1]
   r.mapping=(ts,native)
  if correspondence_error()<=baseline_error+1/128:return
  for r,phase in zip(group,phases):r.phase=phase;r.mapping=None
  return align_corners(group,legacy=True)
 shifts=[int(np.argmin(anchor_cost(mi,anchor))) for mi in range(len(group))]
 reference=group[2];cp=np.roll(corners[2],-anchor)
 reference.phase=reference.knots[cp[0]]
 ts=np.r_[np.mod(reference.knots[cp]-reference.phase,1),1]
 target=reference.normalized(ts[:-1])
 for mi,r in enumerate(group):
  if mi==2:continue
  candidate=normalized[mi]
  shift=shifts[mi]
  candidate=np.roll(candidate,-shift,axis=0)
  ordered=np.roll(corners[mi],-shift)
  r.phase=r.knots[ordered[0]]
  native=np.r_[np.mod(r.knots[ordered]-r.phase,1),1]
  assert np.all(np.diff(native)>0),'Corner order reversed'
  # Sequence alignment keeps shared corners paired when a rounded join gains or loses vertices.
  n,m=len(target)-1,len(candidate)-1
  cost=np.zeros((n+1,m+1));cost[:,0]=np.arange(n+1)*.04;cost[0,:]=np.arange(m+1)*.04
  moves=np.zeros((n+1,m+1),dtype=np.uint8);moves[1:,0]=1;moves[0,1:]=2
  for i in range(1,n+1):
   for j in range(1,m+1):
    wrong_turn=np.sign(reference.turns[cp[i]])!=np.sign(r.turns[ordered[j]])
    choices=[cost[i-1,j-1]+np.sum((target[i]-candidate[j])**2)+4*(ts[i]-native[j])**2+wrong_turn,cost[i-1,j]+.04,cost[i,j-1]+.04]
    moves[i,j]=np.argmin(choices);cost[i,j]=min(choices)
  i,j=n,m;pairs=[]
  while i or j:
   move=moves[i,j]
   if move==0:pairs.append((i,j));i-=1;j-=1
   elif move==1:i-=1
   else:j-=1
  pairs=[(0,0)]+list(reversed(pairs))+[(len(target),len(candidate))]
  r.mapping=(np.array([ts[i] for i,j in pairs]),np.array([native[j] for i,j in pairs]))
 reference.mapping=(ts,ts)
 # A missing terminal corner must not warp the remaining arc between masters.
 if correspondence_error()>2*baseline_error+1/128:
  for r,phase in zip(group,phases):r.phase=phase;r.mapping=None
  if not legacy:align_corners(group,legacy=True)

def quadratic(a,c,b,u):
 u=np.asarray(u)[:,None]
 return (1-u)**2*a+2*u*(1-u)*c+u*u*b

def closest_parameters(a,c,b,points,u):
 u=u.copy()
 for _ in range(6):
  delta=quadratic(a,c,b,u)-points
  derivative=2*((1-u[:,None])*(c-a)+u[:,None]*(b-c))
  denominator=np.sum(derivative**2+delta*2*(a-2*c+b),axis=1)
  step=np.divide(np.sum(delta*derivative,axis=1),denominator,out=np.zeros_like(u),where=np.abs(denominator)>1e-9)
  u=np.clip(u-step,0,1)
 return u

def fit_group(group):
 """Use common segment boundaries; every master must satisfy the same error bound."""
 segments=[];worst=0
 def fit(lo,hi,depth=0):
  nonlocal worst
  assert depth<26,'Quadratic fitting did not converge'
  t=np.linspace(lo,hi,17);u=(t-lo)/(hi-lo)
  ends=[(r.at(lo),r.at(hi)) for r in group]
  controls=[]
  for r,(a,b) in zip(group,ends):
   actual=r.at(t);local=u.copy()
   for _ in range(5):
    weight=2*local*(1-local)
    residual=actual-(1-local[:,None])**2*a-local[:,None]**2*b
    control=np.sum(residual*weight[:,None],axis=0)/max(np.sum(weight**2),1e-12)
    local=closest_parameters(a,control,b,actual,local)
   controls.append(control)
  line_error=quad_error=0;split=(lo+hi)/2
  for r,(a,b),control in zip(group,ends,controls):
   vertices=r.vertices()
   vertices=np.sort(vertices[(vertices>lo)&(vertices<hi)])
   test=np.unique(np.r_[np.linspace(lo,hi,33),vertices,(np.r_[lo,vertices]+np.r_[vertices,hi])/2])
   v=(test-lo)/(hi-lo);actual=r.at(test)
   linear_u=np.clip(np.sum((actual-a)*(b-a),axis=1)/max(float(np.sum((b-a)**2)),1e-12),0,1)
   linear=(1-linear_u[:,None])*a+linear_u[:,None]*b
   q=quadratic(a,control,b,closest_parameters(a,control,b,actual,v))
   line_error=max(line_error,float(np.max(np.linalg.norm(actual-linear,axis=1))))
   errors=np.linalg.norm(actual-q,axis=1);index=np.argmax(errors)
   if errors[index]>quad_error:quad_error=float(errors[index]);split=float(test[index])
   # Also bound excursions of the fitted curve away from the original polygon.
   curve_u=np.linspace(0,1,33);curve=quadratic(a,control,b,curve_u)
   polygon=r.at(np.r_[lo,vertices,hi]);edges=np.diff(polygon,axis=0)
   offset=curve[:,None,:]-polygon[:-1]
   fractions=np.clip(np.sum(offset*edges,axis=2)/np.maximum(np.sum(edges**2,axis=1),1e-12),0,1)
   projections=polygon[:-1]+fractions[:,:,None]*edges
   reverse=np.min(np.linalg.norm(curve[:,None,:]-projections,axis=2),axis=1);index=np.argmax(reverse)
   if reverse[index]>quad_error:quad_error=float(reverse[index]);split=float(lo+curve_u[index]*(hi-lo))
  if min(line_error,quad_error)<=TOLERANCE:
   line=line_error<=TOLERANCE
   segments.append((line,[b for a,b in ends],controls))
   worst=max(worst,line_error if line else quad_error)
  else:
   split=min(hi-(hi-lo)*.1,max(lo+(hi-lo)*.1,split))
   fit(lo,split,depth+1);fit(split,hi,depth+1)
 stops=np.unique(np.r_[0,1,*[r.vertices()[r.corners()] for r in group]]) if any(r.mapping is not None for r in group) else [0,1]
 for lo,hi in zip(stops,stops[1:]):fit(lo,hi)
 return segments,worst

def deduplicate(fonts,glyph_names=None):
 known={};duplicates={}
 for gn in (glyph_names if glyph_names is not None else fonts[0].getGlyphOrder()):
  gs=[f['glyf'][gn] for f in fonts]
  if any(g.numberOfContours<=0 for g in gs):continue
  key=tuple((tuple(g.endPtsOfContours),tuple(g.flags),tuple((x-g.coordinates[0][0],y-g.coordinates[0][1]) for x,y in g.coordinates)) for g in gs)
  if key not in known:known[key]=gn;continue
  base=known[key];duplicates[gn]=base
  for f,g in zip(fonts,gs):
   first=f['glyf'][base].coordinates[0];origin=g.coordinates[0]
   pen=TTGlyphPen(f['glyf']);pen.addComponent(base,(1,0,0,1,origin[0]-first[0],origin[1]-first[1]));f['glyf'][gn]=pen.glyph()
 return duplicates

def compatible(fonts,glyph_names=None):
 full_order=fonts[0].getGlyphOrder();assert all(f.getGlyphOrder()==full_order for f in fonts)
 order=glyph_names if glyph_names is not None else full_order
 duplicates=deduplicate(fonts,glyph_names)
 report={};old_points=new_points=0
 for index,gn in enumerate(order):
  glyphs=[f['glyf'][gn] for f in fonts]
  counts=[g.numberOfContours for g in glyphs]
  assert len(set(counts))==1,(gn,counts)
  if counts[0]<=0:continue
  masters=[rings(g) for g in glyphs];ref=masters[2]
  roles=[tuple(sorted(np.sign(signature(p)[-1]) for p in rs)) for rs in masters]
  assert len(set(roles))==1,(gn,'Outer contours and counters differ between masters',roles)
  # At most seven contours occur here; exhaustive matching avoids another dependency.
  for mi,rs in enumerate(masters):
   if mi==2:continue
   costs=np.array([[np.sum((signature(a)-signature(b))**2) if np.sign(signature(a)[-1])==np.sign(signature(b)[-1]) else np.inf for b in rs] for a in ref])
   matching=min(itertools.permutations(range(len(rs))),key=lambda p:sum(costs[i,j] for i,j in enumerate(p)))
   masters[mi]=[rs[j] for j in matching]
  pens=[TTGlyphPen(None) for _ in fonts];error=0;segment_count=0
  for ri in range(len(ref)):
   group=[Ring(rs[ri]) for rs in masters]
   for mi,r in enumerate(group):
    if mi!=2:r.align(group[2])
   align_corners(group)
   # Preserve two terminal landmarks lost by automatic matching to Regular.
   mono=bool(fonts[0]['post'].isFixedPitch);oblique=bool(fonts[0]['post'].italicAngle)
   anchors=([(529,259,570,473,False)] if gn=='uni00C6' and not mono else
            [(375,-152,371,-167,True),(346,0,288,0,False)] if gn=='uni012F' and mono else [])
   if ri==0 and oblique and anchors:
    ref,black=group[2],group[6];x,y=[a.copy() for a in black.mapping]
    for rx,ry,bx,by,replace in anchors:
     indices=[]
     for ring,point in [(ref,(rx,ry)),(black,(bx,by))]:
      found=np.flatnonzero(np.all(ring.points[:-1]==point,axis=1))
      assert len(found)==1,(gn,'Terminal landmark changed',point)
      indices.append(int(found[0]))
     tx=ref.vertices()[indices[0]];ty=(black.knots[indices[1]]-black.phase)%1
     if replace:
      found=np.flatnonzero(np.isclose(y,ty));assert len(found)==1
      x=np.delete(x,found[0]);y=np.delete(y,found[0])
     at=np.searchsorted(x,tx);x=np.insert(x,at,tx);y=np.insert(y,at,ty)
    assert np.all(np.diff(x)>0) and np.all(np.diff(y)>0),'Terminal mapping reversed'
    black.mapping=(x,y)
   segments,worst=fit_group(group);error=max(error,worst);segment_count+=len(segments)
   for mi,pen in enumerate(pens):
    start=tuple(group[mi].at(0));pen.moveTo(start)
    for si,(line,ends,controls) in enumerate(segments):
     end=start if si==len(segments)-1 else tuple(ends[mi])
     if line:pen.lineTo(end)
     else:pen.qCurveTo(tuple(controls[mi]),end)
    pen.closePath()
  old_points+=len(glyphs[2].coordinates)
  for f,pen in zip(fonts,pens):f['glyf'][gn]=pen.glyph()
  # Separate coincident ogonek points before gvar rounding creates a reverse edge.
  if mono and oblique and gn=='uni012F':
   bold=fonts[5]['glyf'][gn]
   assert tuple(bold.coordinates[29])==tuple(bold.coordinates[30])==(313,-105)
   bold.coordinates[30]=(314,-105)
  new_points+=len(fonts[2]['glyf'][gn].coordinates)
  structures=[(tuple(f['glyf'][gn].endPtsOfContours),tuple(f['glyf'][gn].flags)) for f in fonts]
  assert len(set(structures))==1,(gn,'Fitted structures differ')
  report[gn]={'max_fit_error_units':round(error,4),'segments':segment_count,'original_points':len(glyphs[2].coordinates),'fitted_points':len(fonts[2]['glyf'][gn].coordinates)}
  if index%100==0:print(' fitted',index,'/',len(order),gn,flush=True)
 for f in fonts:
  for gn in order:
   glyph=f['glyf'][gn];glyph.recalcBounds(f['glyf'])
   if hasattr(glyph,'xMin'):f['hmtx'][gn]=(f['hmtx'][gn][0],glyph.xMin)
 return {'original_points_after_deduplication':old_points,'original_points':old_points,'fitted_points':new_points,'deduplicated_glyphs':duplicates,'glyphs':report,'tolerance_units':TOLERANCE}

def flatten_components(font):
 def leaves(gn,transform=Transform()):
  glyph=font['glyf'][gn]
  if not glyph.isComposite():return [(gn,transform)]
  result=[]
  for component in glyph.components:
   base,matrix=component.getComponentInfo()
   result.extend(leaves(base,transform.transform(matrix)))
  return result
 for gn in font.getGlyphOrder():
  glyph=font['glyf'][gn]
  if glyph.isComposite() and any(font['glyf'][c.glyphName].isComposite() for c in glyph.components):
   pen=TTGlyphPen(font['glyf'])
   for base,matrix in leaves(gn):pen.addComponent(base,matrix)
   font['glyf'][gn]=pen.glyph()

def refresh_layout(fonts,inputs,report,previous):
 sources=[TTFont(p) for p in inputs]
 for path,source in zip(inputs,sources):
  old_path=previous/path.name
  assert hashlib.sha256(old_path.read_bytes()).hexdigest()==report['sources'][str(path.relative_to(ROOT))],'Previous source hash differs'
  old=TTFont(old_path)
  assert old.keys()==source.keys() and old.getGlyphOrder()==source.getGlyphOrder(),'Source structure changed'
  for tag in old.keys():
   if tag not in ['GlyphOrder','head','GPOS']:
    assert old[tag].compile(old)==source[tag].compile(source),(path.name,tag,'Non-layout change requires a full rebuild')
  for key,value in vars(old['head']).items():
   if key not in ['checkSumAdjustment','created','modified']:
    assert value==vars(source['head'])[key],(path.name,'head',key)
 for fitted,source in zip(fonts,sources):
  assert fitted.getGlyphOrder()==source.getGlyphOrder()
  fitted['GPOS']=source['GPOS']
 report['layout_refresh']={'previous_sources':report['sources'],'verified_against':str(previous.resolve()),'changed_table':'GPOS','other_source_tables_identical':True}

def build_family(family,slant,reuse=False,layout_from=None):
 folder=ROOT/'source/variable-masters'/('SABModul'+family+slant);folder.mkdir(parents=True,exist_ok=True)
 inputs=[ROOT/'source/masters'/f'SABModul{family}-{style}{slant}.ttf' for style in STYLES]
 hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
 if reuse:
  report=json.loads((folder/'fit-report.json').read_text())
  fonts=[TTFont(folder/(style+'.ttf')) for style in STYLES]
  if layout_from:refresh_layout(fonts,inputs,report,layout_from)
  else:assert report['sources']==hashes,'Compatible masters belong to different source fonts'
 else:
  fonts=[TTFont(p) for p in inputs]
  report=compatible(fonts)
 for font in fonts:flatten_components(font)
 report['sources']=hashes
 (folder/'fit-report.json').write_text(json.dumps(report,indent=2))
 ds=DesignSpaceDocument();axis=AxisDescriptor();axis.name='Weight';axis.tag='wght';axis.minimum=200;axis.default=400;axis.maximum=900;ds.addAxis(axis)
 for (style,weight),font in zip(STYLES.items(),fonts):
  path=folder/f'{style}.ttf';font.save(path)
  source=SourceDescriptor();source.path=str(path);source.name=style;source.familyName='SAB Modul '+family;source.styleName=style+(' Oblique' if slant else '');source.location={'Weight':weight}
  if weight==400:source.copyInfo=source.copyLib=source.copyFeatures=True
  ds.addSource(source)
  instance=InstanceDescriptor();instance.name=source.styleName;instance.familyName=source.familyName;instance.styleName=style+(' Italic' if slant else '');instance.location=source.location.copy();ds.addInstance(instance)
 ds_path=folder/'family.designspace';ds.write(ds_path)
 vf,model,masters=build_vf(ds_path)
 buildStatTable(vf,[{'tag':'wght','name':'Weight','ordering':0,'values':[{'value':w,'name':s,'flags':2 if w==400 else 0} for s,w in STYLES.items()]},
                    {'tag':'ital','name':'Italic','ordering':1,'values':[{'value':1 if slant else 0,'name':'Italic' if slant else 'Roman','flags':0 if slant else 2,**({} if slant else {'linkedValue':1})}]}])
 vf['name'].names=[record for record in vf['name'].names if record.platformID!=1]
 if slant:vf['name'].setName('Regular Italic',17,3,1,0x409)
 vf['name'].setName('SABModul'+family+('Italic' if slant else ''),25,3,1,0x409)
 vf['gasp']=newTable('gasp');vf['gasp'].version=1;vf['gasp'].gaspRange={0xFFFF:0x0F}
 # Dropout control for unhinted variable outlines; this is not stem hinting.
 vf['prep']=newTable('prep');vf['prep'].program=Program()
 vf['prep'].program.fromAssembly(['PUSHW[ ]','511','SCANCTRL[ ]','PUSHB[ ]','4','SCANTYPE[ ]'])
 vf['maxp'].maxStackElements=max(vf['maxp'].maxStackElements,1)
 out=ROOT/'VF';out.mkdir(exist_ok=True)
 filename='SABModul'+family+('-Italic' if slant else '')+'[wght]'
 vf.save(out/(filename+'.ttf'));vf.flavor='woff2';vf.save(out/(filename+'.woff2'))
 print(filename,'points',report['original_points'],'to',report['fitted_points'],'WOFF2',(out/(filename+'.woff2')).stat().st_size,flush=True)

if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--family',choices=['Sans','Mono']);parser.add_argument('--slant',choices=['Roman','Oblique']);parser.add_argument('--reuse-compatible',action='store_true');parser.add_argument('--refresh-layout-from',type=Path);args=parser.parse_args()
 assert not args.refresh_layout_from or args.reuse_compatible,'Layout refresh requires --reuse-compatible'
 for family in [args.family] if args.family else ['Sans','Mono']:
  for slant in ([args.slant] if args.slant else ['Roman','Oblique']):build_family(family,'' if slant=='Roman' else slant,args.reuse_compatible,args.refresh_layout_from)
