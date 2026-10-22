# NOVNAL rewrite — project memory

Rewrite of the old Delphi payment-order program **NOVNAL.exe („ТРЕЗОР")** as a modern app.
The old program has no source code; its behaviour is recovered by reverse engineering and written down
in `extracted/*_spec.md`. The repository is **public** — never commit personal data or passwords.

## Stack and layout

- **Python 3.14 + wxPython 4.3** (Office 2010 style `wx.ribbon`), Firebird via the pure-Python `firebirdsql` driver.
  Virtual environment: `demo/.venv` (wxPython, firebirdsql, passlib, pefile, capstone, fonttools, pillow).
- `app/` — the new program: `main.py` (window + ribbon), `shipment.py` (ВНЕСУВАЊЕ НА НАЛОЗИ), `reports.py` (print-outs), `tdb.py` (USB file), `registers.py` (Шифрарник), `orders.py` (all order
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
- **Every print-out** (shipment print-outs, register lists, reports): **Печати** through the Windows dialog (any
  installed printer, incl. Microsoft Print to PDF / Adobe PDF) **and** the program's own **„Сними како PDF"**
  (`reports.Report` → `to_html` / `to_pdf`, fpdf2 with Segoe UI; reports also Excel where planned).
- **Registers — new fields the old program lacked** (only in the new app's database; `db.ensure_schema()` adds them
  at startup and refuses to run against `D:
alozi`):
  - Institution (`INIT`, screen ГЕНЕРАЛИИ): add **ЕМБС** and **e-mail addresses — two general school addresses and
    one for the finance and accounting department**. Today `INIT` has naziv, adresa, mesto, telefon (9 chars), edb,
    trezsmet, trzkan, trzkodkor, trzinskod.
  - Accounts (`SMETKI`, screen СМЕТКИ): add a **name/description per account** so the user knows which is which;
    show it next to the code wherever an account is chosen or printed.
- The **USB payment file** („Сними", `tdb.py`) stays in the old MAC C encoding and is byte-identical to the old
  program's files (`extracted/tdb_spec.md`; check with `tools/compare_tdb.py` against real files kept outside the repo).

## How to work

- **Run the tests right after every change**, on a fresh throwaway copy of the database, before reporting done:
  restore `work/db/novnal_for_nalozi26.fbk` with `gbak -c` to a scratch `TEST.FDB`, point a `test_settings.ini` at it,
  run every `tools/test_*.py <test_settings.ini>` with `python -I -X utf8` (`-I` ignores `PYTHONIOENCODING`; without
  `-X utf8` Cyrillic output to a log file fails). Report failures honestly.
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

Done and tested: main window, shipment screen (open, delete, booking, **копирање**, **печатење**, **сними**), **all 7 order forms** (60, 61, 62,
70, 73, 76, 80), working-day defaults.
The shipment screen is complete (every old button rebuilt).
Шифрарник: **ГЕНЕРАЛИИ** (old fields + ЕМБС + 3 e-mails) and **СМЕТКИ** (name per account; add, edit, delete only when
unused, code change refused when used, search, Печати / PDF) done and tested (`tools/test_registers.py`). The account
name is shown next to the account on the shipment screen and on the print-outs; an empty account code opens СМЕТКИ to
choose from (as the old program did).
**КОНТА register done and tested (2026-10-22)**: ribbon Шифрарник → Конта (`registers.KontaDialog` / `KontoDialog`, `konta.py`,
`db.list_konta/save_konto/delete_konto/load_konta`, new column `KONTA.OPISFULL`; search in the full name, class 4/7 filter,
full name of the selection shown under the list, add / edit / delete only when unused / code change refused when used,
Печати / PDF; tests in `tools/test_registers.py`). The seed is loaded once per database with
`PYTHONPATH=app python -X utf8 tools\load_konta_seed.py [settings.ini]` (adds missing konta, never touches existing ones) —
**run on the real new database on 2026-10-22** (982 added, the 3 old konta unchanged; backup of the database before the load:
`work/db/new_db_before_konta.fbk`, local). The old MAC C encoding cannot hold Latin letters, so «COVID» / «Д-Е V» are written
with Cyrillic letters in the seed (`db._encodable` refuses any text that does not round-trip).
**КОНТА phase — decisions 2026-10-21** (`extracted/ministry/` holds the public
ministry PDFs and the seed files; `tools/import_konta.py` builds `konta_seed.csv` and `uplatni_seed.csv`):
- Old program facts (checked in the old forms/asm): `KONTA` = `KONTO CHAR(6)` + `OPIS CHAR(30)`; forms `TTRZKON` = КОНТА
  register, `TTRZSM` = СМЕТКИ register (no payment-account list existed). No order form validates or looks up a konto;
  KONTA is read only by the specification (`SPECIF`, description cut at 30). Цел на дознака = 2 × 35 (`celdoz1/2`) on all
  order types; the old Налог 73 form set no MaxLength on it, so a long text crashed the old program — new forms cap at 35.
- **Opis**: the new КОНТА keeps the **full official name** (`opis_full`, searchable when choosing a konto on an order) and
  the **30-character short form** (word boundary) for the old specification column / цел на дознака. 700 of 985 names are cut.
  `konta_seed.csv` = konto;opis30;opis_full;klasa — 393 rashodi (parsed from the Правилник text layer, MAC C → `macc.decode`)
  and 592 prihodi (the Службен весник PDF is scanned: hand-transcribed in `prihodi_transcribed.txt`; cross-check every
  konto against the payment-account table before loading).
- **УПЛАТНИ СМЕТКИ** (new register; seed `uplatni_seed.csv` = banka;kod;naziv;konto, 366 accounts, hand-transcribed into
  `uplatni_transcribed.txt`, name = the konto's official name, 16 rows have no konto in the PDF; every konto is
  cross-checked against `konta_seed.csv` by `tools/import_konta.py`; verified against the real old data: 2610 of 2627 orders
  with an 11-digit account match exactly, the rest are typos in the old data). Section 6 (customs) is printed as 840-
  though its header mentions element 845 — kept as printed. Register fields: official code
  `840-01013`, name, linked prihoden konto. Stored on orders in `podsmetprim` as ONE 11-digit number without separators =
  bank (840/843) + **3-digit municipality code** + 5-digit official code (`840-01258` → `84010301258`), so the treasury
  recognises it. Used on **Налог 61 and 70 only**; on 73 and 76 the account is a free 15-character entry (institution
  accounts such as `703…`, `660…`, `160…`). The field always stays free text (max 15); the list is a shortcut, a hand-typed
  account is saved as typed (at most a soft warning). Приходна шифра (`konprim`) stays free too and can be picked from КОНТА.
- **ОПШТИНИ** (new register, seed `extracted/ministry/opstini.csv`, 81 municipalities): the middle code is a drop-down from
  it; default `103` = Битола, editable in ГЕНЕРАЛИИ (new field) and per order.
- New accounts next year are added by hand in the КОНТА screen (no „import from new Службен весник" feature).
- Build order: КОНТА screen (done) → ОПШТИНИ → УПЛАТНИ СМЕТКИ → order-form changes (61, 70, 73, 76; pick a konto from КОНТА
  with `KontaDialog(pick=True)`).
Next: the other registers (конта, оператори, жиро-сметки/партнери, вработени), the report
„Преглед на пратки по датум", login/operators, „Превземање на налози", the move to SQLite, and finally a custom theme.

Planned new feature (user, 2026-10-21 — build **after the registers**; the old program had nothing like it):
„**Плаќања по примач**" under Прегледи — (1) one recipient (partner/employee from the register, or name/account search
for Налог 73 which has no code), all payments in a period, with total; (2) all recipients with order count and
total for a period. Output: **export to Excel (.xlsx)**, **export to PDF** (written by the program itself, no printer
needed) and **print** through the Windows print dialog (any installed printer, incl. Microsoft Print to PDF / Adobe PDF).
Period filter: the user chooses Датум на валута / на поднесување / на доспевање in the report.

## Keeping this file current

This file is the canonical project record. Claude also keeps private notes outside the repository (credentials,
personal-data warnings, machine state) — update both together when anything changes, and never let them contradict.
