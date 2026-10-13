"""One-storey italic a and canonical accented derivatives from the same base."""
import io, math, unicodedata
import uharfbuzz as hb
from shapely.affinity import affine_transform
from shapely.ops import unary_union
from fontTools.pens.ttGlyphPen import TTGlyphPen
from code_symbols import STEMS,SHEAR,_master_glyph,_line,_cubic


def geometries(weight,italic=False):
    if not italic:return {}
    bowl=_master_glyph('o',weight,True)
    bowl=affine_transform(bowl,[1,-SHEAR,0,1,270*SHEAR,0])
    width=STEMS[weight]/math.cos(math.radians(10))
    x=bowl.bounds[2]-width/2
    stem=_line([(x,0),(x,540)],width)
    tail=_line(_cubic((x,115),(x,25),(x+25,20),(x+65,50)),width)
    shape=affine_transform(unary_union([bowl,stem,tail]),[1,SHEAR,0,1,-270*SHEAR,0])
    return {'a':shape,'а':shape}


def rebuild_accents(font, all_bases=False):
    cmap=font.getBestCmap().copy()
    affected={cp:unicodedata.normalize('NFD',chr(cp)) for cp in cmap
              if cp not in (0x010F, 0x013D, 0x013E, 0x0165)  # Czech/Slovak apostrophe-shaped caron
              and len(unicodedata.normalize('NFD',chr(cp))) == 2
              and all(ord(c) in cmap for c in unicodedata.normalize('NFD',chr(cp)))
              and (all_bases or unicodedata.normalize('NFD',chr(cp))[0] in 'aа')}
    # Disable Unicode recomposition as well as GSUB ccmp in the temporary shaping
    # face. Otherwise HarfBuzz would select the old precomposed outline.
    saved=[(table,table.cmap.copy()) for table in font['cmap'].tables if table.isUnicode()]
    try:
        for table,mapping in saved:
            # Multiple cmap subtables can share the same dictionary in memory.
            table.cmap={cp:name for cp,name in mapping.items() if cp not in affected}
        stream=io.BytesIO();font.save(stream)
    finally:
        for table,mapping in saved:table.cmap=mapping
    face=hb.Face(stream.getvalue());shaper=hb.Font(face);shaper.scale=(1000,1000)
    order=font.getGlyphOrder();records=[]
    for cp,text in affected.items():
        shaping_text = text
        if text[0] in 'ijіј' and unicodedata.combining(text[1]) == 230:
            shaping_text = ('ı' if text[0] in 'iі' else 'ȷ') + text[1:]
        buffer=hb.Buffer();buffer.add_str(shaping_text);buffer.guess_segment_properties()
        hb.shape(shaper,buffer,{'ccmp':False,'mark':True})
        info=buffer.glyph_infos;positions=buffer.glyph_positions
        assert len(info)==len(text) and order[info[0].codepoint]==cmap[ord(shaping_text[0])],(cp,text,info)
        pen=TTGlyphPen(font.getGlyphSet());cursor=0;components=[]
        for item,pos in zip(info,positions):
            name=order[item.codepoint];x=cursor+pos.x_offset;y=pos.y_offset
            pen.addComponent(name,(1,0,0,1,x,y));components.append(dict(glyph=name,x=x,y=y))
            cursor+=pos.x_advance
        assert cursor==600
        name=cmap[cp];glyph=pen.glyph();font['glyf'][name]=glyph;glyph.recalcBounds(font['glyf'])
        font['hmtx'][name]=(600,glyph.xMin)
        records.append(dict(codepoint=f'U+{cp:04X}',text=chr(cp),decomposed=text,components=components))
    return records
