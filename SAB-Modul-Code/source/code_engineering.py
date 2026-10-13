"""Preserve overlapping primitives where boolean unions change topology by weight."""
from shapely.affinity import affine_transform, translate
from code_symbols import STEMS, SHEAR, _master_glyph, _line
from code_extended import _math_shapes
from code_powerline import _line_number, _lock
from code_operators import parts
from shapely.ops import unary_union


def geometries(weight, italic):
    shapes = _math_shapes(STEMS[weight], layers=True)
    result = {ch: shapes[ch] for ch in '∉⊕⊗'}
    if italic:
        result = {ch: [affine_transform(g, [1,SHEAR,0,1,-270*SHEAR,0]) for g in layers]
                  for ch, layers in result.items()}
    result['\ue0a1'] = [translate(g, yoff=-150) for g in _line_number(weight, layers=True)]
    result['\ue0a2'] = [translate(g, yoff=-150) for g in _lock(weight, layers=True)]
    result.update(parts(weight, italic, compatible=True))
    capitals = {ch: _master_glyph(base, weight, False) for ch, base in zip('ΑΒΓΕΖΗΘΙΚΜΝΟΡΤΥΧ', 'ABГEZHӨIKMNOPTYX')}
    s = STEMS[weight]
    capitals['Ξ'] = unary_union([_line([(105,y),(495,y)],s) for y in [s/2,350,700-s/2]])
    if italic:
        capitals = {ch: affine_transform(g,[1,SHEAR,0,1,-270*SHEAR,0]) for ch,g in capitals.items()}
    result.update(capitals)
    return result


def refine_and_extend(font, weight, italic):
    """Correct rounding drift and complete the Cyrillic languages found by FontBakery."""
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    from fontTools.pens.boundsPen import BoundsPen
    from build_code import install_geometry
    cmap = font.getBestCmap()
    repair_outline_spikes(font,weight,italic)
    if italic and weight in (500, 600):
        glyph = font['glyf'][cmap[ord('l')]]
        # The original left stem rounds outward; gvar delta rounding adds another
        # half-unit. Move its two on-curve ends inward by one unit, below 1 px/1000.
        assert len(glyph.coordinates) == 39 and glyph.flags[0] & 1 and glyph.flags[1] & 1
        for i in (0, 1):
            x, y = glyph.coordinates[i]
            glyph.coordinates[i] = (x + 1, y)
        glyph.recalcBounds(font['glyf'])

    def bounds(name):
        gs = font.getGlyphSet(); pen = BoundsPen(gs); gs[name].draw(pen)
        return pen.bounds

    def composed(ch, components):
        name = f'uni{ord(ch):04X}'
        pen = TTGlyphPen(font['glyf'])
        for base, x, y in components:
            pen.addComponent(base, (1, 0, 0, 1, round(x), round(y)))
        glyph = pen.glyph()
        glyph.components[0].flags |= 0x400  # OVERLAP_COMPOUND
        font['glyf'][name] = glyph
        font.setGlyphOrder(list(dict.fromkeys(font.getGlyphOrder() + [name])))
        glyph.recalcBounds(font['glyf'])
        font['hmtx'][name] = (600, glyph.xMin)
        for table in font['cmap'].tables:
            if table.isUnicode() and table.format in (4, 12): table.cmap[ord(ch)] = name

    composed('ʼ', [(cmap[ord('’')], 0, 0)])
    slope = SHEAR if italic else 0
    mark = cmap[0x304]; mx0, my0, mx1, my1 = bounds(mark)
    mark_x = round((mx0 + mx1) / 2 + slope * (my0 - (my0 + my1) / 2))
    for ch, base in zip('ӢӣӮӯ', 'ИиУу'):
        name = cmap[ord(base)]; x0, y0, x1, y1 = bounds(name)
        top = y1 + 40
        anchor = round((x0 + x1) / 2 + slope * (top - (y0 + y1) / 2))
        composed(ch, [(name, 0, 0), (mark, anchor - mark_x, top - my0)])
    width = STEMS[weight]
    tail = _line([(0, -170), (0, 30)], width)
    if italic: tail = affine_transform(tail, [1, SHEAR, 0, 1, 0, 0])
    install_geometry(font, 'code.cyrillic.descender', tail, advance=0)
    for ch, base in zip('ҲҳҶҷҖҗ', 'ХхЧчЖж'):
        name = cmap[ord(base)]; x0, y0, x1, y1 = bounds(name)
        # Measure the rightmost baseline stroke instead of the slanted top bbox.
        from verify_code import intersections
        right = max(b for a, b in intersections(font, name, 10))
        composed(ch, [(name, 0, 0), ('code.cyrillic.descender', right - width / 2, 0)])


