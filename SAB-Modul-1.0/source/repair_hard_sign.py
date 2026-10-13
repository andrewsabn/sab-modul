"""Lengthen Ъ/ъ flags in frozen final masters; preserve advances and other glyphs.

Run from a disposable root release copy. The outer stems keep their thickness;
only the hard-sign counter's horizontal span supplies room for the longer flag.
"""
from pathlib import Path
import copy, json, math, subprocess, tempfile, sys
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import Glyph
from fontTools.ttLib.tables.ttProgram import Program
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.designspaceLib import DesignSpaceDocument, AxisDescriptor, SourceDescriptor
from fontTools.varLib import build as build_vf
import repair_a_junction as common

REPO=common.REPO
NAMES={'uni042A','uni044A'}
FLAG=150

def extend(font,name):
    g=font['glyf'][name]
    assert not g.isComposite()
    slope=math.tan(math.radians(-font['post'].italicAngle))
    pts=[(x-slope*y,y) for x,y in g.coordinates]
    height=max(y for x,y in pts)
    candidates=[min(a[0],b[0]) for a,b in zip(pts,pts[1:]+pts[:1])
                if abs(a[0]-b[0])<1.6 and min(a[1],b[1])<=1 and max(a[1],b[1])>height*.5]
    assert candidates,(font['name'].getDebugName(6),name,'baseline stem not found')
    left=min(candidates);xmin=min(x for x,y in pts);xmax=max(x for x,y in pts)
    right=max(x for x,y in pts if y==height)
    old=left-xmin;delta=max(0,FLAG-old) if old<FLAG-1 else 0;end=xmax-(right-left)
    assert old>0 and end-right>delta,(name,'insufficient counter space',end-right,delta)
    def mapped(x):
        if x<=left:return xmin+(x-xmin)*(FLAG/old) if delta else x
        if x<=right:return x+delta
        if x<end:return right+delta+(x-right)*(end-right-delta)/(end-right)
        return x
    for i,(x,y) in enumerate(pts):g.coordinates[i]=(round(mapped(x)+slope*y),round(y))
    g.program=Program();g.program.fromBytecode([])
    return {'old_flag_units':round(old,3),'new_flag_target':FLAG,'counter_compression':round(delta,3)}

def repair_master(path):
    f=TTFont(path,recalcTimestamp=False);snap=common.table_snapshot(f);old={n:common.glyph_hash(f,n) for n in f.getGlyphOrder()}
    measures={n:extend(f,n) for n in NAMES};common.save_glyf(f,path,NAMES,snap,old)
    return measures

def cff(path,source):
    f=TTFont(source);o=TTFont(path,recalcTimestamp=False);snap=common.table_snapshot(o)
    top=o['CFF '].cff.topDictIndex[0];old={n:common.sha(top.CharStrings[n].bytecode) for n in o.getGlyphOrder()}
    for name in NAMES:
        pen=T2CharStringPen(o['hmtx'][name][0],None)
        flat=Glyph();flat.coordinates,flat.endPtsOfContours,flat.flags=f['glyf'][name].getCoordinates(f['glyf']);flat.numberOfContours=len(flat.endPtsOfContours)
        flat.draw(pen,f['glyf']);top.CharStrings[name]=pen.getCharString(private=top.Private,globalSubrs=o['CFF '].cff.GlobalSubrs)
    o.save(path);new=TTFont(path,recalcTimestamp=False);common.retain_other_tables(snap,new,{'CFF ','head'},str(path.relative_to(REPO)))
    assert all(common.sha(new['CFF '].cff.topDictIndex[0].CharStrings[n].bytecode)==v for n,v in old.items() if n not in NAMES)


