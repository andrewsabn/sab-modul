"""Verify a GPOS-only VF update against preserved outlines and current static masters."""
from pathlib import Path
import hashlib,json,sys
from fontTools.ttLib import TTFont
from fontTools.varLib.instancer import instantiateVariableFont
from proof import ROOT,HEAD,SUB,BODY,NUM,ROUND
from subset_web import shaping_font,shape
from build import WEIGHTS

previous,current=sys.argv[1:3]
families=sys.argv[3:] or ['Sans','Mono']
assert all(family in ['Sans','Mono'] for family in families)
out=ROOT/'iterations'/current
assert out.is_dir()
texts={HEAD,SUB,BODY,NUM,ROUND}
texts.update(row['pair'] for row in json.loads((ROOT/'iterations/24/pairs.json').read_text())['pairs'])
texts.update(['Тр','Ту','Та','То','ГА','АУ','ЛА','ДУ','ЧА','УЧ','Кое','Тф','AV','AT','LT','Ty','Wa','f)','f.','r.','1.1','−37\u202f% [2026]'])
texts.update(a+b for a in '0123456789' for b in '0123456789')
texts.update(a+b for a in '17.,«»()[]{}−$€£₽₸¥%‰' for b in '17')
texts.update(a+b for a in '17' for b in '.,«»()[]{}−$€£₽₸¥%‰')
pending=[];summary=[]
for family in families:
 for italic in [False,True]:
  stem='SABModul'+family+('-Italic' if italic else '')+'[wght]'
  path=ROOT/'VF'/(stem+'.ttf');old_path=ROOT/'iterations'/previous/'fonts'/path.name
  vf,old,web=TTFont(path),TTFont(old_path),TTFont(path.with_suffix('.woff2'))
  unchanged=['glyf','gvar','hmtx','HVAR','GSUB','cmap','fvar']
  for tag in unchanged:assert old[tag].compile(old)==vf[tag].compile(vf),(stem,tag,'Geometry changed')
  tables={tag:vf[tag].compile(vf)==web[tag].compile(web) for tag in ['cmap','hmtx','fvar','gvar','GPOS','GSUB']}
  assert all(tables.values()),(stem,'WOFF2 tables differ')
  full=shaping_font(vf);old_full=shaping_font(old);count=0;sources={};baseline_differences=[];live_rounding=[];instance_rounding=[]
  for style,(weight,_) in WEIGHTS.items():
   source=ROOT/'source/masters'/('SABModul'+family+'-'+style+('Oblique' if italic else '')+'.ttf')
   sources[weight]=hashlib.sha256(source.read_bytes()).hexdigest();static=shaping_font(TTFont(source))
   instance=shaping_font(instantiateVariableFont(vf,{'wght':weight},inplace=False))
   for extras in [{},{'pnum':True},{'pnum':True,'case':True},{'tnum':True,'case':True}]:
    features={'kern':True,'mark':True,'ccmp':True,**extras}
    for text in sorted(texts):
     actual=shape(full,text,weight,features);expected=shape(static,text,weight,features)
     baseline=shape(full,text,weight,{**features,'kern':False})
     static_baseline=shape(static,text,weight,{**features,'kern':False})
     assert baseline==shape(old_full,text,weight,{**features,'kern':False}),(stem,weight,text,'Baseline changed')
     assert [p[0] for p in actual]==[p[0] for p in expected],(stem,weight,text,'Substitutions changed')
     def delta(on,off):return [(a[0],*[x-y for x,y in zip(a[1:],b[1:])]) for a,b in zip(on,off)]
     instantiated=shape(instance,text,weight,features)
     instance_base=shape(instance,text,weight,{**features,'kern':False})
     instance_error=max(abs(x-y) for a,b in zip(delta(instantiated,instance_base),delta(expected,static_baseline)) for x,y in zip(a[1:],b[1:]))
     assert instance_error<=1,(stem,weight,text,extras,'Instantiated kerning differs beyond one unit')
     if instance_error:instance_rounding.append({'weight':weight,'text':text,'features':extras,'difference_units':instance_error})
     rounding=max(abs(x-y) for a,b in zip(delta(actual,baseline),delta(expected,static_baseline)) for x,y in zip(a[1:],b[1:]))
     assert rounding<=1,(stem,weight,text,extras,'Live VF differs beyond one unit of integer output rounding')
     if rounding:live_rounding.append({'weight':weight,'text':text,'features':extras,'difference_units':rounding})
     if baseline!=static_baseline:
      baseline_differences.append({'weight':weight,'text':text,'features':extras,'max_position_difference_units':max(abs(x-y) for a,b in zip(baseline,static_baseline) for x,y in zip(a[1:],b[1:]))})
     count+=1
  report=json.loads((ROOT/'iterations'/previous/(stem+'.verification.json')).read_text())
  report.pop('geometry_and_layout_unchanged_from',None)
  report.update(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),woff2_sha256=hashlib.sha256(path.with_suffix('.woff2').read_bytes()).hexdigest(),woff2_bytes=path.with_suffix('.woff2').stat().st_size,woff2_tables_match_ttf=tables)
  report['geometry_unchanged_from']={'file':str(old_path.relative_to(ROOT)),'sha256':hashlib.sha256(old_path.read_bytes()).hexdigest(),'identical_tables':unchanged,'note':'Geometry measurements inherited from the preserved VF; GPOS rechecked against current static masters.'}
  for row in report['records']:
   if row['kind']=='master':row['source_sha256']=sources[row['weight']]
  report['layout_check']={'comparisons':count,'texts':sorted(texts),'weights':[v[0] for v in WEIGHTS.values()],'features':['kern,mark,ccmp','kern,mark,ccmp,pnum','kern,mark,ccmp,pnum,case','kern,mark,ccmp,tnum,case'],'source':'current unhinted static masters','substituted_glyphs_identical':True,'kerning_comparison_tolerance_units':1,'tolerance_note':'Integer variation deltas can differ by one design unit from static masters. Exact equivalence is not claimed. Old and new VF both yield -29 for ea at 700; static master yields -30.','unkerned_positions_identical_to_previous_vf':True,'baseline_differences_from_static_count':len(baseline_differences),'max_baseline_position_difference_units':max((r['max_position_difference_units'] for r in baseline_differences),default=0),'baseline_difference_examples':baseline_differences[:20],'live_vf_integer_rounding_count':len(live_rounding),'live_vf_integer_rounding_examples':live_rounding[:20],'max_live_vf_kerning_difference_units':max((r['difference_units'] for r in live_rounding),default=0),'instantiated_integer_rounding_count':len(instance_rounding),'instantiated_integer_rounding_examples':instance_rounding[:20],'max_instantiated_kerning_difference_units':max((r['difference_units'] for r in instance_rounding),default=0)}
  pending.append((stem,report));summary.append({'font':stem,'comparisons':count,'unchanged_geometry_tables':unchanged})
for stem,report in pending:
 for folder in [ROOT/'VF',out]:(folder/(stem+'.verification.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2))
(out/'layout-refresh.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
