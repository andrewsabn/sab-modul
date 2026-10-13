"""Build Code masters from the copied, compatible SAB Modul Mono masters."""
from pathlib import Path
import argparse, io, json, math, unicodedata
from fontTools.ttLib import TTFont, newTable
from fontTools.varLib import build as build_variable
from fontTools.varLib.instancer import instantiateVariableFont
from fontTools.fontBuilder import FontBuilder
from fontTools.otlLib.builder import buildStatTable
from fontTools.ttLib.tables._g_l_y_f import Glyph, GlyphCoordinates
from fontTools.ttLib.tables.ttProgram import Program
from fontTools.pens.ttGlyphPen import TTGlyphPen

ROOT = Path(__file__).resolve().parents[1]
STYLES = {300: 'Light', 400: 'Regular', 500: 'Medium', 600: 'SemiBold', 700: 'Bold'}
OLD_STEMS = [(200, 56), (300, 70), (400, 80), (500, 97), (600, 115), (700, 134), (900, 161)]
SLOPE = math.tan(math.radians(10))


def source_weight(stem):
    wanted = stem * 620 / 600
    for (wa, sa), (wb, sb) in zip(OLD_STEMS, OLD_STEMS[1:]):
        if sa <= wanted <= sb:
            return wa + (wanted - sa) * (wb - wa) / (sb - sa)
    raise ValueError(('Stem outside copied master range', stem))


def y_map(y, lower):
    if not lower:
        return y * .9 if y < 0 else y
    if y < 0:
        return y * .9
    if y <= 500:
        return y * 540 / 500
    if y <= 720:
        return 540 + (y - 500) * 180 / 220
    return y


def metadata(font, weight, italic):
    style = STYLES[weight]
    sub = ('Italic' if weight == 400 else style + ' Italic') if italic else style
    family = 'SAB Modul Code'
    ps = 'SABModulCode-' + sub.replace(' ', '')
    font['name'] = newTable('name')
    font['name'].names = []
    legacy = family if weight in (400, 700) else family + ' ' + style
    legacy_sub = ('Bold Italic' if italic else 'Bold') if weight == 700 else ('Italic' if italic else 'Regular')
    FontBuilder(font=font).setupNameTable({
        'familyName': legacy, 'styleName': legacy_sub,
        'typographicFamily': family, 'typographicSubfamily': sub,
        'fullName': family + ' ' + sub, 'psName': ps,
        'uniqueFontIdentifier': 'SAB:1.000:' + ps, 'version': 'Version 1.000',
        'copyright': 'Copyright 2026 Andrew Sabynin (https://sabynin.com/)',
        'manufacturer': 'SAB Type', 'designer': 'SAB Type',
        'description': 'SAB Modul Code. A monospaced type family for code and technical documentation.',
        'licenseDescription': 'This Font Software is licensed under the SIL Open Font License, Version 1.1. This license is available with a FAQ at: https://openfontlicense.org',
    }, mac=True)
    if weight in (400, 700):
        font['name'].names = [n for n in font['name'].names if n.nameID not in (16, 17)]
    buildStatTable(font, [
        {'tag': 'wght', 'name': 'Weight', 'ordering': 0,
         'values': [{'value': weight, 'name': style, 'flags': 2 if weight == 400 else 0, **({'linkedValue': 700} if weight == 400 else {})}]},
        {'tag': 'ital', 'name': 'Italic', 'ordering': 1,
         'values': [{'value': int(italic), 'name': 'Italic' if italic else 'Roman',
                     'flags': 0 if italic else 2, **({} if italic else {'linkedValue': 1})}]},
    ], macNames=True)
    if 'GSUB' in font:
        from fontTools.ttLib.tables.otTables import FeatureParamsStylisticSet
        labels = {'ss01': 'Dotted zero', 'ss02': 'Unslashed zero', 'ss10': 'Disable operator ligatures'}
        for record in font['GSUB'].table.FeatureList.FeatureRecord:
            if record.FeatureTag in labels:
                params = FeatureParamsStylisticSet(); params.Version = 0
                params.UINameID = font['name'].addName(labels[record.FeatureTag])
                record.Feature.FeatureParams = params
    os2 = font['OS/2']
    os2.usWeightClass = weight
    os2.achVendID = 'SABT'
    os2.sTypoAscender, os2.sTypoDescender, os2.sTypoLineGap = 1000, -300, 0
    os2.usWinAscent, os2.usWinDescent = 1000, 300
    os2.sxHeight, os2.sCapHeight = 540, 700
    os2.panose.bProportion = 9
    os2.fsType = 0
    os2.fsSelection = 128 | (1 if italic else 0) | (32 if weight == 700 else 0) | (64 if not italic and weight != 700 else 0)
    font['hhea'].ascent, font['hhea'].descent, font['hhea'].lineGap = 1000, -300, 0
    font['hhea'].caretSlopeRise = 1000 if italic else 1
    font['hhea'].caretSlopeRun = round(SLOPE * 1000) if italic else 0
    font['post'].isFixedPitch = 1
    font['post'].italicAngle = -10 if italic else 0
    font['head'].fontRevision = 1.0
    font['head'].macStyle = int(weight == 700) | (2 if italic else 0)
    widths = [w for w, _ in font['hmtx'].metrics.values() if w]
    os2.xAvgCharWidth = sum(widths) // len(widths)


