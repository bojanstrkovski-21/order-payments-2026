# NOVNAL rewrite — project memory

Rewrite of the old Delphi payment-order program **NOVNAL.exe („ТРЕЗОР")** as a modern app.
The old program has no source code; its behaviour is recovered by reverse engineering and written down
in `extracted/*_spec.md`. The repository is **public** — never commit personal data or passwords.

## Stack and layout

- **Python 3.14 + wxPython 4.3** (Office 2010 style `wx.ribbon`), Firebird via the pure-Python `firebirdsql` driver.
  Virtual environment: `demo/.venv` (wxPython, firebirdsql, passlib, pefile, capstone, fonttools, pillow).
- `app/` — the new program: `main.py` (window + ribbon), `shipment.py` (ВНЕСУВАЊЕ НА НАЛОЗИ), `reports.py` (print-outs), `orders.py` (all order
  forms), `db.py` (all database access), `macc.py` (MAC C ↔ Cyrillic), `workdays.py` + `holidays.txt`, `ui.py`.
- `tools/` — reverse-engineering helpers and the tests (`test_*.py`).
- `extracted/` — recovered specifications (`vnnal_spec.md`, `nalXX_spec.md`), schema, SQL lists, handler map.
  Raw decompiled code/listings/form dumps (`extracted/asm|decomp|forms`) stay local (gitignored).
- Local only (gitignored): `Nalozi/` (old program + data), `work/` (database copies), `app/settings.ini`, `.mcp.json`.

Run the app: `cd app` → `..\demo\.venv\Scripts\python.exe main.py`
Settings: copy `app/settings.example.ini` to `app/settings.ini` and fill in the database path and login.

## Databases

- The old program keeps using `D:\nalozi\NOVNAL.FDB` (Firebird 2.1 on this PC). **Never write to it.**
- The new app has its **own** database: `D:\My Backups\Bojan\nalozi-26\NOVNAL.FDB` (a gbak copy of the live one,
  10 blank partner rows removed). Copy the live database only through `gbak -b -g` (read-only), never by file copy.
- Old schema quirks: text is stored in the **MAC C** font encoding (ASCII drawn as Cyrillic by the „MAC C Swiss"
  font; `` ` ~ { } | q w x y c j `` = ж ч ш ќ ѓ љ њ џ ѕ ц ј) — `macc.py` converts both ways. Amounts are `FLOAT`.
  No primary keys and duplicate rows/`rbr` exist, so single-row update/delete uses `RDB$DB_KEY` (`db.py`).
- **firebirdsql pitfall:** a `SELECT` followed by an `UPDATE`/`DELETE` on the same connection can fail intermittently
  (`op_code = 66`, a late fetch answer). Find the row inside the changing statement (`db._one_row`) and read results
  with `db._first` (drains the cursor), never `fetchone()`. Run the suite several times in a row after DB changes.
- **First version: a one-PC database → SQLite** (user decision 2026-10-21). The move from Firebird comes after the
  screens are rebuilt; only `db.py` changes. Text becomes real Unicode Cyrillic in SQLite; the USB file is still MAC C.

## Decisions by the user (differences from the old program)

- **Датум на валута** = the day the payment goes through the treasury and reaches the recipient.
  Default = next working day after **Датум на поднесување**; it follows the submission date until changed by hand.
- **Non-working days**: weekends; fixed 31.12, 01.01, 06.01, 07.01, 01.05, 24.05, 02.08, 28.08, 08.09, 11.10, 23.10,
  08.12; from Orthodox Easter (calculated): Велики Петок, Велигден Monday, Духовден (Friday before Pentecost);
  **Рамазан Бајрам** (first day) entered each year in `app/holidays.txt`; a holiday on Sunday → next Monday off.
  Водици and Курбан Бајрам are working days. The user gets the ministry's list at the end of each year.
- **Датум на доспевање** = the order's due date: required on all forms, **optional only on Налог 61**
  (the old 61 form had no such field).
- **Amounts are whole denars**: deni fixed at 00 (old orders keep stored deni when edited).
- **62 and 70 may share a shipment**; other types stay separated from 62 (`orders.mixing_error`).
- **Налог 73** is filed under its shipment like every other type (old program swapped valdat/datkniz).
- Delete/edit change exactly one row (the old delete could remove several identical orders).
- **Копирање**: copies get no Датум на доспевање (as the old program) — the user sets the dates on each copy.
- The **USB payment file** („Сними") must stay in the old MAC C encoding — encode with `macc.encode` on export.

## How to work

- **Run the tests right after every change**, on a fresh throwaway copy of the database, before reporting done:
  restore `work/db/novnal_for_nalozi26.fbk` with `gbak -c` to a scratch `TEST.FDB`, point a `test_settings.ini` at it,
  run every `tools/test_*.py <test_settings.ini>`. Report failures honestly.
- Reverse engineering: `tools/delphi_methods.py` (event handlers + field offsets from the Delphi VMTs),
  `tools/delphi_listing.py` (Capstone listing with field names and strings — Ghidra misses many Delphi handlers and
  REA cannot create functions on Windows), `tools/param_map.py` (which value goes into which SQL parameter).
  Confirm findings against the real data before relying on them.
- REA MCP + Ghidra 12.1.4 are configured in `.mcp.json` (local, read-only Windows mode). Reopen the old program
  quickly with `open_binary` path `Nalozi\NOVNAL.exe` + `snapshot_path` `work\rea\novnal_exe.snapshot` (local).
- Git: branch `main` → https://github.com/bojanstrkovski-21/order-payments-2026 (public, MIT `LICENSE` on `main`).
  **The user commits and pushes** with `.\push.ps1 "message"` (pull, add all, commit, push to `main`).
  Claude does **not** commit or push; it leaves the changes in the working tree and tells the user when to push.
  push.ps1 commits everything not in `.gitignore`, so before saying „you can push", check that no database files,
  passwords or real names/accounts/EMBG would be committed.

## Session rules (user's)

- **start-session** (`/start-session`): sync with GitHub (`git pull`), check the setup, run the tests, then give a
  short summary of where the project stands and continue.
- **end-session** (`/end-session`): write memory (this file + Claude's private notes, kept in sync), close the
  REA/Ghidra target with a snapshot, check nothing sensitive would be committed, then tell the user they can run
  `.\push.ps1` with a suggested commit message.

## Progress

Done and tested: main window, shipment screen (open, delete, booking, **копирање**, **печатење**), **all 7 order forms** (60, 61, 62,
70, 73, 76, 80), working-day defaults.
Next: **Сними** (USB file, byte-identical to the old program's),
then the registers (partners, employees, accounts), reports, login/operators, Превземање на налози, the move to
SQLite, and finally a custom theme.

## Keeping this file current

This file is the canonical project record. Claude also keeps private notes outside the repository (credentials,
personal-data warnings, machine state) — update both together when anything changes, and never let them contradict.
