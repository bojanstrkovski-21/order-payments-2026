# NOVNAL rewrite — project memory

Rewrite of the old Delphi payment-order program **NOVNAL.exe („ТРЕЗОР")** as a modern app.
The old program has no source code; its behaviour is recovered by reverse engineering and written down
in `extracted/*_spec.md`. The repository is **public** — never commit personal data or passwords.

## Stack and layout

- **Python 3.14 + wxPython 4.3** (Office 2010 style `wx.ribbon`), Firebird via the pure-Python `firebirdsql` driver.
  Virtual environment: `demo/.venv` (wxPython, firebirdsql, passlib, pefile, capstone, fonttools, pillow).
- `app/` — the new program: `main.py` (window + ribbon), `shipment.py` (ВНЕСУВАЊЕ НА НАЛОЗИ), `orders.py` (all order
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
- Later: possible move to SQLite (one PC) or PostgreSQL (several users) — waiting for the user's answer.

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
- The **USB payment file** („Сними") must stay in the old MAC C encoding — encode with `macc.encode` on export.

## How to work

- **Run the tests right after every change**, on a fresh throwaway copy of the database, before reporting done:
  restore `work/db/novnal_for_nalozi26.fbk` with `gbak -c` to a scratch `TEST.FDB`, point a `test_settings.ini` at it,
  run every `tools/test_*.py <test_settings.ini>`. Report failures honestly.
- Reverse engineering: `tools/delphi_methods.py` (event handlers + field offsets from the Delphi VMTs),
  `tools/delphi_listing.py` (Capstone listing with field names and strings — Ghidra misses many Delphi handlers and
  REA cannot create functions on Windows), `tools/param_map.py` (which value goes into which SQL parameter).
  Confirm findings against the real data before relying on them.
- REA MCP + Ghidra 12.1.4 are configured in `.mcp.json` (local, read-only Windows mode).
- Git: branch `main` → https://github.com/bojanstrkovski-21/order-payments-2026 (public). Commit and push after each
  finished piece; check that no database files, passwords or real names/accounts/EMBG are staged.

## Progress

Done and tested: main window, shipment screen (open, delete, booking), **all 7 order forms** (60, 61, 62, 70, 73, 76,
80), working-day defaults.
Next: Копирање, Печатење („Список", „Спецификација"), **Сними** (USB file, byte-identical to the old program's),
then the registers (partners, employees, accounts), reports, login/operators, Превземање на налози, the database move.
