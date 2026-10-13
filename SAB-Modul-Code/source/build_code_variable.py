"""Fit only new polygon contours; preserve the original compatible Bezier masters."""
import argparse,hashlib,importlib.util,json,sys
from pathlib import Path
import numpy as np
from fontTools.ttLib import TTFont,newTable
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.designspaceLib import DesignSpaceDocument,AxisDescriptor,SourceDescriptor,InstanceDescriptor
from fontTools.varLib import build as build_variable
from fontTools.varLib.interpolatableHelpers import min_cost_perfect_bipartite_matching
from fontTools.otlLib.builder import buildStatTable
ROOT=Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT/'source/upstream'))
STYLES={300:'Light',400:'Regular',500:'Medium',600:'SemiBold',700:'Bold'}
spec=importlib.util.spec_from_file_location('own_fitter',ROOT/'source/upstream/build_variable.py')
fitter=importlib.util.module_from_spec(spec);spec.loader.exec_module(fitter)


def structure(g):
    if g.isComposite():return ('composite',tuple(c.glyphName for c in g.components))
    return (g.numberOfContours,tuple(getattr(g,'endPtsOfContours',[])),tuple(int(x)&1 for x in getattr(g,'flags',[])))


def fit(fonts,report,refit=False):
    order=fonts[0].getGlyphOrder();assert all(f.getGlyphOrder()==order for f in fonts)
    from verify_operator_strokes import SAMPLES
    exact={fonts[0].getBestCmap()[ord(c)] for c in 'Hlx'+''.join(SAMPLES) if c not in '~?'}
    for index,name in enumerate(order):
        gs=[f['glyf'][name] for f in fonts]
        structures=[structure(g) for g in gs]
        if any(g.isComposite() for g in gs):
            assert len(set(structures))==1,(name,'component topology differs')
            continue
        counts=[g.numberOfContours for g in gs]
        assert len(set(counts))==1,(name,'contour topology differs',counts)
        if not counts[0]:continue
        if name in exact:
            assert len(set(structures))==1,(name,'protected outline incompatible')
            continue
        curved = not all(all(flag&1 for flag in g.flags) for g in gs)
        if curved:
            if not refit or name in {fonts[0].getBestCmap()[ord(c)] for c in 'Hlx'}:
                assert len(set(structures))==1,(name,'original Bezier master incompatible')
                continue
        if len(set(structures))==1 and all(list(g.coordinates)==list(gs[0].coordinates) for g in gs[1:]):
            continue
        if curved:
            from verify_variable import OutlinePen
            masters=[]
            for f in fonts:
                glyphset=f.getGlyphSet();pen=OutlinePen(glyphset);glyphset[name].draw(pen)
                rings=[]
                for points in pen.rings:
                    cleaned=[]
                    for point in points:
                        if not cleaned or tuple(point)!=tuple(cleaned[-1]):cleaned.append(point)
                    while len(cleaned)>1 and tuple(cleaned[-1])==tuple(cleaned[0]):cleaned.pop()
                    rings.append(np.asarray(cleaned,dtype=float))
                masters.append(rings)
        else:masters=[fitter.rings(g) for g in gs]
        reference=masters[2]
        roles=[tuple(sorted(np.sign(fitter.signature(p)[-1]) for p in rs)) for rs in masters]
        assert len(set(roles))==1,(name,'counter roles differ',roles)
        for mi,rings in enumerate(masters):
            if mi==2:continue
            costs=[[float(np.sum((fitter.signature(a)-fitter.signature(b))**2)) if np.sign(fitter.signature(a)[-1])==np.sign(fitter.signature(b)[-1]) else 1e15 for b in rings] for a in reference]
            matching,_=min_cost_perfect_bipartite_matching(costs)
            masters[mi]=[rings[j] for j in matching]
        pens=[TTGlyphPen(None) for _ in fonts];error=0;segments_total=0
        for ri in range(len(reference)):
            group=[fitter.Ring(rings[ri]) for rings in masters]
            for mi,ring in enumerate(group):
                if mi!=2:ring.align(group[2])
            fitter.align_corners(group)
            if name == fonts[0].getBestCmap()[ord('~')]:
                # Retain every source corner; refitting then rounding erodes this narrow stroke.
                stops=np.unique(np.r_[0,*[r.vertices() for r in group]])
                for ring,pen in zip(group,pens):
                    points=ring.at(stops);pen.moveTo(tuple(points[0]))
                    for point in points[1:]:pen.lineTo(tuple(point))
                    pen.closePath()
                segments_total+=len(stops)
                continue
            saved_tolerance=fitter.TOLERANCE
            try:
                if name in {fonts[0].getBestCmap()[ord(c)] for c in '~?'}:fitter.TOLERANCE=0.2
                segments,worst=fitter.fit_group(group)
            finally:fitter.TOLERANCE=saved_tolerance
            error=max(error,worst);segments_total+=len(segments)
            for mi,pen in enumerate(pens):
                start=tuple(group[mi].at(0));pen.moveTo(start)
                for si,(line,ends,controls) in enumerate(segments):
                    end=start if si==len(segments)-1 else tuple(ends[mi])
                    if line:pen.lineTo(end)
                    else:pen.qCurveTo(tuple(controls[mi]),end)
                pen.closePath()
        for f,pen,old in zip(fonts,pens,gs):
            glyph=pen.glyph()
            if old.flags[0]&0x40:glyph.flags[0]|=0x40
            f['glyf'][name]=glyph
        assert len(set(structure(f['glyf'][name]) for f in fonts))==1,(name,'fit topology')
        report['fitted'][name]=dict(max_error_units=error,segments=segments_total,original_points=len(gs[2].coordinates),fitted_points=len(fonts[2]['glyf'][name].coordinates))
        if len(report['fitted'])%20==0:print('Fitted',len(report['fitted']),name,flush=True)
    if refit and fonts[0]['post'].italicAngle:
        # Shared point removals eliminate fitting reversals without breaking interpolation.
        repairs={'uni0061':(5,[57,100]),'uni0430':(5,[57,100]),'uni02DB':(7,[23]),'uni2116':(90,[3,39,72,90])}
        for name,(point,endpoints) in repairs.items():
            for f in fonts:
                g=f['glyf'][name]
                assert g.endPtsOfContours==endpoints and g.flags[point]&1,(name,'repair topology changed')
                del g.coordinates[point];del g.flags[point]
                g.endPtsOfContours=[e-1 if e>=point else e for e in endpoints]
            assert len(set(structure(f['glyf'][name]) for f in fonts))==1
            report['fitted'][name]['fitted_points']=len(fonts[2]['glyf'][name].coordinates)
        report['contour_repairs']={n:p for n,(p,_) in repairs.items()}
    for f in fonts:
        for name in order:
            g=f['glyf'][name];g.recalcBounds(f['glyf'])
            f['hmtx'][name]=(f['hmtx'][name][0],getattr(g,'xMin',0))


