import argparse
import json
import math
import re
import subprocess
import sys
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEIGHTS = {"Light": 300, "Regular": 400, "Medium": 500, "SemiBold": 600, "Bold": 700}
FIELDS = ("upm", "advance", "x_height", "cap_height", "ascender", "descender", "line_gap")


def masters(folder=None):
    candidates = []
    for folder in ([folder] if folder else [ROOT / "source" / "code-masters", ROOT / "TTF"]):
        if folder.is_dir():
            candidates.extend(folder.glob("*.ttf"))
    found = {}
    for path in candidates:
        match = re.fullmatch(r"SABModulCode-(Light|Regular|Medium|SemiBold|Bold)(?:-?Italic)?", path.stem)
        if path.stem == "SABModulCode-Italic":
            found[(400, "italic")] = path
        if match:
            style = "italic" if path.stem.endswith("Italic") else "roman"
            found[(WEIGHTS[match.group(1)], style)] = path
    return found


def intersections(font, glyph_name, y, transform=None):
    from fontTools.pens.basePen import BasePen
    hits = []

    class SlicePen(BasePen):
        def _moveTo(self, point):
            self.first = point

        def _lineTo(self, point):
            x0, y0 = self._getCurrentPoint()
            x1, y1 = point
            if y0 != y1 and min(y0, y1) <= y < max(y0, y1):
                hits.append(x0 + (y - y0) * (x1 - x0) / (y1 - y0))

        def _qCurveToOne(self, control, end):
            start = self._getCurrentPoint()
            a = start[1] - 2 * control[1] + end[1]
            b = 2 * (control[1] - start[1])
            c = start[1] - y
            if abs(a) < 1e-12:
                roots = [-c / b] if abs(b) > 1e-12 else []
            else:
                d = b * b - 4 * a * c
                roots = [(-b - math.sqrt(d)) / (2 * a), (-b + math.sqrt(d)) / (2 * a)] if d > 1e-12 else [-b/(2*a)] if abs(d) <= 1e-12 else []
            for t in roots:
                interior = 1e-10 < t < 1 - 1e-10 and abs(2*a*t+b) > 1e-10
                lower_start = abs(t) <= 1e-10 and (b > 1e-10 or (abs(b) <= 1e-10 and a > 0))
                lower_end = abs(t - 1) <= 1e-10 and (2*a+b < -1e-10 or (abs(2*a+b) <= 1e-10 and a > 0))
                if interior or lower_start or lower_end:
                    hits.append((1-t)**2 * start[0] + 2*(1-t)*t*control[0] + t*t*end[0])

        def _closePath(self):
            self._lineTo(self.first)

    glyphs = font.getGlyphSet()
    pen = SlicePen(glyphs)
    if transform is not None:
        from fontTools.pens.transformPen import TransformPen
        pen = TransformPen(pen, transform)
    glyphs[glyph_name].draw(pen)
    hits.sort()
    assert len(hits) % 2 == 0, (glyph_name, y, hits)
    return [(hits[i], hits[i + 1]) for i in range(0, len(hits) - 1, 2)]


def stroke_widths(font, glyph_name, y):
    center_sections = intersections(font, glyph_name, y)
    above = intersections(font, glyph_name, y + 1)
    below = intersections(font, glyph_name, y - 1)
    if not center_sections or not above or not below:
        return []
    widths = []
    for left, right in center_sections:
        center = (left + right) / 2
        nearest = lambda sections: min(sections, key=lambda span: abs((span[0] + span[1]) / 2 - center))
        top, bottom = nearest(above), nearest(below)
        slope = (((top[0] + top[1]) - (bottom[0] + bottom[1])) / 4)
        widths.append((right - left) / (1 + slope * slope) ** 0.5)
    return widths


def bbox(font, name):
    from fontTools.pens.boundsPen import BoundsPen

    pen = BoundsPen(font.getGlyphSet())
    font.getGlyphSet()[name].draw(pen)
    return pen.bounds


def shaped_advance(hb_shape, path, text):
    result = subprocess.run(
        [hb_shape, "--output-format=json", str(path), text],
        check=True, capture_output=True, text=True,
    )
    return sum(item["ax"] for item in json.loads(result.stdout))


