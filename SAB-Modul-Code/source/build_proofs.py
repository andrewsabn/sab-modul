import argparse
import json
import os
from html import escape
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "proofs"
WEIGHTS = {300: "Light", 400: "Regular", 500: "Medium", 600: "SemiBold", 700: "Bold"}
PAIRS = [
    "0 O o", "1 l I | ¦", "' \" ` ‘ ’ “ ”", ", . ; :",
    "- – — ~ _", "{ } ( ) [ ] < >", "Z 2", "S 5", "B 8", "G 6",
    "g 9", "q 9", "rn m", "vv w", "cl d", "З 3", "О 0 о", "Ч 4",
    "б 6", "ь ъ ы", "и й", "ш щ", "л п", "Э Е",
]
LANGUAGE_LINES = [
    "RU: Съешь ещё этих мягких французских булок.",
    "EN: The quick brown fox jumps over the lazy dog.",
    "UK: Їжак їде в Київ. Єдність і гідність України.",
    "KK: Қазақ тілі: Әә Ғғ Ққ Ңң Өө Ұұ Үү Һһ Іі.",
    "SR: Љубав, њива, ђак и ћирилица. Јован чита.",
    "EL: Ελληνικά: ά έ ή ί ό ύ ώ ΐ ΰ. Αθήνα, κόσμος.",
    "PL: Zażółć gęślą jaźń. Pchnąć w tę łódź jeża.",
    "CS: Příliš žluťoučký kůň úpěl ďábelské ódy.",
    "TR: Pijamalı hasta yağız şoföre çabucak güvendi.",
    "LT: Įlinkęs ąžuolas; ė, ū, į, i̇́, į́, í̧, ј́.",
]
OPERATORS = "!= === <= >= => -> :: ;; || && ?? ?. .. ... *= /= %= <> <<= >>="
BOX_ROWS = [
    "┌─┬─┬─┐  ╔═╦═╦═╗  ┏━┳━┳━┓",
    "│ │ │ │  ║ ║ ║ ║  ┃ ┃ ┃ ┃",
    "├─┼─┼─┤  ╠═╬═╬═╣  ┣━╋━╋━┫",
    "│ │ │ │  ║ ║ ║ ║  ┃ ┃ ┃ ┃",
    "└─┴─┴─┘  ╚═╩═╩═╝  ┗━┻━┻━┛",
]
SNIPPET = {
    "Kotlin": """// Конфигурация задаёт поведение продукта без пересборки узла.
data class FeeRule(
    val id: String, val currency: String,
    val percent: BigDecimal, val limit: Money?
)

fun calculateFee(amount: Money, rule: FeeRule): Money {
    require(amount.currency == rule.currency) // Валюты должны совпасть.
    return rule.limit?.let { (amount * rule.percent / 100).min(it) }
}""",
    "JSON": """{
  "schemaVersion": 3,
  "product": "debit-standard",
  "currency": "KZT",
  "limits": {
    "daily": 500000,
    "cashWithdrawal": 200000
  },
  "fee": {"ruleId": "cash-01", "percent": 1.25}
}""",
    "SQL": """-- Схема хранит версии конфигурации и время применения.
CREATE TABLE fcb_product_config (
    product_id TEXT NOT NULL, version INTEGER NOT NULL,
    payload JSONB NOT NULL, applied_at TIMESTAMPTZ,
    PRIMARY KEY (product_id, version)
);
-- Проверяйте резервную копию до импорта.
SELECT product_id, version, applied_at
FROM fcb_product_config WHERE applied_at IS NOT NULL
ORDER BY applied_at DESC LIMIT 10;""",
}


def face_assets(mode, font_dir):
    if font_dir:
        kind = "static" if mode == "stage2" else "variable"
        return kind, (ROOT / font_dir if not Path(font_dir).is_absolute() else Path(font_dir))
    if mode == "stage2":
        return "static", ROOT / "source" / "stage2-masters"
    return "variable", ROOT / "release" / "SAB-Modul-Code-1.0" / "WEB"


