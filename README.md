# SAB Modul

**The corporate type family for [FlyOptima.com](https://flyoptima.com/) and Andrew Sabynin's personal website, [sabynin.com](https://sabynin.com/).** Designed by Andrew Sabynin with Codex for websites, presentations, code and other corporate materials.

This repository contains ready-to-use fonts, original drawing source and masters, the creation methodology, validation reports and a prompt you can adapt to create a type family for your own company.

Read how the family was made: [A corporate typeface of our own with Codex: the FlyOptima case, 2026](https://sabynin.com/en/blog/corporate-font-with-codex/).

## Families

| Family | Purpose | Static TTF styles | Internal OFL version |
|---|---|---:|---|
| SAB Modul Sans | Body text, headings and interfaces | 14 | 1.102 |
| SAB Modul Mono | Numbers, tables and technical materials | 14 | 1.102 |
| SAB Modul Code | Programming and terminals | 10 | 1.003 |

There are 38 static styles for installation. The complete distribution contains 154 files across TTF, OTF, variable fonts and WOFF2, including web subsets. The source includes 202 master and intermediate font files.

## Download and use

[Download the complete archive](https://github.com/andrewsabn/sab-modul/releases/latest/download/SAB-Modul-OFL.zip). It includes fonts, source, the license and reports. See the [usage example](demo.html).

Install either static TTF styles or the variable version of a family. Installing both with identical internal names can cause conflicts. Choose SAB Modul Code for your editor and terminal.

For websites, use the [Sans/Mono CSS](SAB-Modul-1.0/WEB/fonts.css) and [Code CSS](SAB-Modul-Code/code.css), preserving their relative file paths. See the [distribution guide](docs/RELEASE-DETAILS.md).

## License

**SIL Open Font License 1.1 (SIL OFL 1.1).** The complete license is in [LICENSE](LICENSE) and [OFL.txt](OFL.txt). The license description and URL are also embedded in the fonts.

The license permits use, including commercial use, modification and redistribution under the OFL conditions. Fonts cannot be sold on their own; they can be used in paid products. **Reserved Font Name (RFN): SAB Modul.** Modified versions may not use this name without separate written permission from the copyright holder. The declaration appears beside the copyright notice in OFL.txt and in the font metadata.

The earlier public edition without an RFN retains its original terms. Adding an RFN to this edition does not revoke rights already granted. See the [official OFL FAQ, section 8.7](https://openfontlicense.org/ofl-faq/).

The OFL covers the original Font Software in this distribution. Third-party tools and report components retain their own licenses; see [THIRD-PARTY-NOTICES.md](THIRD-PARTY-NOTICES.md). The blog article and its illustrations are not included in this repository.

## Create your own font

The [ready-to-use Codex prompt (in Russian)](font-creation-prompt.md) covers concept selection, regular text, weights and italics, an A4 proof sheet, a validation matrix and independent reviews. Copy and adapt it to your brand, languages and applications. It does not promise the same completion time, cost or artistic result.

The [methodology](METHODOLOGY.md) explains the creation and verification process. [Acceptance decisions and limitations](ACCEPTANCE.md) explain why raw negative check results must not be relabeled as PASS.

## Changes in this release

The shoulder at the upper arc/stem junction of Sans `а/a` and related forms has been removed. The left flags of the Cyrillic hard signs `ъ` and `Ъ` have been lengthened in Sans, Mono and Code. Character advances, code columns and layout tables are preserved. Web files and source masters are updated.

[а/a proofs at 300/600 pt](checks/a-junction/README.md) · [ъ/Ъ in every style at 14/16 pt](checks/hard-sign/README.md) · [Web proofs](checks/hard-sign/web-proof.html).

## Validation of this distribution

Current counts and files are recorded in [checks/SUMMARY.json](checks/SUMMARY.json). OTS checks all 154 delivered files. FontBakery was run with the universal, googlefonts and adobefonts profiles for every TTF/OTF/VF family group. Font Validator was run without raster tests. Raw negative results are retained; exceptions are documented in [ACCEPTANCE.md](ACCEPTANCE.md).

Astra independently reviewed the licensing transition and the а/a repair, then the ъ/Ъ change. The latter comparison covered 356 files and confirmed that unrelated glyphs, metrics, columns, layout tables and variation data were preserved. Astra checked 8,224 geometric cases and accepted the hard-sign design in the reviewed conditions. The primary а/a junction regression covered 56,250 cases; the ъ/Ъ flag regression covered 52,272.

Limitations remain. The italic Sans VF has a small residual а/a stem bend of up to 1.018 units at weight 700; the original horizontal shoulder is gone. Pre-rounding fit errors are not upper bounds for compiled outline errors. Extended language coverage is incomplete. This release does not claim full Google Fonts catalogue compliance; retaining an RFN also requires separate consideration for catalogue admission. Historical Font Validator exceptions and catalogue requirements must not be presented as an unqualified PASS.

The license and RFN were verified in all 356 delivered and source font files. Metadata finalization is byte-idempotent. All 38 web styles were checked in the browser on the diagnostic words without font fallback. A complete clean rebuild of every drawing and all historical graphical-inspector sessions were not repeated. The affected forms were rebuilt; each report states its conditions and limits.

- [Validation summary](checks/SUMMARY.json)
- [Independent ъ/Ъ review (in Russian)](checks/astra-hard-final.md)
- [Independent а/a and RFN review (in Russian)](checks/astra-rfn-a-final.md)
- [License audit of all final files](checks/rfn-update/final-license-audit.json)
- [Font checksums](FONT-SHA256.json)
- [Evidence stages and report scope](checks/EVIDENCE-STAGES.md)
- [Rebuilding Sans/Mono](SAB-Modul-1.0/source/REBUILD.md)
- [Rebuilding Code](SAB-Modul-Code/source/REBUILD.md)

## Repository structure

```text
sab-modul/
├── SAB-Modul-1.0/          Sans and Mono: TTF, OTF, VF, WEB, WOFF2, source
├── SAB-Modul-Code/         Code: TTF, OTF, VF, WEB, WOFF2, source
├── font-creation-prompt.md Ready-to-use font creation prompt (Russian)
├── docs/                  Creation prompt and distribution guide
├── checks/                Raw reports, regressions and independent reviews
├── tools/                 OFL finalization and validation runners
├── licenses/              Third-party report component licenses
├── LICENSE                SIL OFL 1.1
├── OFL.txt                The same complete license text
├── METHODOLOGY.md          Creation and verification approach
├── ACCEPTANCE.md           Criteria, exceptions and limitations
├── FONT-SHA256.json        SHA256 of all 154 delivered fonts
├── SHA256SUMS              Checksums of the current repository files
└── demo.html              Text, numbers and code example
```
