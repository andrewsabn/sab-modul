"""Original geometric drawings for SAB Modul Code punctuation and identifiers."""
from math import cos, radians, sin, pi
from functools import lru_cache
from pathlib import Path

from shapely.affinity import affine_transform, translate
from shapely.geometry import GeometryCollection, LineString, Point, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union
from fontTools.ttLib import TTFont

STEMS = {300: 79, 400: 94, 500: 99, 600: 108, 700: 125}
ANGLE = radians(10)
SHEAR = sin(ANGLE) / cos(ANGLE)


def _line(points, width, cap="square"):
    return LineString(points).buffer(width / 2, cap_style="flat" if cap == "square" else cap, join_style="round", quad_segs=8)


def _shear_safe_line(points, width, italic=False, cap="square"):
    """Return pre-shear geometry whose final normal stroke equals width."""
    if not italic:
        return _line(points, width, cap)
    points = [(x + SHEAR * (y - 270), y) for x, y in points]
    return affine_transform(_line(points, width, cap), [1, -SHEAR, 0, 1, 270*SHEAR, 0])


def _dot(x, y, diameter):
    return Point(x, y).buffer(diameter / 2, quad_segs=16)


def _bezier(start, control, end, count=16):
    return [((1-t)**2*start[0] + 2*(1-t)*t*control[0] + t*t*end[0],
             (1-t)**2*start[1] + 2*(1-t)*t*control[1] + t*t*end[1]) for t in (i/count for i in range(count+1))]


def _curve(points, width):
    return _line(points, width, cap="round")


def _cubic(start, control1, control2, end, count=20):
    return [((1-t)**3*start[0] + 3*(1-t)**2*t*control1[0] + 3*(1-t)*t*t*control2[0] + t**3*end[0],
             (1-t)**3*start[1] + 3*(1-t)**2*t*control1[1] + 3*(1-t)*t*t*control2[1] + t**3*end[1]) for t in (i/count for i in range(count+1))]


def _ring_polygon(points):
    # Insert TrueType implied on-curve points between adjacent off-curve controls.
    expanded = []
    for i, point in enumerate(points):
        expanded.append(point)
        if not point[1] and not points[(i+1) % len(points)][1]:
            nxt = points[(i+1) % len(points)][0]
            expanded.append((((point[0][0]+nxt[0])/2, (point[0][1]+nxt[1])/2), True))
    first = next(i for i,p in enumerate(expanded) if p[1])
    expanded = expanded[first:] + expanded[:first]
    start = expanded[0][0]
    path = [start]
    current = start
    i = 1
    while i < len(expanded):
        point, oncurve = expanded[i]
        if oncurve:
            path.append(point)
            current = point
            i += 1
        else:
            end = expanded[(i+1) % len(expanded)][0]
            path.extend(_bezier(current, point, end, 8)[1:])
            current = end
            i += 2
    return Polygon(path).buffer(0)


@lru_cache(maxsize=128)
def _master_contours(char, weight, italic):
    """Read contours from this project's Code master, never external outlines."""
    root = Path(__file__).resolve().parents[1]
    style = {300:'Light', 400:'Regular', 500:'Medium', 600:'SemiBold', 700:'Bold'}[weight]
    path = root / 'source/code-masters' / f'SABModulCode-{style}{"Italic" if italic else ""}.ttf'
    font = TTFont(path)
    glyph_name = font.getBestCmap().get(ord(char))
    if glyph_name is None:
        raise KeyError(f"Code master lacks {char!r}")
    glyph = font['glyf'][glyph_name]
    coords, ends, flags = glyph.getCoordinates(font['glyf'])
    if not ends:
        return ()
    contours=[]
    start=0
    for end in ends:
        contours.append(_ring_polygon([((coords[i][0],coords[i][1]), bool(flags[i]&1)) for i in range(start,end+1)]))
        start=end+1
    return tuple(contours)


