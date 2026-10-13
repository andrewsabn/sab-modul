from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import subprocess,json,html,hashlib,sys
from fontTools.ttLib import TTFont
ROOT=Path(__file__).resolve().parents[1]
VARIABLE='--variable' in sys.argv
WEB='--web' in sys.argv
assert not (WEB and VARIABLE),'Choose one file set'
OUT=ROOT/('checks-web' if WEB else 'checks-vf' if VARIABLE else 'checks');OUT.mkdir(exist_ok=True)
PATCH=json.loads((ROOT/'checks/checker-fix.json').read_text()) if (ROOT/'checks/checker-fix.json').exists() else None

def check(item):
 if WEB:
  fonts=[item,item.with_name(item.name.replace('[wght]','-Italic[wght]'))]
  assert all(p.exists() for p in fonts),'A script subset lacks its Roman/Italic pair'
  label=item.stem.replace('[wght]','')
 else:
  family,fmt=item;label=family+'-'+fmt
  fonts=sorted((ROOT/fmt).glob('SABModul'+family+('*.ttf' if VARIABLE else '-*.'+fmt.lower())))
 assert fonts,(item,'No files to check')
 hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in fonts}
 decoded=None
 if WEB:
  folder=OUT/'decoded';folder.mkdir(exist_ok=True)
  decoded=[];decoded_fonts=[]
  for source in fonts:
   path=folder/source.with_suffix('.ttf').name
   font=TTFont(source);font.flavor=None;font.save(path)
   decoded.append({'file':str(path.relative_to(ROOT)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'method':'fontTools decoded the delivered WOFF2; FontBakery CLI accepts TTF/OTF only'})
   decoded_fonts.append(path)
  fonts=decoded_fonts
 cmd=[str(Path(sys.executable).with_name('fontbakery')),'check-universal',*map(str,fonts),'--json',str(OUT/(label+'.json')),'--html',str(OUT/(label+'.html')),'--no-progress','--skip-network','--loglevel','FAIL']
 with (OUT/(label+'.log')).open('w') as log:result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 counts={};issues=[]
 report=OUT/(label+'.json')
 if report.exists():
  data=json.loads(report.read_text())
  for section in data['sections']:
   for entry in section['checks']:
    status=entry['result'];counts[status]=counts.get(status,0)+1
    if status in ['FAIL','ERROR','FATAL']:issues.append({'check':entry['key'],'result':status,'logs':entry.get('logs',[])})
 return {'batch':label,'command':cmd,'exit_code':result.returncode,'counts':counts,'issues':issues,'sha256':hashes,'decoded_woff2':decoded,'checker_patch':PATCH['patched_sha256'] if PATCH else None}

items=[p for p in sorted((ROOT/'WEB').glob('*.woff2')) if '-Italic' not in p.name] if WEB else [(f,t) for f in ['Sans','Mono'] for t in (['VF'] if VARIABLE else ['TTF','OTF'])]
assert items,'No fonts to check'
with ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(check,items))
report_name='fontbakery-web-report' if WEB else 'fontbakery-variable-report' if VARIABLE else 'fontbakery-report'
(ROOT/(report_name+'.json')).write_text(json.dumps(results,ensure_ascii=False,indent=2))
body=['<!doctype html><html lang="ru"><meta charset="utf-8"><title>SAB Modul · FontBakery</title><style>body{font:16px/1.5 system-ui;margin:40px;max-width:1000px}td,th{padding:12px;text-align:left;border-bottom:1px solid #ccc}a{color:#006383}</style><h1>FontBakery · независимые проверки семейств и форматов</h1><p>Этот прогон выполнен с --skip-network после ошибки ответа namecheck.fontdata.com в полном прогоне 09. Сетевая проверка уникальности названия остаётся непроверенной. Полный предыдущий отчёт сохранён в iterations/09.</p><p>TTF и OTF проверяются отдельно, чтобы одинаковые начертания разных форматов не считались дубликатами. Sans и Mono также проверяются отдельно.</p><table><tr><th>Набор</th><th>Результаты</th><th>Отчёт</th></tr>']
for r in results:body.append('<tr><td>'+r['batch']+'</td><td>'+html.escape(str(r['counts']))+'</td><td><a href="'+OUT.name+'/'+r['batch']+'.html">Открыть</a></td></tr>')
body.append('</table>')
if PATCH:
 body.append('<p>В FontBakery 1.1.0 применена локальная правка проверки opentype/monospace. Список глифов читается через getGlyphOrder(), который работает с TTF и CFF. Условия проверки сохранены; её результат на 28 TTF совпал с исходным кодом. Проверка заведомо неверного advanceWidthMax по-прежнему выдаёт FAIL. Это прогон с локальной правкой инструмента, не неизменённая версия FontBakery.</p><p><a href="checks/checker-fix.json">Подтверждение правки и хеши</a> · <a href="source/fontbakery-cff.patch">Изменённые строки</a>. Исходные ERROR сохранены в iterations/14.</p>')
else:
 body.append('<p>FontBakery 1.1.0 обращается к таблице glyf даже у CFF. KeyError: glyf в проверке opentype/monospace означает ошибку проверяющей программы. Проверка не исключалась.</p>')
if VARIABLE:body.append('<p>Проверены четыре переменных TTF с осью wght. Они используют smart dropout без хинтинга штрихов. Этот отчёт не оценивает рисунок промежуточных весов и не подтверждает визуальную приёмку.</p>')
if WEB:body.append('<p>FontBakery CLI не принимает WOFF2 напрямую. Каждый поставляемый WOFF2 декодирован через fontTools в checks-web/decoded; проверено содержимое этого TTF. Хеши исходного WOFF2 и декодированного TTF сохранены в JSON. Подмножества проверены по письменностям парами Roman/Italic, чтобы проверить связь начертаний и избежать повторов имён у частей одного шрифта. Совместная проверка семейства находится в fontbakery-variable-report.html. Результат не подтверждает визуальную приёмку и работу границ unicode-range в браузере.</p>')
body.append('</html>')
(ROOT/(report_name+'.html')).write_text('\n'.join(body))
print(json.dumps([{k:r[k] for k in ['batch','exit_code','counts']} for r in results],indent=2))
