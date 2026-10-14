"""Rebuild only corrected numeric contours, preserving layout and other glyphs.

Run once on a release copy. Frozen masters supply the original spacing; the
same compatible curves feed static, CFF, variable and web fonts.
"""
from pathlib import Path
from array import array
import copy, json, math, subprocess, tempfile, sys
from shapely.affinity import affine_transform
from shapely.geometry.polygon import orient
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import Glyph, GlyphCoordinates
from fontTools.ttLib.tables.ttProgram import Program
from fontTools.designspaceLib import DesignSpaceDocument, AxisDescriptor, SourceDescriptor
from fontTools.varLib import build as build_vf
import repair_a_junction as common
import repair_hard_sign as hard

REPO=common.REPO
STYLES=common.STYLES
BUILDER=common.module('digit_builder',common.ROOT/'source/build.py')
FITTER=common.module('digit_fitter',common.ROOT/'source/build_variable.py')
FITTER.TOLERANCE=.35
CODE_STEMS={300:79,400:94,500:99,600:108,700:125}

def polygon_glyph(shape):
    g=Glyph();points=[];ends=[]
    for poly in ([shape] if shape.geom_type=='Polygon' else shape.geoms):
        poly=orient(poly,sign=-1)
        for ring in [poly.exterior,*poly.interiors]:
            for point in list(ring.coords)[:-1]:
                if not points or point!=points[-1]:points.append(point)
            ends.append(len(points)-1)
    g.coordinates=GlyphCoordinates(points);g.endPtsOfContours=ends
    g.flags=array('B',[1]*len(points));g.numberOfContours=len(ends)
    g.program=Program();g.program.fromBytecode([])
    return g

def target_names(font,family):
    digits='23578' if family=='Code' else '02356789'
    cm=font.getBestCmap()
    return {cm[ord(c)]:c for c in digits}|{n:c for c in digits for n in [cm[ord(c)]+'.pnum'] if n in font.getGlyphOrder()}

def drawn(font,name,ch,family,weight,slant):
    if family=='Code' and ch=='3':
        from shapely.geometry import LineString
        from shapely.ops import unary_union
        stem=CODE_STEMS[weight];top=700-stem/2
        bowl=BUILDER.curve((265,390),((585,440),(570,60),(330,stem/2)),((225,stem/2),(150,stem/2+25),(120,140)),steps=192)
        paths=[([(135,top),(465,top)],'flat'), ([(465,top),(265,390)],'round'), (bowl,'round')]
        shape=unary_union([LineString(p).buffer(stem/2,cap_style=cap,join_style='round',quad_segs=32) for p,cap in paths])
        if slant:shape=affine_transform(shape,[1,math.tan(math.radians(10)),0,1,-270*math.tan(math.radians(10)),0])
        return polygon_glyph(shape)
    mono=family!='Sans';thickness=CODE_STEMS[weight]*620/600 if family=='Code' else BUILDER.WEIGHTS[STYLES_BY_WEIGHT[weight]][1]
    width,paths=BUILDER.alphabet('SAB Modul',mono)[ch]
    shape,_,_=BUILDER.geometry(width,paths,'SAB Modul',mono,thickness,False,ch)
    # Existing sidebearings and advances stay exact, including pnum alternates.
    old=font['glyf'][name];slope=math.tan(math.radians(-font['post'].italicAngle))
    oldpoints=[(x-slope*y,y) for x,y in old.coordinates]
    lo=min(x for x,y in oldpoints);hi=max(x for x,y in oldpoints)
    a,_,b,_=shape.bounds;scale=(hi-lo)/(b-a)
    shape=affine_transform(shape,[scale,0,0,1,lo-a*scale,0])
    if slant:shape=affine_transform(shape,[1,slope,0,1,0,0])
    return polygon_glyph(shape)

STYLES_BY_WEIGHT={v:k for k,v in STYLES.items()}

# hhea bearing extrema are derived bounds; line spacing and advances stay frozen.
_original_retain=common.retain_other_tables
def retain_tables(before,font,allowed,label):
    _original_retain(before,font,allowed|{'hhea'},label)
    if 'hhea' in before:
        after=font.getTableData('hhea')
        assert before['hhea'][:12]==after[:12] and before['hhea'][18:]==after[18:],(label,'hhea line metrics changed')
