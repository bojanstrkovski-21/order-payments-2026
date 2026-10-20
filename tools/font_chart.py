r"""Draw a chart of printable ASCII codes rendered in a given font, with the
plain ASCII character under each glyph, so the MAC C letter mapping can be read.

Usage:  python -I tools\font_chart.py <font.ttf> <out.png>
"""
import sys

from PIL import Image, ImageDraw, ImageFont

CHARS = "`~[{]}\\|@^qwxycjQWXYCJ abvgdezijklmnoprstufhcABVGDEZIJKLMNOPRSTUFHC"
CELL_W, CELL_H, COLS = 70, 90, 12


def main(font_path, out_path):
    chars = [c for c in CHARS if c != " "]
    rows = (len(chars) + COLS - 1) // COLS
    img = Image.new("RGB", (COLS * CELL_W, rows * CELL_H), "white")
    draw = ImageDraw.Draw(img)
    glyph_font = ImageFont.truetype(font_path, 44)
    label_font = ImageFont.truetype("consola.ttf", 18)
    for i, ch in enumerate(chars):
        x, y = (i % COLS) * CELL_W, (i // COLS) * CELL_H
        draw.rectangle([x, y, x + CELL_W - 1, y + CELL_H - 1], outline="#bbbbbb")
        draw.text((x + 14, y + 4), ch, font=glyph_font, fill="black")
        draw.text((x + 26, y + 64), ch, font=label_font, fill="#c00000")
    img.save(out_path)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