def face_css(page, family, kind, directory):
    rules = []
    if kind == "static":
        for weight, name in WEIGHTS.items():
            for italic, suffix in ((False, ""), (True, "Italic")):
                file = directory / f"SABModulCode-{name}{suffix}.ttf"
                if not file.exists() and name == "Regular" and italic:
                    file = directory / "SABModulCode-Italic.ttf"
                url = Path(os.path.relpath(file, page.parent)).as_posix()
                rules.append(f'@font-face{{font-family:"{family}";src:url("{url}") format("truetype");font-weight:{weight};font-style:{"italic" if italic else "normal"};font-synthesis:none}}')
    else:
        for italic, filename in ((False, "SABModulCode[wght].woff2"), (True, "SABModulCode-Italic[wght].woff2")):
            url = Path(os.path.relpath(directory / filename, page.parent)).as_posix()
            rules.append(f'@font-face{{font-family:"{family}";src:url("{url}") format("woff2");font-weight:300 700;font-style:{"italic" if italic else "normal"};font-synthesis:none}}')
            boxfile=directory/filename.replace('.woff2','-box-powerline.woff2')
            if boxfile.exists():
                boxurl=Path(os.path.relpath(boxfile,page.parent)).as_posix()
                rules.append(f'@font-face{{font-family:"{family}";src:url("{boxurl}") format("woff2");font-weight:300 700;font-style:{"italic" if italic else "normal"};unicode-range:U+2500-259F,U+E0A0-E0A3,U+E0B0-E0C8;font-synthesis:none}}')
    return "\n".join(rules)


def request(weight, italic=False, family="SAB Modul Code", sample="n"):
    style = "italic " if italic else ""
    return {"family": family, "weight": weight, "style": "italic" if italic else "normal", "sample": sample,
            "css": f'{style}{weight} 14px "{family}"'}


def page_html(page, title, body, requests, mode, font_dir, extra_css="", blind=False, extra_faces="", script=""):
    family = "Blind reference" if blind == "B" else "SAB Modul Code"
    kind, directory = face_assets(mode, font_dir)
    font_css = extra_faces or face_css(page, family, kind, directory)
    status_note = "anonymous sample face" if blind else "font requests"
    request_json = json.dumps(requests, ensure_ascii=False).replace("</", "<\\/")
    return f'''<!doctype html>
<html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>{escape(title)}</title>
<style>
{font_css}
*{{box-sizing:border-box}} body{{margin:2rem;font:16px/1.5 system-ui,sans-serif;background:#f6f7f9;color:#18202a;font-synthesis:none}}
h1,h2{{font-weight:600}} .panel{{padding:1rem;margin:1rem 0;border-radius:8px;background:#fff;overflow:auto}}
.dark{{background:#151922;color:#e6edf3}} .light{{background:#fff;color:#18202a}}
.dark .panel,.light .panel{{background:inherit;color:inherit}}
pre,.sample{{font-family:"{family}",monospace;font-synthesis:none;tab-size:2}}
pre{{margin:.4rem 0;white-space:pre;font-size:14px;line-height:1.55}}
.sample{{white-space:pre;font-size:14px;line-height:1.55}}
.sizes{{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1rem}}
.size{{padding:.7rem;overflow:auto}} .size[data-size="12"] .sample{{font-size:12px}}
.size[data-size="16"] .sample{{font-size:16px}}
.status{{padding:.8rem;border:2px solid #a66c00;background:#fff3cd;color:#503b00;font-weight:700;overflow-wrap:anywhere}}
body:not([data-font-status="READY"]) .fontproof{{display:none}}
body[data-font-status="FAIL"] .status{{border-color:#a30018;background:#ffe8ec;color:#710012}}
.weight300{{font-weight:300}} .weight400{{font-weight:400}} .weight500{{font-weight:500}} .weight600{{font-weight:600}} .weight700{{font-weight:700}}
.italic{{font-style:italic}} .whole{{transform:translateX(0)}} .fractional{{transform:translateX(.5px)}}
.box-row{{font-family:"{family}",monospace;font-size:14px;font-weight:400;line-height:inherit;white-space:pre;font-synthesis:none}}
.whole,.fractional{{line-height:inherit}}
.pending{{padding:.8rem;background:#fff3cd;color:#503b00}} canvas{{image-rendering:auto}}
{extra_css}
</style><body data-font-status="WAIT">
<div class="status" id="font-status" role="status" aria-live="polite">WAIT: loading {escape(status_note)}…</div>
{"" if blind else '<details><summary>Font request record</summary><pre id="font-requests"></pre></details>'}
<details><summary>Browser environment</summary><pre id="browser-environment"></pre></details>
<script type="application/json" id="font-request-data">{request_json}</script>
<div class="fontproof">{body}</div>
<script>
const fontRequests=JSON.parse(document.getElementById('font-request-data').textContent);
const requestRecord=document.getElementById('font-requests');if(requestRecord)requestRecord.textContent=JSON.stringify(fontRequests,null,2);
function captureEnvironment(){{
  const visible=selector=>Array.from(document.querySelectorAll(selector)).filter(el=>!el.hidden&&el.getClientRects().length>0&&getComputedStyle(el).visibility!=='hidden').length;
  window.browserEnvironment={{devicePixelRatio:window.devicePixelRatio,innerWidth:window.innerWidth,innerHeight:window.innerHeight,userAgent:navigator.userAgent,search:location.search}};
  if(document.querySelector('[data-theme]'))window.browserEnvironment.visibleSections={{themes:visible('[data-theme]'),weights:visible('[data-weight]'),sizes:visible('[data-size]')}};
  document.getElementById('browser-environment').textContent=JSON.stringify(window.browserEnvironment,null,2);
}}
async function verifyFaces(){{
  const results=await Promise.all(fontRequests.map(async r=>{{
    const faces=await document.fonts.load(r.css,r.sample);
    return {{request:r,loaded:faces.length>0 && document.fonts.check(r.css,r.sample)}};
  }}));
  const bad=results.filter(x=>!x.loaded);
  document.body.dataset.fontStatus=bad.length?'FAIL':'READY';
  const status=document.getElementById('font-status');
  if({str(bool(blind)).lower()}) status.textContent=bad.length?'FAIL: assigned sample face did not load':'READY: assigned sample face loaded';
  else status.textContent=(bad.length?'FAIL — missing: ':'READY — loaded: ')+results.map(x=>x.request.css+(x.loaded?'':' [FAIL]')).join('; ');
  window.fontLoadResults=results;
  if(bad.length){{window.operatorMetrics={{status:'FAIL',reason:'one or more exact font requests failed'}};const out=document.getElementById('operator-metrics');if(out)out.textContent=JSON.stringify(window.operatorMetrics,null,2);}}
  else{{{script}}}
  captureEnvironment();
}}
verifyFaces().catch(e=>{{document.body.dataset.fontStatus='FAIL';document.getElementById('font-status').textContent='FAIL: '+e;window.operatorMetrics={{status:'FAIL',reason:String(e)}};const out=document.getElementById('operator-metrics');if(out)out.textContent=JSON.stringify(window.operatorMetrics,null,2);captureEnvironment()}});
</script></body></html>'''


