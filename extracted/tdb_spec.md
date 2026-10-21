# СНИМИ — „FORMAT ZA TREZOR" (*.TDB), the payment-order file for the treasury

Recovered from `TVNNAL.JvSpeedButton9Click` and verified against files the old program saved:
`app/tdb.py` reproduces them **byte for byte** (19 of 19 files whose shipment is unchanged in the database;
`tools/compare_tdb.py`). The real files contain personal data and are not part of the repository.

## Rules
- Only for a **booked** shipment (`kniz` row), otherwise „ОВАА ПРАТКА НЕ Е ПРОКНИЖАНА". Done → „ПОДАТОЦИТЕ СЕ СНИМЕНИ".
- File name `N` + dd + mm + yy (of the shipment date) + shipment number, extension = `init.trzkodkor`
  (e.g. `N0510266.TDB`); dialog filter „FORMAT ZA TREZOR (*.TDB) |*.TDB".
- ASCII text in the **MAC C** encoding, **CRLF** after every line (also the last), one header line, then one line per
  order of the shipment in `rbr` order, numbered 1…n.
- CHAR columns are written **with their trailing spaces** (as IBX `AsString` returned them); NULL is empty.
  „Zero-padded" fields are padded only when shorter than their width (i.e. NULL/empty in practice).

## Header (291 characters)
`1` + `init.trzkodkor` (3) + `init.trzinskod` (3) + `kniz.ddd` (8, yyyymmdd) + `kniz.pratka` (1) +
`kniz.vkupnal` zero-padded (6) + sign (`+`/`-`) + `kniz.iznos` (18) + 250 spaces.
(The payroll program writes the same 41-character core without the 250 spaces.)

## Order line (299 characters; 291 when the due date is empty)

| Pos | Width | Content |
|---|---|---|
| 1 | 1 | `slvid` (`2`) |
| 2 | 6 | running number, `%6.6d` |
| 8 | 15 | `smetzadolz` |
| 23 | 15 | `podsmetzadolz` |
| 38 | 6 | `konzadolz` |
| 44 | 2 | `progzadolz`, zero-padded left |
| 46 | 70 | `celdoz1` (35) + space + `celdoz2`, cut to 70 |
| 116 | 6 | `sifra` |
| 122 | 1 | sign of `iznos` |
| 123 | 18 | `iznos`: `%18.2f` of the absolute value, spaces → `0`, `.` → `,` |
| 141 | 18 | `smetprim` as a number, `%18.0f`, spaces → `0` |
| 159 | 70 | `nazprim1` (35) + space + `nazprim2`, cut to 70 |
| 229 | 15 | `podsmetprim`, padded with spaces |
| 244 | 6 | `konprim`, zero-padded left |
| 250 | 2 | `progprim`, zero-padded left |
| 252 | 24 | `povik1`, padded with spaces |
| 276 | 2 | `vidobr` |
| 278 | 1 | `nacin` |
| 279 | 13 | `edb`, zero-padded left |
| 292 | 8 | `dosdat` (yyyymmdd) — only when set |

The old routine has a negative and a positive branch that differ only in the sign character.
