from pathlib import Path
import argparse, shutil, hashlib, json, re
from fontTools.ttLib import TTFont

COPYRIGHT = 'Copyright 2026 Andrew Sabynin (https://sabynin.com/)'
LICENSE = 'This Font Software is licensed under the SIL Open Font License, Version 1.1. This license is available with a FAQ at: https://openfontlicense.org. Reserved Font Name: SAB Modul. Modified Versions may not use the Reserved Font Name without explicit written permission of the copyright holder.'
URL = 'https://openfontlicense.org'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def update(path, revision):
    original = path.read_bytes()
    font = TTFont(path, recalcTimestamp=False, recalcBBoxes=False)
    before = {t: font.getTableData(t) for t in font.keys() if t != 'GlyphOrder'}
    glyph_order = font.getGlyphOrder()
    cff_before = None
    if 'CFF ' in font:
        top = font['CFF '].cff.topDictIndex[0]
        cff_before = {g: sha(top.CharStrings[g].bytecode) for g in glyph_order}
        if hasattr(top, 'Notice'):
            top.Notice = COPYRIGHT
        if hasattr(top, 'Copyright'):
            top.Copyright = COPYRIGHT
        if hasattr(top, 'version'):
            top.version = revision
    names = font['name']
    platforms = {(n.platformID, n.platEncID, n.langID) for n in names.names if n.nameID == 13}
    if not platforms:
        platforms = {(3, 1, 0x409)}
    for n in list(names.names):
        if n.nameID in (0, 13, 14, 5):
            value = {0: COPYRIGHT, 13: LICENSE, 14: URL, 5: 'Version ' + revision}[n.nameID]
            names.setName(value, n.nameID, n.platformID, n.platEncID, n.langID)
        elif n.nameID == 3:
            value = re.sub(r'(?<=:)1\.\d+(?=:)', revision, n.toUnicode())
            names.setName(value, 3, n.platformID, n.platEncID, n.langID)
    for platform, encoding, language in platforms:
        names.setName(COPYRIGHT, 0, platform, encoding, language)
        names.setName(LICENSE, 13, platform, encoding, language)
        names.setName(URL, 14, platform, encoding, language)
    font['head'].fontRevision = float(revision)
    font.save(path)
    new = TTFont(path, recalcTimestamp=False, recalcBBoxes=False)
    assert new.getGlyphOrder() == glyph_order
    changed = []
    for tag, data in before.items():
        after = new.getTableData(tag)
        if data != after:
            changed.append(tag)
            assert tag in ('name', 'head', 'CFF '), (path.name, tag)
        if tag == 'head':
            # Only fontRevision and checkSumAdjustment may differ.
            assert data[:4] == after[:4] and data[12:] == after[12:]
    if cff_before is not None:
        top = new['CFF '].cff.topDictIndex[0]
        assert cff_before == {g: sha(top.CharStrings[g].bytecode) for g in glyph_order}
    assert all(n.toUnicode() == LICENSE for n in new['name'].names if n.nameID == 13)
    assert new['name'].getDebugName(14) == URL
    return {'input_sha256': sha(original), 'sha256': sha(path.read_bytes()),
            'changed_tables': changed, 'drawing_metrics_features_preserved': True,
            'version': revision, 'bytes': path.stat().st_size}


def main():
    p=argparse.ArgumentParser()
    p.add_argument("folder",type=Path);p.add_argument("--revision",required=True)
    a=p.parse_args()
    files=sorted(f for f in a.folder.rglob("*") if f.suffix.lower() in (".ttf",".otf",".woff2"))
    for f in files: update(f,a.revision)
    print("OFL metadata updated:",len(files))
if __name__=="__main__": main()
