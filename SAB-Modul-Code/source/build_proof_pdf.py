"""A4 distinction proof at the specified 11 pt, using embedded Code TTFs."""
from pathlib import Path
import hashlib
import json
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont, shapeStr
from build_proofs import PAIRS, LANGUAGE_LINES

ROOT = Path(__file__).resolve().parents[1]


def draw_shaped(canvas,x,y,text,family,size):
    # Place each shaped glyph explicitly: ReportLab's grouped Ts handling leaks mark rise.
    shaped=shapeStr(text,family,size,force=True);cursor=0
    face=pdfmetrics.getFont(family).face
    for char,pos in zip(shaped,shaped.__shapeData__):
        assert face.charToGlyph.get(ord(char),0)!=0,(text,char,'missing proof glyph')
        canvas.drawString(x+cursor+size*pos.x_offset/1000,y+size*pos.y_offset/1000,str(char))
        cursor+=size*pos.x_advance/1000


def main(font_dir=ROOT/'source/stage2-masters', out=ROOT/'proofs/distinguish-11pt.pdf', report=ROOT/'checks/stage2-pdf-inputs.json'):
    fonts = sorted(font_dir.glob('*.ttf'))
    assert len(fonts) == 10
    canvas = Canvas(str(out), pagesize=A4)
    canvas.setTitle('SAB Modul Code - 11 pt distinction proof')
    for index, font in enumerate(fonts):
        family = 'CodeProof' + str(index)
        face=TTFont(family,str(font));assert face.shapable,'PDF proof requires HarfBuzz shaping'
        pdfmetrics.registerFont(face)
        canvas.setFont('Helvetica', 13)
        canvas.drawString(36, A4[1] - 42, font.stem + ' / 11 pt')
        canvas.setFont(family, 11)
        for row, text in enumerate(PAIRS):
            assert pdfmetrics.stringWidth(text, family, 11) <= A4[0] - 72
            draw_shaped(canvas,36+(row%2)*265,A4[1]-85-(row//2)*22,text,family,11)
        for row,text in enumerate(LANGUAGE_LINES):
            assert pdfmetrics.stringWidth(text,family,11)<=A4[0]-72
            draw_shaped(canvas,36,A4[1]-375-row*22,text,family,11)
        for row,text in enumerate(['val total = amount * 1.25 // Сумма в тенге',
                'if (a != b) { return x => y; } // x -> y',
                '0Oо 1lI| rn/m vv/w cl/d 0123456789',
                'AVATAR, 2007–2026; −37 %; €87,3 → $55,1']):
            draw_shaped(canvas,36,A4[1]-635-row*22,text,family,11)
        canvas.showPage()
    canvas.save()
    report.write_text(json.dumps({
        'pdf': str(out.relative_to(ROOT)), 'sha256': hashlib.sha256(out.read_bytes()).hexdigest(),
        'font_size_pt': 11, 'page_count': len(fonts), 'language_samples':LANGUAGE_LINES, 'shaping':True,
        'fonts': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in fonts},
        'visual_review': 'pending render inspection',
    }, indent=2) + '\n')
    print(out)


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--font-dir',type=Path,default=ROOT/'source/stage2-masters');parser.add_argument('--output',type=Path,default=ROOT/'proofs/distinguish-11pt.pdf');parser.add_argument('--report',type=Path,default=ROOT/'checks/stage2-pdf-inputs.json');args=parser.parse_args();main(args.font_dir.resolve(),args.output.resolve(),args.report.resolve())
