"""Repair the approved Roman VF semicolon dot without changing metrics."""
from pathlib import Path
import argparse
from fontTools.ttLib import TTFont


def repair(font):
    assert 'fvar' in font and font['post'].italicAngle == 0
    glyph = font['glyf'][font.getBestCmap()[ord(';')]]
    assert glyph.endPtsOfContours == [36, 54], 'Unexpected semicolon topology'
    assert tuple(glyph.coordinates[45]) in ((216, 418), (215, 418))
    assert not glyph.flags[45] & 1, 'Expected an off-curve control point'
    glyph.coordinates[45] = (215, 418)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('fonts', type=Path, nargs='+')
    args = parser.parse_args()
    for path in args.fonts:
        font = TTFont(path, recalcTimestamp=False)
        repair(font)
        font.save(path)
        font.close()
        print('Repaired', path)
