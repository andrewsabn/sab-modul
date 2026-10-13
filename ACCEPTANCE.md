# Acceptance scope and retained raw findings

This metadata-only OFL release carries forward the previously owner-accepted drawings for Russian/English corporate use. It does not assert universal language support, an unqualified Google Fonts PASS, or new catalogue admission. The binary drawing/metrics/feature comparison and independent review establish that the licensing change did not alter the accepted forms.

## Font Validator findings

All 6183 error records exactly match the corresponding accepted full baseline: 4041 Sans/Mono and 2142 Code. Raster tests were not enabled. Current raw records remain in XML/JSON. Prior explanations concern legacy fsSelection parsing, unsupported VariationIndex device records, interpretation of null anchors, required Mac name records, and intentional contour overlaps/contacts. These are documented inherited exceptions, not raw PASS results. No new or changed raw error record was found.

## FontBakery findings

All three profiles were run for all delivered TTF/OTF/VF family groups. Raw aggregate 302 FAIL/44 ERROR is preserved. The Adobe profile has no FAIL/ERROR. Code universal Mac name records are retained for compatibility. Google-specific family/copyright/name/weight/axis conventions are not asserted compliant with catalogue requirements. Extended language missing characters are actual limitations and must not be advertised as supported. The current online name-check ERROR is KeyError 'data'; its remote cause was not independently established in this pass.

The supplied CFF checker patch repairs an upstream glyf-only assumption. Its own negative control still rejects invalid advanceWidthMax. It does not erase a font error or modify the fonts.

## Design and application limits

Earlier independent design reviews, fixed proof pages and real-application tests underpin acceptance of the preserved drawings. These sessions were not all repeated after the legal metadata change. Code %/@ retained earlier accepted forms following a thickening trial that worsened small-size counters; a numerical stroke threshold was waived explicitly. A tiny variable semicolon dot repair in the accepted baseline remains intact.

A complete clean drawing rebuild of this OFL snapshot was not repeated; a future drawing change requires a new build and full applicable checks. The OFL finalization step itself is byte-idempotent on all 356 supplied font files. A verified valid binary does not certify every future use, expanded language or artistic uniqueness.
