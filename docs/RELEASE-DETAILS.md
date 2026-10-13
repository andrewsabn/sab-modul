# SAB Modul — OFL distribution

SAB Modul Sans and Mono (1.101) and SAB Modul Code (1.002), by Andrew Sabynin. Prepared for GitHub publication; nothing has been published by this preparation step.

## Contents

38 static TTF styles for installation: Sans 14, Mono 14, Code 10. The complete delivery contains 154 files across TTF, OTF, variable TTF, WOFF2 and web subsets. The source includes 202 font masters/intermediate files, the author's drawing programs and finalization tools. Font hashes are in FONT-SHA256.json. See METHODOLOGY.md, checks/SUMMARY.json and SAB-Modul-1.0/source/REBUILD.md / SAB-Modul-Code/source/REBUILD.md for evidence and limits.

Install TTF styles OR variable fonts for a family, not duplicate static/variable editions with the same internal family names. Replace an older installed edition only after closing applications that cache fonts. Windows: select TTF files and install for the user. macOS: Font Book. Linux: copy TTF files to ~/.local/share/fonts and refresh the font cache. Follow the font-specific settings in your editor to select SAB Modul Code.

For web use, load SAB-Modul-1.0/WEB/fonts.css and SAB-Modul-Code/code.css. Keep their font files beside them at the supplied relative paths. demo.html is a local usage example; serve this directory with an ordinary HTTP server if local-file font access is blocked by your browser.

## License

All supplied SAB Modul fonts and own font source are licensed under SIL Open Font License 1.1, see OFL.txt. No Reserved Font Names are declared. Commercial use, modifications and redistribution are allowed under the OFL conditions; standalone sale of the fonts is prohibited. The license does not apply to the accompanying article, its illustration or external software. External tools retain their own licenses. The FontBakery checker patch retains Apache 2.0; its license is in licenses/.

## Fresh verification and limits

OTS: 154/154. Three full FontBakery profiles on every delivered TTF/OTF/VF family group: 27 runs. Raw results include 302 FAIL and 44 ERROR, not a blanket PASS. Adobe profiles have no FAIL/ERROR. Universal negatives concern Code Mac name records; Google-specific negatives concern catalogue naming/copyright/weight/axis conventions and expanded language coverage. The online name checker returns KeyError 'data'; a current HTTP429 cause was not established.

Font Validator 2.1.6 produced 154 reports without raster tests. All 6183 raw E records are identical to the corresponding previously accepted full reports. Known old-parser limitations and intentional contour contacts are documented; raw exit codes and errors remain visible. Independent Astra audit confirms all 356 delivered/source fonts preserve every non-metadata table; CFF drawing programs also match.

The carried-forward application scope is Russian/English corporate text and code. Full Ukrainian/Tajik/Uzbek-Cyrillic/Turkmen coverage is NOT claimed: fresh broad language checks report missing codepoints. English auxiliary U+02BB is absent. No Google Fonts catalogue admission or worldwide artistic uniqueness is claimed. GUI inspections and a complete drawing-source rebuild were not repeated for this metadata-only OFL transition. Current limitations are explicit, not silently converted to PASS.

Raw report outcomes are preserved. Absolute workstation paths in distributed textual reports are replaced with relative labels for privacy; unredacted originals remain in the private working archive. This is path redaction, not result suppression.

## Repeat the technical checks

Create an isolated Python environment and install requirements-qa.txt. If checking CFF Mono fonts with FontBakery 1.1.0, apply the documented glyf-independent correction first; its regression test also verifies a deliberately wrong advanceWidthMax still fails. Provide the Font Validator 2.1.6 executable yourself; it is not included.

```sh
python SAB-Modul-1.0/source/fix_fontbakery_cff.py
python tools/run_checks.py . /path/to/FontValidator
```

Run this in a copy: check outputs are regenerated. The runner removes expected prior JSON/HTML/XML before each job to avoid stale results after a tool failure. A missing output is not a PASS. FontBakery may need network access; external-service failures are retained.
