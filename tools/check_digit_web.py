"""Compare shipped web numeric outlines and advances with their matching main fonts."""
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.recordingPen import DecomposingRecordingPen
import json
R=Path(__file__).resolve().parents[1];records=[]
for folder in ('SAB-Modul-1.0','SAB-Modul-Code'):
 root=R/folder
 for p in [*(root/'WEB').glob('*.woff2'),*(root/'VF').glob('*.woff2'),*(root/'WOFF2').glob('*.woff2')]:
  f=TTFont(p);family='Sans' if 'Sans' in p.name else 'Mono' if 'Mono' in p.name else 'Code'
  if 'fvar' in f:
   candidates=[q for q in (root/'VF').glob('*'+family+'*.ttf') if bool(TTFont(q)['post'].italicAngle)==bool(f['post'].italicAngle)]
   assert len(candidates)==1;ref=TTFont(candidates[0]);weights=[f['fvar'].axes[0].minValue,400,450.5,f['fvar'].axes[0].maxValue]
  else:ref=TTFont(root/'TTF'/(p.stem+'.ttf'));weights=[None]
  for w in weights:
   a=f.getGlyphSet(location={'wght':w} if w is not None else None);b=ref.getGlyphSet(location={'wght':w} if w is not None else None)
   ns=[n for n in f.getGlyphOrder() if n.startswith('uni003') or n in ('zero.empty','zero.dotted')]
   for n in ns:
    x=DecomposingRecordingPen(a);a[n].draw(x);y=DecomposingRecordingPen(b);b[n].draw(y)
    assert x.value==y.value,(str(p),n,w)
    assert a[n].width==b[n].width,(str(p),n,w,'advance')
   records.append({'file':str(p.relative_to(R)),'weight':w,'numeric_glyphs':len(ns),'outlines_and_advances_match_main_font':True})
jsonout={'cases':sum(r['numeric_glyphs'] for r in records),'fonts':len(set(r['file'] for r in records)),'locations':len(records),'results':records}
(R/'checks/digits/web-format-regression.json').write_text(json.dumps(jsonout,indent=2)+'\n')
print('Web glyph/location matches',jsonout['cases'],'in',jsonout['fonts'],'fonts')
