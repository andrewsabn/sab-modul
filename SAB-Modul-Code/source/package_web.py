"""Create variable WOFF2 web files and verify subset coverage and shaping."""
import argparse
import hashlib
import io
import json
import sys
import unicodedata
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
import uharfbuzz as hb
import ots

ROOT = Path(__file__).resolve().parents[1]
RELEASE = ROOT / 'release' / 'SAB-Modul-Code-1.0'
VF = RELEASE / 'VF'
WEB = RELEASE / 'WEB'
CHECKS = ROOT / 'checks'
BOX = set(range(0x2500, 0x25A0)) | set(range(0xE0A0, 0xE0A4)) | set(range(0xE0B0, 0xE0C9))
WEIGHTS = (300, 400, 450, 500, 600, 700)
FEATURE_SETS = {
    'default': {'zero': True, 'calt': True, 'ccmp': True, 'mark': True},
    'fcb': {'zero': True, 'ss10': True, 'ccmp': True, 'mark': True},
}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ranges(points):
    groups = []
    for cp in sorted(points):
        if groups and cp == groups[-1][1] + 1:
            groups[-1][1] = cp
        else:
            groups.append([cp, cp])
    return ', '.join(f'U+{a:04X}' + (f'-{b:04X}' if b != a else '') for a, b in groups)


def feature_tags(font):
    return {table: sorted({r.FeatureTag for r in font[table].table.FeatureList.FeatureRecord})
            for table in ('GSUB', 'GPOS') if table in font}


def mac_names(font):
    return sorted({(n.nameID, n.toUnicode()) for n in font['name'].names
                   if n.platformID == 1 and n.nameID in (1, 2, 4, 6, 16, 17)})


def as_hb(font):
    font.flavor = None
    data = io.BytesIO()
    font.save(data)
    hbf = hb.Font(hb.Face(data.getvalue()))
    hbf.scale = (1000, 1000)
    order = font.getGlyphOrder()
    return hbf, order


def shape(pair, text, weight, features):
    font, order = pair
    font.set_variations({'wght': weight})
    buffer = hb.Buffer()
    buffer.add_str(text)
    buffer.guess_segment_properties()
    hb.shape(font, buffer, features)
    return [(order[info.codepoint], pos.x_advance, pos.y_advance, pos.x_offset, pos.y_offset)
            for info, pos in zip(buffer.glyph_infos, buffer.glyph_positions)]


def make_subset(source, points, outpath, helper_glyphs=()):
    font = TTFont(source, recalcTimestamp=False)
    if 'kern' in font:
        del font['kern']
    options = subset.Options()
    options.layout_features = ['*', '-kern']
    options.name_IDs = ['*']
    options.name_languages = ['*']
    options.name_legacy = True
    options.glyph_names = True
    options.notdef_glyph = True
    options.notdef_outline = True
    options.hinting = True
    subsetter = subset.Subsetter(options=options)
    subsetter.populate(unicodes=points, glyphs=[g for g in helper_glyphs if g in font.getGlyphOrder()])
    subsetter.subset(font)
    font['name'].names = [n for n in font['name'].names if n.nameID != 25 or n.platformID in (1, 3)]
    font.flavor = 'woff2'
    outpath.parent.mkdir(parents=True, exist_ok=True)
    font.save(outpath)
    return font


