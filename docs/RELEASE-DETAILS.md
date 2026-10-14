# SAB Modul — OFL distribution

SAB Modul Sans and Mono (1.103) and SAB Modul Code (1.004), by Andrew Sabynin. Published at https://github.com/andrewsabn/sab-modul.

## Contents

38 static TTF styles for installation: Sans 14, Mono 14, Code 10. The complete delivery contains 154 files across TTF, OTF, variable TTF, WOFF2 and web subsets. The source includes 202 font masters/intermediate files, the author's drawing programs and finalization tools. Font hashes are in FONT-SHA256.json. See METHODOLOGY.md, checks/SUMMARY.json and SAB-Modul-1.0/source/REBUILD.md / SAB-Modul-Code/source/REBUILD.md for evidence and limits.

Install TTF styles OR variable fonts for a family, not duplicate static/variable editions with the same internal family names. Replace an older installed edition only after closing applications that cache fonts. Windows: select TTF files and install for the user. macOS: Font Book. Linux: copy TTF files to ~/.local/share/fonts and refresh the font cache. Follow the font-specific settings in your editor to select SAB Modul Code.

For web use, load SAB-Modul-1.0/WEB/fonts.css and SAB-Modul-Code/code.css. Keep their font files beside them at the supplied relative paths. demo.html is a local usage example; serve this directory with an ordinary HTTP server if local-file font access is blocked by your browser.

## License

All supplied SAB Modul fonts and own font source are licensed under SIL Open Font License 1.1, see OFL.txt. The Reserved Font Name "SAB Modul" is declared for this edition. Modified versions may not use it without explicit written permission from the copyright holder. Commercial use, modifications and redistribution are allowed under the OFL conditions; standalone sale of the fonts is prohibited. The license does not apply to the accompanying article, its illustration or external software. External tools retain their own licenses. The FontBakery checker patch retains Apache 2.0; its license is in licenses/.

## Fresh verification and limits

OTS: 154/154. Three full FontBakery profiles on every delivered TTF/OTF/VF family group: 27 runs. Raw results include 466 FAIL and 164 ERROR, not a blanket PASS. Adobe profiles have no FAIL/ERROR. Universal negatives concern Code Mac name records; Google-specific negatives concern catalogue naming/copyright/weight/axis conventions and expanded language coverage. The online name checker returns KeyError 'data'; the final run includes a directly sampled HTTP429 rate-limit response from the service.

Font Validator 2.1.6 produced 154 reports without raster tests. All 6183 raw E records are identical to the corresponding previously accepted full reports. Known old-parser limitations and intentional contour contacts are documented; raw exit codes and errors remain visible. The RFN/license audit covers all 356 files. Separate Astra drawing audits confirm only authorized a, Ъ/ъ and numeric glyphs changed, with advances, layout, unrelated glyphs and variation data preserved. The hard-sign design was accepted at 14/16pt in all 38 static styles.

The carried-forward application scope is Russian/English corporate text and code. Full Ukrainian/Tajik/Uzbek-Cyrillic/Turkmen coverage is NOT claimed: fresh broad language checks report missing codepoints. English auxiliary U+02BB is absent. No Google Fonts catalogue admission or worldwide artistic uniqueness is claimed. Current changed forms were rebuilt and inspected in large and small proofs and the browser; the full historical GUI/device matrix and complete clean drawing-source build were not repeated. A tiny residual a-stem bend in Sans italic VF remains documented. Changed CFF programs omit their former glyph-specific hints; TTF changed glyphs were rehinted. 164 additional Google-specific FAIL results concern license templates and the retained RFN text, not a newly detected outline error. Current limitations are explicit, not silently converted to PASS.

Raw report outcomes are preserved. Absolute workstation paths in distributed textual reports are replaced with relative labels for privacy; unredacted originals remain in the private working archive. This is path redaction, not result suppression.

## Repeat the technical checks

Create an isolated Python environment and install requirements-qa.txt. If checking CFF Mono fonts with FontBakery 1.1.0, apply the documented glyf-independent correction first; its regression test also verifies a deliberately wrong advanceWidthMax still fails. Provide the Font Validator 2.1.6 executable yourself; it is not included.

```sh
python SAB-Modul-1.0/source/fix_fontbakery_cff.py
python tools/run_checks.py . /path/to/FontValidator
```

Run this in a copy: check outputs are regenerated. The runner removes expected prior JSON/HTML/XML before each job to avoid stale results after a tool failure. A missing output is not a PASS. FontBakery may need network access; external-service failures are retained.

The numeric revision is independently reviewed in checks/astra-digits-final.md. The final 27 profile runs have no new nonservice FAIL/ERROR or WARN messages against the preceding RFN/hard-sign release. Extra ERROR results belong only to fontdata_namecheck; a direct service request returned HTTP429 rate limit exceeded. Name uniqueness is not certified by this run. Raw results remain unchanged. The first fitted draft had real degenerate 5 terminal lines; these were corrected, rehinted and rechecked before publication. The small terminal refit changes the contour by at most 0.707107 units in independently sampled sections. Exact mathematical G1 continuity is not claimed.
