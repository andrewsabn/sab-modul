# Ъ/ъ readability repair

The original hard-sign flag was largely absorbed by the stem in heavier weights. Its visible lowercase length was only 7–53 units in the inspected Sans/Mono/Code Black/Bold/Regular examples. The repair targets 150 units outside the left stem, for both uppercase and lowercase hard signs.

All 38 static styles and six variable faces are updated. The advance widths, Mono 620/Code 600 columns, vertical stem thickness, outer rightmost stroke and unrelated glyphs/layout are preserved. The horizontal counter span is reduced to make room for the longer flag. This is a deliberate hard-sign redesign, not merely a pixel translation. Frozen masters and compatible masters carry it, and only the two glyphs/variation tuples were transferred into final fonts. Changed TTF glyph instructions were regenerated with the original family's ttfautohint options. Changed CFF drawing programs are regenerated from raw outlines without the glyphSet LSB shift; these changed CFF programs do not carry the earlier per-glyph hint programs.

Regression tested 52,272 glyph/file/weight cases, including every 0.5 step across each delivered variable axis. Minimum observed visible flag 149.159 units; design target 150, test tolerance 145. These are project-specific criteria, not industry standards. See regression.json.

The requested words are «объем», «съешь», «подъезд» and «ОБЪЕКТ». Actual hinted TTF specimens are rendered at 14/16pt at 72dpi and 144dpi. The browser proof uses current shipped WOFF2/VF files at CSS 14/16pt. Tests at these densities do not constitute a complete application/device matrix.

- [Browser proof](web-proof.html)
- [Sans 14/16pt](sans-14-16pt.png) · [72dpi / light-dark](sans-72dpi.png)
- [Mono 14/16pt](mono-14-16pt.png) · [72dpi / light-dark](mono-72dpi.png)
- [Code 14/16pt](code-14-16pt.png) · [72dpi / light-dark](code-72dpi.png)

The earlier prototype-comparison.png is explicitly a concept proof from unhinted test outlines, not the final hinted fonts. Final images above use the shipped TTF files. The bounded rebuild is SAB-Modul-1.0/source/repair_hard_sign.py, with tools/test_hard_sign.py measuring the flag independently of italic shear.