def code_samples():
    return "\n".join(f'<section class="panel"><h2>{escape(name)}</h2><pre>{escape(code)}</pre></section>' for name, code in SNIPPET.items())


def distinguish_html(mode, font_dir):
    requests = [request(weight, italic, sample="".join(PAIRS)) for weight in WEIGHTS for italic in (False, True)]
    samples = "\n".join(PAIRS)
    cards = []
    for weight, italic in ((weight, italic) for weight in WEIGHTS for italic in (False, True)):
        label = WEIGHTS[weight] + (" Italic" if italic else "")
        style = "italic" if italic else "normal"
        heading = f"{label} · {weight}"
        alternates = ''.join(f'<pre class="sample weight{weight} {style}" style="font-feature-settings:\'{feature}\' 1">0 O o</pre><small>{feature}</small>' for feature in ['ss01','ss02'])
        size_cards = "".join(f'<div class="panel size" data-size="{size}"><b>{size}px</b><pre class="sample weight{weight} {style}">{escape(samples)}</pre>{alternates}</div>' for size in (12, 14, 16))
        cards.append(f'<section data-weight="{weight}" data-italic="{int(italic)}"><h3>{heading}</h3><div class="sizes">{size_cards}</div></section>')
    body = '<h1>Различимость знаков</h1>' + "".join(f'<section class="panel {theme}" data-theme="{theme}"><h2>{theme}</h2>{"".join(cards)}</section>' for theme in ("light", "dark"))
    filter_script = r'''const q=new URLSearchParams(location.search);for(const [key,selector] of [['weight','[data-weight]'],['italic','[data-italic]'],['theme','[data-theme]']]){const value=q.get(key);if(value!==null)document.querySelectorAll(selector).forEach(el=>{const actual=el.dataset[key];const expected=key==='italic'?(value==='1'?'1':'0'):value;if(actual!==expected)el.hidden=true;});}'''
    return page_html(OUT / "distinguish.html", "SAB Modul Code: различимость", body, requests, mode, font_dir, script=filter_script)