common.retain_other_tables=retain_tables


def adopt(path,glyphs):
    f=TTFont(path,recalcTimestamp=False);snap=common.table_snapshot(f)
    old={n:common.glyph_hash(f,n) for n in f.getGlyphOrder()}
    for n,g in glyphs.items():f['glyf'][n]=copy.deepcopy(g)
    common.save_glyf(f,path,set(glyphs),snap,old)

def clean_terminal_lines(fonts,selected):
    """Refit only rounded terminal micro-polylines; retain common master topology."""
    from shapely.geometry import LineString
    changes=[]
    for name in selected:
        if name.split('.')[0]!='uni0035':continue
        glyphs=[f['glyf'][name] for f in fonts]
        if glyphs[0].isComposite():continue
        while True:
            starts={0}|{i+1 for i in glyphs[0].endPtsOfContours[:-1]}
            zeros=[i for i in range(1,len(glyphs[0].coordinates)) if i not in starts and
                   all((g.flags[i]&1) and (g.flags[i-1]&1) for g in glyphs) and
                   any(g.coordinates[i]==g.coordinates[i-1] for g in glyphs)]
            if not zeros:break
            first=zeros[0];last=first
            while last+1 in zeros:last+=1
            start=first-1;end=last
            if all(g.coordinates[start]==g.coordinates[end] for g in glyphs):
                assert all(all(g.coordinates[i]==g.coordinates[start] for i in range(start,end+1)) for g in glyphs),'Non-constant closed terminal section'
                remove=set(range(first,end+1));error=0
            else:
                while any(g.coordinates[start]==g.coordinates[end] for g in glyphs):
                    end+=1
                    assert end not in starts and all(g.flags[end]&1 for g in glyphs)
                assert all(all(g.flags[i]&1 for i in range(start,end+1)) for g in glyphs)
                paths=[LineString(list(g.coordinates[start:end+1])) for g in glyphs]
                lines=[LineString([g.coordinates[start],g.coordinates[end]]) for g in glyphs]
                error=max(p.hausdorff_distance(line) for p,line in zip(paths,lines))
                assert error<=1.0,(name,'Terminal refit exceeds one unit',error)
                assert max(p.length for p in paths)<=10,(name,'Not a terminal micro-section')
                remove=set(range(start+1,end))
            assert remove
            changes.append({'glyph':name,'removed_indices':sorted(remove),'max_master_terminal_deviation_units':error})
            for g in glyphs:
                g.coordinates=GlyphCoordinates([p for i,p in enumerate(g.coordinates) if i not in remove])
                g.flags=array('B',[v for i,v in enumerate(g.flags) if i not in remove])
                g.endPtsOfContours=[e-sum(i<=e for i in remove) for e in g.endPtsOfContours]
    return changes

