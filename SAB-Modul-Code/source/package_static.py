"""Package stage-6 SAB Modul Code masters into static TTF, OTF, WOFF2 files."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

from fontTools.pens.qu2cuPen import Qu2CuPen
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.ttLib import TTFont, newTable
from fontTools.fontBuilder import FontBuilder

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / "source/stage6-masters"
DEFAULT_OUT = ROOT / "release/SAB-Modul-Code-1.0"
OTFAUTOHINT = Path("/tmp/sab-cff-hint-env/bin/otfautohint")
TTFAUTOHINT = Path("/opt/homebrew/bin/ttfautohint")
import os, shutil
OTS = Path(os.environ.get("OTS_SANITIZE") or shutil.which("ots-sanitize") or "ots-sanitize")
STYLES = ("Light", "Regular", "Medium", "SemiBold", "Bold")
FORMATS = ("TTF", "OTF", "WOFF2")
FEATURE_TABLES = ("GSUB", "GPOS", "GDEF")
REMOVE_OTF_TABLES = ("glyf", "loca", "fpgm", "prep", "cvt ", "gasp", "LTSH", "hdmx", "VDMX", "DSIG", "TTFA")
RUN_COMMANDS = []


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def table_digest(font, tag):
    return hashlib.sha256(font[tag].compile(font)).hexdigest()


def cff_outline_digest(path):
    from fontTools.pens.recordingPen import RecordingPen
    with TTFont(path) as font:
        gs=font.getGlyphSet(); outlines=[]
        for name in font.getGlyphOrder():
            pen=RecordingPen();gs[name].draw(pen);outlines.append((name,pen.value))
        return hashlib.sha256(json.dumps(outlines).encode()).hexdigest()


def cff_font(source_path, output_path):
    font = TTFont(source_path)
    glyph_order = font.getGlyphOrder()
    glyf = font["glyf"]
    glyph_set = font.getGlyphSet()
    from verify_code import bbox, stroke_widths
    cmap = font.getBestCmap()
    boxes = {ch: bbox(font, cmap[ord(ch)]) for ch in 'HoxObfgp'}
    h_levels = sorted({y for x, y in glyf[cmap[ord('H')]].coordinates})
    assert len(h_levels) == 4, h_levels
    private = {
        'defaultWidthX': 600, 'nominalWidthX': 0,
        'BlueValues': [math.floor(min(boxes[c][1] for c in 'oO')), 0,
                       540, math.ceil(boxes['o'][3]),
                       700, math.ceil(boxes['O'][3]),
                       712, math.ceil(boxes['f'][3])],
        'OtherBlues': [math.floor(boxes['g'][1]), -198],
        'StdHW': h_levels[2] - h_levels[1],
        'StdVW': round(sum(stroke_widths(font, cmap[ord('H')], 175)) / 2),
    }
    char_strings = {}
    for glyph_name in glyph_order:
        width = font["hmtx"].metrics[glyph_name][0]
        char_pen = T2CharStringPen(None if width == 600 else width, glyph_set)
        pen = Qu2CuPen(char_pen, max_err=0.1, all_cubic=True)
        glyph_set[glyph_name].draw(pen)
        char_strings[glyph_name] = char_pen.getCharString(private=None, globalSubrs=None)

    names = font["name"].names
    family = next((n.toUnicode() for n in names if n.nameID == 16), "SAB Modul Code")
    subfamily = next((n.toUnicode() for n in names if n.nameID == 17), next(n.toUnicode() for n in names if n.nameID == 2))
    full_name = next((n.toUnicode() for n in names if n.nameID == 4), f"{family} {subfamily}")
    ps_name = next((n.toUnicode() for n in names if n.nameID == 6), "SABModulCode-Regular")
    os2, post, head = font["OS/2"], font["post"], font["head"]
    font_info = {
        "FamilyName": family,
        "FullName": full_name,
        "Weight": subfamily.replace(" Italic", ""),
        "ItalicAngle": post.italicAngle,
        "isFixedPitch": post.isFixedPitch,
        "UnderlinePosition": post.underlinePosition,
        "UnderlineThickness": post.underlineThickness,
        "FontBBox": [head.xMin, head.yMin, head.xMax, head.yMax],
    }
    del font["glyf"]
    del font["loca"]
    builder = FontBuilder(font=font, isTTF=False)
    builder.setupCFF(ps_name, font_info, char_strings, private)
    for tag in REMOVE_OTF_TABLES:
        if tag in font:
            del font[tag]
    maxp = newTable("maxp")
    maxp.tableVersion = 0x00005000
    maxp.numGlyphs = len(glyph_order)
    font["maxp"] = maxp
    font["head"].indexToLocFormat = 0
    font["head"].flags &= ~0x0008
    font["post"].formatType = 3.0
    font.sfntVersion = "OTTO"
    font.save(output_path)
    font.close()
    # Keep all contours unchanged; only add CFF hints.
    before_hint=cff_outline_digest(output_path)
    hint = _run([OTFAUTOHINT, '--decimal', '--no-flex', '--ignore-fontinfo',
                 '-p', '2', output_path])
    RUN_COMMANDS.append(hint)
    if hint['exit_code']:
        raise RuntimeError(f"otfautohint failed for {output_path}: {hint['output']}")
    assert before_hint==cff_outline_digest(output_path),(output_path,'CFF hinting changed contours')
    hint['unchanged_outline_sha256']=before_hint


def _mac_name_signature(font):
    return sorted((n.nameID, n.langID, n.toUnicode()) for n in font["name"].names if n.platformID == 1)


def _assert_preserved(reference, result, filename, output_format):
    assert len(result.getBestCmap()) == len(reference.getBestCmap()) >= 801, (filename, "cmap size")
    assert result.getBestCmap() == reference.getBestCmap(), (filename, "cmap changed")
    assert result["hmtx"].metrics == reference["hmtx"].metrics, (filename, "hmtx changed")
    advances = {advance for advance, _ in result["hmtx"].metrics.values()}
    assert advances <= {0, 600}, (filename, "invalid advances", advances)
    assert all(tag in result for tag in FEATURE_TABLES), (filename, "missing layout table")
    for tag in FEATURE_TABLES:
        assert table_digest(result, tag) == table_digest(reference, tag), (filename, tag, "table changed")
    assert _mac_name_signature(result) == _mac_name_signature(reference), (filename, "Mac names changed")
    assert result["post"].isFixedPitch == 1, (filename, "post.isFixedPitch")
    assert result["OS/2"].panose.bProportion == 9, (filename, "PANOSE proportion")
    if output_format == "OTF":
        assert result.sfntVersion == "OTTO" and "CFF " in result and "glyf" not in result and "loca" not in result
        assert result["maxp"].tableVersion == 0x00005000
        assert result["post"].formatType == 3.0, (filename, "CFF post format")
    elif output_format in ("TTF", "WOFF2"):
        assert "glyf" in result and "CFF " not in result
        assert result["head"].flags & 0x0008, (filename, "integer PPEM head flag")


def _run(command):
    proc = subprocess.run([str(part) for part in command], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    return {"command": [str(part) for part in command], "exit_code": proc.returncode, "output": proc.stdout}


def package(out_dir=DEFAULT_OUT, font_dir=DEFAULT_SOURCE):
    if not TTFAUTOHINT.is_file() or not os.access(TTFAUTOHINT, os.X_OK):
        raise FileNotFoundError(f"ttfautohint executable missing: {TTFAUTOHINT}")
    if not OTS.is_file() or not os.access(OTS, os.X_OK):
        raise FileNotFoundError(f"OTS sanitizer missing: {OTS}")
    font_dir = Path(font_dir)
    masters = [font_dir / f"SABModulCode-{style}{italic}.ttf" for style in STYLES for italic in ("", "Italic")]
    missing = [str(path) for path in masters if not path.is_file()]
    if missing:
        raise FileNotFoundError("Missing frozen stage-6 masters: " + ", ".join(missing))

    out_dir = Path(out_dir).resolve()
    dirs = {fmt: out_dir / fmt for fmt in FORMATS}
    for folder in dirs.values():
        folder.mkdir(parents=True, exist_ok=True)

    RUN_COMMANDS.clear()
    command_log = RUN_COMMANDS
    outputs = []
    for master_path in masters:
        filename = master_path.name.replace("-RegularItalic", "-Italic")
        hinted_path = dirs["TTF"] / filename
        hint = _run([TTFAUTOHINT, "-D", "cyrl", "-f", "latn", "-x", "14", "-n", master_path, hinted_path])
        command_log.append(hint)
        if hint["exit_code"] != 0:
            raise RuntimeError(f"ttfautohint failed for {filename}: {hint['output']}")
        hinted_font = TTFont(hinted_path)
        hinted_font["head"].flags |= 0x0008
        hinted_font.save(hinted_path)
        hinted_font.close()

        otf_path = dirs["OTF"] / Path(filename).with_suffix(".otf").name
        cff_font(hinted_path, otf_path)
        woff_path = dirs["WOFF2"] / Path(filename).with_suffix(".woff2").name
        woff_font = TTFont(hinted_path)
        woff_font.flavor = "woff2"
        woff_font.save(woff_path)
        woff_font.close()

        reference = TTFont(master_path)
        for fmt, artifact in (("TTF", hinted_path), ("OTF", otf_path), ("WOFF2", woff_path)):
            result = TTFont(artifact)
            _assert_preserved(reference, result, filename, fmt)
            output_head_flags = result["head"].flags
            output_post_format = result["post"].formatType
            result.close()
            with tempfile.TemporaryDirectory(prefix="sab-modul-code-ots-") as tempdir:
                sanitized = Path(tempdir) / artifact.name
                check = _run([OTS, artifact, sanitized])
                command_log.append(check)
                if check["exit_code"] != 0:
                    reference.close()
                    raise RuntimeError(f"OTS failed for {artifact}: {check['output']}")
            outputs.append({
                "format": fmt,
                "path": str(artifact.relative_to(ROOT)),
                "size_bytes": artifact.stat().st_size,
                "sha256": sha256(artifact),
                "ots": "PASS",
                "cmap_entries": len(reference.getBestCmap()),
                "allowed_advances": sorted({a for a, _ in reference["hmtx"].metrics.values()}),
                "feature_tables_preserved": list(FEATURE_TABLES),
                "mac_name_records_preserved": len(_mac_name_signature(reference)),
                "fixed_pitch": reference["post"].isFixedPitch,
                "panose_proportion": reference["OS/2"].panose.bProportion,
                "head_integer_ppem_flag": bool(fmt in ("TTF", "WOFF2") and output_head_flags & 0x0008),
                "post_format": output_post_format,
            })
        reference.close()
        print(f"packaged {filename}: TTF, OTF, WOFF2; OTS PASS 3/3", flush=True)

    if len(outputs) != 30:
        raise AssertionError(f"Expected 30 validated outputs, found {len(outputs)}")
    record = {
        "status": "MECHANICAL_PACKAGE_ONLY_NOT_FINAL_RELEASE",
        "source": str(font_dir.relative_to(ROOT)) + "/*.ttf (read-only)",
        "release_directory": str(out_dir.relative_to(ROOT)),
        "formats": list(FORMATS),
        "font_count": len(masters),
        "output_count": len(outputs),
        "tool_versions": {
            "ttfautohint": "1.8.4",
            "otfautohint": "AFDKO 5.0.1; decimal, no-flex, ignore-fontinfo; outline equality asserted",
            "fontTools": __import__("fontTools").__version__,
            "ots": str(OTS),
        },
        "ttfautohint_options": ["-D", "cyrl", "-f", "latn", "-x", "14", "-n"],
        "outputs": outputs,
        "validation": "OTS PASS for all 30 files; cmap, hmtx, GSUB/GPOS/GDEF, Mac name records, fixed pitch, and PANOSE assertions pass.",
        "not_final_release": True,
    }
    checks = ROOT / "checks"
    checks.mkdir(exist_ok=True)
    (checks / "static-build.json").write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n")
    with (checks / "static-build.log").open("a") as log:
        log.write(f"\n=== successful packaging attempt {time.strftime('%Y-%m-%dT%H:%M:%S%z')} ===\n")
        for item in command_log:
            log.write("$ " + " ".join(item["command"]) + "\n")
            log.write(f"exit={item['exit_code']}\n")
            if item["output"]:
                log.write(item["output"])
                if not item["output"].endswith("\n"):
                    log.write("\n")
    print(f"validated {len(outputs)} static files", flush=True)
    return record


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--font-dir", type=Path, default=DEFAULT_SOURCE)
    args=parser.parse_args()
    try:
        package(args.out_dir, args.font_dir)
    except Exception:
        checks = ROOT / "checks"
        checks.mkdir(exist_ok=True)
        with (checks / "static-build.log").open("a") as log:
            log.write(f"\n=== failed packaging attempt {time.strftime('%Y-%m-%dT%H:%M:%S%z')} ===\n")
            for item in RUN_COMMANDS:
                log.write("$ " + " ".join(item["command"]) + "\n")
                log.write(f"exit={item['exit_code']}\n{item['output']}\n")
            traceback.print_exc(file=log)
        raise


if __name__ == "__main__":
    main()
