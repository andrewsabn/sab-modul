"""Diagonal terminals must reach the same alignment zones as straight stems."""
import build

for mono in (False, True):
    data = build.alphabet('SAB Modul', mono)
    for style, (_, thickness) in build.WEIGHTS.items():
        for oblique in (False, True):
            for char in 'уухxyvVWXAY':
                shape, advance, _ = build.geometry(*data[char], 'SAB Modul', mono, thickness, oblique, char)
                bottom, top = shape.bounds[1::2]
                height = 700 if char.isupper() else build.XHEIGHT
                if char != 'A':
                    assert abs(top-height) < .5, (mono, style, oblique, char, 'top', top, height)
                if char in 'хxXA':
                    assert abs(bottom) < .5, (mono, style, oblique, char, 'bottom', bottom)
                if char in 'уy':
                    assert bottom < -200, (char, 'lost descender', bottom)
                if mono:
                    assert advance == build.MONO_ADVANCE
            be, _, _ = build.geometry(*data['б'], 'SAB Modul', mono, thickness, oblique, 'б')
            assert abs(be.bounds[1]) < .5, (mono, style, oblique, 'б', 'floating bowl', be.bounds[1])
print('PASS: diagonal terminal zones, descenders and Mono advance in 28 styles')
