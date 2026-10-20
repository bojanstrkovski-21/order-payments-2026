r"""Annotated disassembly of the published event handlers of one Delphi form
class, for handlers Ghidra did not turn into functions.

Each handler runs from its entry to the next published method entry (any class).
Annotations: string literals (UnicodeString / AnsiString, MAC C decoded), form and
data-module field names for [reg+offset] operands, and handler names for calls.

Usage:  python -I tools\delphi_listing.py <exe> <app_methods.md> <ClassName> <out_dir> [handler ...]
"""
import re
import struct
import sys
from pathlib import Path

import capstone
import pefile

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "app"))
import macc  # noqa: E402

HEADER = re.compile(r"^## (\w+) \(VMT")
METHOD = re.compile(r"^- `(\w+)` 0x([0-9a-f]+)$")
FIELD = re.compile(r"^- `\+0x([0-9a-f]+)` (\w+)$")
OFFSET = re.compile(r"\[(e[a-ds][xip]|e[sd]i|ebp|esp)(?: \+ 0x([0-9a-f]+))?\]")
IMM = re.compile(r"0x([0-9a-f]{6,8})\b")

# Helpers identified so far (see docs in extracted/vnnal_spec.md).
KNOWN_CALLS = {
    0x59210C: "TControl.GetText",
    0x49E914: "TControl.SetColor",
    0x49E654: "TControl.SetVisible",
    0x49E794: "TControl.SetText",
    0x5FD6F4: "TDataSet.Fields[i]",
    0x60F8A8: "TDataSet.First",
    0x60FBC4: "TDataSet.Next",
    0x60D054: "TDataSet.Open",
    0x6094AC: "TParams.Items[i]",
    0x60BC84: "TParam.SetAsString",
}


def parse_methods(path):
    classes, current = {}, None
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if m := HEADER.match(line):
            current = classes.setdefault(m.group(1), {"methods": {}, "fields": {}})
        elif current is not None and (m := METHOD.match(line)):
            current["methods"][m.group(1)] = int(m.group(2), 16)
        elif current is not None and (m := FIELD.match(line)):
            current["fields"][int(m.group(1), 16)] = m.group(2)
    return classes


class Image:
    def __init__(self, exe):
        pe = pefile.PE(exe, fast_load=True)
        self.base = pe.OPTIONAL_HEADER.ImageBase
        self.mem = pe.get_memory_mapped_image()

    def valid(self, va):
        return self.base <= va < self.base + len(self.mem) - 16

    def read(self, va, n):
        return self.mem[va - self.base:va - self.base + n]

    def literal(self, va):
        """Return the Delphi string literal starting at va, or None."""
        if not self.valid(va) or va - 12 < self.base:
            return None
        codepage, elem, refcnt, length = struct.unpack("<HHiI", self.read(va - 12, 12))
        if refcnt != -1 or not 0 < length < 4000:
            return None
        if elem == 2 and codepage == 1200:
            return self.read(va, length * 2).decode("utf-16-le", errors="replace")
        if elem == 1:
            raw = self.read(va, length).decode("cp1251", errors="replace")
            return f"{raw}  «{macc.decode(raw)}»" if raw.isascii() else raw
        return None


def main(exe, methods_md, cls, out_dir, only):
    classes = parse_methods(methods_md)
    form = classes[cls]
    dm_fields = classes.get("Tdm", {}).get("fields", {})
    handler_names = {addr: f"{c}.{n}" for c, info in classes.items() for n, addr in info["methods"].items()}
    starts = sorted(handler_names)
    img = Image(exe)
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    for name, start in sorted(form["methods"].items(), key=lambda kv: kv[1]):
        if only and name not in only:
            continue
        end = next((s for s in starts if s > start), start + 0x400)
        lines = [f"; {cls}.{name}  0x{start:x}-0x{end:x}"]
        for ins in md.disasm(img.read(start, end - start), start):
            text = f"{ins.mnemonic} {ins.op_str}".strip()
            notes = []
            # Offsets in "call [reg+off]" are virtual method slots, not fields.
            for m in OFFSET.finditer("" if ins.mnemonic == "call" else ins.op_str):
                if m.group(2):
                    off = int(m.group(2), 16)
                    labels = []
                    if off in form["fields"]:
                        labels.append(form["fields"][off])
                    if off in dm_fields:
                        labels.append("dm." + dm_fields[off])
                    if labels:
                        notes.append(f"+0x{off:x}=" + "|".join(labels))
            for m in IMM.finditer(ins.op_str):
                va = int(m.group(1), 16)
                if ins.mnemonic == "call" or ins.mnemonic.startswith("j"):
                    label = handler_names.get(va) or KNOWN_CALLS.get(va)
                    if label:
                        notes.append(label)
                    continue
                if (s := img.literal(va)) is not None:
                    notes.append(repr(s))
            note = ("    ; " + "; ".join(notes)) if notes else ""
            lines.append(f"{ins.address:08x}  {text:48}{note}")
        (out / f"{name}_0x{start:x}.asm").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print(f"{name:24} 0x{start:x}  {len(lines) - 1} instructions")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], set(sys.argv[5:]))
