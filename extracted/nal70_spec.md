# НАЛОГ 70 — БАРАЊЕ ЗА ПЛАЌАЊЕ НА ЈАВНИ ДАВАЧКИ И ЗА ПЛАЌАЊА ПОМЕЃУ БУЏЕТСКИ КОРИСНИЦИ (TNAL70)

Recovered from `forms/TNAL70.dfm`, `asm/TNAL70/` and the opener `TVNNAL.JvSpeedButton3Click`.
Same rules as Налог 60 (`nal60_spec.md`) except where listed.

## Layout differences
- Payer side: **no** Трезорска сметка field (but `smetzadolz` is still saved as `init.trezsmet`);
  shows **Единствен даночен број** = `init.edb` (read-only).
- No Повикување на број – одобрување.
- Recipient side: Назив и седиште на примач (partner `naziv`, `mesto`), then a block with
  **Уплатна сметка** (15 chars, upper case, editable), **Сметка на буџетски корисник – примач** (partner `ziro`, read-only),
  **Приходна шифра** (6 digits), **програма** (2 chars, upper case).
- Tab order: partner, valuta, dospevanje, расходно конто, програма, цел ×2, уплатна сметка, приходна шифра, програма на примач,
  износ, датум и место на поднесување.

## Saved row (`dodaj`)
As Налог 60 plus: `edb = init.edb`, `podsmetprim = Уплатна сметка`, `konprim = Приходна шифра`, `progprim = програма на примач`,
**`nacin = '3'`** (60/62 use '2'), `vidobr = '70'`. `povik1` is not written.
Required on save (old app): valuta, расходно конто, програма, цел (line 1), partner — the recipient block is optional.

## Editing (`JvXPButton4Click`)
`update promet set konzadolz, progzadolz, celdoz1, celdoz2, smetprim, nazprim1, nazprim2, podsmetprim, konprim, progprim,
iznos, datpod, mespod, valdat, sifprim, datdos, dosdat where pratka, rbr, datkniz` — `edb` is not rewritten.
New app: exactly the selected row (RDB$DB_KEY).

## Mixing
Old app: refused when the shipment has 62 orders („ВО ОВАА ПРАТКА ИМА НАЛОЗИ 62").
**New app (user decision): 70 may share a shipment with 62.**

New-app changes shared with Налог 60: Датум на доспевање required, deni always 00.
