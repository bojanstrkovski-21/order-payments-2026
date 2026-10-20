r"""Split a saved REA batch_decompile result into one .c file per function.

Usage:  python -I tools\save_decomp.py <batch_result.json> <out_dir> [name=0xaddr ...]
Names map addresses to handler names (e.g. sifsmetExit=0x74a68c) for the file names.
"""
import json
import sys
from pathlib import Path


def main(result_path, out_dir, pairs):
    names = {addr.lower(): name for name, addr in (p.split("=") for p in pairs)}
    data = json.loads(Path(result_path).read_text(encoding="utf-8"))
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for item in data["normalized_result"]["items"]:
        addr = item.get("address", "?").lower()
        code = item.get("pseudocode")
        if code is None:
            code = json.dumps(item, ensure_ascii=False, indent=1)
        name = names.get(addr, addr)
        (out / f"{name}_{addr}.c").write_text(code, encoding="utf-8")
        print(f"{name:24} {addr}  {len(code.splitlines())} lines")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3:])
