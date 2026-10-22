"""УПЛАТНИ СМЕТКИ helpers.

Official register code is banka-kod (e.g. 840-01013). On Налог 61/70 the field
podsmetprim stores one 11-digit number = bank (3) + municipality (3) + kod (5).
"""

from __future__ import annotations

NAZIV_MAX = 400  # UPLATNI.NAZIV VARCHAR; MAC C is 1:1 for encodable text


def format_code(banka: str, kod: str) -> str:
    """Display form: 840-01013."""
    return f"{(banka or '').strip()}-{(kod or '').strip()}"


def parse_code(code: str) -> tuple[str, str]:
    """Parse '840-01013', '84001013', or 11-digit podsmetprim into (banka, kod)."""
    s = (code or "").strip().replace(" ", "")
    if "-" in s:
        left, right = s.split("-", 1)
    elif len(s) == 11 and s.isdigit():
        # podsmetprim = banka(3) + opstina(3) + kod(5)
        left, right = s[:3], s[6:11]
    elif len(s) == 8 and s.isdigit():
        left, right = s[:3], s[3:]
    else:
        raise ValueError("Шифрата мора да биде од облик 840-01013.")
    banka, kod = left.strip(), right.strip()
    if not (len(banka) == 3 and banka.isdigit()):
        raise ValueError("Банката мора да има 3 цифри (840 или 843).")
    if not (len(kod) == 5 and kod.isdigit()):
        raise ValueError("Кодот мора да има 5 цифри.")
    return banka, kod


def to_podsmetprim(banka: str, kod: str, opstina: str) -> str:
    """11-digit podsmetprim: banka + 3-digit municipality + 5-digit kod.

    Example: 840-01258 + opstina 103 → 84010301258
    """
    b = (banka or "").strip()
    k = (kod or "").strip()
    o = (opstina or "").strip()
    if not (len(b) == 3 and b.isdigit()):
        raise ValueError("Банката мора да има 3 цифри.")
    if not (len(k) == 5 and k.isdigit()):
        raise ValueError("Кодот мора да има 5 цифри.")
    if not (len(o) == 3 and o.isdigit()):
        raise ValueError("Општината мора да има 3 цифри.")
    return f"{b}{o}{k}"


def matches_podsmetprim(podsmetprim: str, banka: str, kod: str) -> bool:
    """True if podsmetprim is 11 digits with this banka at 1..3 and kod at 7..11."""
    p = (podsmetprim or "").strip()
    b = (banka or "").strip()
    k = (kod or "").strip()
    if len(p) != 11 or not p.isdigit():
        return False
    return p[:3] == b and p[6:11] == k