def main():
    records=[]
    for family in (sys.argv[1:] or ('Sans','Mono','Code')):
        root=REPO/('SAB-Modul-Code' if family=='Code' else 'SAB-Modul-1.0')
        for path in sorted((root/'TTF').glob('*'+family+'*.ttf')):
            master=root/('source/stage6-masters' if family=='Code' else 'source/masters')/path.name
            if family=='Code' and not master.exists() and path.name=='SABModulCode-Italic.ttf':
                master=master.with_name('SABModulCode-RegularItalic.ttf')
            measures=repair_master(master)
            with tempfile.TemporaryDirectory() as t:
                hinted=Path(t)/path.name
                opts=['-D','cyrl','-f','latn']+(['-x','14','-n'] if family=='Code' else ['-I'])
                subprocess.run(['ttfautohint',*opts,str(master),str(hinted)],check=True,capture_output=True)
                h=TTFont(hinted,recalcTimestamp=False);f=TTFont(path,recalcTimestamp=False);snap=common.table_snapshot(f)
                old={n:common.glyph_hash(f,n) for n in f.getGlyphOrder()}
                for tag in ('fpgm','prep','cvt '):assert f.getTableData(tag)==h.getTableData(tag),(path.name,tag,'hint control change')
                for field in ('maxStorage','maxStackElements','maxFunctionDefs','maxInstructionDefs','maxTwilightPoints'):
                    setattr(f['maxp'],field,max(getattr(f['maxp'],field),getattr(h['maxp'],field)))
                for n in NAMES:f['glyf'][n]=copy.deepcopy(h['glyf'][n])
                common.save_glyf(f,path,NAMES,snap,old)
                web=TTFont(path,recalcTimestamp=False);web.flavor='woff2';web.save(root/'WOFF2'/(path.stem+'.woff2'))
                cff(root/'OTF'/(path.stem+'.otf'),master)
            records.append({'file':str(path.relative_to(REPO)),'measurements':measures,'metrics_layout_other_glyphs_preserved':True})
            print('Hard signs:',path.stem,flush=True)
        for slant in ('','Italic' if family=='Code' else 'Oblique'):
            folder=root/'source'/('variable-masters-refit' if family=='Code' else 'variable-masters')/(('Italic' if slant else 'Roman') if family=='Code' else 'SABModul'+family+slant)
            masters=sorted(folder.glob('*.ttf'));ds=DesignSpaceDocument();axis=AxisDescriptor();axis.name='Weight';axis.tag='wght';axis.minimum=300 if family=='Code' else 200;axis.default=400;axis.maximum=700 if family=='Code' else 900;ds.addAxis(axis)
            for p in masters:
                repair_master(p);f=TTFont(p);s=SourceDescriptor();s.path=str(p);s.name=p.stem;s.location={'Weight':f['OS/2'].usWeightClass};ds.addSource(s)
            fresh,_,_=build_vf(ds)
            for p in list((root/'VF').glob('*'))+list((root/'WEB').glob('*.woff2')):
                if not p.is_file() or family not in p.name or p.suffix not in ('.ttf','.woff2'):continue
                f=TTFont(p,recalcTimestamp=False)
                if bool(f['post'].italicAngle)!=bool(slant):continue
                changed=NAMES&set(f.getGlyphOrder())
                if not changed:continue
                snap=common.table_snapshot(f);old={n:common.glyph_hash(f,n) for n in f.getGlyphOrder()};oldvar=copy.deepcopy(f['gvar'].variations)
                for name in changed:
                    f['glyf'][name]=copy.deepcopy(fresh['glyf'][name]);f['gvar'].variations[name]=copy.deepcopy(fresh['gvar'].variations.get(name,[]))
                assert all(f['gvar'].variations[n]==v for n,v in oldvar.items() if n not in changed)
                common.save_glyf(f,p,changed,snap,old)
                records.append({'file':str(p.relative_to(REPO)),'metrics_layout_other_glyphs_variations_preserved':True})
            report_path=folder/'fit-report.json'
            if report_path.exists():
                report=json.loads(report_path.read_text());report['hard_sign_repair']={'glyphs':sorted(NAMES),'flag_units':FLAG,'topology_preserved':True};report_path.write_text(json.dumps(report,indent=2)+'\n')
    out=REPO/'checks/hard-sign';out.mkdir(exist_ok=True)
    existing=out/'source-repair.json'
    if existing.exists():
        records=json.loads(existing.read_text())['records']+records
    (out/'source-repair.json').write_text(json.dumps({'flag_units':FLAG,'scope':'All three families, all 38 static styles and six variable faces; all matching web fonts.','records':records},indent=2)+'\n')
    print('Hard-sign repair complete')

if __name__=='__main__':main()
