"""Build the seed lists for the КОНТА register from the ministry PDFs (extracted/ministry/).

  rashodi (class 4)  : read from the text layer of the Правилник; its text is in the old MAC C encoding -> macc.decode
  prihodi (class 7)  : the Службен весник PDF is scanned, so the text was transcribed by hand into
                       extracted/ministry/prihodi_transcribed.txt (one "konto name" per line) - read from there
  uplatni smetki     : hand-transcribed too (scanned) into extracted/ministry/uplatni_transcribed.txt
Output (extracted/ministry/): konta_seed.csv  (konto;opis30;opis_full;klasa)
                              uplatni_seed.csv (banka;kod;naziv;konto) - every konto is checked against konta_seed

Run:  demo/.venv/Scripts/python.exe -I -X utf8 tools/import_konta.py
"""
import csv
import re
import sys
from pathlib import Path

import pymupdf

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "app"))
import macc  # noqa: E402
from konta import OPIS_LEN, short_name as short  # noqa: E402

MIN = ROOT / "extracted" / "ministry"
RASHODI = MIN / "Pravilnik_za_klasifikacija_na_rashodite.pdf"
PRIHODI_TXT = MIN / "prihodi_transcribed.txt"
UPLATNI_TXT = MIN / "uplatni_transcribed.txt"


def rashodi_rows():
    """[(konto, full name)] from the Правилник, wrapped names joined."""
    doc = pymupdf.open(RASHODI)
    out, last = [], None
    for page in doc:
        lines = []
        for b in page.get_text("dict")["blocks"]:
            for ln in b.get("lines", []):
                text, prev = "", None
                for s in ln["spans"]:
                    if not s["text"].strip():
                        continue
                    # spans in a different font can split one word: join without a space when they touch
                    if prev is not None and s["bbox"][0] - prev["bbox"][2] > 1.5 and not text.endswith(" "):
                        text += " "
                    text += s["text"].strip() if prev is None else s["text"].lstrip() if text.endswith(" ") else s["text"]
                    prev = s
                if text.strip():
                    lines.append((round(ln["bbox"][1]), ln["bbox"][0], text.strip()))
        # merge fragments that sit on the same baseline (code, then name) into one row
        rows = {}
        for y, x, t in sorted(lines):
            key = next((k for k in rows if abs(k - y) <= 3), y)
            rows.setdefault(key, []).append((x, t))
        last_y = None
        for y in sorted(rows):
            text = " ".join(t for _, t in sorted(rows[y])).strip()
            m = re.match(r"^(\d{6})\s*-?\s*(.*)$", text)
            if m:
                out.append([m.group(1), m.group(2)])
                last, last_y = out[-1], y
            elif last is not None and last_y is not None and y - last_y <= 16 and not re.match(r"^\d{1,5}\b", text) \
                    and not text.isdigit():
                last[1] += " " + text
                last_y = y
            else:
                last = None
    return [(c, macc.decode(n)) for c, n in out]


def prihodi_rows():
    rows = []
    for line in PRIHODI_TXT.read_text(encoding="utf8").splitlines():
        m = re.match(r"^(\d{6})\s+(.+)$", line.strip())
        if m:
            rows.append((m.group(1), m.group(2)))
    return rows


def uplatni_rows(names):
    """[(banka, kod, naziv, konto)]; the name of a row with a konto is the konto's official name."""
    rows, problems = [], []
    for line in UPLATNI_TXT.read_text(encoding="utf8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^(84[03])-(\d{5})\s+(?:(\d{6})|-\s+(.+))$", line)
        if not m:
            problems.append("cannot read: " + line)
            continue
        banka, kod, konto, naziv = m.groups()
        if konto:
            if konto not in names:
                problems.append(f"{banka}-{kod}: konto {konto} is not in the konta list")
            naziv = names.get(konto, "")
        rows.append((banka, kod, naziv, konto or ""))
    codes = [(b, k) for b, k, _, _ in rows]
    problems += [f"duplicate account {b}-{k}" for b, k in sorted(set(c for c in codes if codes.count(c) > 1))]
    return rows, problems


def main():
    seen, result = {}, []
    for source in (rashodi_rows(), prihodi_rows()):
        for konto, name in source:
            name = " ".join(name.split())
            if konto in seen:
                print("duplicate", konto, "|", seen[konto], "|", name)
                continue
            seen[konto] = name
            result.append((konto, short(name), name, konto[0]))
    result.sort()
    with open(MIN / "konta_seed.csv", "w", encoding="utf8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["konto", "opis30", "opis_full", "klasa"])
        w.writerows(result)
    print(len(result), "konta,", sum(1 for r in result if r[3] == "4"), "rashodi,", sum(1 for r in result if r[3] == "7"), "prihodi")
    print("names cut to", OPIS_LEN, ":", sum(1 for r in result if r[1] != r[2]))
    rows, problems = uplatni_rows(seen)
    with open(MIN / "uplatni_seed.csv", "w", encoding="utf8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["banka", "kod", "naziv", "konto"])
        w.writerows(rows)
    print(len(rows), "uplatni smetki,", sum(1 for r in rows if not r[3]), "without a konto")
    for p in problems:
        print("PROBLEM:", p)


if __name__ == "__main__":
    main()
