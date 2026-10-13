"""Own geometric drawings for arrows, mathematics, keyboard legends, and markers."""
from math import pi, sin, cos

from shapely.affinity import affine_transform, scale, translate
from shapely.geometry import Point, Polygon, box
from shapely.ops import unary_union

from code_symbols import STEMS, SHEAR, _line, _curve, _cubic, _fit_cell

MATH_CODEPOINTS = (
    0x2200, 0x2202, 0x2203, 0x2205, 0x2206, 0x2207, 0x2208, 0x2209,
    0x220B, 0x220F, 0x2211, 0x2212, 0x2213, 0x2217, 0x2218, 0x2219,
    0x221A, 0x221D, 0x221E, 0x2220, 0x2223, 0x2225, 0x2227, 0x2228,
    0x2229, 0x222A, 0x222B, 0x2234, 0x2235, 0x223C, 0x2248, 0x2260,
    0x2261, 0x2264, 0x2265, 0x2282, 0x2283, 0x2286, 0x2287, 0x2295,
    0x2297, 0x22A5,
)
assert len(MATH_CODEPOINTS) >= 40 and all(0x2200 <= cp <= 0x22FF for cp in MATH_CODEPOINTS)

ARROWS = ''.join(chr(cp) for cp in (*range(0x2190, 0x219A), *range(0x21D0, 0x21DA)))
KEYS = '⌘⌥⇧⌃⏎⌫␣'
MARKERS = '✓✗•◦▪▫○●◆◇▶▼▲◀'


def _oval(x, y, rx, ry, width):
    outer = scale(Point(x, y).buffer(1, quad_segs=20), rx, ry, origin=(x, y))
    inner = scale(Point(x, y).buffer(1, quad_segs=20), max(0, rx-width), max(0, ry-width), origin=(x, y))
    return outer.difference(inner)


def _poly(points, width):
    return _line(points, width, cap='round')