def main():
    records=[]
    for family in (sys.argv[1:] or ('Sans','Mono','Code')):
        root=REPO/('SAB-Modul-Code' if family=='Code' else 'SAB-Modul-1.0')
        styles={k:w for k,w in STYLES.items() if family!='Code' or w in CODE_STEMS}
        for slant in ('','Italic' if family=='Code' else 'Oblique'):
            paths=[];fonts=[]
            for style,weight in styles.items():
                p=root/('source/stage6-masters' if family=='Code' else 'source/masters')/f'SABModul{family}-{style}{slant}.ttf'
                f=TTFont(p,recalcTimestamp=False)
                for name,ch in target_names(f,family).items():f['glyf'][name]=drawn(f,name,ch,family,weight,bool(slant))
                paths.append(p);fonts.append(f)
            selected=list(target_names(fonts[0],family))
            fitted=FITTER.compatible(fonts,selected)
            fitted['terminal_cleanup']=clean_terminal_lines(fonts,selected)
            folder=root/'source'/('variable-masters-refit' if family=='Code' else 'variable-masters')/(('Italic' if slant else 'Roman') if family=='Code' else 'SABModul'+family+slant)
            ds=DesignSpaceDocument();axis=AxisDescriptor();axis.name='Weight';axis.tag='wght';axis.minimum=min(styles.values());axis.default=400;axis.maximum=max(styles.values());ds.addAxis(axis)
            for (style,weight),master,f in zip(styles.items(),paths,fonts):
                glyphs={n:f['glyf'][n] for n in selected}
                adopt(master,glyphs)
                vp=folder/(master.name if family=='Code' else style+'.ttf');adopt(vp,glyphs)
                s=SourceDescriptor();s.path=str(vp);s.name=style;s.location={'Weight':weight};ds.addSource(s)
                filename=master.name
                if family=='Code' and style=='Regular' and slant:filename='SABModulCode-Italic.ttf'
                dest=root/'TTF'/filename
                with tempfile.TemporaryDirectory() as tmp:
                    hinted=Path(tmp)/filename;opts=['-D','cyrl','-f','latn']+(['-x','14','-n'] if family=='Code' else ['-I'])
                    subprocess.run(['ttfautohint',*opts,str(master),str(hinted)],check=True,capture_output=True)
                    h=TTFont(hinted,recalcTimestamp=False);original=TTFont(dest,recalcTimestamp=False);snap=common.table_snapshot(original)
                    old={n:common.glyph_hash(original,n) for n in original.getGlyphOrder()}
                    for tag in ('fpgm','prep','cvt '):assert original.getTableData(tag)==h.getTableData(tag),(filename,tag,'hint control change')
                    for field in ('maxStorage','maxStackElements','maxFunctionDefs','maxInstructionDefs','maxTwilightPoints'):
                        setattr(original['maxp'],field,max(getattr(original['maxp'],field),getattr(h['maxp'],field)))
                    for n in selected:original['glyf'][n]=copy.deepcopy(h['glyf'][n])
                    common.save_glyf(original,dest,set(selected),snap,old)
                web=TTFont(dest,recalcTimestamp=False);web.flavor='woff2';web.save(root/'WOFF2'/(dest.stem+'.woff2'))
                hard.NAMES=set(selected);hard.cff(root/'OTF'/(dest.stem+'.otf'),master)
                records.append({'file':str(dest.relative_to(REPO)),'glyphs':selected,'advances_layout_other_glyphs_preserved':True})
                print('Digits:',dest.stem,flush=True)
            fresh,_,_=build_vf(ds)
            for p in list((root/'VF').glob('*'))+list((root/'WEB').glob('*.woff2')):
                if not p.is_file() or family not in p.name or p.suffix not in ('.ttf','.woff2'):continue
                original=TTFont(p,recalcTimestamp=False)
                if bool(original['post'].italicAngle)!=bool(slant):continue
                changed=set(selected)&set(original.getGlyphOrder())
                if not changed:continue
                snap=common.table_snapshot(original);old={n:common.glyph_hash(original,n) for n in original.getGlyphOrder()};oldvar={n:copy.deepcopy(v) for n,v in original['gvar'].variations.items()}
                for n in changed:
                    original['glyf'][n]=copy.deepcopy(fresh['glyf'][n]);original['gvar'].variations[n]=copy.deepcopy(fresh['gvar'].variations.get(n,[]))
                assert all(original['gvar'].variations[n]==v for n,v in oldvar.items() if n not in changed)
                common.save_glyf(original,p,changed,snap,old)
                records.append({'file':str(p.relative_to(REPO)),'glyphs':sorted(changed),'advances_layout_other_glyphs_and_variations_preserved':True})
            report=folder/'fit-report.json'
            if report.exists():
                d=json.loads(report.read_text());d['digit_repair']=fitted;report.write_text(json.dumps(d,indent=2)+'\n')
    out=REPO/'checks/digits';out.mkdir(parents=True,exist_ok=True)
    (out/'source-repair.json').write_text(json.dumps({'scope':'Scoped numeric rebuild; high resolution original skeletons, continuous 2/5 joins, aligned 2/7, shared compatible curves. Code non-target numerals retain their previously curved drawings.','records':records},indent=2)+'\n')

if __name__=='__main__':main()
