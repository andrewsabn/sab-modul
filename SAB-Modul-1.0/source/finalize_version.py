"""Normalize release metadata after building; preserve timestamps and geometry."""
from pathlib import Path
from fontTools.ttLib import TTFont
root = Path(__file__).resolve().parents[1]
for folder in ("TTF", "OTF", "WOFF2", "VF", "WEB"):
    for path in sorted((root / folder).iterdir()):
        if path.suffix not in (".ttf", ".otf", ".woff2"):
            continue
        font = TTFont(path, recalcTimestamp=False)
        for record in font["name"].names:
            if record.nameID == 5:
                record.string = "Version 1.000"
            elif record.nameID == 3:
                record.string = "SAB:1.000:" + font["name"].getDebugName(6)
        font["head"].fontRevision = 1.0
        if "CFF " in font:
            font["CFF "].cff.topDictIndex[0].version = "1.000"
        font.save(path)
        check = TTFont(path)
        assert check["name"].getDebugName(5) == "Version 1.000"
        assert check["head"].fontRevision == 1.0
