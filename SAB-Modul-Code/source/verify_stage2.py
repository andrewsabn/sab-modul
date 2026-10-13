"""Inspect compiled stage-2 files, preserving failed and unmeasured criteria."""
from pathlib import Path
import hashlib
import json
import math
import subprocess

import ots
from fontTools.ttLib import TTFont
from verify_code import bbox, intersections, stroke_widths

ROOT = Path(__file__).resolve().parents[1]


def shape(path, text, features=''):
    command = ['hb-shape', '--output-format=json', '--no-glyph-names', str(path), text]
    if features:
        command.append('--features=' + features)
    return json.loads(subprocess.check_output(command, text=True))


def main(font_dir=ROOT/'source/stage2-masters', output=ROOT/'checks/stage2.json'):
    records, logs = [], []
    expected_files = {f'SABModulCode-{style}{suffix}.ttf' for style in ['Light', 'Regular', 'Medium', 'SemiBold', 'Bold']
                for suffix in ['', 'Italic']}
    if (font_dir/'SABModulCode-Italic.ttf').exists():
        expected_files.remove('SABModulCode-RegularItalic.ttf'); expected_files.add('SABModulCode-Italic.ttf')
    def save(status):
        report = dict(run_status=status, fonts=records,
                      missing_files=sorted(expected_files - {Path(r['file']).name for r in records}),
                      pending=['Windows Edge distinguish at 12/14/16px both themes',
                               '11pt PDF distinction', 'Independent final reviews'])
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        output.with_name(output.stem+'-ots.log').write_text('\n'.join(logs))
    save('IN_PROGRESS')
    for path in sorted(font_dir.glob('*.ttf')):
        f = TTFont(path)
        cmap = f.getBestCmap()
        original = TTFont(ROOT.parent / 'SAB-Modul-1.0/release/1.0/TTF/SABModulMono-Regular.ttf')
        checks = []

        def check(label, actual, expected, ok):
            checks.append(dict(label=label, actual=actual, expected=expected, status='PASS' if ok else 'FAIL'))

        missing = sorted(set(original.getBestCmap()) - set(cmap))
        check('Preserve original cmap', missing, [], not missing)
        features = {r.FeatureTag for table in ['GSUB', 'GPOS'] if table in f
                    for r in f[table].table.FeatureList.FeatureRecord}
        required = {'zero', 'ss01', 'ss02', 'ccmp', 'mark', 'tnum', 'case'}
        check('Stage-2 OpenType features', sorted(features), sorted(required), required <= features)
        pair_lookups = [lookup.LookupType for lookup in f['GPOS'].table.LookupList.Lookup
                        if lookup.LookupType == 2 or (lookup.LookupType == 9 and
                            any(sub.ExtensionLookupType == 2 for sub in lookup.SubTable))]
        check('No kerning table or pair positioning', {'kern': 'kern' in f, 'pair_lookups': pair_lookups},
              {'kern': False, 'pair_lookups': []}, 'kern' not in f and not pair_lookups)
        for char in '()[]{}-–—':
            name = cmap[ord(char)]
            if name + '.case' in f.getGlyphOrder():
                shaped = shape(path, char, 'case=1')
                check('case substitution ' + char, shaped, f.getGlyphID(name + '.case'),
                      len(shaped) == 1 and shaped[0]['g'] == f.getGlyphID(name + '.case') and shaped[0]['ax'] == 600)
        zero = cmap[48]
        from shapely.geometry import Polygon
        for alternate in ['zero.empty', 'zero.dotted']:
            glyph = f['glyf'][alternate]
            coordinates, ends, flags = glyph.getCoordinates(f['glyf'])
            start, rings = 0, []
            for end in ends:
                rings.append(Polygon(coordinates[start:end+1]))
                start = end + 1
            rings.sort(key=lambda p: p.area, reverse=True)
            expected_count = 2 if alternate == 'zero.empty' else 3
            convex_error = (rings[1].convex_hull.area - rings[1].area) / rings[1].area
            ok = len(rings) == expected_count and convex_error < .001
            if alternate == 'zero.dotted':
                ok = ok and rings[1].contains(rings[2])
            check('Zero alternate counter has no slash spikes ' + alternate,
                  {'contours': len(rings), 'counter_concavity': convex_error},
                  {'contours': expected_count, 'counter_concavity': '<0.001', 'dot': 'isolated within counter'}, ok)
        for settings, expected in [('', zero), ('ss01=1', 'zero.dotted'),
                                   ('ss02=1', 'zero.empty'), ('zero=1', zero),
                                   ('ss01=1,ss02=1', 'zero.empty'),
                                   ('ss01=1,zero=1', zero), ('ss02=1,zero=1', zero),
                                   ('ss01=1,ss02=1,zero=1', zero)]:
            result = shape(path, '0', settings)
            expected_gid = f.getGlyphID(expected)
            check('Zero ' + (settings or 'default'), result, {'gid': expected_gid, 'advance': 600},
                  len(result) == 1 and result[0]['g'] == expected_gid and result[0]['ax'] == 600)
        bounds = {char: bbox(f, cmap[ord(char)]) for char in '0Il1|¦.,;:()[]{}<>=3З'}
        bar = stroke_widths(f, cmap[ord('|')], 350)
        ell = stroke_widths(f, cmap[ord('l')], 350)
        check('Vertical bar is thinner and taller than l',
              {'bar_stems': bar, 'l_stems': ell, 'bar_bounds': bounds['|'], 'l_bounds': bounds['l']},
              'bar normal stroke < l, bar height > l',
              len(bar) == len(ell) == 1 and bar[0] < ell[0] and
              bounds['|'][3] - bounds['|'][1] > bounds['l'][3] - bounds['l'][1])
        for char in '()[]{}':
            actual = [bounds[char][1], bounds[char][3]]
            check('Delimiter extent ' + char, actual, [-300, 1000], actual == [-300, 1000])
        for char in '<>':
            actual = [bounds[char][1], bounds[char][3]]
            check('Angle operator centered at270 (owner-approved criterion)', actual,
                  'vertical center270 +/-1', abs(sum(actual)/2-270)<=1)
        check('Digit zero cap alignment with round overshoot', [bounds['0'][1], bounds['0'][3]],
              'baseline/cap 0/700, optical overshoot <=12',
              abs(bounds['0'][1]) <= 12 and abs(bounds['0'][3] - 700) <= 12)
        equals = f['glyf'][cmap[ord('=')]]
        gap = intersections(f, cmap[ord('=')], 270)
        upper, lower = (intersections(f, cmap[ord('=')], y) for y in [380, 160])
        check('Equals two bars with clear middle at axis270',
              {'contours': equals.numberOfContours, 'gap': gap, 'upper': upper, 'lower': lower},
              '2 contours, no ink at270, one bar at160 and380',
              equals.numberOfContours == 2 and not gap and len(upper) == len(lower) == 1)
        from fontTools.pens.boundsPen import BoundsPen
        from fontTools.pens.transformPen import TransformPen
        angle = math.radians(-f['post'].italicAngle)
        pen = BoundsPen(f.getGlyphSet())
        f.getGlyphSet()[cmap[ord('.')]].draw(TransformPen(pen, (math.cos(angle), math.sin(angle), -math.sin(angle), math.cos(angle), 0, 0)))
        period_diameter = min(bounds['.'][3] - bounds['.'][1], pen.bounds[2] - pen.bounds[0])
        stems = stroke_widths(f, cmap[ord('H')], 175) + stroke_widths(f, cmap[ord('l')], 350)
        stem = sum(stems) / len(stems)
        check('Dot minimum diameter', period_diameter, '>=160', period_diameter >= 160)
        check('Dot >=max(160,1.2*stem) (owner-approved criterion)',
              period_diameter, max(160,stem*1.2), period_diameter >= max(160,stem*1.2))
        dot_top = intersections(f, cmap[ord('.')], 100)
        comma_top = intersections(f, cmap[ord(',')], 100)
        dot_widths = [right-left for left,right in dot_top]
        comma_widths = [right-left for left,right in comma_top]
        same_head = (bounds['.'][3] == bounds[','][3] and len(dot_widths) == len(comma_widths) == 1
                     and abs(dot_widths[0] - comma_widths[0]) <= 1)
        check('Comma retains dot head at same height', comma_widths, dot_widths, same_head)
        tail = bounds['.'][1] - bounds[','][1]
        check('Comma tail below dot', tail, '>=120', tail >= 120)
        ze = f['glyf'][cmap[ord('З')]].compile(f['glyf'])
        three = f['glyf'][cmap[ord('3')]].compile(f['glyf'])
        check('Ze/three binary data differ (not a legibility verdict)', ze != three, True, ze != three)
        marked = shape(path, 'q\u0301', 'ccmp=0')
        check('Combining acute advances no cell', [r['ax'] for r in marked], [600, 0],
              len(marked) == 2 and [r['ax'] for r in marked] == [600, 0])
        disabled = shape(path, 'q\u0301', 'ccmp=0,mark=0')
        q_bounds, acute_bounds = bbox(f, cmap[ord('q')]), bbox(f, cmap[0x301])
        clearance = acute_bounds[1] + marked[1]['dy'] - q_bounds[3] if len(marked) == 2 else None
        check('q+acute mark changes shaping and clears q by40 units',
              {'enabled': marked, 'disabled': disabled, 'clearance': clearance},
              'mark changes offsets; clearance40 +/-1',
              marked != disabled and clearance is not None and abs(clearance - 40) <= 1)
        result = ots.sanitize(str(path), capture_output=True)
        log = '\n'.join(x.decode(errors='replace') if isinstance(x, bytes) else str(x or '')
                        for x in [result.stdout, result.stderr])
        logs.append(path.name + '\n' + log)
        check('OTS', result.returncode, 0, result.returncode == 0)
        records.append(dict(file=str(path.relative_to(ROOT)), sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                            bounds=bounds, checks=checks))
        save('IN_PROGRESS')
        print(path.name, sum(c['status'] == 'FAIL' for c in checks), 'FAIL')
    missing = expected_files - {Path(r['file']).name for r in records}
    save('COMPLETE' if not missing else 'INCOMPLETE')
    return int(bool(missing) or any(c['status'] == 'FAIL' for r in records for c in r['checks']))


if __name__ == '__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--font-dir',type=Path,default=ROOT/'source/stage2-masters');parser.add_argument('--output',type=Path,default=ROOT/'checks/stage2.json');args=parser.parse_args();raise SystemExit(main(args.font_dir.resolve(),args.output.resolve()))
