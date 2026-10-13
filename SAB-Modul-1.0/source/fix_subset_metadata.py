"""Recalculate OS/2 subset averages and layout context without changing glyphs."""
from pathlib import Path
from fontTools.ttLib import TTFont
from fontTools.otlLib.maxContextCalc import maxCtxFont
import hashlib, json
root=Path(__file__).resolve().parents[1]
changes=[]
for p in sorted((root/'WEB').glob('*-*.woff2')):
    if '[wght]-' not in p.name:
        continue
    f=TTFont(p,recalcTimestamp=False)
    fields={}
    if 'Sans' in p.name:
        widths=[a for a,b in f['hmtx'].metrics.values() if a>0]
        fields['xAvgCharWidth']=sum(widths)//len(widths)
    if 'Mono' in p.name and '-symbols.' in p.name:
        fields['usMaxContext']=maxCtxFont(f)
    delta={k:{'before':getattr(f['OS/2'],k),'after':v} for k,v in fields.items() if getattr(f['OS/2'],k)!=v}
    if not delta:
        continue
    before={t:f.getTableData(t) for t in f.keys() if t not in ('GlyphOrder','OS/2','head')}
    old=hashlib.sha256(p.read_bytes()).hexdigest()
    for k,v in fields.items():setattr(f['OS/2'],k,v)
    f.save(p)
    check=TTFont(p)
    assert all(check.getTableData(t)==data for t,data in before.items())
    assert all(getattr(check['OS/2'],k)==v for k,v in fields.items())
    changes.append({'file':str(p.relative_to(root)),'before_sha256':old,'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'fields':delta})
if changes:
    (root/'checks/subset-metadata-fix.json').write_text(json.dumps(changes,indent=2))
print('Updated subset metadata:',len(changes))
