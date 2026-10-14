"""Digit regressions at alignment lines; run before and after the scoped rebuild."""
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import DecomposingRecordingPen
import json, sys, math
from fontTools.pens.basePen import BasePen

class Flat(BasePen):
    def __init__(self,gs):super().__init__(gs);self.rings=[];self.points=[]
    def _moveTo(self,p):self.points=[p]
    def _lineTo(self,p):self.points.append(p)
    def _qCurveToOne(self,c,b):
        a=self._getCurrentPoint()
        for i in range(1,41):
            t=i/40;self.points.append(tuple((1-t)**2*a[k]+2*t*(1-t)*c[k]+t*t*b[k] for k in (0,1)))
    def _curveToOne(self,c,d,b):
        a=self._getCurrentPoint()
        for i in range(1,61):
            t=i/60;self.points.append(tuple((1-t)**3*a[k]+3*t*(1-t)**2*c[k]+3*t*t*(1-t)*d[k]+t**3*b[k] for k in (0,1)))
    def _closePath(self):self.rings.append(self.points);self.points=[]
    def _endPath(self):self._closePath()

ROOT=Path(__file__).resolve().parents[1]

def inspect(font,location=None):
    gs=font.getGlyphSet(location=location);cm=font.getBestCmap();failures=[]
    for ch in '27':
        p=BoundsPen(gs);gs[cm[ord(ch)]].draw(p);b=p.bounds
        if ch=='2' and b[3]>712:failures.append(f'2 exceeds optical cap limit: {b[3]:.3f}')
        if ch=='7' and abs(b[1])>1.5:failures.append(f'7 misses baseline: {b[1]:.3f}')
    slope=math.tan(math.radians(-font['post'].italicAngle))
    p=Flat(gs);gs[cm[ord('2')]].draw(p)
    pts=[(x-slope*y,y) for ring in p.rings for x,y in ring]
    lo=min(x for x,y in pts)
    if min(y for x,y in pts if x<=lo+1)>2:
        failures.append('2 lower-left protrusion lies above the baseline')
    p=DecomposingRecordingPen(gs);gs[cm[ord('5')]].draw(p);last=None
    for op,args in p.value:
        if op=='moveTo':last=args[0]
        elif op in ('lineTo','qCurveTo','curveTo'):
            end=args[-1]
            if op=='lineTo' and last is not None:
                if end==last:failures.append('5 has a zero-length line after rounding')
                a=(last[0]-slope*last[1],last[1]);b=(end[0]-slope*end[1],end[1])
                if 355<min(a[1],b[1]) and max(a[1],b[1])<395 and abs(a[1]-b[1])<6 and abs(a[0]-b[0])>22 and max(a[0],b[0])<230:
                    failures.append('5 exposed horizontal cap at bowl/stem junction')
            last=end
    for ch in '0235689':
        p=DecomposingRecordingPen(gs);gs[cm[ord(ch)]].draw(p)
        if not any(op in ('qCurveTo','curveTo') for op,args in p.value):
            failures.append(f'{ch} has no curved segments')
    return failures

if __name__=='__main__':
    results=[]
    for family,folder in [('Sans','SAB-Modul-1.0'),('Mono','SAB-Modul-1.0'),('Code','SAB-Modul-Code')]:
        for path in sorted((ROOT/folder/'TTF').glob('*'+family+'*.ttf')):
            results.append({'file':str(path.relative_to(ROOT)),'failures':inspect(TTFont(path))})
    bad=[r for r in results if r['failures']]
    print(json.dumps({'styles':len(results),'failed_styles':len(bad),'examples':bad[:3]},indent=2))
    sys.exit(bool(bad))
