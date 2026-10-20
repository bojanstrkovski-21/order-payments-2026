r"""Extract Delphi form resources (binary DFM, "TPF0") from a PE file and
write each one as readable text DFM.

Usage:  python -I tools\extract_forms.py <exe> <out_dir>
"""
import struct
import sys
from pathlib import Path

import pefile

RT_RCDATA = 10
ANSI = "cp1251"  # Macedonian/Serbian Cyrillic forms use the Windows-1251 code page


class Reader:
    def __init__(self, data):
        self.data = data
        self.pos = 0

    def byte(self):
        b = self.data[self.pos]
        self.pos += 1
        return b

    def take(self, n):
        chunk = self.data[self.pos:self.pos + n]
        self.pos += n
        return chunk

    def unpack(self, fmt):
        size = struct.calcsize(fmt)
        return struct.unpack(fmt, self.take(size))[0]

    def shortstr(self):
        return self.take(self.byte()).decode(ANSI, errors="replace")


def quote(text):
    """Quote a string the way Delphi's text DFM does, keeping it readable."""
    if text == "":
        return "''"
    return "'" + text.replace("'", "''").replace("\r", "'#13'").replace("\n", "'#10'") + "'"


def read_value(r, indent):
    t = r.byte()
    pad = "  " * indent
    if t == 0:   # vaNull
        return "nil"
    if t == 1:   # vaList
        items = []
        while r.data[r.pos] != 0:
            items.append(read_value(r, indent + 1))
        r.byte()
        if not items:
            return "()"
        inner = "\n".join(f"{pad}  {item}" for item in items)
        return f"(\n{inner})"
    if t == 2:
        return str(r.unpack("<b"))
    if t == 3:
        return str(r.unpack("<h"))
    if t == 4:
        return str(r.unpack("<i"))
    if t == 5:   # vaExtended: 80-bit float
        mant, exp = struct.unpack("<QH", r.take(10))
        sign = -1 if exp & 0x8000 else 1
        exp &= 0x7FFF
        value = 0.0 if exp == 0 and mant == 0 else sign * mant / (1 << 63) * 2.0 ** (exp - 16383)
        return repr(value)
    if t in (6, 7):  # vaString, vaIdent
        s = r.shortstr()
        return quote(s) if t == 6 else s
    if t == 8:
        return "False"
    if t == 9:
        return "True"
    if t == 10:  # vaBinary
        n = r.unpack("<i")
        blob = r.take(n)
        return f"{{ binary {n} bytes }}" if n > 64 else "{" + blob.hex().upper() + "}"
    if t == 11:  # vaSet
        names = []
        while True:
            s = r.shortstr()
            if not s:
                break
            names.append(s)
        return "[" + ", ".join(names) + "]"
    if t == 12:  # vaLString
        n = r.unpack("<i")
        return quote(r.take(n).decode(ANSI, errors="replace"))
    if t == 13:
        return "nil"
    if t == 14:  # vaCollection
        items = []
        while True:
            k = r.byte()
            if k == 0:
                break
            index = ""
            if k in (2, 3, 4):
                r.pos -= 1
                index = f" [{read_value(r, indent)}]"
                k = r.byte()
            props = read_props(r, indent + 2)
            items.append(f"{pad}  item{index}\n{props}{pad}  end")
        if not items:
            return "<>"
        return "<\n" + "\n".join(items) + ">"
    if t == 15:
        return repr(r.unpack("<f"))
    if t == 16:  # vaCurrency: int64 scaled by 10000
        return repr(r.unpack("<q") / 10000)
    if t == 17:  # vaDate
        return repr(r.unpack("<d"))
    if t == 18:  # vaWString
        n = r.unpack("<i")
        return quote(r.take(n * 2).decode("utf-16-le", errors="replace"))
    if t == 19:
        return str(r.unpack("<q"))
    if t == 20:  # vaUTF8String
        n = r.unpack("<i")
        return quote(r.take(n).decode("utf-8", errors="replace"))
    if t == 21:
        return repr(r.unpack("<d"))
    raise ValueError(f"unknown DFM value type {t} at offset {r.pos - 1}")


def read_props(r, indent):
    out = []
    pad = "  " * indent
    while True:
        name = r.shortstr()
        if not name:
            break
        out.append(f"{pad}{name} = {read_value(r, indent)}\n")
    return "".join(out)


def read_object(r, indent=0):
    pad = "  " * indent
    keyword = "object"
    prefix = r.data[r.pos]
    if prefix & 0xF0 == 0xF0:
        r.byte()
        flags = prefix & 0x0F
        if flags & 1:
            keyword = "inherited"
        if flags & 4:
            keyword = "inline"
        if flags & 2:  # child position
            read_value(r, indent)
    cls = r.shortstr()
    name = r.shortstr()
    text = f"{pad}{keyword} {name}: {cls}\n" if name else f"{pad}{keyword} {cls}\n"
    text += read_props(r, indent + 1)
    while r.data[r.pos] != 0:
        text += read_object(r, indent + 1)
    r.byte()
    return text + f"{pad}end\n"


def main(exe, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    pe = pefile.PE(exe)
    count = 0
    for rtype in pe.DIRECTORY_ENTRY_RESOURCE.entries:
        if rtype.id != RT_RCDATA:
            continue
        for entry in rtype.directory.entries:
            name = str(entry.name) if entry.name else f"#{entry.id}"
            for lang in entry.directory.entries:
                data = pe.get_data(lang.data.struct.OffsetToData, lang.data.struct.Size)
                if not data.startswith(b"TPF0"):
                    continue
                r = Reader(data)
                r.pos = 4
                (out / f"{name}.dfm").write_text(read_object(r), encoding="utf-8")
                count += 1
    print(f"wrote {count} forms to {out}")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
