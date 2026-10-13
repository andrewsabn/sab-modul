# Rebuilding and verifying the OFL release

Work in a disposable copy. The shipped binaries are accepted drawings with OFL metadata applied, not a new drawing revision. The current fonts are identified by root FONT-SHA256.json; historical manifests explicitly describe earlier versions.

## Reproduce this release preparation

Use Python 3.12, fontTools 4.66.1 and Brotli. In a copy of the root distribution run:

```sh
python tools/apply_ofl.py SAB-Modul-1.0 --revision 1.101
python tools/apply_ofl.py SAB-Modul-Code --revision 1.002
```

This step is idempotent on the supplied files. It finalizes metadata only. The reports in checks/license-regression.json and source-license-regression.json record allowed differences; astra-independent-audit.json independently compares every delivered and source font.

## Full drawing build, for development

The preserved masters and drawing programs allow further development. A complete clean drawing rebuild of this OFL package has NOT been repeated; its output must be revalidated before distribution. Earlier accepted rebuild results do not establish binary identity for this package. Python dependencies include fontTools[woff], numpy, shapely and uharfbuzz. For hinted static Sans/Mono builds provide ttfautohint 1.8.4 on PATH. Any optional OTS executable is selected with OTS_SANITIZE or PATH.

Sans/Mono development pipeline, from its family directory:

```sh
python source/build_variable.py --reuse-compatible
python source/verify_variable.py
python source/build.py
python source/finish.py
python source/subset_web.py
python source/finalize_version.py
python source/fix_subset_metadata.py
python source/update_license.py
python source/apply_review_fixes.py
python ../tools/apply_ofl.py . --revision 1.101
```

Code preserves successive masters, drawing modules, repair_vf_semicolon.py and validators. Its upstream directory contains the author's own Sans/Mono drawing source, not an external font library. Run drawing changes only in a copy and use the final metadata tool afterward. Historical intermediate masters do not equal the final Code drawings.

## Publication cleanup

Environment-specific remote installation and proof helpers requiring private reference files were omitted. Third-party comparison fonts and private credentials are not distributed. Original private working archives remain unchanged. This package contains no claim that missing reference-based proofs were rerun. Fresh OTS, Font Validator and FontBakery outputs are in checks/; raw negative outcomes remain visible.