def transform(font, italic):
    cmap = font.getBestCmap()
    chars = {name: chr(cp) for cp, name in cmap.items()}
    glyf = font['glyf']
    flattened = {}
    for name in font.getGlyphOrder():
        if glyf[name].isComposite():
            coordinates, ends, flags = glyf[name].getCoordinates(glyf)
            glyph = Glyph()
            glyph.numberOfContours = len(ends)
            glyph.coordinates, glyph.endPtsOfContours, glyph.flags = GlyphCoordinates(coordinates), list(ends), flags[:]
            # Component-local overlap flags become interior points after flattening.
            for i in range(len(glyph.flags)):
                glyph.flags[i] &= ~0x40
            if glyph.flags:
                glyph.flags[0] |= 0x40
            glyph.program = Program()
            glyph.program.fromBytecode([])
            flattened[name] = glyph
    for name, glyph in flattened.items():
        glyf[name] = glyph
    for name in font.getGlyphOrder():
        glyph = glyf[name]
        assert not glyph.isComposite(), ('Compatible master must be flattened', name)
        ch = chars.get(name, '')
        base = unicodedata.normalize('NFD', ch)[:1]
        lower = bool(base and base.islower() and base not in 'ßſðþ')
        if glyph.numberOfContours > 0:
            detached = set()
            start = 0
            for end in glyph.endPtsOfContours:
                if lower and min(y for x, y in glyph.coordinates[start:end+1]) >= 500:
                    detached.update(range(start, end+1))
                start = end + 1
            for i, (x, y) in enumerate(glyph.coordinates):
                yy = y + 40 if i in detached else y_map(y, lower)
                # Undo/reapply the shear so changing x-height does not change the italic angle.
                xx = (x - SLOPE * y + 18) * 600 / 620 + SLOPE * yy - 18 if italic else x * 600 / 620
                glyph.coordinates[i] = (round(xx), round(yy))
            glyph.recalcBounds(glyf)
        advance, _ = font['hmtx'][name]
        font['hmtx'][name] = (600 if advance else 0, getattr(glyph, 'xMin', 0))
    # Anchor positions are rebuilt with the Code glyphs at the punctuation/features stage.
    for table in ['fpgm', 'prep', 'cvt ', 'gvar', 'HVAR', 'MVAR', 'avar', 'fvar', 'cvar', 'DSIG']:
        if table in font:
            del font[table]


