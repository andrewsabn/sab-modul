"""Read-only regression for the known Mono Italic ogonek micro-loop."""
import sys
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from fontTools.misc.bezierTools import segmentSegmentIntersections
class Segments(BasePen):
 def __init__(self,gs):super().__init__(gs);self.segments=[]
 def _moveTo(self,p):self.start=p
 def _lineTo(self,p):self.segments.append([self._getCurrentPoint(),p])
 def _qCurveToOne(self,c,p):self.segments.append([self._getCurrentPoint(),c,p])
 def _closePath(self):
  if self._getCurrentPoint()!=self.start:self._lineTo(self.start)
 def _endPath(self):self._closePath()
f=TTFont(sys.argv[1]);bad=[]
for w in [650,675,680,690,700,710,720,730,740,750,800,900]:
 gs=f.getGlyphSet(location={'wght':w});p=Segments(gs);gs[f.getBestCmap()[0x12F]].draw(p)
 assert len(p.segments[20])==3 and len(p.segments[22])==2
 for hit in segmentSegmentIntersections(p.segments[20],p.segments[22]):
  if 0<hit.t1<1 and 0<hit.t2<1:bad.append((w,hit.pt))
assert not bad,('Mono Italic ogonek has an internal Q/line crossing',bad)
print('No known ogonek micro-loop at the 12 regression weights')