def operator_script(mode):
    weights = "[400]" if mode == "stage2" else "[400,450]"
    pending450 = "window.operatorMetrics.weights[450]={status:'PENDING',reason:'450 coverage awaits final VF; no static 450 face is used.'};if(window.operatorMetrics.status==='PASS')window.operatorMetrics.status='PARTIAL';" if mode == "stage2" else ""
    return r'''const symbols=[...new Set(Array.from(document.getElementById('operator-string').textContent).filter(c=>!/\s/.test(c)))];
const colors=[{name:'light',bg:'#ffffff',fg:'#18202a'},{name:'dark',bg:'#151922',fg:'#e6edf3'}];
function Y(v){v/=255;return v<=0.04045?v/12.92:((v+0.055)/1.055)**2.4}
function density(glyph,weight,palette){
  const canvas=document.createElement('canvas');canvas.width=9;canvas.height=19;
  const c=canvas.getContext('2d',{willReadFrequently:true});c.fillStyle=palette.bg;c.fillRect(0,0,9,19);
  const scale=14/1000;c.save();c.beginPath();c.rect(0,0,600*scale,1300*scale);c.clip();
  c.font=`${weight} 14px "SAB Modul Code"`;c.textBaseline='alphabetic';c.fillStyle=palette.fg;c.fillText(glyph,0,14);c.restore();
  const p=c.getImageData(0,0,9,19).data, bg=palette.bg.match(/[\da-f]{2}/gi).map(x=>parseInt(x,16)), fg=palette.fg.match(/[\da-f]{2}/gi).map(x=>parseInt(x,16));
  const ybg=.2126*Y(bg[0])+.7152*Y(bg[1])+.0722*Y(bg[2]), yfg=.2126*Y(fg[0])+.7152*Y(fg[1])+.0722*Y(fg[2]);let sum=0;
  for(let i=0;i<p.length;i+=4){const yp=.2126*Y(p[i])+.7152*Y(p[i+1])+.0722*Y(p[i+2]);sum+=Math.max(0,Math.min(1,(yp-ybg)/(yfg-ybg)));}
  return {D:sum/(9*19),roi:{width:9,height:19,emCell:[600,1300],clipPx:[8.4,18.2],baselinePx:14}};
}
window.operatorMetrics={status:'PASS',method:'linear-sRGB full-cell ink coverage; fixed 9x19 raster ROI, 600x1300 em clip, baseline y=14px; space excluded; each unique non-space operator tested against n with ±10% threshold; no ink-only normalization.',weights:{}};
for(const weight of MEASURE_WEIGHTS){const weightResult=window.operatorMetrics.weights[weight]={};for(const palette of colors){const n=density('n',weight,palette),items={};for(const glyph of symbols){const d=density(glyph,weight,palette).D,ratio=n.D?d/n.D:null,deviation=ratio===null?null:ratio-1,pass=deviation!==null&&Math.abs(deviation)<=.10;items[glyph]={D:d,relativeToN:ratio,deviation,pass};if(!pass)window.operatorMetrics.status='FAIL';}weightResult[palette.name]={background:palette.bg,foreground:palette.fg,nD:n.D,roi:n.roi,glyphs:items};}}
PENDING_450
document.getElementById('operator-metrics').textContent=JSON.stringify(window.operatorMetrics,null,2);'''.replace('MEASURE_WEIGHTS',weights).replace('PENDING_450',pending450)


def operators_html(mode, font_dir):
    requests = [request(weight, sample=OPERATORS + "n") for weight in ((400, 450) if mode == "release" else (400,))]
    operator_status = ("<p id='operator-stage-status' class='pending'>450: PENDING until final VF; 400 is measured from the stage 2 face.</p>"
                       if mode != "release" else "<p id='operator-stage-status'>Canvas metrics populate after the font request succeeds.</p>")
    body = f'''<h1>Операторы</h1><section class="panel"><pre id="operator-string" class="sample">{escape(OPERATORS)}</pre></section>
{operator_status}<pre id="operator-metrics"></pre>'''
    return page_html(OUT / "operators.html", "SAB Modul Code: операторы", body, requests, mode, font_dir,
                     extra_css=".pending{padding:.8rem;background:#fff3cd;color:#503b00}", script=operator_script(mode))