def build_stage1():
    targets_path = ROOT / 'checks/targets.json'
    assert targets_path.exists(), 'Stage 0 measured targets must be frozen before contour changes'
    targets = json.loads(targets_path.read_text())
    assert (ROOT / 'checks/etalons.md').exists()
    destination = ROOT / 'source/code-masters'
    destination.mkdir(parents=True, exist_ok=True)
    provenance = []
    for italic in [False, True]:
        folder = ROOT / 'source/upstream/variable-masters' / ('SABModulMonoOblique' if italic else 'SABModulMono')
        variable, _, _ = build_variable(folder / 'family.designspace')
        buffer = io.BytesIO()
        variable.save(buffer)
        buffer.seek(0)
        variable = TTFont(buffer)
        for weight, style in STYLES.items():
            stem = targets['stems'][str(weight)]
            location = source_weight(stem / math.cos(math.radians(10)) if italic else stem)
            font = instantiateVariableFont(variable, {'wght': location}, inplace=False)
            transform(font, italic)
            metadata(font, weight, italic)
            path = destination / ('SABModulCode-' + style + ('Italic' if italic else '') + '.ttf')
            font.save(path)
            provenance.append({'file': str(path.relative_to(ROOT)), 'weight': weight,
                               'italic': italic, 'target_stem': stem, 'source_weight': location})
            print(path.name, 'from Mono wght', round(location, 4), flush=True)
    (ROOT / 'checks/stage1-build.json').write_text(json.dumps(provenance, indent=2) + '\n')


def install_geometry(font, name, geometry, advance=600):
    from shapely.geometry.polygon import orient
    pen = TTGlyphPen(None)
    layers = geometry if isinstance(geometry, list) else [geometry]
    polygons = [p for layer in layers for p in ([layer] if layer.geom_type == 'Polygon' else layer.geoms)]
    for polygon in polygons:
        if polygon.is_empty:
            continue
        assert polygon.is_valid, (name, 'invalid drawn contour')
        polygon = orient(polygon, sign=-1)
        for ring in [polygon.exterior, *polygon.interiors]:
            points = []
            for x, y in list(ring.coords)[:-1]:
                point = (round(x), round(y))
                if not points or points[-1] != point:
                    points.append(point)
            if len(points) > 1 and points[0] == points[-1]:
                points.pop()
            if len(points) < 3:
                continue
            pen.moveTo(points[0])
            for point in points[1:]:
                pen.lineTo(point)
            pen.closePath()
    glyph = pen.glyph()
    if len(layers) > 1 and glyph.numberOfContours > 0:
        glyph.flags[0] |= 0x40  # OVERLAP_SIMPLE: preserve union rendering in variable masters.
    font['glyf'][name] = glyph
    glyph.recalcBounds(font['glyf'])
    font['hmtx'][name] = (advance, getattr(glyph, 'xMin', 0))
    if name not in font.getGlyphOrder():
        font.setGlyphOrder(font.getGlyphOrder() + [name])


def build_stage2():
    from shapely.affinity import translate
    from code_symbols import geometries
    from code_features import compile_features
    destination = ROOT / 'source/stage2-masters'
    destination.mkdir(parents=True, exist_ok=True)
    records = []
    for path in sorted((ROOT / 'source/code-masters').glob('*.ttf')):
        font = TTFont(path)
        weight = font['OS/2'].usWeightClass
        italic = bool(font['post'].italicAngle)
        shapes = geometries(weight, italic)
        cmap = font.getBestCmap()
        for char, geometry in shapes.items():
            name = cmap.get(ord(char), f'uni{ord(char):04X}') if len(char) == 1 else char
            install_geometry(font, name, geometry)
            if len(char) == 1:
                for table in font['cmap'].tables:
                    if table.isUnicode() and table.format in (4, 12):
                        table.cmap[ord(char)] = name
            if name + '.pnum' in font.getGlyphOrder():
                install_geometry(font, name + '.pnum', geometry)
            if name + '.case' in font.getGlyphOrder():
                install_geometry(font, name + '.case', translate(geometry, yoff=350-(geometry.bounds[1]+geometry.bounds[3])/2))
        feature_source = compile_features(font, italic)
        metadata(font, weight, italic)
        font.save(destination / path.name)
        (destination / (path.stem + '.fea')).write_text(feature_source)
        records.append({'file': path.name, 'modified': sorted(shapes), 'weight': weight, 'italic': italic})
        print(path.name, len(shapes), 'drawn glyphs', flush=True)
    assert len(records) == 10
    (ROOT / 'checks/stage2-build.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')


