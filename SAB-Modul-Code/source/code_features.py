"""Code-specific shaping; marks follow the measured final glyph bounds."""
import copy
import math
import unicodedata
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.pens.boundsPen import BoundsPen
from verify_code import intersections


def features(font, italic=False):
    cmap = font.getBestCmap()
    glyphs = font.getGlyphSet()
    slope = math.tan(math.radians(10)) if italic else 0
    stem = min(right - left for left, right in intersections(font, cmap[ord('H')], 175))

    def bounds(name):
        pen = BoundsPen(glyphs)
        glyphs[name].draw(pen)
        return pen.bounds

    lines = ['languagesystem DFLT dflt;', 'languagesystem latn dflt;',
             'languagesystem cyrl dflt;', 'languagesystem grek dflt;']
    compositions = []
    for cp, name in sorted(cmap.items()):
        parts = unicodedata.normalize('NFD', chr(cp))
        if len(parts) > 1 and all(ord(c) in cmap for c in parts):
            compositions.append('sub ' + ' '.join(cmap[ord(c)] for c in parts) + ' by ' + name + ';')
    if compositions:
        lines.append('feature ccmp {\n' + '\n'.join(compositions) + '\n} ccmp;')

    top_marks = [name for cp, name in sorted(cmap.items()) if unicodedata.combining(chr(cp)) == 230]
    soft_dotted = {cmap[ord(base)]: cmap[ord(dotless)]
                   for base, dotless in zip('ijіј', 'ıȷıȷ')
                   if ord(base) in cmap and ord(dotless) in cmap}
    if 0x12F in cmap and cmap[0x12F] + '.dotless' in font.getGlyphOrder():
        soft_dotted[cmap[0x12F]] = cmap[0x12F] + '.dotless'
    if top_marks and soft_dotted:
        lines.append('@TopMarks = [' + ' '.join(top_marks) + '];')
        rules = [f"sub {base}' @TopMarks by {dotless};"
                 for base, dotless in soft_dotted.items()]
        lines.append('feature ccmp {\nlookupflag UseMarkFilteringSet @TopMarks;\n'
                     + '\n'.join(rules) + '\n} ccmp;')

    groups = set()
    mark_stacking = []
    for cp, name in sorted(cmap.items()):
        if not unicodedata.category(chr(cp)).startswith('M'):
            continue
        box = bounds(name)
        if not box:
            continue
        group = 'ogonek' if cp == 0x328 else 'bottom' if cp in (0x326, 0x327) else 'top'
        groups.add(group)
        yy = box[3] if group in ('bottom', 'ogonek') else box[1]
        xx = (box[0] + box[2]) / 2 + slope * (yy - (box[1] + box[3]) / 2)
        lines.append(f'markClass {name} <anchor {round(xx)} {round(yy)}> @{group};')
        stack_y = box[1] - 40 if group in ('bottom', 'ogonek') else box[3] + 40
        stack_x = (box[0] + box[2]) / 2 + slope * (stack_y - (box[1] + box[3]) / 2)
        mark_stacking.append(f'pos mark {name} <anchor {round(stack_x)} {round(stack_y)}> mark @{group};')
    positions = []
    letter_glyphs = list(sorted(cmap.items()))
    if 0x12F in cmap and cmap[0x12F] + '.dotless' in font.getGlyphOrder():
        letter_glyphs.append((0x12F, cmap[0x12F] + '.dotless'))
    for cp, name in letter_glyphs:
        if not unicodedata.category(chr(cp)).startswith('L'):
            continue
        box = bounds(name)
        if not box:
            continue
        anchors = []
        for group in sorted(groups):
            yy = 0 if group in ('bottom', 'ogonek') else box[3] + 40
            if group == 'ogonek':
                feet = intersections(font, name, 2)
                xx = max((right for left, right in feet), default=box[2]) - stem / 4
            else:
                xx = (box[0] + box[2]) / 2 + slope * (yy - (box[1] + box[3]) / 2)
            anchors.append(f'<anchor {round(xx)} {round(yy)}> mark @{group}')
        positions.append(f'pos base {name} ' + ' '.join(anchors) + ';')
    if positions:
        lines.append('feature mark {\n' + '\n'.join(positions) + '\n} mark;')

    if mark_stacking:
        lines.append('feature mkmk {\n' + '\n'.join(mark_stacking) + '\n} mkmk;')

    zero = cmap[ord('0')]
    if all(name in font.getGlyphOrder() for name in ['zero.dotted', 'zero.empty']):
        lines.extend([
            f'feature ss01 {{sub {zero} by zero.dotted;}} ss01;',
            f'feature ss02 {{sub [{zero} zero.dotted] by zero.empty;}} ss02;',
            f'feature zero {{sub {zero} by {zero};}} zero;',
        ])
    tabular = [f'sub {cmap[ord(c)]} by {cmap[ord(c)]};' for c in '0123456789']
    lines.append('feature tnum {' + ' '.join(tabular) + '} tnum;')
    case = [f'sub {cmap[ord(c)]} by {cmap[ord(c)]}.case;' for c in '()[]{}-–—'
            if cmap[ord(c)] + '.case' in font.getGlyphOrder()]
    if case:
        lines.append('feature case {' + ' '.join(case) + '} case;')
    from code_operators import feature_source
    lines.append(feature_source(font))
    return '\n'.join(lines) + '\n'


def compile_features(font, italic=False):
    cmap = font.getBestCmap()
    if all(cp in cmap for cp in (0x12F, 0x69, 0x131)):
        # Preserve the ogonek; only replace its dotted i component.
        original = font['glyf'][cmap[0x12F]]
        if original.isComposite():
            alternate = copy.deepcopy(original)
            for component in alternate.components:
                if component.glyphName == cmap[0x69]:
                    component.glyphName = cmap[0x131]
            name = cmap[0x12F] + '.dotless'
            font['glyf'][name] = alternate
            alternate.recalcBounds(font['glyf'])
            font['hmtx'][name] = (600, alternate.xMin)
            font.setGlyphOrder(list(dict.fromkeys(font.getGlyphOrder() + [name])))
    source = features(font, italic)
    for tag in ['GSUB', 'GPOS', 'GDEF', 'kern']:
        if tag in font:
            del font[tag]
    addOpenTypeFeaturesFromString(font, source)
    return source