def _master_glyph(char, weight, italic):
    contours=sorted(_master_contours(char, weight, italic), key=lambda p:p.area, reverse=True)
    if not contours:
        return GeometryCollection()
    parents=[]
    depths=[]
    for i, contour in enumerate(contours):
        parent=next((j for j in range(i-1,-1,-1) if contours[j].contains(contour.representative_point())),None)
        parents.append(parent)
        depths.append(0 if parent is None else depths[parent]+1)
    filled=[]
    for i,contour in enumerate(contours):
        if depths[i] % 2 == 0:
            holes=[list(contours[j].exterior.coords) for j,p in enumerate(parents) if p==i and depths[j] % 2 == 1]
            filled.append(Polygon(contour.exterior.coords, holes).buffer(0))
    return unary_union(filled)


def _zero_alternates(weight, italic):
    contours = _master_contours('0', weight, italic)
    if len(contours) != 3:
        raise ValueError(f"Expected three contours in own zero, found {len(contours)}")
    # The two original counters bound the empty interior. Subtract their hull from
    # the outer contour; subtracting a guessed slash left diagonal spikes.
    interior = contours[1].union(contours[2]).convex_hull
    empty = contours[0].difference(interior)
    center = interior.centroid
    return empty, empty.union(_dot(center.x,center.y,160))


def _fit_cell(shape):
    minx, _, maxx, _ = shape.bounds
    if maxx-minx > 600:
        raise ValueError(f"Drawing exceeds 600-unit cell: {shape.bounds}")
    return translate(shape, xoff=(600-(maxx-minx))/2-minx)


def _question_shape(stem,italic=False):
    hook=(_cubic((140,560),(140,690),(460,690),(460,560))
          +_cubic((460,560),(460,470),(300,465),(300,380))[1:]+[(300,245)])
    return unary_union([_shear_safe_line(hook,stem*1.2,italic,'round'),
                        _dot(300,70,164 if italic else 160)])


