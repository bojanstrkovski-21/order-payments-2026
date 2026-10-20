r"""Show which glyph a MAC C style font draws for each printable ASCII code.

Usage:  python -I tools\font_map.py <font.ttf> [<font.ttf> ...]
Prints the family name and, for every ASCII code 0x21-0x7E, the glyph name.
"""
import sys

from fontTools.ttLib import TTFont


def describe(path):
    font = TTFont(path, lazy=True)
    family = font["name"].getDebugName(4) or font["name"].getDebugName(1)
    cmap = font.getBestCmap() or {}
    # Symbol-encoded fonts map ASCII into the U+F000 private range.
    symbol = any(0xF000 <= cp <= 0xF0FF for cp in cmap)
    print(f"== {path}\n   family: {family}   symbol-encoded: {symbol}")
    rows = []
    for code in range(0x21, 0x7F):
        glyph = cmap.get(code) or cmap.get(0xF000 + code)
        rows.append(f"{chr(code)}={glyph}")
    for i in range(0, len(rows), 8):
        print("   " + "  ".join(rows[i:i + 8]))


if __name__ == "__main__":
    for p in sys.argv[1:]:
        describe(p)
