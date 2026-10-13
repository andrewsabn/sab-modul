"""Build anonymous SAB Modul Code / JetBrains Mono comparison artifacts."""
from __future__ import annotations

import hashlib
import html
import json
import shutil
import sys
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "release/SAB-Modul-Code-1.0/blind-test"
SOURCE_DIR = ROOT / "release/SAB-Modul-Code-1.0/TTF"
A_FONT = SOURCE_DIR / "SABModulCode-Regular.ttf"
JETBRAINS_SOURCE = ROOT / "references/JetBrainsMono/fonts/ttf/JetBrainsMono-Regular.ttf"
JETBRAINS_OFL = ROOT / "references/JetBrainsMono/OFL.txt"

sys.path.insert(0, str(ROOT / "source"))
from build_proofs import SNIPPET  # noqa: E402

FEATURES = "'ss10' 1, 'calt' 0"


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_text() -> str:
    assert {k: len(v.splitlines()) for k, v in SNIPPET.items()} == {"Kotlin": 10, "JSON": 10, "SQL": 10}
    return "\n".join(SNIPPET.values())


def html_page(label: str, font_url: str) -> str:
    sample = source_text()
    sections = "".join(
        f'<section><h2>{html.escape(language)}</h2><pre>{html.escape(text)}</pre></section>'
        for language, text in SNIPPET.items()
    )
    return f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>FCB sample {label}</title>
