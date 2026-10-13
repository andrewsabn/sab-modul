"""Final release step: distinct bullet, copyright and neutral description."""
from pathlib import Path
import hashlib
import json
import math
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
from fontTools.ttLib.tables.TupleVariation import TupleVariation
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.varLib.models import VariationModel, normalizeValue

ROOT = Path(__file__).resolve().parents[1]
COPYRIGHT = 'Copyright 2026 Andrew Sabynin (https://sabynin.com/)'
DESCRIPTION = "SAB Modul is an original type family designed for text, interfaces and display use."
DIAMETERS = {200: 160, 300: 180, 400: 200, 500: 220, 600: 240, 700: 260, 900: 280}


def bullet(weight, advance):
    radius = DIAMETERS[weight] / 2
    cx, cy = advance / 2, 250
    pen = TTGlyphPen(None)
    pen.moveTo((cx + radius, cy))
    for i in range(8):
        mid = -(i + .5) * math.pi / 4
        end = -(i + 1) * math.pi / 4
        control = radius / math.cos(math.pi / 8)
        endpoint = (cx + radius, cy) if i == 7 else (cx + radius * math.cos(end), cy + radius * math.sin(end))
        pen.qCurveTo((cx + control * math.cos(mid), cy + control * math.sin(mid)), endpoint)
    pen.closePath()
    glyph = pen.glyph()
    glyph.recalcBounds(None)
    return glyph


def apply(path):
    old_hash = hashlib.sha256(path.read_bytes()).hexdigest()
    font = TTFont(path, recalcTimestamp=False)
    for name_id, text in ((0, COPYRIGHT), (10, DESCRIPTION)):
        for record in font['name'].names:
            if record.nameID == name_id:
                record.string = text
        font['name'].setName(text, name_id, 3, 1, 0x409)
    name = font.getBestCmap().get(0x2022)
    if name:
        advance = 620 if 'Mono' in font['name'].getDebugName(1) else 400
        weight = font['OS/2'].usWeightClass
        glyph = bullet(weight, advance)
        font['hmtx'][name] = (advance, glyph.xMin)
        if 'glyf' in font:
            font['glyf'][name] = glyph
            if 'gvar' in font:
                axis, = font['fvar'].axes
                assert (axis.axisTag, axis.minValue, axis.defaultValue, axis.maxValue) == ('wght', 200, 400, 900)
                weights = list(DIAMETERS)
                locations = [{'wght': normalizeValue(w, (200, 400, 900))} for w in weights]
                model = VariationModel(locations)
                coordinates = []
                for w in weights:
                    g = bullet(w, advance)
                    coordinates.append(GlyphCoordinates(list(g.coordinates) + [(0, 0), (advance, 0), (0, 0), (0, 0)]))
                deltas = model.getDeltas(coordinates, round=GlyphCoordinates.__round__)
                font['gvar'].variations[name] = [TupleVariation(s, d) for s, d in zip(model.supports[1:], deltas[1:])]
                if advance == 400:
                    hvar = font['HVAR'].table
                    assert hvar.AdvWidthMap is not None
                    zero = next((outer << 16) | inner for outer, data in enumerate(hvar.VarStore.VarData)
                                for inner, row in enumerate(data.Item) if not any(row))
                    hvar.AdvWidthMap.mapping[name] = zero
        else:
            top = font['CFF '].cff.topDictIndex[0]
            pen = T2CharStringPen(advance, None)
            glyph.draw(pen, None)
            top.CharStrings[name] = pen.getCharString(private=top.Private, globalSubrs=font['CFF '].cff.GlobalSubrs)
        widths = [a for a, _ in font['hmtx'].metrics.values() if a > 0]
        font['OS/2'].xAvgCharWidth = sum(widths) // len(widths)
        font['hhea'].recalc(font)
    font.save(path)
    return {'file': str(path.relative_to(ROOT)), 'before_sha256': old_hash,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bullet_updated': bool(name)}


if __name__ == '__main__':
    changes = [apply(p) for folder in ('TTF', 'OTF', 'WOFF2', 'VF', 'WEB')
               for p in sorted((ROOT / folder).iterdir()) if p.suffix in ('.ttf', '.otf', '.woff2')]
    assert len(changes) == 110
    (ROOT / 'checks/fable-fixes.json').write_text(json.dumps({'copyright': COPYRIGHT,
        'description': DESCRIPTION, 'bullet_diameters': DIAMETERS, 'files': changes}, indent=2))
    print('Updated', len(changes), 'fonts;', sum(x['bullet_updated'] for x in changes), 'contain bullet')
