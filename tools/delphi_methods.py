r"""List published methods (event handlers) of Delphi classes with their code
addresses, by walking the VMTs of a 32-bit Delphi XE2 executable.

Usage:  python -I tools\delphi_methods.py <exe> <out.md> [ClassName ...]
"""
import struct
import sys

import pefile

# Delphi XE2 32-bit VMT layout: negative offsets from the VMT pointer.
VMT_SELF = -88
VMT_FIELD_TABLE = -68
VMT_METHOD_TABLE = -64
VMT_CLASS_NAME = -56
VMT_PARENT = -48


def main(exe, out_path, wanted):
    pe = pefile.PE(exe, fast_load=True)
    base = pe.OPTIONAL_HEADER.ImageBase
    image = pe.get_memory_mapped_image()
    text = next(s for s in pe.sections if s.Name.rstrip(b"\0") == b".text")
    lo = base + text.VirtualAddress
    hi = lo + text.Misc_VirtualSize

    def u32(va):
        return struct.unpack_from("<I", image, va - base)[0]

    def u16(va):
        return struct.unpack_from("<H", image, va - base)[0]

    def shortstr(va):
        n = image[va - base]
        return image[va - base + 1:va - base + 1 + n].decode("latin-1")

    def in_text(va):
        return lo <= va < hi

    classes = {}
    for off in range(text.VirtualAddress, text.VirtualAddress + text.Misc_VirtualSize - 4, 4):
        vmt = base + off - VMT_SELF  # candidate VMT whose self pointer lives here
        if struct.unpack_from("<I", image, off)[0] != vmt or not in_text(vmt):
            continue
        name_ptr = u32(vmt + VMT_CLASS_NAME)
        if not in_text(name_ptr):
            continue
        name = shortstr(name_ptr)
        if not name.isidentifier():
            continue
        methods = []
        table = u32(vmt + VMT_METHOD_TABLE)
        if table and in_text(table):
            count = u16(table)
            p = table + 2
            for _ in range(count):
                size = u16(p)
                addr = u32(p + 2)
                methods.append((shortstr(p + 6), addr))
                p += size
        fields = []
        table = u32(vmt + VMT_FIELD_TABLE)
        if table and in_text(table):
            # Field table: count (word), class table pointer, then {offset dword, class index word, name}.
            count = u16(table)
            p = table + 6
            for _ in range(count):
                offset = u32(p)
                fname = shortstr(p + 6)
                fields.append((fname, offset))
                p += 6 + 1 + len(fname)
        parent_ptr = u32(vmt + VMT_PARENT)
        parent = shortstr(u32(u32(parent_ptr) + VMT_CLASS_NAME)) if parent_ptr and in_text(parent_ptr) else ""
        classes[name] = (vmt, parent, methods, fields)

    lines = [f"# Delphi published methods in {exe}", ""]
    for name in sorted(classes):
        if wanted and name not in wanted:
            continue
        vmt, parent, methods, fields = classes[name]
        if not methods and not wanted:
            continue
        lines.append(f"## {name} (VMT 0x{vmt:x}, parent {parent})")
        lines += [f"- `{m}` 0x{a:x}" for m, a in sorted(methods, key=lambda x: x[1])]
        if fields:
            lines.append("")
            lines.append("Fields (instance offset):")
            lines += [f"- `+0x{o:x}` {f}" for f, o in sorted(fields, key=lambda x: x[1])]
        lines.append("")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"{len(classes)} classes, {sum(1 for c in classes.values() if c[2])} with published methods")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], set(sys.argv[3:]))
