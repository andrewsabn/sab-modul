"""Original orthogonal terminal geometry, decoded from Unicode direction names."""
import json, unicodedata
from shapely.geometry import box, LineString
from shapely.ops import unary_union
from code_symbols import STEMS, _cubic, _line

CELL=box(0,-450,600,1150)
ENDS={'LEFT':(0,350),'RIGHT':(600,350),'UP':(300,1150),'DOWN':(300,-450)}


def directions(name):
    words=name.replace('BOX DRAWINGS ','').replace('ARC ','')
    default=next((w for w in words.split() if w in ['LIGHT','HEAVY','SINGLE','DOUBLE']), 'LIGHT')
    result={}
    for clause in words.split(' AND '):
        tokens=clause.split()
        style=next((w for w in tokens if w in ['LIGHT','HEAVY','SINGLE','DOUBLE']),default)
        for direction in ENDS:
            if direction in tokens or ('HORIZONTAL' in tokens and direction in ['LEFT','RIGHT']) or ('VERTICAL' in tokens and direction in ['UP','DOWN']):
                result[direction]=style
    return result


def arm(direction, width):
    x,y=ENDS[direction];r=width/2
    return box(min(300,x)-r,min(350,y)-r,max(300,x)+r,max(350,y)+r).intersection(CELL)


def drawing(cp, weight):
    name=unicodedata.name(chr(cp));t=STEMS[weight];heavy=round(t*1.58)
    if 'DASH' in name:
        n=4 if 'QUADRUPLE' in name else 3 if 'TRIPLE' in name else 2
        length=600 if 'HORIZONTAL' in name else 1600
        width=heavy if 'HEAVY' in name else t
        pieces=[]
        for i in range(n):
            a=(i+.16)*length/n;b=(i+.84)*length/n
            pieces.append(box(a,350-width/2,b,350+width/2) if length==600 else box(300-width/2,-450+a,300+width/2,-450+b))
        return unary_union(pieces)
    if 'DIAGONAL' in name:
        slash=_line([(0,-450),(600,1150)],t)
        back=_line([(0,1150),(600,-450)],t)
        shape=unary_union([slash,back]) if 'CROSS' in name else slash if 'UPPER RIGHT' in name else back
        return shape.intersection(CELL)
    if 'ARC' in name:
        points=[(300,-450),(300,170)]+_cubic((300,170),(300,269.4),(380.6,350),(480,350))[1:]+[(600,350)]
        from shapely.affinity import affine_transform
        shape=_line(points,t)
        if 'LEFT' in name:shape=affine_transform(shape,[-1,0,0,1,600,0])
        if 'UP' in name:shape=affine_transform(shape,[1,0,0,-1,0,700])
        return shape.intersection(CELL)
    arms=directions(name)
    if 'DOUBLE' not in arms.values():
        return unary_union([arm(d,heavy if s=='HEAVY' else t) for d,s in arms.items()])
    # A border of an orthogonal network creates joined double rails without
    # crossing an absent arm. Open each port at the cell boundary.
    rail=round(t*.55);gap=round(t*.55);outer=2*rail+gap
    double=[d for d,s in arms.items() if s=='DOUBLE']
    outside=unary_union([arm(d,outer) for d in double])
    inside=unary_union([arm(d,gap) for d in double])
    shape=outside.difference(inside)
    for d,s in arms.items():
        if s!='DOUBLE':
            # Extend the single stem to the far double rail at a mixed join.
            shape=shape.union(arm(d,t)).union(box(300-t/2,350-outer/2,300+t/2,350+outer/2) if d in ['UP','DOWN'] else box(300-outer/2,350-t/2,300+outer/2,350+t/2))
    return shape.intersection(CELL)


def block(cp):
    # Full terminal-height cells are aligned to the same y=350 center as the rules.
    lo,hi=-450,1150
    if cp==0x2580:return box(0,350,600,hi)
    if 0x2581<=cp<=0x2588:return box(0,lo,600,lo+1600*(cp-0x2580)/8)
    if 0x2589<=cp<=0x258F:return box(0,lo,600*(0x2590-cp)/8,hi)
    if cp==0x2590:return box(300,lo,600,hi)
    if cp in [0x2591,0x2592,0x2593]:
        # Exact 25/50/75% ink area. Pattern topology stays constant at every weight.
        threshold={0x2591:1,0x2592:2,0x2593:3}[cp]
        return unary_union([box(x*75,lo+y*200,(x+1)*75,lo+(y+1)*200) for y in range(8) for x in range(8) if (x+2*y)%4<threshold])
    if cp==0x2594:return box(0,hi-200,600,hi)
    if cp==0x2595:return box(525,lo,600,hi)
    quadrants={0x2596:'c',0x2597:'d',0x2598:'a',0x2599:'acd',0x259A:'ad',0x259B:'abc',0x259C:'abd',0x259D:'b',0x259E:'bc',0x259F:'bcd'}
    corners={'a':box(0,350,300,hi),'b':box(300,350,600,hi),'c':box(0,lo,300,350),'d':box(300,lo,600,350)}
    return unary_union([corners[q] for q in quadrants[cp]])


def geometries(weight,italic=False):
    result={chr(cp):drawing(cp,weight) for cp in range(0x2500,0x2580)}
    result.update({chr(cp):block(cp) for cp in range(0x2580,0x25A0)})
    from code_powerline import geometries as powerline
    result.update(powerline(weight,italic))
    return result


def selfcheck():
    records=[]
    for w in STEMS:
        g={chr(cp):drawing(cp,w) for cp in range(0x2500,0x2580)}
        g.update({chr(cp):block(cp) for cp in range(0x2580,0x25A0)})
        assert len(g)==160
        assert all(s.is_valid and not s.is_empty for s in g.values())
        for ch in '─━═':assert g[ch].bounds[0]==0 and g[ch].bounds[2]==600
        for ch in '│┃║':assert g[ch].bounds[1]==-450 and g[ch].bounds[3]==1150
        for ch in '┌╔┏':assert g[ch].bounds[0]>0 and g[ch].bounds[3]<600
        for ch in '┘╝┛':assert g[ch].bounds[2]<600 and g[ch].bounds[1]>100
        assert g['▔'].area==120000 and g['▕'].area==120000 and g['▜'].area==720000
        for ch,area in [('░',240000),('▒',480000),('▓',720000)]:assert g[ch].area==area
        assert len(list(g['╌'].geoms))==2 and len(list(g['┄'].geoms))==3 and len(list(g['┈'].geoms))==4
        records.append(dict(weight=w,unicode_geometry=160,status='PASS'))
    return records
if __name__=='__main__':print(json.dumps(selfcheck(),indent=2))
