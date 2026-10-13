"""Run the same Microsoft-derived Font Validator used for the accepted Mono."""
from pathlib import Path
import collections,concurrent.futures,hashlib,json,subprocess,xml.etree.ElementTree as ET
from fontTools.ttLib import TTFont
ROOT=Path(__file__).resolve().parents[1]
RELEASE=ROOT/'release/SAB-Modul-Code-1.0'
OUT=ROOT/'checks/fontvalidator'
EXE=Path('/tmp/sab-font-validator-2.1.6/FontVal-2.1.6-osx-10.9-x64/FontValidator')

def check(path):
    rel=path.relative_to(RELEASE);folder=OUT/str(rel).replace('/','__');folder.mkdir(parents=True,exist_ok=True)
    decoded=path
    if path.suffix=='.woff2':
        decoded=folder/path.with_suffix('.ttf').name
        f=TTFont(path,recalcTimestamp=False);f.flavor=None;f.save(decoded)
    cmd=[str(EXE),'-file',str(decoded),'-report-dir',str(folder),'-no-raster-tests']
    with (folder/'run.log').open('w') as log:
        try: code=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=120).returncode
        except subprocess.TimeoutExpired:code='timeout'
    reports=list(folder.glob('*.report.xml'));counts=collections.Counter();issues=[]
    if reports:
        for e in ET.parse(reports[0]).iter('Report'):
            counts[e.get('ErrorType')]+=1
            if e.get('ErrorType') in ['E','W','A']:issues.append(e.attrib)
    result=dict(file=str(rel),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),command=cmd,exit_code=code,counts=dict(counts),issues=issues,report=str(reports[0].relative_to(ROOT)) if reports else None)
    print(str(rel),code,dict(counts),flush=True)
    return result

if __name__=='__main__':
    inputs=[p for folder in ['TTF','OTF','WOFF2','VF','WEB'] for p in sorted((RELEASE/folder).iterdir()) if p.suffix in ['.ttf','.otf','.woff2']]
    assert len(inputs)==44 and EXE.is_file()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(check,inputs))
    (ROOT/'checks/fontvalidator.json').write_text(json.dumps(dict(version='HinTak Font Validator 2.1.6, Microsoft-derived',binary_sha256=hashlib.sha256(EXE.read_bytes()).hexdigest(),raster_tests=False,results=results),indent=2)+'\n')
