# НАЛОГ 73 — БАРАЊЕ ЗА БЕЗГОТОВИНСКИ ПОВРАТ НА СРЕДСТВА (TNAL73)

Recovered from `forms/TNAL73.dfm`, `asm/TNAL73/` (`tools/param_map.py`) and the opener `TVNNAL.JvSpeedButton13Click`.

## Layout
- Top: Трезорска канцеларија, Датум на валута (`vd73`, default tomorrow), Датум на доспевање, Образец 73. **No register code.**
- Payer block (`Panel1`): Трезорска сметка (`init.trezsmet`), Сметка на буџетски корисник (shipment account `smetbukor`),
  **Приходно конто** (6) → `konzadolz`, **Потпрограма** (2) → `progzadolz`. „Уплатна сметка" is shown read-only and never
  filled or saved → left out.
- Назив и седиште на буџетски корисник (`init.naziv`, `init.mesto`); Цел на дознака (2 × 35).
- Recipient, **typed in**: Сметка на примач (15) → `smetprim`, Назив и седиште (35 + 20) → `nazprim1/2`,
  Единствен даночен број (13) → `edb`; block (`Panel2`): Сметка на буџетски корисник – примач (18) → `podsmetprim`,
  Расходно конто / приходно конто (6) → `konprim`, Потпрограма (2) → `progprim`.
- Износ, Повикување (24) → `povik1`, Датум и место на поднесување (`dp73`, default today; `init.mesto`).

## Saved row (`dodaj`)
`slvid='2'`, `nacin='2'`, `sifra='000000'`, `vidobr='73'`, `sifprim` = 4 spaces (no register), `smetzadolz = init.trezsmet`,
`podsmetzadolz` = shipment budget account, `sifsmet` = shipment account, `pratka` = shipment.
Required (old app): Датум на валута, Приходно конто, Потпрограма, Сметка на примач, Назив на примач, Цел на дознака.

**Dates — old app:** `valdat` = the *shipment* date, `datkniz` = the form's Датум на валута (`vd73`). So the order was
filed under a different date than its shipment whenever the two differed (79 of 101 real 73 orders), and disappeared
from the shipment it was entered in.
**New app:** like every other order type — `datkniz` = shipment date (the order stays in its shipment),
`valdat` = the form's Датум на валута. (Pending user confirmation.) Existing orders are not changed.

## Editing (`JvXPButton4Click`)
Updates `podsmetzadolz, konzadolz, progzadolz, celdoz1, celdoz2, smetprim, nazprim1, nazprim2, edb, podsmetprim, konprim,
progprim, iznos, povik1, datpod, mespod, valdat, datdos, dosdat`. New app: exactly the selected row.

New-app changes shared with the other forms: Датум на доспевање required, deni always 00.
