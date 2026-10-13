"""Apply the recorded CFF glyph-enumeration fix to this dedicated FontBakery runtime."""
from pathlib import Path
from types import SimpleNamespace
from importlib.metadata import version
import hashlib,json,difflib
from fontTools.ttLib import TTFont
import fontbakery.checks.opentype.monospace as module
import fontbakery.checks.conditions
from fontbakery.testable import Font

ROOT=Path(__file__).resolve().parents[1]
target=Path(module.__file__)
backup=target.with_suffix('.py.sab-original')
original=backup.read_text() if backup.exists() else target.read_text()
old='ttFont["glyf"].glyphs';new='ttFont.getGlyphOrder()'
assert original.count(old)==2,'Review the upstream checker before applying this patch'
fixed=original.replace(old,new)
assert target.read_text() in [original,fixed],'Unexpected local checker modifications'
before={'__name__':module.__name__};after={'__name__':module.__name__}
exec(compile(original,str(target),'exec'),before)
exec(compile(fixed,str(target),'exec'),after)

def results(check,font):
 stats=Font.glyph_metrics_stats.func(SimpleNamespace(ttFont=font))
 return [(status.name,getattr(message,'code',None),getattr(message,'message',str(message))) for status,message in check(font,stats)]

records=[]
for path in sorted((ROOT/'TTF').glob('*.ttf')):
 font=TTFont(path)
 assert results(before['check_monospace'],font)==results(after['check_monospace'],font),path.name
 records.append({'file':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'unchanged_result':True})
for path in sorted((ROOT/'OTF').glob('SABModulMono-*.otf')):
 font=TTFont(path);checks=results(after['check_monospace'],font)
 assert all(status not in ['FAIL','ERROR','FATAL'] for status,_,_ in checks),(path.name,checks)
 records.append({'file':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'result':checks})
bad=TTFont(next((ROOT/'TTF').glob('SABModulMono-*.ttf')))
bad['hhea'].advanceWidthMax=9999
assert any(status=='FAIL' and code=='bad-advanceWidthMax' for status,code,_ in results(after['check_monospace'],bad))
if not backup.exists():backup.write_text(original)
target.write_text(fixed)
(ROOT/'source/fontbakery-cff.patch').write_text(''.join(difflib.unified_diff(original.splitlines(True),fixed.splitlines(True),fromfile='fontbakery/checks/opentype/monospace.py',tofile='fontbakery/checks/opentype/monospace.py')))
report={'fontbakery_version':version('fontbakery'),'local_patch':'Enumerate glyphs through getGlyphOrder for both glyf and CFF; all conditions retained','original_sha256':hashlib.sha256(original.encode()).hexdigest(),'patched_sha256':hashlib.sha256(fixed.encode()).hexdigest(),'negative_control':'bad-advanceWidthMax still fails','files':records}
(ROOT/'checks/checker-fix.json').write_text(json.dumps(report,ensure_ascii=False,indent=2))
print('CFF checker patch verified:',len(records),'font checks; negative control passed')