def _drawings(weight, italic):
    stem = STEMS[weight]
    op = stem*1.1
    punct = stem*1.2
    vstem = stem / cos(ANGLE) if italic else stem
    vop = op / cos(ANGLE) if italic else op
    vp = punct / cos(ANGLE) if italic else punct
    S = lambda points, width, cap="square": _shear_safe_line(points, width, italic, cap)
    C = lambda points, width: S(points, width, cap="round")
    U = unary_union
    d = {}

    # A flat-topped digit 3 contrasts structurally with the original round Cyrillic Ze.
    top = 700 - stem / 2
    bowl = (_cubic((265,390),(585,440),(570,60),(330,stem/2))
            + _cubic((330,stem/2),(225,stem/2),(150,stem/2+25),(120,140))[1:])
    d['3'] = U([S([(135,top),(465,top)],stem), C([(465,top),(265,390)],stem), C(bowl,stem)])
    d['|'] = S([(300,-100),(300,900)], stem*.65)
    d['¦'] = U([S([(300,-126),(300,278)],punct),S([(300,378),(300,780)],punct)])
    d['!'] = U([S([(300,185),(300,700)],punct),_dot(300,70,164 if italic else 160)])
    d['?'] = _question_shape(stem,italic)

    # Straight and typographic quotation marks use different heights and shapes.
    d["'"] = _shear_safe_line([(300, 490), (300, 730)], stem*1.2, italic)
    d['"'] = U([_shear_safe_line([(x, 520), (x, 730)], stem*1.2, italic) for x in (200, 400)])
    d['`'] = _shear_safe_line([(405, 730), (195, 470)], stem*1.2, italic)
    opening = C(_bezier((60, 720), (-60, 675), (-35, 530)), punct)
    closing = affine_transform(opening, [-1, 0, 0, -1, 0, 1250])
    d['‘'], d['’'] = (translate(shape, xoff=300) for shape in [opening, closing])
    d['“'] = U([translate(opening, xoff=x) for x in [155, 445]])
    d['”'] = U([translate(closing, xoff=x) for x in [155, 445]])

    # Punctuation dots keep the requested 160-unit visible diameter.
    diameter = 164 if italic else 160
    dot = _dot(300, 70, diameter)
    comma_tail = C([(300, -10), (300, -70), (255, -145)], punct)
    d['.'] = dot
    d[','] = U([dot, comma_tail])
    d[':'] = U([_dot(300, 430, diameter), dot])
    d[';'] = U([_dot(300, 430, diameter), dot, comma_tail])

    # Dashes and mathematical operators share the y=270 center axis.
    d['-'] = S([(170, 270), (430, 270)], op)
    d['–'] = S([(125, 270), (475, 270)], op)
    d['—'] = S([(90, 270), (510, 270)], op)
    d['−'] = S([(115, 270), (485, 270)], op)
    d['_'] = S([(110, -145), (490, -145)], op)
    d['~'] = C([(105+390*i/40, 270+90*sin(2*pi*i/40)) for i in range(41)], op)

    # Tall delimiters span exact -300..1000 extents including stroke edges.
    lo, hi = -300, 1000
    half=vp/2
    d['('] = C(_cubic((390,hi-half),(100,hi-150),(100,lo+150),(390,lo+half), 48), punct)
    d[')'] = affine_transform(d['('], [-1,0,0,1,600,0])
    d['['] = U([box(180,lo,180+vp,hi), box(180,hi-vp,400,hi), box(180,lo,400,lo+vp)])
    d[']'] = affine_transform(d['['], [-1,0,0,1,600,0])
    brace_top = (_cubic((410,hi-half),(300,hi-half),(300,860),(300,665))
                 + _cubic((300,665),(300,460),(300,350),(195,350))[1:])
    brace_left = brace_top + [(x,700-y) for x,y in reversed(brace_top[:-1])]
    brace_right=[(600-x,y) for x,y in brace_left]
    d['{'] = C(brace_left, punct)
    d['}'] = C(brace_right, punct)
    # Angle brackets are operator forms centered on the operator axis, not full-height delimiters.
    d['<'] = S([(470, 500), (130, 270), (470, 40)], op)
    d['>'] = S([(130, 500), (470, 270), (130, 40)], op)

    # Operators and technical punctuation.
    d['+'] = U([S([(300, 80), (300, 460)], op), S([(110, 270), (490, 270)], op)])
    d['×'] = U([S([(165, 405), (435, 135)], op), S([(165, 135), (435, 405)], op)])
    d['='] = U([S([(110, 380), (490, 380)], op), S([(110, 160), (490, 160)], op)])
    d['/'] = _shear_safe_line([(155, -100), (445, 760)], stem*1.1, italic)
    d['\\'] = _shear_safe_line([(155, 760), (445, -100)], stem*1.1, italic)
    rays=[]
    for i in range(5):
        a=-pi/2+i*2*pi/5
        rays.append(S([(300,270),(300+230*cos(a),270+230*sin(a))], op))
    d['*'] = U(rays)
    d['#'] = U([S([(185, -55), (185, 595)], op), S([(415, -55), (415, 595)], op), S([(55, 150), (545, 150)], op), S([(55, 390), (545, 390)], op)])
    d['^'] = S([(140, 350), (300, 680), (460, 350)], op - 0.1)  # Avoid outward integer rounding of both diagonals.

    percent_parts = _master_contours('%', weight, False)
    old_slash = max(percent_parts, key=lambda p: p.bounds[3] - p.bounds[1])
    percent_rings = _master_glyph('%', weight, False).difference(old_slash)
    d['%'] = U([percent_rings, S([(110,45),(490,655)],op + 0.2)])

    if italic:
        result = {}
        for key, shape in d.items():
            shape = affine_transform(shape, [1, SHEAR, 0, 1, -270*SHEAR, 0])
            result[key] = _fit_cell(shape)
        d = result
    for char in '<>':
        shape = d[char]
        d[char] = translate(shape, yoff=270-(shape.bounds[1]+shape.bounds[3])/2)
    for char, shape in zip('()[]{}', (d[x] for x in '()[]{}')):
        minx,miny,maxx,maxy=shape.bounds
        d[char]=affine_transform(shape,[1,0,0,1300/(maxy-miny),0,-300-miny*1300/(maxy-miny)])
    # Both zero alternates use the actual zero oval after removing only its slash interior.
    d['zero.empty'],d['zero.dotted']=_zero_alternates(weight,italic)
    return d


def geometries(weight: int, italic: bool = False) -> dict[str, BaseGeometry]:
    """Return original 600-unit Unicode drawings for one weight and style."""
    if weight not in STEMS:
        raise ValueError(f"Unsupported weight: {weight}")
    return _drawings(weight, italic)
