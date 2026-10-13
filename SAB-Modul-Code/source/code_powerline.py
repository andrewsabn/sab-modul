"""Original monochrome geometry for the Powerline PUA subset used by this project.

Assignments are drawn from upstream Powerline/Powerline Extra symbol lists. This
module contains fresh outlines, not contours extracted from their fonts.
"""
from __future__ import annotations

from math import cos, pi, sin
from shapely.geometry import GeometryCollection, LineString, Point, Polygon, box
from shapely.affinity import translate, scale
from shapely.ops import unary_union

STEMS = {300: 79, 400: 94, 500: 99, 600: 108, 700: 125}
CORE_POWERLINE = tuple(range(0xE0A0, 0xE0A4)) + tuple(range(0xE0B0, 0xE0BC))
CODEPOINTS = tuple(range(0xE0A0, 0xE0A4)) + tuple(range(0xE0B0, 0xE0C9))


def _union(shapes):
    shapes = [s for s in shapes if s is not None and not s.is_empty]
    return unary_union(shapes) if shapes else GeometryCollection()


def _stroke(weight):
    return STEMS[weight]


def _line(points, width):
    return LineString(points).buffer(width / 2, cap_style="round", join_style="round", quad_segs=8)


def _ring(shape, weight):
    """A monochrome outline for Unicode 'white' separator assignments."""
    t = max(22, round(STEMS[weight] * .34))
    inner = shape.buffer(-t, join_style="mitre")
    return shape.difference(inner) if not inner.is_empty else shape


def _triangle(direction):
    return {
        'right': Polygon([(0,0),(0,1000),(600,500)]),
        'left': Polygon([(600,0),(600,1000),(0,500)]),
        'down': Polygon([(0,1000),(600,1000),(300,0)]),
        'up': Polygon([(0,0),(600,0),(300,1000)]),
    }[direction]


def _quarter_triangle(which):
    pts = {
        'lower-left': [(0,0),(600,0),(0,1000)],
        'lower-right': [(0,0),(600,0),(600,1000)],
        'upper-left': [(0,1000),(0,0),(600,1000)],
        'upper-right': [(600,1000),(0,1000),(600,0)],
    }[which]
    return Polygon(pts)


def _open_chevron(direction, weight):
    # White triangle variants use the two diagonal strokes, leaving the base open.
    pts = [(0,0),(600,500),(0,1000)] if direction == 'right' else [(600,0),(0,500),(600,1000)]
    s=_stroke(weight)
    return _union([_line(pts[:2],s),_line(pts[1:],s)]).intersection(box(0,0,600,1000))


def _semicircle(direction):
    # Filled half-disc with vertical diameter at the cell edge and curved tip.
    if direction == 'right':
        pts = [(0,0)] + [(600*sin(pi*i/32), 500-500*cos(pi*i/32)) for i in range(33)] + [(0,1000)]
    else:
        pts = [(600,0)] + [(600-600*sin(pi*i/32), 500-500*cos(pi*i/32)) for i in range(33)] + [(600,1000)]
    return Polygon(pts)


def _flame(direction):
    # Three-lobed flame edge, simplified to a single original silhouette.
    pts = ([(0,0),(145,120),(115,235),(280,355),(235,475),(440,635),(390,760),(600,1000),(0,1000)]
           if direction == 'right' else
           [(600,0),(455,120),(485,235),(320,355),(365,475),(160,635),(210,760),(0,1000),(600,1000)])
    return Polygon(pts)


def _squares(direction, size):
    # A repeated stepped-square transition rather than a copied upstream contour.
    d = size
    cells=[]
    for row in range(3):
        for col in range(3):
            include = (col <= row) if direction == 'right' else (col >= 2-row)
            if include:
                x0 = col*200 + (200-d)/2
                y0 = row*(1000/3) + (1000/3-d)/2
                cells.append(box(x0,y0,x0+d,y0+d))
    # Horizontal transition edge touches both cell ends.
    cells += [box(0,0,35,1000), box(565,0,600,1000)]
    return _union(cells)


def _icicles():
    # Top edge remains flush; distinct downward triangular teeth make a path edge.
    pts=[(0,1000),(600,1000),(600,0),(500,280),(420,0),(330,370),(240,0),(150,280),(70,0),(0,210)]
    return Polygon(pts)


def _branch(weight):
    s=STEMS[weight]
    # Git branch: two stems, two joins, and three round node terminals.
    tracks=[_line([(180,120),(180,760)],s), _line([(180,430),(405,650),(405,880)],s)]
    tracks.extend(Point(x,y).buffer(s*.68,quad_segs=12) for x,y in [(180,120),(180,760),(405,880)])
    return _union(tracks)