def check_one(path, weight, style, target, tolerance, hb_shape):
    from fontTools.ttLib import TTFont

    font = TTFont(path, recalcBBoxes=False, recalcTimestamp=False)
    cmap = font.getBestCmap()
    x_name, h_name, l_name, i_name, m_name, n_name = (cmap[ord(ch)] for ch in "xHlimn")
    actual = {
        "file": str(path.relative_to(ROOT)),
        "weight": weight,
        "style": style,
        "sha256": __import__("hashlib").sha256(path.read_bytes()).hexdigest(),
        "upm": font["head"].unitsPerEm,
        "advance_values": sorted({font["hmtx"][name][0] for name in font.getGlyphOrder()}),
        "x_height_os2": getattr(font["OS/2"], "sxHeight", None),
        "cap_height_os2": getattr(font["OS/2"], "sCapHeight", None),
        "x_bbox": bbox(font, x_name),
        "H_bbox": bbox(font, h_name),
        "ascender": font["hhea"].ascent,
        "descender": font["hhea"].descent,
        "line_gap": font["hhea"].lineGap,
        "typo_ascender": font["OS/2"].sTypoAscender,
        "typo_descender": font["OS/2"].sTypoDescender,
        "typo_line_gap": font["OS/2"].sTypoLineGap,
        "use_typo_metrics": bool(font["OS/2"].fsSelection & 0x80),
        "stem_H_y175": stroke_widths(font, h_name, 175),
        "stem_l_y350": stroke_widths(font, l_name, 350),
        "stem_scan_geometry": "outline lines and exact quadratic Bezier intersections",
    }
    failures = []

    def require(ok, message):
        if not ok:
            failures.append(message)

    require(actual["upm"] == target["upm"], f"head.unitsPerEm={actual['upm']} expected {target['upm']}")
    require(actual["x_height_os2"] == target["x_height"], f"OS/2.sxHeight={actual['x_height_os2']} expected {target['x_height']}")
    require(actual["cap_height_os2"] == target["cap_height"], f"OS/2.sCapHeight={actual['cap_height_os2']} expected {target['cap_height']}")
    require(actual["x_bbox"][3] == target["x_height"], f"x outline top={actual['x_bbox'][3]} expected {target['x_height']}")
    require(actual["H_bbox"][3] == target["cap_height"], f"H outline top={actual['H_bbox'][3]} expected {target['cap_height']}")
    for field, got in (("ascender", actual["ascender"]), ("descender", actual["descender"]), ("line_gap", actual["line_gap"])):
        require(got == target[field], f"hhea.{field}={got} expected {target[field]}")
    require((actual["typo_ascender"], actual["typo_descender"], actual["typo_line_gap"]) == (target["ascender"], target["descender"], target["line_gap"]), "OS/2 typo metrics differ from target")
    require(actual["use_typo_metrics"], "OS/2.fsSelection USE_TYPO_METRICS is unset")

    expected_stem = target["stems"][str(weight)]
    measured = actual["stem_H_y175"] + actual["stem_l_y350"]
    actual["stem_target"] = expected_stem
    actual["stem_measurements"] = measured
    require(len(actual["stem_H_y175"]) == 2, f"H y=175 has {len(actual['stem_H_y175'])} stem crossings, expected 2")
    require(len(actual["stem_l_y350"]) == 1, f"l y=350 has {len(actual['stem_l_y350'])} stem crossing, expected 1")
    require(all(abs(width - expected_stem) <= tolerance for width in measured), f"measured H/l stems {measured} differ from {expected_stem} by more than {tolerance}")

    mark_names = {cmap[cp] for cp in cmap if unicodedata.category(chr(cp)).startswith("M")}
    if "GDEF" in font and font["GDEF"].table.GlyphClassDef:
        mark_names.update(name for name, cls in font["GDEF"].table.GlyphClassDef.classDefs.items() if cls == 3)
    allowed_zero = mark_names | {"caron.alt"}
    helper = "code.cyrillic.descender"
    if helper in font.getGlyphOrder():
        require(helper not in cmap.values(), "component-only descender must not be an encoded character")
        users = [g for g in font["glyf"].glyphs if font["glyf"][g].isComposite()
                 and any(c.glyphName == helper for c in font["glyf"][g].components)]
        require(len(users) == 6, "descender helper must serve exactly six Cyrillic components")
        allowed_zero.add(helper)
    zero_width = {name for name in font.getGlyphOrder() if font["hmtx"][name][0] == 0}
    advance_errors = {
        name: font["hmtx"][name][0]
        for name in font.getGlyphOrder()
        if (name in allowed_zero and font["hmtx"][name][0] != 0)
        or (name not in allowed_zero and font["hmtx"][name][0] != target["advance"])
    }
    actual["zero_width_glyphs"] = sorted(zero_width)
    actual["mark_glyphs"] = sorted(mark_names)
    actual["advance_errors"] = advance_errors
    require(zero_width <= allowed_zero, f"zero-advance non-mark/helper glyphs: {sorted(zero_width - allowed_zero)}")
    require(not advance_errors, f"glyph advances outside 0/600 exception rules: {advance_errors}")
    require(all(font["hmtx"][name][0] == 0 for name in allowed_zero if name in font["hmtx"].metrics), "a Unicode/GDEF mark or caron.alt has nonzero advance")
    require("caron.alt" in font.getGlyphOrder() and font["hmtx"]["caron.alt"][0] == 0, "caron.alt missing or not zero-width")

    advances = {}
    for label, text in (("i10", "i" * 10), ("m10", "m" * 10), ("n80", "n" * 80)):
        advances[label] = shaped_advance(hb_shape, path, text)
    actual["hb_shape_advances"] = advances
    actual["n80_width_px_at_14"] = advances["n80"] * 14 / target["upm"]
    require(advances["i10"] == target["advance"] * 10, f"hb-shape i×10={advances['i10']}")
    require(advances["m10"] == target["advance"] * 10, f"hb-shape m×10={advances['m10']}")
    require(actual["n80_width_px_at_14"] == 672, f"80-cell calculated width at 14px={actual['n80_width_px_at_14']}")
    actual["browser_width"] = "pending: verify actual HTML width after font loading"
    font.close()
    return actual, failures


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--font-dir', type=Path)
    parser.add_argument('--output', type=Path, default=ROOT / 'checks/stage1.json')
    args = parser.parse_args()
    if args.font_dir:
        args.font_dir = args.font_dir.resolve()
    args.output = args.output.resolve()
    files = masters(args.font_dir)
    expected = {(weight, style) for weight in WEIGHTS.values() for style in ("roman", "italic")}
    missing = sorted(f"{weight}-{style}" for weight, style in expected - files.keys())
    if missing:
        print("FAIL: missing generated Code TTFs: " + ", ".join(missing))
        return 1
    target_path = ROOT / "checks" / "targets.json"
    if not target_path.exists():
        print("FAIL: checks/targets.json is pending stage 0 measurements")
        return 1
    target = json.loads(target_path.read_text(encoding="utf-8"))
    absent = [field for field in FIELDS if field not in target]
    absent += [f"stems.{weight}" for weight in WEIGHTS.values() if str(weight) not in target.get("stems", {})]
    if absent:
        print("FAIL: targets.json missing fields: " + ", ".join(absent))
        return 1
    try:
        hb_shape = subprocess.run(["hb-shape", "--version"], check=True, capture_output=True, text=True).stdout.strip()
        __import__("fontTools")
    except (FileNotFoundError, subprocess.CalledProcessError, ImportError) as error:
        print(f"FAIL: stage 1 verifier dependency unavailable: {error}")
        return 1

    results, failures = [], []
    for key in sorted(files):
        result, problems = check_one(files[key], key[0], key[1], target, 1, "hb-shape")
        results.append(result)
        failures.extend(f"{result['file']}: {problem}" for problem in problems)
    report = {
        "status": "FAIL" if failures else "PASS",
        "targets": str(target_path.relative_to(ROOT)),
        "hb_shape_version": hb_shape,
        "masters": results,
        "failures": failures,
        "browser_measurement": "pending; hb-shape does not verify browser raster width",
    }
    output = args.output
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"{report['status']}: {len(results)} masters checked; report {output.relative_to(ROOT)}")
    for failure in failures:
        print("- " + failure)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