def repair_outline_spikes(font,weight,italic):
    """Remove audited rounding wedges; keep the surrounding design intact."""
    from array import array
    from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
    repairs={
        (400,False): {'@':[(550,333),(517,332),(538,332)]},
        (400,True): {'@':[(591,333),(560,332),(570,331),(579,330)],
                     'α':[(471,517),(471,516),(476,540)]},
        (700,True): {'@':[(603,334),(561,333),(571,331),(579,330),(586,329)],
                     'β':[(147,9),(147,10),(108,-210)]},
        (300,False): {'∂':[(422,301),(422,300),(423,321)]},
    }
    if weight==600 and italic:
        g=font['glyf'][font.getBestCmap()[0x02DB]]
        i=list(g.coordinates).index((271,-58))
        assert tuple(g.coordinates[i-1])==(272,-58) and tuple(g.coordinates[i+1])==(275,-58)
        # Close the audited one-unit loop; the following control point stays put.
        g.coordinates[i]=(272,-58)
    for char,chain in repairs.get((weight,italic),{}).items():
        name=font.getBestCmap()[ord(char)];g=font['glyf'][name]
        coords=[];flags=[];ends=[];start=0;found=0
        for end in g.endPtsOfContours:
            ring=list(zip(g.coordinates[start:end+1],g.flags[start:end+1]));start=end+1
            for i in range(len(ring)-len(chain)+1):
                if [tuple(p) for p,f in ring[i:i+len(chain)]]==chain:
                    assert all(f&1 for p,f in ring[i:i+len(chain)])
                    del ring[i+1:i+len(chain)-1];found+=1;break
            coords.extend(p for p,f in ring);flags.extend(f for p,f in ring);ends.append(len(coords)-1)
        assert found==1,(name,weight,italic,'audited wedge moved')
        g.coordinates=GlyphCoordinates(coords);g.flags=array('B',flags);g.endPtsOfContours=ends;g.recalcBounds(font['glyf'])


def remove_degenerate_segments(font):
    """Remove empty segments and exact collinear reversals without changing ink area."""
    from fontTools.pens.basePen import BasePen
    from fontTools.pens.ttGlyphPen import TTGlyphPen
    class CleanPen(BasePen):
        def __init__(self):
            super().__init__(None); self.pen = TTGlyphPen(None); self.removed = 0
        def _moveTo(self, p): self.pen.moveTo(p)
        def _lineTo(self, p):
            if p == self._getCurrentPoint(): self.removed += 1
            else: self.pen.lineTo(p)
        def _qCurveToOne(self, c, p):
            if c in (self._getCurrentPoint(), p):
                self.removed += 1; self._lineTo(p)
            else: self.pen.qCurveTo(c, p)
        def _closePath(self): self.pen.closePath()
    gs = font.getGlyphSet(); changes = {}
    for name in font.getGlyphOrder():
        old = font['glyf'][name]
        if old.numberOfContours <= 0: continue
        pen = CleanPen(); gs[name].draw(pen)
        glyph = pen.pen.glyph()
        from fontTools.ttLib.tables._g_l_y_f import GlyphCoordinates
        from array import array
        coords=[]; flags=[]; ends=[]; start=0
        for end in glyph.endPtsOfContours:
            ring=list(zip(glyph.coordinates[start:end+1],glyph.flags[start:end+1])); start=end+1
            changed=True
            while changed and len(ring)>3:
                changed=False
                for i in range(len(ring)):
                    (a,fa),(b,fb),(c,fc)=ring[i-1],ring[i],ring[(i+1)%len(ring)]
                    ab=(b[0]-a[0],b[1]-a[1]);bc=(c[0]-b[0],c[1]-b[1])
                    if fa&fb&fc&1 and ab[0]*bc[1]==ab[1]*bc[0] and ab[0]*bc[0]+ab[1]*bc[1]<=0:
                        del ring[i];pen.removed+=1;changed=True;break
            coords.extend(p for p,f in ring);flags.extend(f for p,f in ring);ends.append(len(coords)-1)
        glyph.coordinates=GlyphCoordinates(coords);glyph.flags=array('B',flags);glyph.endPtsOfContours=ends
        if pen.removed:
            if old.flags[0] & 0x40: glyph.flags[0] |= 0x40
            font['glyf'][name] = glyph; glyph.recalcBounds(font['glyf'])
            changes[name] = pen.removed
    return changes


def remove_unreachable_helpers(font):
    order = font.getGlyphOrder()
    dead = {n for n in order if n.endswith('.pnum') or n in ('caron.alt', 'uni0064.caron')}
    assert not (dead & set(font.getBestCmap().values()))
    for name in set(order) - dead:
        g = font['glyf'][name]
        if g.isComposite(): assert not any(c.glyphName in dead for c in g.components), name
    for name in dead:
        del font['glyf'][name]; del font['hmtx'].metrics[name]
    font.setGlyphOrder([name for name in order if name not in dead])
    return sorted(dead)