def boxes_html(mode, font_dir):
    request_face = request(400, sample="\n".join(BOX_ROWS))
    rows = "\n".join(f'<div class="box-row">{escape(row)}</div>' for row in BOX_ROWS)
    tests = []
    for theme in ("light", "dark"):
        for line_height in ("1.0", "1.5", "1.55"):
            tests.append(f'<section class="panel {theme}"><h3>{theme}, line-height {line_height}</h3><div style="font-size:14px;line-height:{line_height}"><div class="whole">{rows}</div></div><p>Сдвиг 0.5 CSS px</p><div style="font-size:14px;line-height:{line_height}"><div class="fractional">{rows}</div></div></section>')
    body = '<h1>Box drawing: одинарные, двойные, жирные пересечения</h1>' + "".join(tests) + '<details><summary>Raster continuity</summary><pre id="cell-metrics"></pre></details>'
    script = r'''const results=[];for(const theme of ['light','dark'])for(const lh of [1,1.5,1.55])for(const offset of [0,.5])for(const pair of [['─','│'],['━','┃'],['═','║']]){
const canvas=document.createElement('canvas');canvas.width=130;canvas.height=150;const c=canvas.getContext('2d',{willReadFrequently:true});c.fillStyle=theme==='light'?'#fff':'#000';c.fillRect(0,0,130,150);c.fillStyle=theme==='light'?'#000':'#fff';c.font='400 14px "SAB Modul Code"';c.textBaseline='alphabetic';c.fillText(pair[0].repeat(10),20+offset,32);for(let i=0;i<5;i++)c.fillText(pair[1],100+offset,32+i*14*lh);
const image=c.getImageData(0,0,130,150).data;const ink=(x,y)=>{const v=image[(y*130+x)*4];return theme==='light'?255-v:v};const h=[],v=[];for(let x=Math.ceil(22+offset);x<Math.floor(102+offset);x++){let max=0;for(let y=24;y<=30;y++)max=Math.max(max,ink(x,y));if(max<20)h.push(x);}for(let y=28;y<Math.floor(27+4*14*lh);y++){let max=0;for(let x=101;x<=108;x++)max=Math.max(max,ink(x,y));if(max<20)v.push(y);}results.push({theme,lineHeight:lh,offset,horizontal:pair[0],vertical:pair[1],horizontalGaps:h,verticalGaps:v,pass:!h.length&&!v.length});}
document.getElementById('cell-metrics').textContent=JSON.stringify({pass:results.every(r=>r.pass),method:'Actual Canvas raster, 14px DPR1 backing; background gaps below 20/255 ink across straight runs. Does not prove corner semantics.',results},null,2);'''
    return page_html(OUT / "boxes.html", "SAB Modul Code: box drawing", body, [request_face], mode, font_dir, script=script)


def critical_html(mode, font_dir):
    body = '<h1>FCB: контрольный фрагмент, 30 строк</h1><section class="panel light">' + code_samples() + '</section><section class="panel dark">' + code_samples() + '</section>'
    requests=[request(w,sample="\n".join(SNIPPET.values())) for w in ([400,450] if mode=='release' else [400])]
    css=".fontproof pre{font-feature-settings:'zero' 1,'calt' 1,'ss10' 1}.fontproof .light{font-weight:400}"
    if mode=='release':css+=".fontproof .dark{font-weight:450}"
    return page_html(OUT / "check-critical.html", "SAB Modul Code: FCB", body, requests, mode, font_dir, extra_css=css)


