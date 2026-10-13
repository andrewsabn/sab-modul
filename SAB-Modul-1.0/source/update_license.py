"""Update only the embedded OFL license; preserve all other font data."""
from pathlib import Path
from fontTools.ttLib import TTFont
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
LICENSE='This Font Software is licensed under the SIL Open Font License, Version 1.1. This license is available with a FAQ at: https://openfontlicense.org'
changes=[]
for folder in ['TTF','OTF','WOFF2','VF','WEB']:
 for p in sorted((ROOT/folder).iterdir()):
  if p.suffix not in ['.ttf','.otf','.woff2']:continue
  f=TTFont(p,recalcTimestamp=False)
  before={t:f.getTableData(t) for t in f.keys() if t not in ['GlyphOrder','name','head']}
  names={(n.nameID,n.platformID,n.platEncID,n.langID):n.toUnicode() for n in f['name'].names if n.nameID!=13}
  old=hashlib.sha256(p.read_bytes()).hexdigest()
  for n in f['name'].names:
   if n.nameID==13:n.string=LICENSE
  f.save(p);g=TTFont(p)
  assert all(g.getTableData(t)==b for t,b in before.items())
  assert {(n.nameID,n.platformID,n.platEncID,n.langID):n.toUnicode() for n in g['name'].names if n.nameID!=13}==names
  assert all(n.toUnicode()==LICENSE for n in g['name'].names if n.nameID==13)
  changes.append({'file':str(p.relative_to(ROOT)),'before_sha256':old,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'only_nameID13_changed':True})
(ROOT/'checks/license-update.json').write_text(json.dumps({'license':LICENSE,'files':changes},indent=2))
print('License updated:',len(changes),'fonts; other tables and name records unchanged')
