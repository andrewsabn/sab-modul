"""Create a browser DOM-width comparison for complete and unicode-range fonts."""
from pathlib import Path
import json,hashlib,sys
ROOT=Path(__file__).resolve().parents[1]
out=ROOT/'iterations'/sys.argv[1]/'browser-subsets';out.mkdir(exist_ok=False)
faces=[]
for family in ['Sans','Mono']:
 for slant in ['', '-Italic']:
  style='oblique 10deg' if slant else 'normal'
  name='SABModul'+family+slant+'[wght].woff2'
  faces.append(f"@font-face{{font-family:'Full {family}';font-style:{style};font-weight:200 900;src:url('../../../VF/{name}') format('woff2')}}")
samples=['AVATAR Wa Ty','Технологический руководитель банков','Строю финтех и управляю теми, кто его делает.','FlyOptima - финтех','АV','AУ','Т.','T.','Т,','«Т','Т»','Т-','-а','T-','−37 %','756 → 648','2007-2026','$87,3 → $55,1','№ 17','[FCB]','éV','AVé','ŁA','AŁ','Тё','е\u0308','a\u0301','«Технологии»','release v0.8.0-mac']
page='''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Проверка веб-подмножеств SAB</title>
<link rel="stylesheet" href="../../../WEB/fonts.css"><style>FACES
body{font:16px/1.5 system-ui;margin:32px;color:#171717;background:#fff}h1{font-size:24px}table{border-collapse:collapse}td,th{padding:8px;text-align:left;border-bottom:1px solid #ccc}button{font:inherit;padding:10px;cursor:pointer}button:focus-visible{outline:3px solid #005d7e}#measure{position:absolute;left:-20000px;top:0;white-space:pre}.sample{display:inline-block;white-space:pre;font-kerning:normal;font-synthesis:none;letter-spacing:0}pre{white-space:pre-wrap} .pair{font-size:40px;margin:20px 0}</style>
<h1>Полный шрифт и веб-подмножества</h1><p id="status">Загрузка шрифтов…</p><button id="download" disabled>Скачать отчёт</button><div id="examples"></div><details><summary>Результат в JSON</summary><pre id="report"></pre></details><div id="measure" aria-hidden="true"></div>
<script>
const samples=SAMPLES;
(async()=>{
 try{
 const records=[],loaded=[];
 for(const family of ['Sans','Mono']) for(const style of ['normal','oblique 10deg']){
  for(const name of ['Full '+family,'SAB Modul '+family]){
   const fonts=await document.fonts.load(`${style} 400 96px "${name}"`,samples.join(' '));
   if(!fonts.length||fonts.some(f=>f.status!=='loaded'))throw Error('Font loading failed: '+name+' '+style);
   loaded.push({family:name,style,count:fonts.length});
  }
 }
 await document.fonts.ready;
 const box=document.getElementById('measure');
 for(const family of ['Sans','Mono']) for(const style of ['normal','oblique 10deg']) for(const weight of [300,400,700,900]) for(const size of [14,30,96]) for(const text of samples){
  const widths={};
  for(const kind of ['full','subset']){
   const span=document.createElement('span');span.className='sample';span.textContent=text;
   span.style.fontFamily=`"${kind==='full'?'Full '+family:'SAB Modul '+family}"`;span.style.fontWeight=weight;span.style.fontSize=size+'px';span.style.fontStyle=style;
   box.append(span);widths[kind]=span.getBoundingClientRect().width;span.remove();
  }
  records.push({family,style,weight,size,text,...widths,delta:widths.subset-widths.full});
 }
 const failures=records.filter(r=>Math.abs(r.delta)>1/64);
 const result={userAgent:navigator.userAgent,devicePixelRatio,viewport:[innerWidth,innerHeight],loaded,comparisons:records.length,mismatches:failures.length,maxDelta:Math.max(...records.map(r=>Math.abs(r.delta))),toleranceCssPx:1/64,scope:'DOM text advance only; not proof of identical outlines or Windows raster',records};
 document.getElementById('status').textContent=`Проверено ${records.length}. Расхождений ширины ${failures.length}. Максимум ${result.maxDelta.toFixed(4)} px.`;
 document.getElementById('report').textContent=JSON.stringify(result,null,2);
 const seen=new Set();
 for(const r of failures.filter(r=>r.size===96&&r.weight===400&&r.style==='normal')){
  const key=r.family+r.text;if(seen.has(key)||seen.size===10)continue;seen.add(key);
  const p=document.createElement('p');p.textContent=r.family+' / '+r.text+' / '+r.delta.toFixed(3)+' px';document.getElementById('examples').append(p);
 }
 const button=document.getElementById('download');button.disabled=false;button.onclick=()=>{const a=document.createElement('a');a.download='browser-subsets.json';a.href=URL.createObjectURL(new Blob([JSON.stringify(result,null,2)],{type:'application/json'}));a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000)};
 }catch(error){document.getElementById('status').textContent='Ошибка: '+error.message;}
})();
</script></html>'''.replace('FACES','\n'.join(faces)).replace('SAMPLES',json.dumps(samples,ensure_ascii=False))
(out/'index.html').write_text(page)
(out/'inputs.json').write_text(json.dumps({'iteration':sys.argv[1],'files':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for folder in ['VF','WEB'] for p in (ROOT/folder).glob('*') if p.suffix in ['.woff2','.css']},'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},indent=2))
print(out/'index.html')
