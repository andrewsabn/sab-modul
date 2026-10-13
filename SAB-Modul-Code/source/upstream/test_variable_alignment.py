"""Regression: a disappearing corner must not rotate the section-sign counter."""
import numpy as np
import hashlib,tempfile
from pathlib import Path
from fontTools.ttLib import TTFont
from build_variable import ROOT,STYLES,Ring,rings,align_corners,deduplicate,flatten_components,refresh_layout
from verify_variable import boundary
import build

def test_mono_contour_roles():
 data=build.alphabet('SAB Modul',True)
 for weight in [200,250,300,350,400,450,500,550,600,650,700,800,900]:
  thickness=float(np.interp(weight,[v[0] for v in build.WEIGHTS.values()],[v[1] for v in build.WEIGHTS.values()]))
  for oblique in [False,True]:
   for c in '0®':
    w,paths=data[c];g,_,_=build.geometry(w,paths,'SAB Modul',True,thickness,oblique,c)
    pieces=list(g.geoms) if hasattr(g,'geoms') else [g]
    assert sorted(len(p.interiors) for p in pieces)==([2] if c=='0' else [1,1]),(weight,oblique,c)
 print('Mono 0 and registered sign keep contour roles in all 26 samples')

def test_short_edge_corner():
 points=np.array([(0,0),(50,0),(50,50),(49,50),(0,50)],dtype=float)
 ring=Ring(points)
 assert set(map(tuple,ring.points[ring.corners()]))=={(0,0),(50,0),(50,50),(0,50)}
 assert len(ring.corners(legacy=True))==3
 font=TTFont(ROOT/'source/masters/SABModulMono-Black.ttf')
 ring=Ring(rings(font['glyf']['uni043A'])[0])
 assert set(ring.corners(legacy=True)).issubset(set(ring.corners()))
 print('Short-edge corner detected; existing Black ka corners preserved')

def test_nine_correspondence():
 fonts=[TTFont(ROOT/'source/masters'/f'SABModulMono-{style}.ttf') for style in STYLES]
 group=[Ring(rings(f['glyf']['uni0039'])[0]) for f in fonts]
 for i,r in enumerate(group):
  if i!=2:r.align(group[2])
 align_corners(group)
 samples=[r.normalized(np.linspace(0,1,129)) for r in group]
 error=max(float(np.max(np.linalg.norm(a-b,axis=1))) for a,b in zip(samples,samples[1:]))
 assert error<.15,('Nine outer contour correspondence distorted',error)
 print('Nine alignment passed',round(error,4))

def test_mono_yu_ae_counters():
 data=build.alphabet('SAB Modul',True)
 for weight in range(200,901,50):
  thickness=float(np.interp(weight,[v[0] for v in build.WEIGHTS.values()],[v[1] for v in build.WEIGHTS.values()]))
  for oblique in [False,True]:
   for c in 'ЮюÆ':
    g,_,_=build.geometry(*data[c],'SAB Modul',True,thickness,oblique,c)
    assert g.geom_type=='Polygon' and len(g.interiors)==1,(c,weight,oblique,'Counter closes')
 print('Mono Yu and AE retain counters in all 90 samples')

def test_section_counter():
 fonts=[TTFont(ROOT/'source/masters'/f'SABModulSans-{style}.ttf') for style in STYLES]
 group=[Ring(rings(f['glyf'][f.getBestCmap()[0xA7]])[1]) for f in fonts]
 for i,r in enumerate(group):
  if i!=2:r.align(group[2])
 align_corners(group)
 samples=[r.normalized(np.linspace(0,1,129)) for r in group]
 error=max(float(np.max(np.linalg.norm(a-b,axis=1))) for a,b in zip(samples,samples[1:]))
 assert error<.25,('Section counter correspondence rotated',error)
 print('Section counter alignment passed',round(error,4))

def test_flatten_components():
 fonts=[TTFont(ROOT/'source/masters'/f'SABModulSans-{style}.ttf') for style in STYLES]
 deduplicate(fonts)
 for f in fonts:
  glyphset=f.getGlyphSet()
  before={gn:boundary(glyphset,gn) for gn in f.getGlyphOrder()}
  flatten_components(f);glyphset=f.getGlyphSet()
  for gn,expected in before.items():
   g=f['glyf'][gn]
   if g.isComposite():assert all(not f['glyf'][c.glyphName].isComposite() for c in g.components),gn
   actual=boundary(glyphset,gn)
   if expected.is_empty:assert actual.is_empty,gn
   else:assert expected.hausdorff_distance(actual)<1e-9,gn
 print('Flattened components preserve all Sans master outlines')

def test_layout_refresh_rejects_metric_change():
 previous=ROOT/'source/masters';original=previous/'SABModulSans-Regular.ttf'
 with tempfile.TemporaryDirectory(dir=ROOT/'source') as tmp:
  path=Path(tmp)/original.name;modified=TTFont(original)
  advance,lsb=modified['hmtx']['uni0041'];modified['hmtx']['uni0041']=(advance+1,lsb);modified.save(path)
  report={'sources':{str(path.relative_to(ROOT)):hashlib.sha256(original.read_bytes()).hexdigest()}}
  try:refresh_layout([TTFont(original)],[path],report,previous)
  except AssertionError as error:assert 'hmtx' in str(error),error
  else:raise AssertionError('Layout refresh accepted a changed advance')
 print('Layout refresh rejects a one-unit advance change')

if __name__=='__main__':
 test_short_edge_corner()
 test_mono_contour_roles()
 test_nine_correspondence()
 test_mono_yu_ae_counters()
 test_section_counter()
 test_flatten_components()
 test_layout_refresh_rejects_metric_change()
