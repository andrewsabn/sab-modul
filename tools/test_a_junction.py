"""Reject the short flat shoulder before the Sans a stem."""
from pathlib import Path
import argparse, math
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.recordingPen import DecomposingRecordingPen

def shoulders(font, cp=0x61, location=None):
    glyph = font.getBestCmap().get(cp)
    if glyph is None: return []
    glyphs=font.getGlyphSet(location=location);pen = DecomposingRecordingPen(glyphs); glyphs[glyph].draw(pen)
    shear = math.tan(math.radians(-font['post'].italicAngle))
    def upright(p): return (p[0] - shear*p[1], p[1])
    contours=[]; points=[]
    for op, args in pen.value:
        if op == 'moveTo': points=[upright(args[0])]
        elif op in ('lineTo','qCurveTo','curveTo'): points.append(upright(args[-1]))
        elif op == 'closePath': contours.append(points);points=[]
    result=[]
    for pts in contours:
        for i,a in enumerate(pts):
            b=pts[(i+1)%len(pts)];c=pts[(i+2)%len(pts)]
            if abs(b[1]-a[1])<.65 and .65<abs(b[0]-a[0])<25 and abs(c[0]-b[0])<.65 and c[1]<b[1]-80 and b[1]>250:
                result.append({'from':a,'to':b,'units':abs(b[0]-a[0])})
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('font',type=Path);p.add_argument('--weight',type=float);a=p.parse_args()
    f=TTFont(a.font)
    if a.weight is not None: f=instantiateVariableFont(f,{'wght':a.weight},inplace=False)
    defects=shoulders(f)
    assert not defects, f'Flat shoulder at Sans a junction: {defects}'
    print('PASS: no flat shoulder at a junction')