def _line_number(weight, layers=False):
    s=STEMS[weight]
    # Compact LN marker, geometric lettering inside a rounded rectangular badge.
    outline=box(75,170,525,830).buffer(-s/2).boundary.buffer(s/2,join_style='round')
    l=_line([(170,650),(170,350),(260,350)],s)
    n=_line([(330,350),(330,650),(435,350),(435,650)],s)
    return [outline,l,n] if layers else _union([outline,l,n])


def _lock(weight, layers=False):
    s=STEMS[weight]
    body=box(125,120,475,570).buffer(-s/2).boundary.buffer(s/2,join_style='round')
    shackle=_line([(205,560),(205,735),(240,820),(300,860),(360,820),(395,735),(395,560)],s)
    keyhole=_union([Point(300,390).buffer(s*.58,quad_segs=10),_line([(300,370),(300,260)],s*.75)])
    return [body,shackle,keyhole] if layers else _union([body,shackle,keyhole])


def _column_number(weight):
    s=STEMS[weight]
    # Column marker: a corner bracket and number-like vertical/horizontal strokes.
    return _union([_line([(110,180),(110,820),(490,820)],s),
                   _line([(245,360),(245,640),(325,690),(395,640),(395,360)],s),
                   _line([(455,360),(455,690)],s)])


def _geometry(code, weight):
    if code == 0xE0A0: return _branch(weight)
    if code == 0xE0A1: return _line_number(weight)
    if code == 0xE0A2: return _lock(weight)
    if code == 0xE0A3: return _column_number(weight)
    core_dirs={0xE0B0:'right',0xE0B1:'right',0xE0B2:'left',0xE0B3:'left'}
    if code in core_dirs:
        shape=_triangle(core_dirs[code])
        return _open_chevron(core_dirs[code],weight) if code in (0xE0B1,0xE0B3) else shape
    if 0xE0B4 <= code <= 0xE0B7:
        direction='right' if code in (0xE0B4,0xE0B5) else 'left'
        shape=_semicircle(direction)
        return _ring(shape,weight) if code in (0xE0B5,0xE0B7) else shape
    if 0xE0B8 <= code <= 0xE0BF:
        group=(code-0xE0B8)//2
        which=('lower-left','lower-right','upper-left','upper-right')[group]
        shape=_quarter_triangle(which)
        return shape if code % 2 == 0 else _ring(shape,weight)
    if 0xE0C0 <= code <= 0xE0C3:
        direction='right' if code in (0xE0C0,0xE0C1) else 'left'
        shape=_flame(direction)
        return _ring(shape,weight) if code in (0xE0C1,0xE0C3) else shape
    if 0xE0C4 <= code <= 0xE0C7:
        direction='right' if code in (0xE0C4,0xE0C6) else 'left'
        size=120 if code in (0xE0C4,0xE0C5) else 190
        return _squares(direction,size)
    if code == 0xE0C8: return _icicles()
    raise KeyError(f"No Powerline assignment for U+{code:04X}")


def geometries(weight: int, italic: bool = False) -> dict[str, object]:
    """Return all 29 assigned glyph geometries with one 600-unit advance.

    PUA separator silhouettes stay upright in italic masters so adjacent segment
    backgrounds keep the same full-cell joins. Weight changes internal strokes.
    """
    if weight not in STEMS:
        raise ValueError(f"Unsupported weight: {weight}")
    # Full-cell separators align to the box/block bounds; standalone icons retain their scale.
    return {chr(cp): translate(scale(_geometry(cp,weight),xfact=1,yfact=1.6,origin=(0,0)),yoff=-450)
            if cp>=0xE0B0 else translate(_geometry(cp,weight),yoff=-150) for cp in CODEPOINTS}


def selfcheck():
    from shapely.validation import explain_validity
    all_results={}
    for weight in STEMS:
        for italic in (False,True):
            g=geometries(weight,italic)
            assert len(g)==29
            for ch,shape in g.items():
                assert not shape.is_empty, f"empty U+{ord(ch):04X}"
                assert shape.is_valid, f"invalid U+{ord(ch):04X}: {explain_validity(shape)}"
                x0,y0,x1,y1=shape.bounds
                assert x0 >= -1 and x1 <= 601 and y0 >= -451 and y1 <= 1151, f"out of cell U+{ord(ch):04X}: {shape.bounds}"
            all_results[f"{weight}-{'italic' if italic else 'roman'}"]={'count':len(g),'all_valid_nonempty':True}
    return {'status':'PASS','weights':all_results,'advance':600,'italic_shear':False}


if __name__ == '__main__':
    import json
    print(json.dumps(selfcheck(),indent=2))