def build(italic=False,reuse=False,refit=False):
    suffix='Italic' if italic else ''
    folder=ROOT/('source/variable-masters-refit' if refit else 'source/variable-masters')/('Italic' if italic else 'Roman');folder.mkdir(parents=True,exist_ok=True)
    inputs=[ROOT/'source/stage6-masters'/f'SABModulCode-{style}{suffix}.ttf' for style in STYLES.values()]
    hashes={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    report_path=folder/'fit-report.json'
    if reuse:
        report=json.loads(report_path.read_text());assert report['input_sha256']==hashes
        if refit and italic:assert report.get('contour_repairs')=={'uni0061':5,'uni0430':5,'uni02DB':7,'uni2116':90},'Rebuild fitted masters for contour repairs'
        fonts=[TTFont(folder/p.name) for p in inputs]
    else:
        report=dict(input_sha256=hashes,fitted={},tolerance_units=fitter.TOLERANCE,status='IN_PROGRESS')
        fonts=[TTFont(p) for p in inputs]
        try:fit(fonts,report,refit)
        except Exception as e:
            report.update(status='FAIL',error=repr(e));report_path.write_text(json.dumps(report,indent=2)+'\n');raise
        for p,f in zip(inputs,fonts):f.save(folder/p.name)
        report['status']='PASS';report_path.write_text(json.dumps(report,indent=2)+'\n')
    ds=DesignSpaceDocument();axis=AxisDescriptor();axis.name='Weight';axis.tag='wght';axis.minimum=300;axis.default=400;axis.maximum=700;ds.addAxis(axis)
    for (weight,style),p in zip(STYLES.items(),inputs):
        src=SourceDescriptor();src.path=str(folder/p.name);src.name=style;src.familyName='SAB Modul Code';src.styleName=('Italic' if weight==400 else style+' Italic') if italic else style;src.location={'Weight':weight}
        if weight==400:src.copyInfo=src.copyLib=src.copyFeatures=True
        ds.addSource(src)
        instance=InstanceDescriptor();instance.familyName=src.familyName;instance.styleName=src.styleName;instance.name=src.styleName;instance.location=src.location.copy();ds.addInstance(instance)
    path=folder/'family.designspace';ds.write(path)
    vf,_,_=build_variable(path,optimize=False)
    # Adjacent triangular supports reproduce integer masters without nested-delta rounding.
    from fontTools.ttLib.tables.TupleVariation import TupleVariation
    raw=[TTFont(folder/p.name) for p in inputs]
    locations=[-1,0,1/3,2/3,1]
    for name in vf.getGlyphOrder():
        coords=[f['glyf']._getCoordinatesAndControls(name,f['hmtx'].metrics)[0] for f in raw]
        base=coords[1];variations=[]
        for i,loc in enumerate(locations):
            if i==1:continue
            delta=coords[i]-base
            if not any(x or y for x,y in delta):continue
            lower=locations[max(0,i-1)];upper=locations[min(4,i+1)]
            variations.append(TupleVariation({'wght':(lower,loc,upper)},list(delta)))
        vf['gvar'].variations[name]=variations
    for f in raw:f.close()
    buildStatTable(vf,[{'tag':'wght','name':'Weight','ordering':0,'values':[{'value':w,'name':s,'flags':2 if w==400 else 0,**({'linkedValue':700} if w==400 else {})} for w,s in STYLES.items()]},
                      {'tag':'ital','name':'Italic','ordering':1,'values':[{'value':int(italic),'name':'Italic' if italic else 'Roman','flags':0 if italic else 2,**({} if italic else {'linkedValue':1})}]}],macNames=True)
    prefix='SABModulCode'+suffix
    for platform,encoding,language in [(3,1,0x409),(1,0,0)]:vf['name'].setName(prefix,25,platform,encoding,language)
    from fontTools.ttLib.tables.ttProgram import Program
    vf['prep']=newTable('prep');vf['prep'].program=Program()
    vf['prep'].program.fromBytecode(bytes.fromhex('B801FF85B0048D'))
    vf['gasp']=newTable('gasp');vf['gasp'].version=1;vf['gasp'].gaspRange={0xFFFF:0x0F}
    if not italic and refit:
        from repair_vf_semicolon import repair
        repair(vf)
    out=ROOT/('checks/fable/refit-VF' if refit else 'release/SAB-Modul-Code-1.0/VF');out.mkdir(parents=True,exist_ok=True)
    filename='SABModulCode'+('-Italic' if italic else '')+'[wght]'
    vf.save(out/(filename+'.ttf'));vf.flavor='woff2';vf.save(out/(filename+'.woff2'))
    print(filename,'WOFF2',(out/(filename+'.woff2')).stat().st_size,flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--italic',action='store_true');parser.add_argument('--reuse',action='store_true');parser.add_argument('--refit',action='store_true');args=parser.parse_args();build(args.italic,args.reuse,args.refit)
