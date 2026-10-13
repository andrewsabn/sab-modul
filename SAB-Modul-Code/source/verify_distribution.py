"""Sanitize every delivered font and record the exact bytes, without exclusions."""
import hashlib,json
from pathlib import Path
from fontTools.ttLib import TTFont
import ots
ROOT=Path(__file__).resolve().parents[1]
release=ROOT/'release/SAB-Modul-Code-1.0'
rows=[]
for folder in ['TTF','OTF','WOFF2','VF','WEB']:
 for path in sorted((release/folder).glob('*')):
  if path.suffix not in ['.ttf','.otf','.woff2']:continue
  f=TTFont(path,recalcTimestamp=False);run=ots.sanitize(str(path),capture_output=True)
  row={'file':str(path.relative_to(release)),'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
       'cmap':len(f.getBestCmap()),'advances':sorted({a for a,b in f['hmtx'].metrics.values()}),
       'mac_names':sum(n.platformID==1 for n in f['name'].names),'ots_exit':run.returncode,
       'ots_stdout':run.stdout.decode(errors='replace'),'ots_stderr':run.stderr.decode(errors='replace')}
  rows.append(row)
  assert run.returncode==0 and row['advances']==[0,600] and row['mac_names']>0,row
  assert f['post'].isFixedPitch==1 and f['OS/2'].panose.bProportion==9
  assert (f['hhea'].ascent,f['hhea'].descent,f['hhea'].lineGap)==(1000,-300,0)
  assert 'kern' not in f
  for lookup in f['GPOS'].table.LookupList.Lookup:
   assert lookup.LookupType!=2
   if lookup.LookupType==9:assert all(st.ExtensionLookupType!=2 for st in lookup.SubTable)
  print(row['file'],'OTS PASS',row['bytes'],row['sha256'],flush=True)
assert len(rows)==44,len(rows)
(ROOT/'checks/distribution.json').write_text(json.dumps({'status':'PASS','font_count':len(rows),'files':rows},indent=2)+'\n')
