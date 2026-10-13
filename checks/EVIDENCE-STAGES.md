# Evidence stages

The initial public release ofl-2026-10-13 did not declare an RFN. Its metadata-only license-regression.json, source-license-regression.json, astra-independent-audit.json, astra-ofl-review-final.md and astra-idempotence.json are historical. Their assertions of unchanged drawings relate only to that stage.

rfn-update/metadata-regression.json describes the subsequent RFN/version stage before drawing repairs. rfn-update/final-license-audit.json identifies the final a+Ъ/ъ files and verifies their exact license/RFN/version records and metadata finalizer idempotence.

astra-rfn-a-* and a-junction describe the Sans a repair before the later hard-sign repair. The initial astra-rfn-a-audit.json detected a CFF offset, subsequently corrected and independently rechecked in astra-rfn-a-cff-final.json. The final review records a tiny remaining italic VF bend and the actual post-rounding fit limits.

astra-hard-* and hard-sign describe the all-family Ъ/ъ repair. Their baseline already contained the accepted a repair and RFN. The hard-sign comparison independently confirms a was not changed again. Earlier source fit error fields predate the hard-sign coordinate transformation; current static source hashes are separately identified.

Current ots.json, fontvalidator.json, fontbakery-runs.json and SUMMARY.json relate to the final fonts in FONT-SHA256.json. Raw statuses remain unchanged by path redaction. Font Validator does not perform raster tests in this package. The full clean drawing rebuild and complete GUI/device matrix were not repeated.