def _math_shapes(stem, layers=False):
    S = lambda pts: _poly(pts, stem)
    C = lambda pts: _curve(pts, stem)
    U = unary_union
    ring = lambda x,y,r: _oval(x,y,r,r,stem)
    d = {}
    # Quantifiers and set relations.
    d['∀'] = U([S([(100,480),(300,60),(500,480)]), S([(185,300),(415,300)])])
    d['∂'] = U([_oval(285,210,175,175,stem), C(_cubic((460,210),(530,470),(350,650),(180,490)))])
    d['∃'] = U([S([(120,480),(480,480),(480,60),(120,60)]), S([(180,270),(480,270)])])
    d['∅'] = U([ring(300,270,205), S([(130,90),(470,450)])])
    d['∆'] = S([(100,85),(300,455),(500,85),(100,85)])
    d['∇'] = S([(100,455),(300,85),(500,455),(100,455)])
    d['∈'] = U([C(_cubic((480,450),(50,500),(50,40),(480,90))), S([(157,270),(480,270)])])
    d['∉'] = U([d['∈'], S([(140,90),(460,450)])])
    d['∋'] = affine_transform(d['∈'], [-1,0,0,1,600,0])
    d['∏'] = U([S([(110,455),(490,455)]), S([(155,455),(155,85)]), S([(445,455),(445,85)])])
    d['∑'] = S([(490,455),(135,455),(385,270),(135,85),(490,85)])
    d['−'] = S([(105,270),(495,270)])
    d['∓'] = U([S([(130,410),(470,410)]), S([(300,60),(300,240)]), S([(130,150),(470,150)])])
    d['∗'] = U([S([(300,65),(300,475)]), S([(125,165),(475,375)]), S([(125,375),(475,165)])])
    d['∘'] = ring(300,270,170)
    d['∙'] = Point(300,270).buffer(72, quad_segs=20)
    d['√'] = S([(85,235),(155,235),(220,60),(340,490),(495,490)])
    d['∝'] = C(_cubic((515,435),(430,445),(380,430),(300,270)) + _cubic((300,270),(220,110),(85,95),(85,270))[1:] +
                _cubic((85,270),(85,445),(220,430),(300,270))[1:] + _cubic((300,270),(380,110),(430,95),(515,105))[1:])
    d['∞'] = C(_cubic((300,270),(200,455),(80,445),(80,270)) + _cubic((80,270),(80,95),(200,85),(300,270))[1:] +
                _cubic((300,270),(400,455),(520,445),(520,270))[1:] + _cubic((520,270),(520,95),(400,85),(300,270))[1:])
    d['∠'] = S([(475,460),(115,90),(490,90)])
    d['∣'] = S([(300,70),(300,470)])
    d['∥'] = U([S([(225,70),(225,470)]), S([(375,70),(375,470)])])
    d['∧'] = S([(90,140),(300,430),(510,140)])
    d['∨'] = S([(90,400),(300,110),(510,400)])
    d['∩'] = C([(90,120)] + _cubic((90,120),(90,390),(510,390),(510,120))[1:])
    d['∪'] = C([(90,420)] + _cubic((90,420),(90,150),(510,150),(510,420))[1:])
    d['∫'] = C(_cubic((370,510),(210,545),(395,145),(230,50)))
    d['∴'] = U([Point(x,y).buffer(50,quad_segs=12) for x,y in [(180,150),(420,150),(300,390)]])
    d['∵'] = U([Point(x,y).buffer(50,quad_segs=12) for x,y in [(180,390),(420,390),(300,150)]])
    wave=[(95+410*i/48,270+58*sin(2*pi*i/48)) for i in range(49)]
    d['∼'] = C(wave)
    d['≈'] = U([translate(C(wave),yoff=100), translate(C(wave),yoff=-100)])
    d['≠'] = U([S([(100,380),(500,380)]),S([(100,160),(500,160)]),S([(175,90),(425,450)])])
    d['≡'] = U([S([(110,480),(490,480)]),S([(110,270),(490,270)]),S([(110,60),(490,60)])])
    d['≤'] = U([S([(440,505),(140,340),(440,175)]),S([(140,0),(490,0)])])
    d['≥'] = affine_transform(d['≤'],[-1,0,0,1,600,0])
    d['⊂'] = C(_cubic((465,440),(105,520),(80,90),(465,100)) + [(465,100)])
    d['⊃'] = affine_transform(d['⊂'],[-1,0,0,1,600,0])
    d['⊆'] = U([translate(d['⊂'],yoff=70),S([(140,-20),(490,-20)])])
    d['⊇'] = affine_transform(d['⊆'],[-1,0,0,1,600,0])
    enclosed=lambda pts:_line(pts,stem*.65)
    circle=_oval(300,270,220,220,stem*.55)
    d['⊕'] = U([circle,enclosed([(300,105),(300,435)]),enclosed([(135,270),(465,270)])])
    d['⊗'] = U([circle,enclosed([(180,150),(420,390)]),enclosed([(180,390),(420,150)])])
    d['⊥'] = U([S([(100,145),(500,145)]),S([(300,145),(300,445)])])
    if layers:
        d['∉'] = [d['∈'], S([(140,90),(460,450)])]
        d['⊕'] = [circle,enclosed([(300,105),(300,435)]),enclosed([(135,270),(465,270)])]
        d['⊗'] = [circle,enclosed([(180,150),(420,390)]),enclosed([(180,390),(420,150)])]
    return d


def _arrows(stem):
    # Construct heads at the shaft endpoints, including the diagonal directions.
    from math import hypot
    width=round(stem*1.1)
    specs={
        '←':(-1,0,False), '→':(1,0,False), '↑':(0,1,False), '↓':(0,-1,False),
        '↖':(-1,1,False), '↗':(1,1,False), '↘':(1,-1,False), '↙':(-1,-1,False),
        '↔':(1,0,True), '↕':(0,1,True),
    }
    result={}
    for single,double in zip('←↑→↓↔↕↖↗↘↙','⇐⇑⇒⇓⇔⇕⇖⇗⇘⇙'):
        dx,dy,both=specs[single];length=hypot(dx,dy);ux,uy=dx/length,dy/length;nx,ny=-uy,ux
        half=205 if not (dx and dy) else 240
        start=(300-ux*half,270-uy*half);end=(300+ux*half,270+uy*half)
        def head(point,sign):
            px,py=point;bx,by=px-sign*ux*155,py-sign*uy*155
            return [(bx+nx*145,by+ny*145),(px,py),(bx-nx*145,by-ny*145)]
        heads=[_line(head(end,1),width)]
        if both:heads.append(_line(head(start,-1),width))
        result[single]=unary_union([_line([start,end],width),*heads])
        # One open head and two parallel rails, with clear space between rails.
        rail=round(width*.55);offset=rail*.95
        double_heads=[_line(head(end,1),rail)]
        if both:double_heads.append(_line(head(start,-1),rail))
        rails=[]
        for sign in [-1,1]:
            trim=offset*155/145
            a=(start[0]+nx*offset*sign+(ux*trim if both else 0),start[1]+ny*offset*sign+(uy*trim if both else 0))
            b=(end[0]+nx*offset*sign-ux*trim,end[1]+ny*offset*sign-uy*trim)
            rails.append(_line([a,b],rail))
        result[double]=unary_union([*rails,*double_heads])
    return result


