"""Rebuild only Sans a-derived glyphs from the continuous source path.

Preserve all metrics/layout and unrelated glyphs. Refit only the affected
compatible master glyphs, then transfer only those VF glyphs and tuples.
Run in a copy; requires the frozen masters and ttfautohint 1.8.4 on PATH.
"""
from pathlib import Path
import argparse, copy, hashlib, importlib.util, json, math, subprocess, tempfile
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import Glyph
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.varLib import build as build_vf
from fontTools.designspaceLib import DesignSpaceDocument, AxisDescriptor, SourceDescriptor

ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parent
STYLES={'Thin':200,'Light':300,'Regular':400,'Medium':500,'SemiBold':600,'Bold':700,'Black':900}
CHARACTERS='aаæàáâãäåāăąª'
NAMES={f'uni{ord(c):04X}' for c in CHARACTERS}

def module(name,path):
    s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m

def sha(data): return hashlib.sha256(data).hexdigest()

def glyph_hash(font,name):
    return sha(font['glyf'][name].compile(font['glyf']))

def rebuilt_glyph(builder,ch,thickness,slanted):
    width,paths=builder.alphabet('SAB Modul',False)[ch]
    geometry,advance,lsb=builder.geometry(width,paths,'SAB Modul',False,thickness,slanted,ch)
    if ch=='ą':
        geometry,advance,lsb=builder.geometry(*builder.alphabet('SAB Modul',False)['a'],'SAB Modul',False,thickness,slanted,'a')
        mark,_,_=builder.geometry(*builder.alphabet('SAB Modul',False)['\u0328'],'SAB Modul',False,thickness,slanted,'\u0328')
        foot=geometry.intersection(builder.LineString([(-2000,2),(4000,2)]))
        bx=round(foot.bounds[2]-thickness*.25)
        mark_y=thickness*builder.stroke_ratio(thickness)/2
        slope=math.tan(math.radians(10)) if slanted else 0
        mx=round(85*.91+slope*mark_y-(18 if slanted else 0));my=round(mark_y)
        geometry=builder.unary_union([geometry,builder.affine_transform(mark,[1,0,0,1,bx-mx,-my])])
        lsb=math.floor(geometry.bounds[0])
    pen=TTGlyphPen(None)
    for ring in builder.contours(geometry):
        pen.moveTo(ring[0])
        for p in ring[1:]:pen.lineTo(p)
        pen.closePath()
    return pen.glyph(),advance,lsb

def retain_other_tables(before,font,allowed,label):
    for tag,data in before.items():
        if tag not in allowed:assert font.getTableData(tag)==data,(label,'unexpected table change',tag)

def table_snapshot(font):
    return {tag:font.getTableData(tag) for tag in font.keys() if tag!='GlyphOrder'}

def save_glyf(font,path,changed,before,old_glyphs):
    for name,old in old_glyphs.items():
        if name not in changed:assert glyph_hash(font,name)==old,(path.name,'unrelated glyph',name)
    if 'maxp' in font:
        font['maxp'].maxSizeOfInstructions=max([len(g.program.getBytecode()) for g in font['glyf'].glyphs.values() if hasattr(g,'program')] or [0])
    font.save(path)
    check=TTFont(path,recalcTimestamp=False)
    retain_other_tables(before,check,{'glyf','loca','head','maxp','gvar'},str(path.relative_to(REPO)))


