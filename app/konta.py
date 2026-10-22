"""КОНТА helpers. The old program stored a 30-character description (KONTA.OPIS, also the width of the specification
column); the new register also keeps the full official name (KONTA.OPISFULL, user decision 2026-10-21)."""

OPIS_LEN = 30   # old KONTA.OPIS CHAR(30)
FULL_LEN = 400  # new KONTA.OPISFULL (longest official name: 329)


def short_name(text: str, limit: int = OPIS_LEN) -> str:
    """The full name cut at a word boundary to at most `limit` characters."""
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    if text[limit] != " " and " " in cut:
        cut = cut[:cut.rfind(" ")]
    return cut.rstrip(" -,(")


def konto_class(konto: str) -> str:
    """'4' (rashodi) or '7' (prihodi) — first digit of the konto."""
    return konto[:1]
