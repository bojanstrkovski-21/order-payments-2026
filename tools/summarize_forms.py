r"""Build an index of the extracted text DFM files: one row per form with its
caption, size and event handlers, plus every SQL block grouped by form.

Usage:  python -I tools\summarize_forms.py <forms_dir> <out_dir>
"""
import re
import sys
from pathlib import Path

OBJECT = re.compile(r"^(\s*)(?:object|inherited|inline) (\w+): (\w+)")
PROP = re.compile(r"^\s*(\w+(?:\.\w+)*) = (.*)$")
SQL_PROP = re.compile(r"^\s*(\w*SQL)\.Strings = \($")
LINE = re.compile(r"^\s*'(.*)'\)?$")


def unquote(text):
    return text.replace("''", "'").replace("'#13'", "").replace("'#10'", "")


def parse(path):
    lines = path.read_text(encoding="utf-8").splitlines()
    form = {"file": path.name, "caption": "", "width": "", "height": "", "events": [], "sql": [], "classes": {}}
    stack = []
    i = 0
    while i < len(lines):
        line = lines[i]
        m = OBJECT.match(line)
        if m:
            depth = len(m.group(1)) // 2
            del stack[depth:]
            stack.append(m.group(2))
            form["classes"][m.group(3)] = form["classes"].get(m.group(3), 0) + 1
            i += 1
            continue
        m = SQL_PROP.match(line)
        if m:
            body = []
            i += 1
            while i < len(lines):
                lm = LINE.match(lines[i])
                if lm:
                    body.append(unquote(lm.group(1)))
                if lines[i].rstrip().endswith(")"):
                    break
                i += 1
            form["sql"].append((stack[-1] if stack else "?", m.group(1), "\n".join(body).strip()))
            i += 1
            continue
        m = PROP.match(line)
        if m and len(stack) == 1:
            name, value = m.groups()
            if name == "Caption":
                form["caption"] = unquote(value.strip("'"))
            elif name in ("ClientWidth", "Width") and not form["width"]:
                form["width"] = value
            elif name in ("ClientHeight", "Height") and not form["height"]:
                form["height"] = value
        if m and m.group(1).startswith("On"):
            form["events"].append(f"{stack[-1] if stack else '?'}.{m.group(1)} -> {m.group(2)}")
        i += 1
    return form


def main(forms_dir, out_dir):
    out = Path(out_dir)
    forms = [parse(p) for p in sorted(Path(forms_dir).glob("*.dfm"))]

    index = ["# Forms in NOVNAL.exe", "", "| Form | Caption | Size | Event handlers | SQL blocks | Main component types |", "|---|---|---|---|---|---|"]
    for f in forms:
        top = sorted(f["classes"].items(), key=lambda kv: -kv[1])[:4]
        types = ", ".join(f"{name}×{count}" for name, count in top)
        index.append(f"| {f['file']} | {f['caption']} | {f['width']}×{f['height']} | {len(f['events'])} | {len(f['sql'])} | {types} |")
    index += ["", "## Event handlers per form", ""]
    for f in forms:
        if f["events"]:
            index.append(f"### {f['file']}")
            index += [f"- `{e}`" for e in f["events"]]
            index.append("")
    (out / "forms_index.md").write_text("\n".join(index), encoding="utf-8")

    sql = []
    for f in forms:
        for component, kind, body in f["sql"]:
            if body:
                sql.append(f"-- {f['file']} / {component}.{kind}\n{body};\n")
    (out / "sql_from_forms.sql").write_text("\n".join(sql), encoding="utf-8")
    print(f"{len(forms)} forms, {sum(len(f['events']) for f in forms)} event handlers, {len(sql)} SQL blocks")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