def main():
    builder=module('sans_builder',ROOT/'source/build.py')
    fitter=module('sans_fitter',ROOT/'source/build_variable.py')
    records=[]
    for slant in ('','Oblique'):
        frozen=[]
        for style,weight in STYLES.items():
            path=ROOT/'source/masters'/f'SABModulSans-{style}{slant}.ttf'
            font=TTFont(path,recalcTimestamp=False);before=table_snapshot(font);old_glyphs={n:glyph_hash(font,n) for n in font.getGlyphOrder()}
            thickness=builder.WEIGHTS[style][1]
            for ch in CHARACTERS:
                name=f'uni{ord(ch):04X}'
                # Existing accented components inherit the updated base outline.
                if font['glyf'][name].isComposite():continue
                new,advance,lsb=rebuilt_glyph(builder,ch,thickness,bool(slant))
                assert font['hmtx'][name][1]==lsb and abs(font['hmtx'][name][0]-advance)<=1,(style,ch,'source metrics changed unexpectedly',font['hmtx'][name],(advance,lsb))
                # Removing an internal cap can change a floating bound by <1 unit.
                # Keep the accepted advance; this repair does not alter text spacing.
                font['glyf'][name]=new
            save_glyf(font,path,NAMES,before,old_glyphs)
            frozen.append(TTFont(path,recalcTimestamp=False))
            # Hint the changed point topology with the same control functions.
            with tempfile.TemporaryDirectory() as tmp:
                hinted=Path(tmp)/'hinted.ttf'
                subprocess.run(['ttfautohint','-D','cyrl','-f','latn','-I',str(path),str(hinted)],check=True,capture_output=True)
                hintfont=TTFont(hinted,recalcTimestamp=False)
                destination=ROOT/'TTF'/path.name
                original=TTFont(destination,recalcTimestamp=False)
                for tag in ('fpgm','prep','cvt '):
                    assert original.getTableData(tag)==hintfont.getTableData(tag),(path.name,'hint control table changed',tag)
                before=table_snapshot(original);old_glyphs={n:glyph_hash(original,n) for n in original.getGlyphOrder()}
                for field in ('maxStorage','maxStackElements','maxFunctionDefs','maxInstructionDefs','maxTwilightPoints'):
                    setattr(original['maxp'],field,max(getattr(original['maxp'],field),getattr(hintfont['maxp'],field)))
                for name in NAMES:original['glyf'][name]=copy.deepcopy(hintfont['glyf'][name])
                save_glyf(original,destination,NAMES,before,old_glyphs)
                # Matching full static web format, including current hint instructions.
                original=TTFont(destination,recalcTimestamp=False);original.flavor='woff2'
                original.save(ROOT/'WOFF2'/(path.stem+'.woff2'))
                # CFF has expanded accent outlines; rebuild all thirteen derivatives.
                otf_path=ROOT/'OTF'/(path.stem+'.otf')
                otf=TTFont(otf_path,recalcTimestamp=False);otf_before=table_snapshot(otf)
                top=otf['CFF '].cff.topDictIndex[0]
                old_chars={n:sha(top.CharStrings[n].bytecode) for n in otf.getGlyphOrder()}
                glyphs=hintfont.getGlyphSet()
                for name in NAMES:
                    pen=T2CharStringPen(otf['hmtx'][name][0],glyphs)
                    flat=Glyph();flat.coordinates,flat.endPtsOfContours,flat.flags=hintfont['glyf'][name].getCoordinates(hintfont['glyf'])
                    flat.numberOfContours=len(flat.endPtsOfContours)
                    flat.draw(pen,hintfont['glyf'])
                    top.CharStrings[name]=pen.getCharString(private=top.Private,globalSubrs=otf['CFF '].cff.GlobalSubrs)
                otf.save(otf_path);check=TTFont(otf_path,recalcTimestamp=False)
                retain_other_tables(otf_before,check,{'CFF ','head'},str(otf_path.relative_to(REPO)))
                new_top=check['CFF '].cff.topDictIndex[0]
                assert all(sha(new_top.CharStrings[n].bytecode)==v for n,v in old_chars.items() if n not in NAMES),'Unrelated CFF charstrings changed'
            records.append({'style':style+slant,'static_metrics_layout_unrelated_glyphs_preserved':True})
            print('Repaired static',style+slant,flush=True)
        # Fit only these glyphs; do not reprocess any unrelated compatible outline.
        for f in frozen:
            for tag in ('glyf','hmtx','post'): _=f[tag]
        subset=[copy.deepcopy(f) for f in frozen]
        selected=[n for n in frozen[0].getGlyphOrder() if n in NAMES]
        fit_report=fitter.compatible(subset,selected)
        folder=ROOT/'source/variable-masters'/('SABModulSans'+slant)
        sources=[]
        for (style,weight),fit in zip(STYLES.items(),subset):
            p=folder/(style+'.ttf');f=TTFont(p,recalcTimestamp=False)
            before=table_snapshot(f);old_glyphs={n:glyph_hash(f,n) for n in f.getGlyphOrder()}
            for name in NAMES:f['glyf'][name]=copy.deepcopy(fit['glyf'][name])
            save_glyf(f,p,NAMES,before,old_glyphs)
            source=SourceDescriptor();source.path=str(p);source.name=style;source.location={'Weight':weight};sources.append(source)
        ds=DesignSpaceDocument();axis=AxisDescriptor();axis.name='Weight';axis.tag='wght';axis.minimum=200;axis.default=400;axis.maximum=900;ds.addAxis(axis)
        for s in sources:ds.addSource(s)
        fresh,_,_=build_vf(ds)
        for p in list((ROOT/'VF').glob('*'))+list((ROOT/'WEB').glob('*.woff2')):
            if not p.is_file() or 'Sans' not in p.name or p.suffix not in ('.ttf','.woff2'):continue
            original=TTFont(p,recalcTimestamp=False)
            if bool(original['post'].italicAngle)!=bool(slant):continue
            changed=NAMES&set(original.getGlyphOrder())
            if not changed:continue
            before=table_snapshot(original);old_glyphs={n:glyph_hash(original,n) for n in original.getGlyphOrder()}
            old_tuples={n:copy.deepcopy(v) for n,v in original['gvar'].variations.items()}
            for name in changed:
                replacement=copy.deepcopy(fresh['glyf'][name])
                if replacement.isComposite():assert all(c.glyphName in original.getGlyphOrder() for c in replacement.components)
                original['glyf'][name]=replacement
                original['gvar'].variations[name]=copy.deepcopy(fresh['gvar'].variations.get(name,[]))
            assert all(original['gvar'].variations[n]==v for n,v in old_tuples.items() if n not in changed),'Unrelated variation tuples changed'
            save_glyf(original,p,changed,before,old_glyphs)
            records.append({'file':str(p.relative_to(REPO)),'changed_glyphs':sorted(changed),'metrics_layout_unrelated_glyphs_preserved':True})
        report_path=folder/'fit-report.json';report=json.loads(report_path.read_text())
        report['glyphs'].update(fit_report['glyphs']);report['deduplicated_glyphs'].update(fit_report['deduplicated_glyphs'])
        report['sources']={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in (ROOT/'source/masters').glob('SABModulSans-*'+slant+'.ttf') if bool(TTFont(p)['post'].italicAngle)==bool(slant)}
        report['local_a_junction_repair']={'glyphs':sorted(NAMES),'unrelated_fitted_glyphs_preserved':True}
        report_path.write_text(json.dumps(report,indent=2)+'\n')
    destination=REPO/'checks/a-junction/source-repair.json';destination.parent.mkdir(exist_ok=True)
    destination.write_text(json.dumps({'root_cause':'Internal flat cap from a separate upper stem path; fixed by joining the source arc and stem.','scope':'Sans only, seven weights and both slants, including a-derived forms.','records':records},indent=2)+'\n')
    print('Source repair completed')

if __name__=='__main__':main()
