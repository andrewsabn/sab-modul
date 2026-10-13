from pathlib import Path
import sys, json, hashlib, subprocess, concurrent.futures, collections, os
import xml.etree.ElementTree as ET
from fontTools.ttLib import TTFont
import ots

root = Path(sys.argv[1]).resolve()
out = root/'checks'
manifest = json.loads((root/'FONT-SHA256.json').read_text())
fonts = [root/r for r in manifest]
ots_bin = Path(ots.__file__).parent/'ots-sanitize'
validator = Path(sys.argv[2]).resolve()
env = dict(os.environ, LC_ALL='C', LANG='C')

def one_ots(p):
    r = subprocess.run([str(ots_bin),str(p)],capture_output=True,text=True,timeout=90)
    return {'file':str(p.relative_to(root)),'exit_code':r.returncode,
            'output':r.stdout+r.stderr,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}

def one_validator(p):
    rel = str(p.relative_to(root))
    d = out/'fontvalidator'/rel.replace('/','__')
    d.mkdir(parents=True,exist_ok=True)
    actual = p
    if p.suffix=='.woff2':
        f=TTFont(p,recalcTimestamp=False);f.flavor=None
        actual=d/(p.stem+'.ttf');f.save(actual)
    for pattern in ('*.report.xml', '*.report.html'):
        for stale in d.glob(pattern): stale.unlink()
    with (d/'run.log').open('wb') as log:
        r=subprocess.run([str(validator),'-file',str(actual),'-report-dir',str(d),'-no-raster-tests'],stdout=log,stderr=subprocess.STDOUT,timeout=120,env=env)
    xmls=list(d.glob('*.report.xml'))
    issues=[]
    if xmls:issues=[dict(n.attrib) for n in ET.parse(xmls[0]).iter('Report')]
    return {'file':rel,'exit_code':r.returncode,'report':str(xmls[0].relative_to(root)) if xmls else None,
            'counts':dict(collections.Counter(n.get('ErrorType') for n in issues)),
            'issues':[n for n in issues if n.get('ErrorType') in ('E','W')]}

def one_bakery(job):
    family, folder, profile, paths = job
    d=out/'fontbakery';d.mkdir(exist_ok=True)
    label=family+'-'+folder+'-'+profile
    cmd=[str(Path(sys.executable).with_name('fontbakery')),'check-'+profile,*map(str,paths),
         '--json',str(d/(label+'.json')),'--html',str(d/(label+'.html')),
         '--no-progress','--no-colors','--loglevel','FAIL','--timeout','5']
    for suffix in ('.json', '.html'):
        stale = d/(label+suffix)
        if stale.exists(): stale.unlink()
    with (d/(label+'.log')).open('wb') as log:
        r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=1200,env=env)
    data=json.loads((d/(label+'.json')).read_text()) if (d/(label+'.json')).exists() else {}
    result={'label':label,'exit_code':r.returncode,'fonts':len(paths),'counts':data.get('result',{}),
            'json':str((d/(label+'.json')).relative_to(root))}
    print(label,result['counts'],flush=True)
    return result

jobs=[]
for family in ('Sans','Mono','Code'):
    group=root/('SAB-Modul-Code' if family=='Code' else 'SAB-Modul-1.0')
    for folder in ('TTF','OTF','VF'):
        paths=sorted(p for p in (group/folder).glob('*') if family in p.name and p.suffix in ('.ttf','.otf'))
        for profile in ('universal','googlefonts','adobefonts'):jobs.append((family,folder,profile,paths))

with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    results=list(pool.map(one_ots,fonts))
(out/'ots.json').write_text(json.dumps(results,indent=2)+'\n')
print('OTS:',sum(x['exit_code']==0 for x in results),'/',len(results),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
    results=list(pool.map(one_validator,fonts))
(out/'fontvalidator.json').write_text(json.dumps({'raster_tests':False,'results':results},indent=2)+'\n')
print('Font Validator reports:',sum(bool(x['report']) for x in results),'/',len(results),flush=True)
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    runs=list(pool.map(one_bakery,jobs))
(out/'fontbakery-runs.json').write_text(json.dumps(runs,indent=2)+'\n')
print('Full FontBakery profile runs:',len(runs),flush=True)