def build_next_stage(stage):
    from code_features import compile_features
    destination = ROOT / f'source/stage{stage}-masters'
    destination.mkdir(parents=True, exist_ok=True)
    records = []
    for path in sorted((ROOT / f'source/stage{stage-1}-masters').glob('*.ttf')):
        font = TTFont(path)
        weight, italic = font['OS/2'].usWeightClass, bool(font['post'].italicAngle)
        if stage == 3:
            from code_boxes import geometries as boxes
            from code_extended import geometries as extended
            from code_greek import geometries as greek
            shapes = {**extended(weight, italic), **greek(weight, italic), **boxes(weight, italic)}
        elif stage == 4:
            from code_operators import parts
            shapes = parts(weight, italic)
        elif stage == 6:
            from code_engineering import geometries
            shapes = geometries(weight, italic)
        else:
            from copy import deepcopy
            from code_italic import geometries as italic_a
            shapes = italic_a(weight, italic)
            original = TTFont(ROOT / 'source/stage2-masters' / path.name)
            minus = font.getBestCmap()[0x2212]
            font['glyf'][minus] = deepcopy(original['glyf'][minus])
            font['hmtx'][minus] = original['hmtx'][minus]
        cmap = font.getBestCmap()
        for char, geometry in shapes.items():
            name = cmap.get(ord(char), f'uni{ord(char):04X}') if len(char) == 1 else char
            install_geometry(font, name, geometry)
            if len(char) == 1:
                for table in font['cmap'].tables:
                    if table.isUnicode() and table.format in (4, 12):
                        table.cmap[ord(char)] = name
        if stage == 6:
            from code_engineering import refine_and_extend
            refine_and_extend(font, weight, italic)
        source = compile_features(font, italic)
        accents = []
        if (stage == 5 and italic) or stage == 6:
            from code_italic import rebuild_accents
            accents = rebuild_accents(font, all_bases=stage == 6)
            source = compile_features(font, italic)
        if stage == 6:
            from code_engineering import remove_degenerate_segments
            remove_degenerate_segments(font)
            from code_engineering import remove_unreachable_helpers
            remove_unreachable_helpers(font)
        metadata(font, weight, italic)
        # Typographic layout stays 1000/-300; Windows clipping bounds must include
        # terminal strokes extending to adjacent rows at line-height 1.5.
        bounds = []
        for name in font.getGlyphOrder():
            glyph = font['glyf'][name]
            glyph.recalcBounds(font['glyf'])
            if hasattr(glyph, 'yMax'):
                bounds.append((glyph.yMin, glyph.yMax))
        font['OS/2'].usWinAscent = max(1000, max(y1 for y0, y1 in bounds))
        font['OS/2'].usWinDescent = max(300, -min(y0 for y0, y1 in bounds))
        font['OS/2'].recalcUnicodeRanges(font)
        font.save(destination / path.name)
        (destination / (path.stem + '.fea')).write_text(source)
        records.append({'file': path.name, 'weight': weight, 'italic': italic,
                        'drawn': sorted(shapes), 'cmap': len(font.getBestCmap()),
                        'winAscent': font['OS/2'].usWinAscent, 'winDescent': font['OS/2'].usWinDescent,
                        'rebuilt_accents': accents})
        print(path.name, len(shapes), 'drawn', len(font.getBestCmap()), 'encoded', flush=True)
    assert len(records) == 10
    (ROOT / f'checks/stage{stage}-build.json').write_text(json.dumps(records, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--stage', choices=['1', '2', '3', '4', '5', '6'], default='1')
    args = parser.parse_args()
    if args.stage == '1':
        build_stage1()
    elif args.stage == '2':
        build_stage2()
    else:
        build_next_stage(int(args.stage))