<style>
@font-face{{font-family:"BlindFace";src:url("{html.escape(font_url,quote=True)}") format("truetype");font-weight:400;font-style:normal;font-synthesis:none}}
*{{box-sizing:border-box}}
body{{margin:24px;background:#151922;color:#e6edf3;font-family:system-ui,sans-serif}}
#status{{margin:0 0 14px;font:600 12px/1.4 system-ui,sans-serif;color:#c6d3e0}}
main{{max-width:1050px;margin:auto}}
h1{{font:600 15px/1.4 system-ui,sans-serif;margin:0 0 12px}}
section{{margin:0 0 8px}}
h2{{font:600 10px/1.35 system-ui,sans-serif;letter-spacing:.04em;margin:0 0 3px;color:#aebdce}}
pre{{margin:0;padding:0;white-space:pre;tab-size:2;font:400 14px/1.45 "BlindFace",monospace;font-synthesis:none;font-feature-settings:{FEATURES};color:#e6edf3}}
#proof{{visibility:hidden}}
body[data-font-status="READY"] #proof{{visibility:visible}}
body[data-font-status="FAIL"] #status{{color:#ff8796}}
</style>
</head>
<body data-font-status="WAIT">
<main>
<div id="status" role="status" aria-live="polite">Loading sample…</div>
<div id="proof"><h1>FCB sample {label}</h1>{sections}</div>
</main>
<script>
(async()=>{{
 const family='400 14px "BlindFace"';
 const sample={json.dumps(sample,ensure_ascii=False)};
 try{{
   const faces=await document.fonts.load(family,sample);
   await document.fonts.ready;
   const loaded=faces.length>0&&document.fonts.check(family,sample);
   document.body.dataset.fontStatus=loaded?'READY':'FAIL';
   document.getElementById('status').textContent=loaded?'READY':'FAIL: sample font did not load';
   window.fontLoadGuard={{status:loaded?'READY':'FAIL',request:family,featureSettings:{json.dumps(FEATURES)},loadedFaces:faces.length}};
 }}catch(error){{
   document.body.dataset.fontStatus='FAIL';
   document.getElementById('status').textContent='FAIL: sample font did not load';
   window.fontLoadGuard={{status:'FAIL',error:String(error)}};
 }}
}})();
</script>
</body>
</html>
'''


def write_pdf(path: Path, label: str, font_path: Path) -> dict:
    font_name = f"BlindFace{label}"
    pdfmetrics.registerFont(TTFont(font_name, str(font_path)))
    page_w, page_h = A4
    margin = 40
    content_x = margin + 16
    content_w = page_w - 2 * content_x
    leading = 14.3
    sections = list(SNIPPET.items())
    total_height = sum(14 + len(code.splitlines()) * leading for _, code in sections)
    panel_top = page_h - 72
    panel_bottom = panel_top - total_height - 26
    assert panel_bottom > 36, (label, "PDF content exceeds A4 height")

    canvas = Canvas(str(path), pagesize=A4, pageCompression=1)
    canvas.setTitle(f"FCB sample {label}")
    canvas.setAuthor("Blind comparison")
    canvas.setFillColor(HexColor("#ffffff"))
    canvas.rect(0, 0, page_w, page_h, stroke=0, fill=1)
    canvas.setFillColor(HexColor("#17191c"))
    canvas.setFont("Helvetica", 9)
    canvas.drawString(margin, page_h - 45, f"FCB sample {label}")
    canvas.setFillColor(HexColor("#ffffff"))
    canvas.roundRect(margin, panel_bottom, page_w - 2 * margin, panel_top - panel_bottom, 5, stroke=0, fill=1)

    y = panel_top - 20
    line_widths=[]
    for language, code in sections:
        canvas.setFillColor(HexColor("#555b63"))
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(content_x, y, language)
        y -= 13
        canvas.setFillColor(HexColor("#17191c"))
        canvas.setFont(font_name, 11)
        for line in code.splitlines():
            width=pdfmetrics.stringWidth(line, font_name, 11)
            line_widths.append(width)
            assert width <= content_w, (label, language, line, width, content_w)
            canvas.drawString(content_x, y, line)
            y -= leading
        y -= 1
    canvas.save()

    reader=PdfReader(str(path))
    assert len(reader.pages)==1, (label, "expected one PDF page", len(reader.pages))
    extracted="\n".join((page.extract_text() or "") for page in reader.pages)
    missing=[line for code in SNIPPET.values() for line in code.splitlines() if line.strip() and line not in extracted]
    assert not missing, (label, "PDF text extraction missed source lines", missing[:3])
    # ReportLab's font resources must carry an embedded TrueType program.
    page=reader.pages[0]
    font_resources=page["/Resources"]["/Font"].get_object()
    embedded=False
    for resource in font_resources.values():
        obj=resource.get_object()
        descriptor=obj.get("/FontDescriptor")
        if descriptor:
            embedded=embedded or bool(descriptor.get_object().get("/FontFile2"))
    assert embedded, (label, "font not embedded")
    return {
        "theme":"light","pages":1,"font_size_pt":11,"line_count":sum(len(v.splitlines()) for v in SNIPPET.values()),
        "maximum_line_width_pt":round(max(line_widths),3),"available_line_width_pt":round(content_w,3),
        "all_source_lines_extract":True,"font_embedded":True,
    }


def build():
    assert A_FONT.is_file(), A_FONT
    assert JETBRAINS_SOURCE.is_file(), JETBRAINS_SOURCE
    assert JETBRAINS_OFL.is_file(), JETBRAINS_OFL
    DEST.mkdir(parents=True, exist_ok=True)
    reference_dir=DEST/"reference"
    reference_dir.mkdir(exist_ok=True)
    jetbrains_font=reference_dir/"JetBrainsMono-Regular.ttf"
    jetbrains_ofl=reference_dir/"OFL.txt"
    shutil.copyfile(JETBRAINS_SOURCE,jetbrains_font)
    shutil.copyfile(JETBRAINS_OFL,jetbrains_ofl)

    html_a=DEST/"A.html"
    html_b=DEST/"B.html"
    html_a.write_text(html_page("A", "../TTF/SABModulCode-Regular.ttf"),encoding="utf-8")
    html_b.write_text(html_page("B", "reference/JetBrainsMono-Regular.ttf"),encoding="utf-8")
    key=DEST/"key.txt"
    key.write_text("A = SAB Modul Code Regular\nB = JetBrains Mono Regular\n",encoding="utf-8")

    pdf_a=DEST/"A.pdf"
    pdf_b=DEST/"B.pdf"
    pdf_a_meta=write_pdf(pdf_a,"A",A_FONT)
    pdf_b_meta=write_pdf(pdf_b,"B",jetbrains_font)
    assert pdf_a_meta==pdf_b_meta, (pdf_a_meta,pdf_b_meta)

    expected_html={
        label:{"path":str(path.relative_to(ROOT)),"sha256":digest(path),"bytes":path.stat().st_size,
               "font_url":"../TTF/SABModulCode-Regular.ttf" if label=="A" else "reference/JetBrainsMono-Regular.ttf",
               "font_request":"400 14px \"BlindFace\"","font_weight":400,"font_size_px":14,
               "theme":"dark","font_feature_settings":FEATURES,"load_guard_present":'document.fonts.load' in path.read_text(encoding='utf-8')}
        for label,path in (("A",html_a),("B",html_b))
    }
    assert all(item["load_guard_present"] for item in expected_html.values())
    inputs={
        "A":{"file":"release/SAB-Modul-Code-1.0/TTF/SABModulCode-Regular.ttf","sha256":digest(A_FONT)},
        "B":{"file":"release/SAB-Modul-Code-1.0/blind-test/reference/JetBrainsMono-Regular.ttf","sha256":digest(jetbrains_font),"license":"release/SAB-Modul-Code-1.0/blind-test/reference/OFL.txt","license_sha256":digest(jetbrains_ofl)},
    }
    pdfs={label:{"path":str(path.relative_to(ROOT)),"sha256":digest(path),"bytes":path.stat().st_size,**meta}
          for label,path,meta in (("A",pdf_a,pdf_a_meta),("B",pdf_b,pdf_b_meta))}
    record={
        "status":"READY_FOR_BLIND_TEST_NO_VOTES_RECORDED",
        "excerpt_source":"source/build_proofs.py:SNIPPET",
        "line_counts":{k:len(v.splitlines()) for k,v in SNIPPET.items()},"total_lines":30,
        "feature_settings":FEATURES,"html":expected_html,"pdf":pdfs,"font_inputs":inputs,
        "human_tests":"Owner and two readers; no results recorded by generator.",
        "html_runtime_load":"NOT_BROWSER_TESTED; both pages hide specimen until document.fonts.load/check succeeds",
        "visual_review":"PENDING_RENDER_REVIEW",
    }
    check_path=ROOT/"checks/blind-test.json"
    check_path.write_text(json.dumps(record,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    log_path=ROOT/"checks/blind-test.log"
    lines=["SAB Modul Code blind-test artifact build",f"HTML A SHA-256 {expected_html['A']['sha256']}",
           f"HTML B SHA-256 {expected_html['B']['sha256']}",f"PDF A SHA-256 {pdfs['A']['sha256']}",
           f"PDF B SHA-256 {pdfs['B']['sha256']}","HTML request guards: A and B require exact 400 14px BlindFace load before showing specimen.",
           "HTML runtime load was not browser-tested; no READY result is claimed.",
           "PDFs: one light A4 page each, 11 pt, 30 source lines, embedded TTF; no votes/results captured."]
    log_path.write_text("\n".join(lines)+"\n",encoding="utf-8")
    print(json.dumps(record,ensure_ascii=False,indent=2))


if __name__=="__main__":
    build()