def _keyboard(stem):
    # Keyboard symbols use thinner strokes so enclosed counters remain open.
    s=stem*.65;S=lambda p:_line(p,s);C=lambda p:_curve(p,s);U=unary_union;d={}
    # Command has four closed loops joined by a central square.
    command_width=stem*.35
    loops=[_oval(x,y,80,80,command_width) for x,y in [(140,110),(140,430),(460,110),(460,430)]]
    # Lines meet loop tangents; passing through the loop centers would fill them.
    rails=[[(220,110),(220,430)],[(380,110),(380,430)],[(140,190),(460,190)],[(140,350),(460,350)]]
    d['⌘']=U([*loops,*[_line(points,command_width) for points in rails]])
    d['⌥']=U([S([(95,440),(220,440),(395,100),(510,100)]),S([(330,440),(510,440)])])
    d['⇧']=S([(300,500),(95,295),(210,295),(210,70),(390,70),(390,295),(505,295),(300,500)])
    d['⌃']=S([(100,170),(300,430),(500,170)])
    d['⏎']=U([S([(485,470),(485,230),(105,230)]),S([(245,370),(105,230),(245,90)])])
    d['⌫']=U([S([(70,270),(215,450),(525,450),(525,90),(215,90),(70,270)]),S([(275,345),(445,175)]),S([(445,345),(275,175)])])
    d['␣']=S([(100,365),(100,160),(500,160),(500,365)])
    return d


def _markers(stem):
    s=stem;S=lambda p:_poly(p,s);U=unary_union;d={}
    d['✓']=S([(95,270),(235,115),(505,440)])
    d['✗']=U([S([(135,100),(465,440)]),S([(135,440),(465,100)])])
    d['•']=Point(300,270).buffer(105,quad_segs=20)
    d['◦']=_oval(300,270,105,105,s*.5)
    d['▪']=box(205,175,395,365)
    d['▫']=box(190,160,410,380).difference(box(190+s*.5,160+s*.5,410-s*.5,380-s*.5))
    d['○']=_oval(300,270,190,190,s)
    d['●']=Point(300,270).buffer(190,quad_segs=20)
    d['◆']=Polygon([(300,490),(510,270),(300,50),(90,270)])
    d['◇']=Polygon([(300,490),(510,270),(300,50),(90,270)]).difference(Polygon([(300,490-s),(510-s,270),(300,50+s),(90+s,270)]))
    d['▶']=Polygon([(165,475),(475,270),(165,65)])
    d['▼']=Polygon([(90,430),(510,430),(300,70)])
    d['▲']=Polygon([(90,110),(510,110),(300,470)])
    d['◀']=Polygon([(435,475),(125,270),(435,65)])
    return d


def geometries(weight: int, italic: bool=False) -> dict[str, object]:
    """Return own, cell-centered 600-unit geometries keyed by Unicode characters."""
    if weight not in STEMS:
        raise ValueError(f'Unsupported weight: {weight}')
    stem=STEMS[weight]
    result={**_arrows(stem),**_math_shapes(stem),**_keyboard(stem),**_markers(stem)}
    assert set(ARROWS)<=result.keys() and set(KEYS)<=result.keys() and set(MARKERS)<=result.keys()
    assert set(map(ord,result)) & set(MATH_CODEPOINTS)==set(MATH_CODEPOINTS)
    if italic:
        result={ch:affine_transform(g,[1,SHEAR,0,1,-270*SHEAR,0]) for ch,g in result.items()}
    result={ch:_fit_cell(g) for ch,g in result.items()}
    assert all(not g.is_empty and g.is_valid and g.bounds[0]>=-1e-6 and g.bounds[2]<=600+1e-6 for g in result.values())
    return result


if __name__ == '__main__':
    for w in STEMS:
        for italic in (False,True):
            shapes=geometries(w,italic)
            assert len(shapes)==len(set(shapes))
            assert len(set(map(ord,shapes)) & set(MATH_CODEPOINTS))>=40
            print(w,italic,len(shapes),len(MATH_CODEPOINTS),'PASS')
