"""Check actual VF endpoints, intermediate widths, stems, shaping and WOFF2 tables."""
import argparse, hashlib, io, json, sys
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
import ots
import uharfbuzz as hb
from verify_code import bbox, stroke_widths, intersections
from code_symbols import STEMS
from code_operators import OPERATORS
ROOT=Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT/'source/upstream'))
from verify_variable import compare, OutlinePen
import numpy as np
from shapely.geometry import LineString, Polygon
from shapely.validation import explain_validity
STYLES={300:'Light',400:'Regular',500:'Medium',600:'SemiBold',700:'Bold'}
CRITICAL_CONTOURS=['uni0061','uni0430','uni02DB','uni0328','uni2116','uni00B8','uni0327','uni007E','code.op15.0','code.op15.1','code.op4.0','code.op4.1']


class ContourPen(OutlinePen):
 def _qCurveToOne(self,c,b):
  a=np.asarray(self._getCurrentPoint());c=np.asarray(c);b=np.asarray(b)
  t=np.linspace(0,1,257)[1:,None]
  self.points.extend(map(tuple,(1-t)**2*a+2*t*(1-t)*c+t*t*b))
 def _closePath(self):
  points=[]
  for p in self.points:
   if not points or max(abs(p[i]-points[-1][i]) for i in (0,1))>1e-9:points.append(p)
  if len(points)>1:
   if max(abs(points[-1][i]-points[0][i]) for i in (0,1))<=1e-9:points[-1]=points[0]
   else:points.append(points[0])
   self.rings.append(points)
  self.points=[]


def contour_errors(font, names=None):
 glyphset=font.getGlyphSet();errors=[]
 for name in font.getGlyphOrder() if names is None else names:
  pen=ContourPen(glyphset);glyphset[name].draw(pen)
  for i,ring in enumerate(pen.rings):
   if not LineString(ring).is_simple:
    errors.append({'glyph':name,'contour':i,'error':explain_validity(Polygon(ring))})
 return errors


def critical_axis_errors(font, weights=range(300,701)):
 errors=[]
 for weight in weights:
  inst=instantiateVariableFont(font,{'wght':weight},inplace=False)
  for rounded in [False,True]:
   if rounded:
    for name in inst.getGlyphOrder():
     g=inst['glyf'][name]
     if g.numberOfContours>0:g.coordinates.toInt()
   errors.extend({'weight':weight,'rounded':rounded,**e} for e in contour_errors(inst,CRITICAL_CONTOURS))
   bars=intersections(inst,'code.op4.0',300,(0,1,1,0,0,0))
   if len(bars)!=2 or bars[1][0]-bars[0][1]<80:
    errors.append({'weight':weight,'rounded':rounded,'glyph':'code.op4.0','error':'Double arrow gap below80 units','bars':bars})
 return errors


