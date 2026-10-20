r"""Map each parameter of the SQL statements in a Delphi handler listing to its source.

Reads an annotated listing from delphi_listing.py. For every TParams.Items[i] call it reports
the parameter index, its name from the SQL text, and the nearest preceding source in the same
stretch of code: a form/data-module field, a string literal, or a global variable.

Usage:  python -I tools\param_map.py <listing.asm>
"""
import re
import sys
from pathlib import Path

SQL = re.compile(r"; '((?:insert|update|select|delete)[^']*)'", re.I)
PARAM = re.compile(r":(\w+)")
FIELD = re.compile(r"\+0x[0-9a-f]+=(\S+)")
LITERAL = re.compile(r"; '([^']*)'")
GLOBAL = re.compile(r"push dword ptr \[(0x80[0-9a-f]{4})\]")
INDEX = re.compile(r"mov edx, (0x[0-9a-f]+|\d+)\s*$")


def main(path):
    """Delphi sets a parameter either as  <load value>; Items(i); Set…(value)  or as  Items(i); <load constant>; Set….
    So sources seen before Items(i) and between Items(i) and the Set… call both belong to parameter i."""
    lines = Path(path).read_text(encoding="utf-8").splitlines()
    params, sources, index, current = [], [], None, None

    def flush():
        nonlocal current, sources
        if current is not None:
            i, name, before = current
            print(f"  {i:2d} {name:32} <- {', '.join(dict.fromkeys(before + sources)) or '?'}")
            current, sources = None, []

    for line in lines:
        if m := SQL.search(line):
            flush()
            if params:
                print()
            text = m.group(1)
            kind = text.split()[0].lower()
            params = PARAM.findall(text)
            if kind == "insert":  # parameters follow the column list order
                cols = re.search(r"\(([^)]*)\)", text).group(1).split(",")
                params = [f"{c.strip()} (:{p})" for c, p in zip(cols, params)]
            print(f"== {kind}: {text[:90]}{'...' if len(text) > 90 else ''}")
            sources = []
            continue
        if not params:
            continue
        if "xor edx, edx" in line:
            index = 0
        elif m := INDEX.search(line.split(";")[0]):
            index = int(m.group(1), 0)
        if "TParams.Items" in line and index is not None:
            flush()
            current = (index, params[index] if index < len(params) else f"#{index}", sources)
            sources, index = [], None
            continue
        if "TParam." in line or re.search(r"call 0x60[0-9a-f]{4}\b", line):
            flush()
            continue
        for rx, fmt in ((FIELD, "{}"), (GLOBAL, "global {}")):
            for m in rx.finditer(line):
                if not m.group(1).startswith(("dm.DataSource", "dm.SPECO", "dm.PROMET", "dm.IBTrans")):
                    sources.append(fmt.format(m.group(1)))
        if (m := LITERAL.search(line)) and not SQL.search(line):
            sources.append(f"'{m.group(1)}'")


if __name__ == "__main__":
    main(sys.argv[1])
