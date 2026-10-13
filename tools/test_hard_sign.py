"""Measure the visible hard-sign flag independently of italic shear."""
import math
from fontTools.pens.recordingPen import DecomposingRecordingPen

def flag_units(font,cp,location=None):
    gs=font.getGlyphSet(location=location);name=font.getBestCmap().get(cp)
    if not name:return None
    pen=DecomposingRecordingPen(gs);gs[name].draw(pen)
    slope=math.tan(math.radians(-font['post'].italicAngle));contours=[];points=[]
    for op,args in pen.value:
        if op=='moveTo':points=[args[0]]
        elif op in ('lineTo','qCurveTo','curveTo'):points.append(args[-1])
        elif op=='closePath':contours.append(points)
    pts=[(x-slope*y,y) for ring in contours for x,y in ring]
    height=max(y for x,y in pts);xmin=min(x for x,y in pts)
    candidates=[]
    for ring in contours:
        upright=[(x-slope*y,y) for x,y in ring]
        for a,b in zip(upright,upright[1:]+upright[:1]):
            if abs(a[0]-b[0])<2 and min(a[1],b[1])<=1 and max(a[1],b[1])>height*.5:
                candidates.append(min(a[0],b[0]))
    assert candidates,(name,'stem not found')
    return min(candidates)-xmin