def main(font_dir=ROOT/'release/SAB-Modul-Code-1.0/VF', output=ROOT/'checks/variable-verification.json', source_dir=ROOT/'source/stage6-masters'):
 records=[]
 for italic in [False,True]:
  path=font_dir/('SABModulCode'+('-Italic' if italic else '')+'[wght].ttf')
  font=TTFont(path);web=TTFont(path.with_suffix('.woff2'));cmap=font.getBestCmap()
  axis=font['fvar'].axes
  assert len(axis)==1 and (axis[0].axisTag,axis[0].minValue,axis[0].defaultValue,axis[0].maxValue)==('wght',300,400,700)
  assert len(cmap)==829 and any(font['gvar'].variations.values())
  assert all(font[t].compile(font)==web[t].compile(web) for t in ['cmap','hmtx','fvar','gvar','GPOS','GSUB'])
  assert any(n.platformID==1 for n in font['name'].names)
  row={'file':path.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'cmap':len(cmap),'weights':[],'ots':[]}
  for file in [path,path.with_suffix('.woff2')]:
   run=ots.sanitize(str(file),capture_output=True)
   row['ots'].append(dict(file=file.name,exit=run.returncode,stdout=run.stdout.decode(),stderr=run.stderr.decode()))
   assert run.returncode==0,row['ots'][-1]
  face=hb.Font(hb.Face(path.read_bytes()));face.scale=(1000,1000)
  def shaped(text,weight,features):
   face.set_variations({'wght':weight});b=hb.Buffer();b.add_str(text);b.guess_segment_properties();hb.shape(face,b,features)
   return [(g.codepoint,p.x_advance,p.y_advance,p.x_offset,p.y_offset) for g,p in zip(b.glyph_infos,b.glyph_positions)]
  for weight in range(300,701,50):
   inst=instantiateVariableFont(font,{'wght':weight},inplace=False)
   bad_contours=contour_errors(inst)
   assert not bad_contours,(path.name,weight,'self-intersecting contours',bad_contours)
   assert {a for a,b in inst['hmtx'].metrics.values()}=={0,600}
   assert (inst['hhea'].ascent,inst['hhea'].descent,inst['hhea'].lineGap)==(1000,-300,0)
   assert bbox(inst,cmap[ord('x')])[3]==540 and bbox(inst,cmap[ord('H')])[3]==700
   lower=max(w for w in STEMS if w<=weight);upper=min(w for w in STEMS if w>=weight)
   target=STEMS[lower] if lower==upper else STEMS[lower]+(STEMS[upper]-STEMS[lower])*(weight-lower)/(upper-lower)
   stems=stroke_widths(inst,cmap[ord('H')],175)+stroke_widths(inst,cmap[ord('l')],350)
   stem_pass=all(abs(s-target)<=1 for s in stems)
   for text in OPERATORS+['iiiiiiiiii','mmmmmmmmmm','и'*80,'a\u0301','а\u0301','www fi ff']:
    off=shaped(text,weight,{'calt':False});on=shaped(text,weight,{'calt':True});restored=shaped(text,weight,{'calt':True,'ss10':True})
    assert off==restored and sum(x[1] for x in off)==sum(x[1] for x in on),(weight,text)
    if text in OPERATORS:assert len(on)==len(text) and all(x[1]==600 for x in on)
   item={'weight':weight,'stem_target':target,'stems':stems,'advance':600,'width_80_at_14px':672,'shaping':'PASS','stem_tolerance_units':1,'stem_pass':stem_pass}
   item['self_contours']={'status':'PASS','glyphs':len(inst.getGlyphOrder()),'quadratic_subdivisions':256,'coincident_epsilon_units':1e-9}
   if weight in STYLES:
    source=source_dir/('SABModulCode-'+STYLES[weight]+('Italic' if italic else '')+'.ttf')
    item['source_sha256']=hashlib.sha256(source.read_bytes()).hexdigest()
    item.update(compare(TTFont(source),inst))
    assert item['max_outline_distance_units']<=2,(path.name,weight,item)
    assert item['max_advance_difference_units']==0
   row['weights'].append(item)
   print(path.name,weight,'PASS' if stem_pass else 'FAIL stem tolerance',stems,flush=True)
  records.append(row)
  critical=critical_axis_errors(font)
  row['critical_axis']={'weights':[300,700],'step':1,'glyphs':CRITICAL_CONTOURS,'roundings':[False,True],'errors':critical}
  status='FAIL' if critical or any(not w['stem_pass'] for r in records for w in r['weights']) else ('PASS' if len(records)==2 else 'IN_PROGRESS')
  output.write_text(json.dumps({'status':status,'files':records},indent=2)+'\n')
  assert not critical,(path.name,'critical contours across integer axis',critical)
 assert len(records)==2
 return int(any(not w['stem_pass'] for r in records for w in r['weights']))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--font-dir',type=Path,default=ROOT/'release/SAB-Modul-Code-1.0/VF');p.add_argument('--output',type=Path,default=ROOT/'checks/variable-verification.json');p.add_argument('--source-dir',type=Path,default=ROOT/'source/stage6-masters');a=p.parse_args();raise SystemExit(main(a.font_dir,a.output,a.source_dir))