def blind_html(page, label, mode, font_dir):
    if label == "A":
        family, request_face = "SAB Modul Code", request(400, sample="\n".join(SNIPPET.values()))
        font_css = ""
    else:
        family = "Blind reference"
        jetbrains = ROOT / "references" / "JetBrainsMono" / "fonts" / "ttf" / "JetBrainsMono-Regular.ttf"
        url = Path(os.path.relpath(jetbrains, page.parent)).as_posix()
        font_css = f'@font-face{{font-family:"{family}";src:url("{url}") format("truetype");font-weight:400;font-style:normal;font-synthesis:none}}'
        request_face = request(400, family=family, sample="\n".join(SNIPPET.values()))
    return page_html(page, f"FCB sample {label}", '<main class="panel dark">' + code_samples() + '</main>', [request_face], mode, font_dir, blind=label, extra_faces=font_css)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=("release", "stage2"), default="release")
    parser.add_argument("--stage2", action="store_true", help="use static faces from source/stage2-masters")
    parser.add_argument("--font-dir", help="font directory, relative to project root or absolute")
    args = parser.parse_args()
    if args.stage2:
        args.mode = "stage2"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "distinguish.html").write_text(distinguish_html(args.mode, args.font_dir), encoding="utf-8")
    (OUT / "operators.html").write_text(operators_html(args.mode, args.font_dir), encoding="utf-8")
    (OUT / "boxes.html").write_text(boxes_html(args.mode, args.font_dir), encoding="utf-8")
    (OUT / "check-critical.html").write_text(critical_html(args.mode, args.font_dir), encoding="utf-8")
    (OUT / "ligatures.html").write_text(ligatures_html(args.mode, args.font_dir), encoding="utf-8")
    (OUT / "extended.html").write_text(extended_html(args.mode, args.font_dir), encoding="utf-8")
    (OUT / "italic.html").write_text(italic_html(args.mode, args.font_dir), encoding="utf-8")
    if args.mode == "release":
        (OUT / "css.html").write_text(css_html(),encoding="utf-8")
    blind = OUT / "blind-test"
    blind.mkdir(exist_ok=True)
    for label in ("A", "B"):
        page = blind / f"{label}.html"
        page.write_text(blind_html(page, label, args.mode, args.font_dir), encoding="utf-8")
    (blind / "key.txt").write_text("A — SAB Modul Code\nB — JetBrains Mono\n", encoding="utf-8")


def ligatures_html(mode='stage2', font_dir='source/stage4-masters'):
    from code_operators import OPERATORS as sequences
    rows=[]
    for weight, italic in [(400,False),(700,True)]:
        for theme in ['light','dark']:
            samples=[]
            for features,label in [("'calt' 1, 'ss10' 0",'calt'),("'calt' 0, 'ss10' 0",'off'),("'calt' 1, 'ss10' 1",'ss10')]:
                spans=' '.join(f'<span class="cell-test" data-features="{label}" style="display:inline-block">{escape(text)}</span>' for text in sequences)
                samples.append(f'<p>{label}</p><div class="sample" style="font-feature-settings:{features};white-space:normal">{spans}</div>')
            rows.append(f'<section class="panel {theme}" style="font-weight:{weight};font-style:{"italic" if italic else "normal"}"><h3>{weight} {"Italic" if italic else "Roman"} {theme}</h3>{"".join(samples)}</section>')
    script=r'''const metrics=[];for(const el of document.querySelectorAll('.cell-test')){const node=el.firstChild,chars=[];for(let i=0;i<node.length;i++){const range=document.createRange();range.setStart(node,i);range.setEnd(node,i+1);const r=range.getBoundingClientRect();chars.push({index:i,width:r.width,x:r.x,text:range.toString()});}const bounds=el.getBoundingClientRect();metrics.push({text:el.textContent,features:el.dataset.features,weight:getComputedStyle(el).fontWeight,style:getComputedStyle(el).fontStyle,width:bounds.width,chars,pass:chars.every(c=>Math.abs(c.width-8.4)<.04)&&Math.abs(bounds.width-8.4*node.length)<.06});}document.getElementById('cell-metrics').textContent=JSON.stringify({pass:metrics.every(m=>m.pass),method:'DOM Range selection bounds for each character, expected 600/1000*14=8.4 CSS px',metrics},null,2);'''
    body='<h1>Контекстные операторы и выделение по ячейкам</h1>'+''.join(rows)+'<details><summary>Измерения выделения</summary><pre id="cell-metrics"></pre></details>'
    return page_html(OUT/'ligatures.html','SAB Modul Code: ligatures',body,[request(400),request(700,True)],mode,font_dir,script=script)


