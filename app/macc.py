"""Conversion between the old MAC C font encoding used in the NOVNAL database
and real Unicode Cyrillic.

The old app stores plain ASCII and relies on the "MAC C Swiss" font to draw it
as Macedonian Cyrillic. Mapping read from the font itself (tools/font_chart.py).
"""

_ASCII = "abvgdezijklmnoprstufhc`~{}|qwxy" "ABVGDEZIJKLMNOPRSTUFHC@^[]\\QWXY"
_CYRILLIC = "абвгдезијклмнопрстуфхцжчшќѓљњџѕ" "АБВГДЕЗИЈКЛМНОПРСТУФХЦЖЧШЌЃЉЊЏЅ"

_TO_UNICODE = str.maketrans(_ASCII, _CYRILLIC)
_TO_MACC = str.maketrans(_CYRILLIC, _ASCII)


def decode(stored: str | None) -> str:
    """Database value (MAC C ASCII) -> Unicode Cyrillic for display. Trailing CHAR padding is removed."""
    if stored is None:
        return ""
    return stored.rstrip().translate(_TO_UNICODE)


def encode(text: str) -> str:
    """Unicode Cyrillic typed in the new app -> MAC C ASCII for the database.

    Characters the old encoding cannot hold become '?', which is what the old app did too.
    """
    converted = text.translate(_TO_MACC)
    return "".join(ch if ord(ch) < 128 else "?" for ch in converted)


if __name__ == "__main__":
    samples = ["zbiren nalog za plata", "MODA SPORT", "~e{ka ]u`na", "Wiva Qubov Xvaka Yvezda"]
    for s in samples:
        u = decode(s)
        assert encode(u) == s, (s, u, encode(u))
        print(f"{s!r:30} -> {u}")
