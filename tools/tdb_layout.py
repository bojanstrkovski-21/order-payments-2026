r"""Inspect old „FORMAT ZA TREZOR" (*.TDB) files: line lengths, record types and a field split of one record.

Usage:  python -I tools\tdb_layout.py <file.TDB> [<file.TDB> ...]
Read-only. The files contain personal data — do not copy them into the repository.
"""
import collections
import sys
from pathlib import Path

# Field widths of a type-2 (order) record, worked out from the old program and the files (see tdb_spec.md).
ORDER_FIELDS = [
    ("type", 1), ("seq", 6), ("smetzadolz", 15), ("podsmetzadolz", 15), ("konzadolz", 6), ("progzadolz", 2),
    ("cel", 70), ("sifra", 6), ("sign", 1), ("iznos", 18), ("smetprim", 18), ("nazprim1", 35), ("nazprim2", 35),
    ("podsmetprim", 15), ("konprim", 6), ("progprim", 2), ("povik1", 24), ("vidobr", 2), ("nacin", 1), ("edb", 13),
    ("dosdat", 8),
]


def split(record, fields):
    out, pos = [], 0
    for name, width in fields:
        out.append((name, record[pos:pos + width]))
        pos += width
    return out, record[pos:]


def main(paths):
    stats = collections.Counter()
    for path in paths:
        data = Path(path).read_bytes()
        stats["files"] += 1
        stats["ends with CRLF"] += data.endswith(b"\r\n")
        stats["non-ascii files"] += any(b > 127 for b in data)
        lines = data.decode("ascii", "replace").split("\r\n")
        if lines and lines[-1] == "":
            lines.pop()
        for line in lines:
            stats[f"type {line[:1]} len {len(line)}"] += 1
    for key, value in sorted(stats.items()):
        print(f"{key:28} {value}")


if __name__ == "__main__":
    main(sys.argv[1:])