def extended_html(mode, font_dir):
    from verify_stage3 import REQUIRED
    groups={**REQUIRED, 'cyrillic_completion':set(map(ord,'ʼҲҳӢӣӮӯҶҷҖҗ')), 'math_42':set(map(ord,'∀∂∃∅∆∇∈∉∋∏∑−∓∗∘∙√∝∞∠∣∥∧∨∩∪∫∴∵∼≈≠≡≤≥⊂⊃⊆⊇⊕⊗⊥'))}
    panels=[]
    for name, points in groups.items():
        chars=[chr(cp) for cp in sorted(points)]
        rows='\n'.join(' '.join(chars[i:i+32]) for i in range(0,len(chars),32))
        panels.append(f'<section class="panel"><h3>{name}: {len(chars)}</h3><pre style="font-size:22px;line-height:1.65">{escape(rows)}</pre></section>')
    return page_html(OUT/'extended.html','SAB Modul Code: coverage','<h1>Набор знаков</h1>'+''.join(panels),[request(400,sample=''.join(chr(cp) for cps in groups.values() for cp in cps))],mode,font_dir)


def italic_html(mode, font_dir):
    panels=[]
    for weight in WEIGHTS:
        code='val accountData = api.validateAccount(parameters)'
        comment='// Мама написала аннотацию: validate account data and all parameters'
        panels.append(f'<section class="panel dark weight{weight}"><h3>{weight}</h3><pre>{code}</pre><pre class="italic">{comment}</pre><pre class="italic">a а à á â ã ä å ā ă ą</pre></section>')
    return page_html(OUT/'italic.html','SAB Modul Code: italic','<h1>Код и комментарий, 14 px</h1>'+''.join(panels),[request(w,i,sample='aаàáâãäåāăą') for w in WEIGHTS for i in [False,True]],mode,font_dir)


def css_html():
    return r'''<!doctype html><html lang="en"><meta charset="utf-8"><title>Production CSS check</title>
<link rel="stylesheet" href="../release/SAB-Modul-Code-1.0/code.css">
<style>body{font:20px/1.5 sans-serif;margin:32px}section{padding:18px;margin:18px 0}.dark{background:#151922;color:#e6edf3}.light{background:#fff;color:#18202a}#browser-environment,#cell-metrics{white-space:pre-wrap;font:12px monospace}code{white-space:pre}</style>
<body data-font-status="WAIT"><div id="status">WAIT</div>
<section class="light"><code id="light">val value = 012345 // Строка, 400 ──</code></section>
<section class="dark"><code id="dark">val value = 012345 // Строка, 450 ──</code></section>
<section class="dark fcb-doc"><pre id="parent"><code id="nested">x -> y !== z // FCB ss10, nested pre/code</code></pre></section>
<section class="light"><code class="fcb-doc" id="direct">x -> y !== z // Direct FCB class</code></section>
<details><summary>Computed CSS and environment</summary><pre id="browser-environment"></pre><pre id="cell-metrics"></pre></details>
<script>
(async()=>{
 const loaded=[];for(const style of ['normal','italic'])for(const weight of [400,450]){const faces=await document.fonts.load(`${style} ${weight} 14px "SAB Modul Code"`,'aа0─');loaded.push(faces.length>=2);}
 await document.fonts.ready;
 const read=id=>{const s=getComputedStyle(document.getElementById(id));return {id,size:parseFloat(s.fontSize),weight:s.fontWeight,features:s.fontFeatureSettings,lineHeight:s.lineHeight,tabSize:s.tabSize,synthesis:s.fontSynthesis};};
 const rows=['light','dark','parent','nested','direct'].map(read),get=id=>rows.find(x=>x.id===id);
 const pass=loaded.every(Boolean)&&rows.every(x=>Math.abs(x.size-18.4)<.02&&x.tabSize==='2'&&x.synthesis==='none'&&Math.abs(parseFloat(x.lineHeight)/x.size-1.55)<.002)&&get('light').weight==='400'&&get('dark').weight==='450'&&get('nested').weight==='450'&&get('direct').weight==='400'&&['parent','nested','direct'].every(id=>get(id).features.includes('ss10'));
 document.body.dataset.fontStatus=loaded.every(Boolean)?'READY':'FAIL';document.getElementById('status').textContent=pass?'PASS production CSS':'FAIL production CSS';
 document.getElementById('cell-metrics').textContent=JSON.stringify({pass,loaded,rows},null,2);
 document.getElementById('browser-environment').textContent=JSON.stringify({devicePixelRatio,innerWidth,innerHeight,userAgent:navigator.userAgent},null,2);
})().catch(e=>{document.body.dataset.fontStatus='FAIL';document.getElementById('status').textContent=String(e)});
</script></body></html>'''


if __name__ == "__main__":
    main()
