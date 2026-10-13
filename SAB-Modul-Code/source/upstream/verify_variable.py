from pathlib import Path
import argparse,hashlib,json,math,tempfile
import numpy as np
from shapely.geometry import MultiLineString
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from fontTools.varLib.instancer import instantiateVariableFont
import build as static_builder

ROOT=Path(__file__).resolve().parents[1]

class OutlinePen(BasePen):
 def __init__(self,glyphset,tolerance=0.25):super().__init__(glyphset);self.rings=[];self.points=[];self.tolerance=tolerance
 def _moveTo(self,p):self.points=[p]
 def _lineTo(self,p):self.points.append(p)
 def _qCurveToOne(self,c,b):
  a=np.asarray(self._getCurrentPoint());c=np.asarray(c);b=np.asarray(b)
  steps=max(4,math.ceil(math.sqrt(np.linalg.norm(a-2*c+b)/(4*self.tolerance))))
  for t in np.linspace(0,1,steps+1)[1:]:self.points.append(tuple((1-t)**2*a+2*t*(1-t)*c+t*t*b))
 def _closePath(self):
  if len(self.points)>1:self.rings.append(self.points+[self.points[0]])
  self.points=[]
 def _endPath(self):self._closePath()

def boundary(glyphset,name,tolerance=0.005):
 pen=OutlinePen(glyphset,tolerance);glyphset[name].draw(pen)
 return MultiLineString(pen.rings)

def compare(a,b):
 ga=a.getGlyphSet();gb=b.getGlyphSet();distances={};advances={}
 assert a.getBestCmap()==b.getBestCmap(),'Character maps differ'
 for name in a.getGlyphOrder():
  first=boundary(ga,name);second=boundary(gb,name)
  if first.is_empty or second.is_empty:assert first.is_empty==second.is_empty,name
  else:distances[name]=float(first.hausdorff_distance(second))+0.01  # Sum of both curve-flattening error bounds.
  advances[name]=abs(a['hmtx'][name][0]-b['hmtx'][name][0])
 return {'curve_flattening_error_per_outline':0.005,'distance_includes_error_margin':0.01,'max_outline_distance_units':max(distances.values()),'worst_outlines':sorted(distances.items(),key=lambda v:v[1],reverse=True)[:20],'max_advance_difference_units':max(advances.values())}

def verify(family,slant,intermediate=True):
 filename='SABModul'+family+('-Italic' if slant else '')+'[wght]'
 path=ROOT/'VF'/(filename+'.ttf');vf=TTFont(path)
 web=TTFont(path.with_suffix('.woff2'))
 web_tables={tag:vf[tag].compile(vf)==web[tag].compile(web) for tag in ['cmap','hmtx','fvar','gvar','GPOS','GSUB']}
 assert all(web_tables.values()),('WOFF2 changes layout or variation tables',web_tables)
 axis=vf['fvar'].axes;assert len(axis)==1 and (axis[0].axisTag,axis[0].minValue,axis[0].defaultValue,axis[0].maxValue)==('wght',200,400,900)
 assert 'gvar' in vf and any(vf['gvar'].variations.values()),'No actual outline variation'
 records=[]
 for style,(weight,thickness) in static_builder.WEIGHTS.items():
  source=ROOT/'source/masters'/f'SABModul{family}-{style}{slant}.ttf'
  instance=instantiateVariableFont(vf,{'wght':weight},inplace=False)
  record={'weight':weight,'kind':'master','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),**compare(TTFont(source),instance)}
  records.append(record);print(filename,weight,round(record['max_outline_distance_units'],3),'units',flush=True)
 if intermediate:
  original_root=static_builder.ROOT
  try:
   with tempfile.TemporaryDirectory() as tmp:
    static_builder.ROOT=Path(tmp)
    for weight in [250,350,450,550,650,800]:
     thickness=float(np.interp(weight,[v[0] for v in static_builder.WEIGHTS.values()],[v[1] for v in static_builder.WEIGHTS.values()]))
     result=static_builder.build('SAB Modul',family=='Mono','Regular',weight,thickness,bool(slant),('ttf',))
     direct=TTFont(Path(tmp)/'TTF'/(result['file']+'.ttf'))
     instance=instantiateVariableFont(vf,{'wght':weight},inplace=False)
     record={'weight':weight,'kind':'intermediate','source':'same parametric drawing at interpolated stem thickness',**compare(direct,instance)}
     records.append(record);print(filename,weight,round(record['max_outline_distance_units'],3),'units (intermediate)',flush=True)
  finally:static_builder.ROOT=original_root
 report={'file':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'woff2_sha256':hashlib.sha256(path.with_suffix('.woff2').read_bytes()).hexdigest(),'woff2_bytes':path.with_suffix('.woff2').stat().st_size,'woff2_tables_match_ttf':web_tables,'method':'Hausdorff distance between all glyph contours; quadratic flattening error <= 0.25 units; compared to original drawing, including intermediate weights','records':records,'visual_acceptance':False}
 (ROOT/'VF'/(filename+'.verification.json')).write_text(json.dumps(report,indent=2))
 return report

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--family',choices=['Sans','Mono']);p.add_argument('--slant',choices=['Roman','Oblique']);p.add_argument('--masters-only',action='store_true');args=p.parse_args()
 for family in [args.family] if args.family else ['Sans','Mono']:
  for slant in [args.slant] if args.slant else ['Roman','Oblique']:verify(family,'' if slant=='Roman' else slant,not args.masters_only)
