"""Cell-preserving contextual operators drawn from this family's own geometry."""
from shapely.affinity import translate, affine_transform
from shapely.geometry import box
from shapely.ops import unary_union
from code_symbols import STEMS, SHEAR, _line, _dot, _master_glyph, _shear_safe_line, _question_shape

OPERATORS = ['!==', '===', '...', '->', '=>', '<-', '<=', '>=', '!=', '==',
             '::', '++', '--', '||', '&&', '??', '|>', '<|', '//']


def parts(weight, italic=False, compatible=False):
    width = STEMS[weight] * 1.1
    result = {}
    for index, sequence in enumerate(OPERATORS):
        n = len(sequence)
        end = n * 600 - 120
        def line(points):
            if italic and sequence in ('<-', '>=', '<|'):
                # Reflection reverses the shear used to compensate stroke width.
                points = [(-x, y) for x, y in points]
                return affine_transform(_shear_safe_line(points, width, True), [-1,0,0,1,0,0])
            return _shear_safe_line(points, width, italic)
        layers = None
        if sequence in ('->', '=>', '<-'):
            tip = end
            head = line([(tip-220, 470), (tip, 270), (tip-220, 70)])
            # Match the equals-sign spacing; the old 150-unit separation merged at Bold 16px.
            shafts = [line([(120, y), (tip-(30 if compatible and sequence != '=>' else 80), y)]) for y in ([160, 380] if sequence == '=>' else [270])]
            shape = unary_union([head, *shafts])
            if sequence == '<-':
                shape = affine_transform(shape, [-1, 0, 0, 1, n*600, 0])
        elif sequence in ('==', '===', '!=', '!=='):
            levels = [60, 270, 480] if len(sequence) == 3 else [160, 380]
            layers = [line([(120, y), (end, y)]) for y in levels]
            shape = unary_union(layers)
            if sequence[0] == '!':
                layers.append(line([(n*300-160, 5), (n*300+160, 535)]))
                shape = unary_union(layers)
        elif sequence in ('<=', '>='):
            shape = unary_union([line([(end, 510), (140, 310), (end, 110)]),
                                 line([(140, -65), (end, -65)])])
            if sequence == '>=':
                shape = affine_transform(shape, [-1, 0, 0, 1, n*600, 0])
            shape = translate(shape, yoff=270-(shape.bounds[1]+shape.bounds[3])/2)
        elif sequence == '--':
            shape = line([(130, 270), (end-10, 270)])
        elif sequence == '++':
            shape = unary_union([line([(130, 270), (end-10, 270)]),
                                 *[line([(x, 70), (x, 470)]) for x in [300, 900]]])
        elif sequence == '...':
            shape = unary_union([_dot(x, 70, 160) for x in [360, 900, 1440]])
        elif sequence == '::':
            shape = unary_union([_dot(x, y, 160) for x in [390, 810] for y in [70, 430]])
        elif sequence == '||':
            shape = unary_union([_line([(x, -100), (x, 900)], STEMS[weight]*.65) for x in [400, 800]])
        elif sequence in ('&&', '??'):
            if sequence == '??':
                for cell, offset in enumerate((35, 565)):
                    piece = translate(_question_shape(STEMS[weight], italic), xoff=offset)
                    if italic:
                        piece = affine_transform(piece, [1, SHEAR, 0, 1, -270*SHEAR, 0])
                    # Keep each question intact; clipping at x=600 changes topology across weights.
                    result[f'code.op{index}.{cell}'] = translate(piece, xoff=-cell*600)
                continue
            shape = unary_union([translate(_master_glyph('&', weight, False), xoff=12 if compatible else 65),
                                 translate(_master_glyph('&', weight, False), xoff=588 if compatible else 535)])
        elif sequence == '//':
            shape = unary_union([_shear_safe_line([(x-145, -100), (x+145, 760)], STEMS[weight]*1.1, italic) for x in [380, 820]])
        else:  # Pipelines retain both the vertical delimiter and the open arrowhead.
            shape = unary_union([line([(230, 20), (230, 520)]),
                                 line([(700, 470), (1020, 270), (700, 70)])])
            if sequence == '<|':
                shape = affine_transform(shape, [-1, 0, 0, 1, 1200, 0])
        if compatible and layers is not None:
            if italic:
                layers = [affine_transform(g, [1, SHEAR, 0, 1, -270*SHEAR, 0]) for g in layers]
            for cell in range(n):
                result[f'code.op{index}.{cell}'] = [translate(g.intersection(box(cell*600, -1200, (cell+1)*600, 1800)), xoff=-cell*600) for g in layers]
            continue
        if italic:
            shape = affine_transform(shape, [1, SHEAR, 0, 1, -270*SHEAR, 0])
        assert shape.bounds[0] >= 0 and shape.bounds[2] <= n*600, (sequence, shape.bounds)
        for cell in range(n):
            piece = translate(shape.intersection(box(cell*600, -1200, (cell+1)*600, 1800)), xoff=-cell*600)
            assert not piece.is_empty, (sequence, cell)
            result[f'code.op{index}.{cell}'] = piece
    return result


def feature_source(font):
    """All contextual outputs still have one glyph and one advance per character."""
    if 'code.op0.0' not in font.getGlyphOrder():
        return ''
    cmap = font.getBestCmap()
    boundary=' '.join(cmap[ord(c)] for c in '!%&*+-./:<=>?^|~')
    lines, rules, restores = [f'@CodeOpBoundary = [{boundary}];'], [], []
    for index, sequence in enumerate(OPERATORS):
        marked = []
        for cell, char in enumerate(sequence):
            base, alternate = cmap[ord(char)], f'code.op{index}.{cell}'
            lookup = f'CodeOp{index}Part{cell}'
            lines.append(f'lookup {lookup} {{ sub {base} by {alternate}; }} {lookup};')
            marked.append(f"{base}' lookup {lookup}")
            restores.append(f'sub {alternate} by {base};')
        context=' '.join(cmap[ord(c)]+"'" for c in sequence)
        rules.extend([f'ignore sub @CodeOpBoundary {context};',f'ignore sub {context} @CodeOpBoundary;',
                      'sub ' + ' '.join(marked) + ';'])
    lines.append('feature calt {\n' + '\n'.join(rules) + '\n} calt;')
    # Lookup order is intentional: ss10 restores every calt output even if both are enabled.
    lines.append('feature ss10 {\n' + '\n'.join(restores) + '\n} ss10;')
    return '\n'.join(lines) + '\n'
