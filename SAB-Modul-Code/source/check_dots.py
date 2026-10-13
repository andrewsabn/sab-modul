"""Guard the accepted minimum dot diameter in static and variable Code fonts."""
import argparse,json
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.pens.boundsPen import BoundsPen
from fontTools.pens.recordingPen import RecordingPen
from verify_code import stroke_widths


def check(font):
    cmap=font.getBestCmap()
    stem=max(stroke_widths(font,cmap[ord('l')],270))
    rows=[]
    for char in '.:;':
        glyphs=font.getGlyphSet();drawing=RecordingPen()
        glyphs[cmap[ord(char)]].draw(drawing)
        pen=BoundsPen(glyphs);bounds=[];found=0
        for operation,arguments in drawing.value:
            getattr(pen,operation)(*arguments)
            if operation=='closePath':
                bounds.append(pen.bounds);pen=BoundsPen(glyphs)
        for x0,y0,x1,y1 in bounds:
            # The semicolon's lower dot joins its tail; guard its separate upper dot.
            if char==';' and y0<200: continue
            diameter=min(x1-x0,y1-y0)
            rows.append(dict(char=char,diameter=diameter,stem=stem,minimum=max(160,1.2*stem),passed=diameter>=160 and diameter>=1.2*stem))
            found+=1
        if found!={'.':1,':':2,';':1}[char]:
            rows.append(dict(char=char,passed=False,error='Expected dot contours absent'))
    return rows


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('fonts',type=Path,nargs='+')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();records=[]
    for path in args.fonts:
        font=TTFont(path)
        for weight in ([300,400,500,550,600,700] if 'fvar' in font else [font['OS/2'].usWeightClass]):
            instance=instantiateVariableFont(font,{'wght':weight},inplace=False) if 'fvar' in font else font
            rows=check(instance)
            records.append(dict(file=str(path),weight=weight,rows=rows))
    ok=bool(records) and all(row['passed'] for record in records for row in record['rows'])
    args.output.write_text(json.dumps(dict(status='PASS' if ok else 'FAIL',records=records),indent=2)+'\n')
    print('PASS' if ok else 'FAIL',len(records),'font instances;',sum(len(r['rows']) for r in records),'dot checks')
    raise SystemExit(0 if ok else 1)
