from pathlib import Path
from fontTools.ttLib import TTFont
import sys,json,hashlib

ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'iterations'/sys.argv[1]
assert out.is_dir()
styles=['Thin','Light','Regular','Medium','SemiBold','Bold','Black'];report={}
for family in ['Sans','Mono']:
 for slant in ['', 'Oblique']:
  paths=[ROOT/'source/masters'/f'SABModul{family}-{s}{slant}.ttf' for s in styles]
  fonts=[TTFont(p) for p in paths];order=fonts[0].getGlyphOrder()
  assert all(f.getGlyphOrder()==order for f in fonts),'Master glyph orders differ'
  contour_issues={};point_issues={};component_issues={};winding_issues={}
  for gn in order:
   gs=[f['glyf'][gn] for f in fonts];ns=[g.numberOfContours for g in gs]
   if len(set(ns))>1:contour_issues[gn]=ns
   elif ns[0]<0:
    refs=[tuple((c.glyphName,tuple(tuple(row) for row in getattr(c,'transform',[[1,0],[0,1]]))) for c in g.components) for g in gs]
    if len(set(refs))>1:component_issues[gn]=refs
   elif ns[0]>0:
    windings=[]
    for g in gs:
     start=0;signs=[]
     for end in g.endPtsOfContours:
      points=list(g.coordinates[start:end+1]);start=end+1
      area=sum(a[0]*b[1]-a[1]*b[0] for a,b in zip(points,points[1:]+points[:1]))
      signs.append(1 if area>0 else -1 if area<0 else 0)
     windings.append(tuple(sorted(signs)))
    if len(set(windings))>1:winding_issues[gn]=windings
    counts=[tuple(g.endPtsOfContours) for g in gs]
    if len(set(counts))>1:point_issues[gn]=[len(g.coordinates) for g in gs]
  report[family+slant]={'styles':styles,'glyphs':len(order),'composites':sum(fonts[0]['glyf'][gn].isComposite() for gn in order),'contour_count_mismatches':contour_issues,'component_mismatches':component_issues,'winding_count_mismatches':winding_issues,'point_count_mismatches':point_issues,'sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
  print(family+slant,'glyphs',len(order),'contours',len(contour_issues),'components',len(component_issues),'winding',len(winding_issues),'points',len(point_issues))
(out/'master-topology.json').write_text(json.dumps({'limitation':'Matching contour counts alone does not prove point correspondence or interpolation quality','families':report},ensure_ascii=False,indent=2))
