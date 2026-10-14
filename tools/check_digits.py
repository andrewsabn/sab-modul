"""Check numeric geometry and non-numeric invariants against a prior release directory."""
from pathlib import Path
import sys,json,copy,hashlib,collections
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.varLib.instancer import instantiateVariableFont
from shapely.geometry import Polygon
from shapely.validation import explain_validity
R=Path(__file__).resolve().parents[1];B=Path(sys.argv[1]).resolve();sys.path.insert(0,str(R/'tools'))
from test_digits import inspect,Flat
O=R/'checks/digits';O.mkdir(exist_ok=True)
def sha(b):return hashlib.sha256(b).hexdigest()
def names(f,family):
 c=f.getBestCmap();digits='23578' if family=='Code' else '02356789'
 return {c[ord(x)] for x in digits if ord(x) in c}|{c[ord(x)]+'.pnum' for x in digits if ord(x) in c and c[ord(x)]+'.pnum' in f.getGlyphOrder()}
reg=[]
for rel in sorted(p.relative_to(B) for p in B.rglob('*') if p.suffix in ('.ttf','.otf','.woff2')):
 if rel.parts[0]=='checks':continue
 old=TTFont(B/rel,recalcTimestamp=False);new=TTFont(R/rel,recalcTimestamp=False);family='Code' if 'Code' in str(rel) else 'Sans' if 'Sans' in str(rel) else 'Mono'
 allowed=names(old,family);changed=[]
 assert old.getGlyphOrder()==new.getGlyphOrder(),rel
 for t in ('hmtx','cmap','GPOS','GSUB','GDEF','HVAR','fvar','avar','STAT','fpgm','prep','cvt '):
  if t in old:assert old.getTableData(t)==new.getTableData(t),(str(rel),t)
 for g in old.getGlyphOrder():
  if 'glyf' in old:
   a=old['glyf'][g].compile(old['glyf']);b=new['glyf'][g].compile(new['glyf'])
  else:a=old['CFF '].cff.topDictIndex[0].CharStrings[g].bytecode;b=new['CFF '].cff.topDictIndex[0].CharStrings[g].bytecode
  if a!=b:changed.append(g);assert g in allowed,(str(rel),'non-digit',g)
 if 'gvar' in old:
  ov={n:copy.deepcopy(v) for n,v in old['gvar'].variations.items()};nv={n:copy.deepcopy(v) for n,v in new['gvar'].variations.items()}
  assert all(ov[g]==nv[g] for g in ov if g not in allowed),(str(rel),'unrelated gvar')
 reg.append({'file':str(rel),'sha256':sha((R/rel).read_bytes()),'changed_glyphs':changed,'unchanged_advances_layout_non_digit_shapes_and_variations':True})
(O/'binary-regression.json').write_text(json.dumps({'fonts':len(reg),'baseline':'Published RFN a/hard-sign release at999d526','results':reg},indent=2)+'\n');print('Binary regression',len(reg),flush=True)
records=[];bad=[];tested=0
for family,folder in [('Sans','SAB-Modul-1.0'),('Mono','SAB-Modul-1.0'),('Code','SAB-Modul-Code')]:
 for p in sorted([* (R/folder/'TTF').glob('*'+family+'*.ttf'),*(R/folder/'OTF').glob('*'+family+'*.otf'),*(R/folder/'VF').glob('*'+family+'*.ttf')]):
  f=TTFont(p);cm=f.getBestCmap();weights=[None] if 'fvar' not in f else sorted(set([float(w) for w in range(int(f['fvar'].axes[0].minValue),int(f['fvar'].axes[0].maxValue)+1,25)]+[w+.5 for w in range(int(f['fvar'].axes[0].minValue),int(f['fvar'].axes[0].maxValue),25)]))
  ns=[(ch,cm[ord(ch)]) for ch in '0123456789']+[(n,n) for n in f.getGlyphOrder() if n.endswith('.pnum') or n in ('zero.empty','zero.dotted')]
  for w in weights:
   loc={'wght':w} if w is not None else None;gs=f.getGlyphSet(location=loc)
   failures=inspect(f,loc)
   for ch,n in ns:
    pen=Flat(gs);gs[n].draw(pen);bp=BoundsPen(gs);gs[n].draw(bp)
    invalid=[explain_validity(Polygon(q)) for q in pen.rings if not Polygon(q).is_valid]
    rec={'file':str(p.relative_to(R)),'weight':w,'glyph':n,'bounds':bp.bounds,'rings':len(pen.rings),'invalid_rings':invalid}
    records.append(rec);tested+=1
    if invalid:bad.append(rec)
   if failures:bad.append({'file':str(p.relative_to(R)),'weight':w,'failures':failures})
  print('Geometry',p.name,'locations',len(weights),flush=True)
(O/'geometry-audit.json').write_text(json.dumps({'cases':tested,'failures':bad,'sampling':'All static TTF/OTF styles, main VF every25 weight units and +0.5 offsets; includes pnum and Code zero forms. Sampled curve flattening, not a proof for every real-valued weight.','records':records},indent=2)+'\n')
print('Geometry cases',tested,'failures',len(bad),bad[:5],flush=True)
assert not bad