def check_font(path, source_tags, source_macs, wanted, require_full_tags=False):
    font = TTFont(path, recalcTimestamp=False)
    cm = set(font.getBestCmap())
    tags = feature_tags(font)
    mac = mac_names(font)
    advances = {a for a, _ in font['hmtx'].metrics.values()}
    problems = []
    if not wanted <= cm:
        problems.append('missing intended cmap codepoints: ' + ', '.join(f'U+{x:04X}' for x in sorted(wanted-cm)))
    if 'kern' in font:
        problems.append('legacy kern table present')
    if any('kern' in table_tags for table_tags in tags.values()):
        problems.append('kern layout feature present')
    if not set(source_macs) <= set(mac):
        problems.append('Mac name records were removed')
    if require_full_tags and tags != source_tags:
        problems.append(f'feature tags changed: source={source_tags}, output={tags}')
    if not advances <= {0, 600}:
        problems.append(f'non-cell advances present: {sorted(advances-{0,600})}')
    run = ots.sanitize(str(path), capture_output=True)
    stdout = run.stdout.decode(errors='replace') if isinstance(run.stdout, bytes) else run.stdout
    stderr = run.stderr.decode(errors='replace') if isinstance(run.stderr, bytes) else run.stderr
    if run.returncode:
        problems.append('OTS rejected file')
    return font, {'file': path.name, 'bytes': path.stat().st_size, 'sha256': digest(path),
                  'cmap_count': len(cm), 'cmap_codepoints': sorted(cm), 'feature_tags': tags,
                  'mac_name_record_count': len(mac), 'advance_values': sorted(advances),
                  'ots': {'exit_code': run.returncode, 'stdout': stdout, 'stderr': stderr},
                  'problems': problems, 'status': 'PASS' if not problems else 'FAIL'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--vf-dir', type=Path, default=VF)
    parser.add_argument('--web-dir', type=Path, default=WEB)
    parser.add_argument('--report', type=Path, default=CHECKS / 'web-build.json')
    parser.add_argument('--log', type=Path, default=CHECKS / 'web-build.log')
    args = parser.parse_args()
    sys.path.insert(0, str(ROOT / 'source'))
    from code_operators import OPERATORS

    args.web_dir.mkdir(parents=True, exist_ok=True)
    records, problems, log = [], [], []
    for style, italic in (('Roman', False), ('Italic', True)):
        stem = 'SABModulCode-Italic[wght]' if italic else 'SABModulCode[wght]'
        source = args.vf_dir / (stem + '.ttf')
        if not source.exists():
            raise FileNotFoundError(source)
        full = TTFont(source, recalcTimestamp=False)
        cmap = full.getBestCmap()
        points = set(cmap)
        assert all(font['head'].unitsPerEm == 1000 for font in (full,))
        assert 'wght' in {axis.axisTag for axis in full['fvar'].axes}
        source_tags = feature_tags(full)
        source_macs = mac_names(full)
        assert source_macs, f'{source.name}: no Mac name records'
        assert not any('kern' in ts for ts in source_tags.values()) and 'kern' not in full, f'{source.name}: kern is present'
        source_sha = digest(source)
        tnum_helpers = [cmap[cp] + '.pnum' for cp in range(ord('0'), ord('9') + 1)
                        if cmap[cp] + '.pnum' in full.getGlyphOrder()]
        full_pair = as_hb(full)

        latin = {cp for cp in points if cp < 0x80 or 'LATIN' in unicodedata.name(chr(cp), '')}
        cyrillic = {cp for cp in points if 'CYRILLIC' in unicodedata.name(chr(cp), '')}
        box = points & BOX
        common = {cp for cp in points if unicodedata.category(chr(cp)).startswith('M') or chr(cp).isspace()}
        symbol = points - latin - cyrillic - box - common
        groups = {'latin': latin, 'cyrillic': cyrillic, 'symbols': symbol, 'box-powerline': box}
        feature_support = {ord(c) for c in '0123456789Aa()[]{}-–—'}
        feature_support |= {ord(c) for sequence in OPERATORS for c in sequence}
        feature_support &= points
        assigned = set().union(*groups.values())
        if assigned | common != points:
            raise AssertionError(f'{style}: input cmap not covered; missing={sorted(points-assigned-common)}')

        # Main face includes every non-box glyph in one shaping run; box glyphs load separately.
        main_points = points - box
        main_path = args.web_dir / (stem + '.woff2')
        main_font = make_subset(source, main_points, main_path, tnum_helpers)
        main_font.close()

        subset_paths = {}
        for group, primary in groups.items():
            if not primary:
                raise AssertionError(f'{style}: empty {group} subset')
            wanted = primary | common | feature_support
            # Include case counterparts together so local case substitutions stay self-contained.
            while True:
                counterparts = {ord(mapped) for cp in wanted for mapped in
                                (chr(cp).lower(), chr(cp).upper(), chr(cp).title())
                                if len(mapped) == 1 and ord(mapped) in points}
                if counterparts <= wanted:
                    break
                wanted |= counterparts
            name = f'{stem}-{group}.woff2'
            path = args.web_dir / name
            subfont = make_subset(source, wanted, path, tnum_helpers)
            subfont.close()
            subset_paths[group] = (path, wanted)

        # Check main and script files, preserve names and feature tags in each artifact.
        main_font, main_rec = check_font(main_path, source_tags, source_macs, main_points, True)
        if set(main_font.getBestCmap()) & BOX:
            main_rec['problems'].append('box/Powerline cmap leaked into main no-box face')
            main_rec['status'] = 'FAIL'
        main_font.close()
        main_rec.update({'family_style': style, 'kind': 'main-no-box', 'source': str(source),
                         'source_sha256': source_sha, 'target_max_bytes': 120000 if not italic else None,
                         'size_result': ('PASS' if main_path.stat().st_size <= 120000 else 'FAIL') if not italic else 'NOT_LIMITED',
                         'unicode_range': ranges(main_points)})
        if not italic and main_path.stat().st_size > 120000:
            reason = f'{main_path.name} is {main_path.stat().st_size} bytes; exceeds 120000-byte limit'
            main_rec['problems'].append(reason)
            main_rec['status'] = 'FAIL'
            problems.append(reason)
        records.append(main_rec)
        log.append(f'{style} main no-box WOFF2: {main_path.stat().st_size} bytes, SHA-256 {digest(main_path)}, size {main_rec["size_result"]}')

        for group, (path, wanted) in subset_paths.items():
            sf, row = check_font(path, source_tags, source_macs, wanted, True)
            sf.close()
            row.update({'family_style': style, 'kind': 'script-subset', 'subset': group,
                        'source': str(source), 'source_sha256': source_sha, 'unicode_range': ranges(set(row['cmap_codepoints']))})
            records.append(row)
            log.append(f'{style} {group} WOFF2: {row["bytes"]} bytes, cmap {row["cmap_count"]}, SHA-256 {row["sha256"]}, {row["status"]}')
            problems.extend(f'{path.name}: {p}' for p in row['problems'])

        # Compare shaping against the unsplit VF, including every character and operator sequence.
        compare_targets = [('main-no-box', main_path, main_points)] + [
            (group, path, wanted) for group, (path, wanted) in subset_paths.items()]
        for label, path, wanted in compare_targets:
            subfont = TTFont(path, recalcTimestamp=False)
            reduced_pair = as_hb(subfont)
            samples = [chr(cp) for cp in sorted(wanted)]
            samples.extend(''.join(chr(cp) for cp in sorted(wanted)))
            samples.extend(seq for seq in OPERATORS if set(map(ord, seq)) <= wanted)
            samples.extend(s for s in ('AVATAR Wa Ty 0171', 'Технологический руководитель банков',
                                      '−37 % [2026]', 'a\u0301', 'е\u0308', 'и\u0306')
                           if set(map(ord, s)) <= wanted)
            count = 0
            shape_fails = []
            for weight in WEIGHTS:
                for feature_name, feature_set in FEATURE_SETS.items():
                    for text in samples:
                        try:
                            expected = shape(full_pair, text, weight, feature_set)
                            actual = shape(reduced_pair, text, weight, feature_set)
                        except Exception as exc:
                            shape_fails.append({'weight': weight, 'features': feature_name, 'text': text, 'error': repr(exc)})
                            break
                        count += 1
                        if expected != actual:
                            shape_fails.append({'weight': weight, 'features': feature_name, 'text': text,
                                                'expected': expected, 'actual': actual})
                            break
                    if shape_fails:
                        break
                if shape_fails:
                    break
            subfont.close()
            row = next(r for r in records if r['file'] == path.name)
            row['shaping_comparisons'] = count
            row['shaping_status'] = 'PASS' if not shape_fails else 'FAIL'
            row['shaping_failures'] = shape_fails
            if shape_fails:
                problems.append(f'{path.name}: shaping mismatch at {shape_fails[0]}')
            log.append(f'{style} {label} shaping: {count} comparisons; {row["shaping_status"]}')

        full.close()

    # Full union and separate-face cmap rules must cover exactly source VF codepoints.
    for style in ('Roman', 'Italic'):
        stem = 'SABModulCode-Italic[wght]' if style == 'Italic' else 'SABModulCode[wght]'
        source = args.vf_dir / (stem + '.ttf')
        source_points = set(TTFont(source, recalcTimestamp=False).getBestCmap())
        union = set()
        for row in records:
            if row.get('family_style') == style and row.get('kind') == 'script-subset':
                union |= set(row['cmap_codepoints'])
        missing = source_points - union
        if missing:
            problems.append(f'{style}: four subset union missing {len(missing)} source codepoints: {sorted(missing)}')
        if union != source_points:
            log.append(f'{style}: subset cmap union {len(union)} vs VF {len(source_points)} (duplicates may exist in shared marks)')
        else:
            log.append(f'{style}: four subset cmap union exactly {len(union)} source codepoints')

    css = []
    for style, italic in (('normal', False), ('italic', True)):
        stem = 'SABModulCode-Italic[wght]' if italic else 'SABModulCode[wght]'
        main_rec = next(r for r in records if r['file'] == stem + '.woff2')
        css.append(f"""@font-face {{
  font-family: 'SAB Modul Code';
  font-style: {style};
  font-weight: 300 700;
  font-display: swap;
  src: url('./WEB/{stem}.woff2') format('woff2');
  unicode-range: {main_rec['unicode_range']};
}}""")
        box_rec = next(r for r in records if r['file'] == stem + '-box-powerline.woff2')
        box_cp = set(box_rec['cmap_codepoints']) & BOX
        css.append(f"""@font-face {{
  font-family: 'SAB Modul Code';
  font-style: {style};
  font-weight: 300 700;
  font-display: swap;
  src: url('./WEB/{stem}-box-powerline.woff2') format('woff2');
  unicode-range: {ranges(box_cp)};
}}""")
    css.append("""code, pre, .sab-code {
  font-family: 'SAB Modul Code', monospace;
  font-size: .92em;
  line-height: 1.55;
  font-weight: 400;
  font-feature-settings: 'zero', 'calt';
  font-synthesis: none;
  tab-size: 2;
}
pre code, pre .sab-code {
  font-size: inherit;
  line-height: inherit;
  font-weight: inherit;
  font-feature-settings: inherit;
}
@media (prefers-color-scheme: dark) {
  code, pre, .sab-code { font-weight: 450; }
}
.dark code, .dark pre, .dark .sab-code,
[data-theme='dark'] code, [data-theme='dark'] pre, [data-theme='dark'] .sab-code {
  font-weight: 450;
}
.light code, .light pre, .light .sab-code,
[data-theme='light'] code, [data-theme='light'] pre, [data-theme='light'] .sab-code {
  font-weight: 400;
}
.fcb-doc, .fcb-doc code, .fcb-doc pre, .fcb-doc .sab-code {
  font-feature-settings: 'zero', 'ss10';
}""")

    css_path = args.web_dir.parent / 'code.css'
    css_path.write_text('\n\n'.join(css) + '\n', encoding='utf-8')

    report = {'status': 'FAIL' if problems else 'PASS', 'source_directory': str(args.vf_dir),
              'output_directory': str(args.web_dir), 'source_vfs': [
                  {'file': p.name, 'sha256': digest(p), 'bytes': p.stat().st_size,
                   'cmap_count': len(TTFont(p, recalcTimestamp=False).getBestCmap())}
                  for p in (args.vf_dir/'SABModulCode[wght].ttf', args.vf_dir/'SABModulCode-Italic[wght].ttf')],
              'weights_tested': list(WEIGHTS), 'feature_sets_tested': FEATURE_SETS,
              'box_powerline_codepoints': sorted(BOX), 'subset_groups': list(groups),
              'main_roman_size_limit_bytes': 120000,
              'main_roman_actual_bytes': next(r['bytes'] for r in records if r['file']=='SABModulCode[wght].woff2'),
              'main_roman_size_result': next(r['size_result'] for r in records if r['file']=='SABModulCode[wght].woff2'),
              'outputs': records, 'css': {'file': str(css_path), 'sha256': digest(css_path)}, 'problems': problems}
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    args.log.parent.mkdir(parents=True, exist_ok=True)
    args.log.write_text('\n'.join(log + [f'CSS {css_path} SHA-256 {digest(css_path)}', f'OVERALL {report["status"]}'] + ['FAIL ' + p for p in problems]) + '\n', encoding='utf-8')
    for line in log:
        print(line, flush=True)
    print(f'OVERALL {report["status"]}; report {args.report}; CSS {css_path}', flush=True)
    if problems:
        for problem in problems:
            print('FAIL ' + problem, flush=True)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
