# Acceptance scope and retained raw findings

This release preserves prior Russian/English corporate acceptance, with owner-authorized a and Ъ/ъ drawing repairs plus OFL/RFN metadata. It does not assert universal language support or catalogue admission. The bounded rebuilds and independent audits preserve all unrelated glyphs, advances, layout and variation data. Astra separately accepts the hard-sign redesign in the reviewed 14/16pt conditions.

## Font Validator findings

All 6183 error records exactly match the corresponding accepted full baseline: 4041 Sans/Mono and 2142 Code. Raster tests were not enabled. Current raw records remain in XML/JSON. Prior explanations concern legacy fsSelection parsing, unsupported VariationIndex device records, interpretation of null anchors, required Mac name records, and intentional contour overlaps/contacts. These are documented inherited exceptions, not raw PASS results. No new or changed raw error record was found.

## FontBakery findings

All three profiles were run for all delivered TTF/OTF/VF family groups. The final raw aggregate is 466 FAIL/44 ERROR. Compared with the initial public OFL reports, 164 additional FAIL check results concern only Google-specific license checks: the OFL copyright template and exact nameID 13 license-description string. The latter intentionally includes RFN and modification restrictions at the owner’s request. Copyright and RFN are valid distribution choices, not assertions of Google Fonts catalogue compatibility. The prior OFL-copyright check was skipped in the initial reports; the current packaged license is inspected. All current raw outcomes remain visible. See fontbakery-regression.json for per-check negative-message counts, which can exceed check-result counts because both Mac and Windows records may be reported. The Adobe profile has no FAIL/ERROR. Code universal Mac name records are retained for compatibility. Google-specific family/copyright/name/weight/axis conventions are not asserted compliant with catalogue requirements. Extended language missing characters are actual limitations and must not be advertised as supported. The current online name-check ERROR is KeyError 'data'; its remote cause was not independently established in this pass.

The supplied CFF checker patch repairs an upstream glyf-only assumption. Its own negative control still rejects invalid advanceWidthMax. It does not erase a font error or modify the fonts.

## Design and application limits

Earlier independent design reviews, fixed proof pages and real-application tests underpin acceptance of the preserved drawings. These sessions were not all repeated after the legal metadata change. Code %/@ retained earlier accepted forms following a thickening trial that worsened small-size counters; a numerical stroke threshold was waived explicitly. A tiny variable semicolon dot repair in the accepted baseline remains intact.

The current a and hard-sign changes were rebuilt from frozen final/compatible masters and fully rechecked with the shipped technical gates. A complete clean rebuild of every glyph was not repeated. Changed CFF charstrings use regenerated raw outlines without earlier glyph-specific hints; TTF changed glyphs were rehinted. A tiny residual a-stem bend in Sans italic VF is documented at 1.018 units at wght 700. Pre-rounding fit errors are not upper bounds for final compiled contours. The OFL finalization step itself is byte-idempotent on all 356 supplied font files. A verified valid binary does not certify every future use, expanded language or artistic uniqueness.
