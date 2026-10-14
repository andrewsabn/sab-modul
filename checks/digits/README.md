# Numeric repair and verification

The 2026-10-14 revision corrects the exposed 2/5 joins in all families, reduces the cap overshoot of 2 to about 708 units and aligns 7 with the baseline. Both 8 counters remain independent ovals without the old reverse wave; the outer waist has a small continuous round transition. Curved Sans/Mono numerals and the flat-topped Code 3 use compatible quadratic contours in static and variable fonts. 1/4 were checked and retained. Other already-curved Code numerals and its slashed/dotted/empty zero variants retain their drawings.

Every weight and slant is covered: Sans 14, Mono 14, Code 10. Existing pnum forms use the matching repaired numerals. Character advances, tabular widths, hmtx, layout/features, unrelated glyph programs and unrelated variation data remain unchanged. Derived hhea bearing extrema can change with glyph bounds; line metrics and advanceWidthMax do not. Earlier a and Ъ/ъ repairs remain intact.

## Visual proofs

- [Browser proof with actual static WOFF2 files](web-proof.html), all 38 styles at 14/16pt and 300pt.
- `*-300pt.png`: each static style, all ten numerals on shared cap/baseline guides, 144dpi.
- `*-258-600pt.png`: Regular/Bold close-ups for each family, 144dpi.
- `*-small-all-styles.png`: dates, times, prices and confusing characters at 14/16pt, 144dpi.
- `*-interpolation.png`: each main VF at both weight extremes and 450.5.

## Repeating the checks

Run in a copy of the repository. The baseline directory must contain the preceding RFN/hard-sign release, not a copy of the new files.

```sh
python tools/test_digits.py
python tools/check_digits.py /path/to/previous-release
python tools/check_digit_web.py
python tools/render_digits.py
python tools/run_checks.py . /path/to/FontValidator
```

`test_digits.py` rejects the prior 38 static styles and accepts the repaired 38. Its localized 5-cap test distinguishes the old exposed elbow from the legitimate bowl crown; the zero-length-line check also detects the first fitted draft's degenerate terminals. The explicit geometry audit tests static TTF/OTF, main VF every 25 weight units and +0.5 offsets, existing pnum and Code zero forms. This is sampled checking, not a proof for every real-valued weight.

`binary-regression.json` compares all 356 delivered/source fonts with the prior release. `web-format-regression.json` compares 2,788 numeric glyph/location combinations in 72 web files. Browser verification checks 38 large and 76 small text nodes with the actual custom fonts, without fallback.

## Terminal cleanup and accuracy limits

The first full check found 32 additional WARN results, all caused by repeated zero-length 5 lines after rounding in Mono/Code static TTF. Its negative-message comparison remains in `history/first-pass-gate-regression.json`; unredacted full first-pass reports remain in the private working evidence. The final pass replaces that draft.

The scoped rebuild refits only the terminal micro-polylines to common straight segments, preserves matching point topology across masters, and redoes the affected hint programs. Master Hausdorff deviation is at most 0.707106782 units. Astra independently checks 2,828 intermediate terminal sections and the complete corrected file set. The source fit tolerance 0.35 units precedes final rounding and this cleanup; it is not an upper bound for compiled-outline error. Exact mathematical G1 continuity is not claimed. The visible structural shelves and steps are removed in the reviewed 300/600pt conditions.

OTS, Font Validator and all 27 FontBakery profile runs are repeated on the final font hashes. Raw FAIL/ERROR and inherited exceptions remain visible; this revision does not claim Google Fonts catalogue admission. See [the current summary](../SUMMARY.json), [the independent review](../astra-digits-final.md) and [acceptance limits](../../ACCEPTANCE.md).
