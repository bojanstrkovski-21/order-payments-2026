# НАЛОГ 60 — БАРАЊЕ ЗА ПЛАЌАЊЕ кон небуџетски институции (TNAL60)

Recovered from `forms/TNAL60.dfm`, `asm/TNAL60/` and the opener `TVNNAL.JVSpeedButton1Click`.

## Opening a new order (from the shipment screen)
- Refused when the shipment already contains a 62 order: „ВО ОВАА ПРАТКА ИМА НАЛОЗИ 62".
- `rbr` = last `rbr` of the shipment (ordered by rbr) + 1, zero-padded to 6; 1 for an empty shipment.
- Pre-filled: Трезорска канцеларија = `init.trzkan`; Трезорска сметка = `init.trezsmet`;
  Сметка на буџетски корисник = `smetki.smetbukor` of the shipment account; Назив и седиште = `init.naziv`, `init.mesto`;
  Датум на валута = **tomorrow**; Датум на поднесување = today; Место на поднесување = `init.mesto`; deni = „00".
- Buttons: ПОНАТАМУ (save, clear, next order), КРАЈ (save and close), ОТКАЗ (close without saving).

## Fields (tab order)
| # | Field | Column | Rule |
|---|---|---|---|
| 0 | Шифра на партнер (4 digits) | `sifprim` | Empty → open the partner register. Unknown → „НЕМА ТАКОВ ДЕЛОВЕН ПАРТНЕР". Found → Сметка на примач = `partneri.ziro`, Назив = `naziv`, Седиште = `mesto` (display only). |
| 1 | Датум на валута | `valdat` | Required („ВНЕСЕТЕ ДАТУМ"), valid („НЕИСПРАВЕН ДАТУМ"). |
| 2 | Датум на доспевање | `datdos`, `dosdat` | Old app: optional (empty → `datdos` NULL, `dosdat` ''). **New app: required** („ВНЕСЕТЕ ДАТУМ") — user decision, the old behaviour was a bug. `dosdat` = yyyymmdd. |
| 3 | Расходно конто (6 digits) | `konzadolz` | Required. |
| 4 | Програма (2 chars, upper) | `progzadolz` | Required. |
| 5–6 | Цел на дознака (2 × 35) | `celdoz1`, `celdoz2` | Line 1 required. |
| 7–8 | Износ: денари + дени | `iznos` | Old app: deni „00" or „50" („ВНЕСЕТЕ 00 ИЛИ 50"). **New app: deni always 00** (fixed, read-only; user decision) — whole denars, empty/zero → „ВНЕСЕТЕ ИЗНОС". |
| 9 | Повикување на број – одобрување (24) | `povik1` | |
| 11 | Датум на поднесување | `datpod` | Required. |
| 12 | Место на поднесување | `mespod` | |
Missing required values on save → „ВНЕСЕТЕ ВРЕДНОСТИ". The second „повикување" box (`Edit12`) is disabled and never saved.

## Saved row (`dodaj`)
`slvid='2'`, `nacin='2'`, `sifra='000000'`, `vidobr='60'`, `smetzadolz=init.trezsmet`, `podsmetzadolz=smetbukor`,
`smetprim/nazprim1/nazprim2` from the partner, `pratka`/`datkniz` = the shipment, `sifsmet` = shipment account.
Columns not written: `podsmetprim, konprim, progprim, edb, brkniz`.

## Editing (АЖУРИРАЈ, `JvXPButton4Click`)
`update promet set konzadolz, progzadolz, celdoz1, celdoz2, smetprim, nazprim1, nazprim2, iznos, povik1, datpod, mespod,
valdat, sifprim, datdos, dosdat where pratka, rbr, datkniz`. **New app:** updates exactly the selected row (RDB$DB_KEY),
because `rbr` is duplicated in 308 shipments.
