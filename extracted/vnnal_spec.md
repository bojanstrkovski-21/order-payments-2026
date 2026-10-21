# ВНЕСУВАЊЕ НА НАЛОЗИ (TVNNAL) — behaviour of the old app

Recovered from `forms/TVNNAL.dfm` and the handler listings in `asm/TVNNAL/`
(addresses from `app_methods.md`). Messages are quoted exactly.

## Shipment header (Panel1)

| Field | Control | Rule |
|---|---|---|
| Шифра на сметка | `sifsmet` (2 digits) | Empty → leave the screen. Else `select * from smetki where sifra=:sif`; not found → message, stay in field; found → show `SMETBUKOR` next to it (`Label3`). |
| Пратка бр. | `brprat` (1 char, upper case) | Empty → message, stay in field. |
| Датум на валута | `MaskEdit1` (dd/mm/yyyy) | Empty → „ВНЕСЕТЕ ДАТУМ"; invalid → „НЕИСПРАВЕН ДАТУМ". Stored as the shipment date (global `0x808fe0`). |

After the date (`MaskEdit1Exit`):
1. `select * from kniz where (pratka=:prat) and (datkniz=:dkniz)`. If a row exists the shipment is **booked**:
   all action buttons are disabled except printing, and the message
   „ОВАА ПРАТКА Е ПРОКНИЖАНА. ДОЗВОЛЕН Е САМО ПРЕГЛЕД И ПЕЧАТЕЊЕ!" is shown.
   If `kniz.sifsmet` ≠ the entered account → „ОВАА ПРАТКА Е ОД ДРУГА СМЕТКА", header is cleared.
2. `select * from promet where (pratka=:prat) and (datkniz=:dkniz) order by rbr`.
   If the first order's `sifsmet` ≠ entered account → „ОВАА ПРАТКА Е ОД ДРУГА СМЕТКА".
3. `soberi`: total = sum of `IZNOS`; grid footer shows „Vkupno :" and the total; record count shown.
4. Header disabled, action bar (Panel2) and grid shown.

Esc in the grid resets the screen to an empty header.

## Grid columns (SMDBGrid1)

ВИД НА НАЛОГ (`vidobr`), ШИФРА НА ПРИМАЧ (`sifprim`), НАЗИВ НА ПРИМАЧ (`nazprim1`), СЕДИШТЕ НА ПРИМАЧ (`nazprim2`),
ИЗНОС, СМЕТКА НА ПРИМАЧ (`smetprim`), ПОДСМЕТКА НА ПРИМАЧ (`podsmetprim`), КОНТО (`konzadolz`), ПРОГРАМА (`progzadolz`),
ЦЕЛ НА ДОЗНАКА (`celdoz1`), КОНТО НА ПРИМАЧ (`konprim`), ПРОГ. НА ПРИМАЧ (`progprim`), ДАТУМ НА ВАЛУТА (`valdat`),
ДАТУМ НА ПОДНЕС. (`datpod`), ДАТУМ НА ДОСПЕВАЊЕ (`datdos`).

## Action bar (Panel2)

| Button | Handler | Behaviour |
|---|---|---|
| Налог 60/61/62/70/73/76/80 | `JVSpeedButton1Click`… | Open the order form of that type for this shipment (TNAL60…TNAL80). *Not yet analysed.* |
| Копирање | `JvSpeedButton11Click` → GroupBox2 | Copy orders from another shipment (see below). |
| Ажурирање | `JvSpeedButton5Click` | Edit the selected order in its form. *Not yet analysed.* |
| Бришење | `JVSpeedButton6Click` | Confirm „ОВОЈ ЗАПИС ЌЕ БИДЕ ИЗБРИШАН !" (ОК / Не); delete the current order; subtract its amount from the total. |
| Книжење | `JVSpeedButton7Click` → GroupBox3 | No orders → „НЕМА НИШТО ЗА КНИЖЕЊЕ". Else ask Датум на поднесување, Датум на валута, Плата (Д/Н). |
| Печатење | `JVSpeedButton8Click` → GroupBox1 | Print-outs, see below. |
| Сними | `JvSpeedButton9Click` | Save to file (SaveDialog). *Not yet analysed.* |
| Излез | `JVSpeedButton10Click` | Close. |

### Printing (`JVSpeedButton8Click`, `JvXPButton1Click`, `QuickRep1/2/3`)
Dialog „PE^ATEWE": Br. na kopii (empty → „ВНЕСЕТЕ БРОЈ НА КОПИИ"); Вид „Spisok"/„Specifikacija" only matters for
salary shipments. If the shipment has any order of type 60/61/70/73/76/80 → **QuickRep1** „СПЕЦИФИКАЦИЈА на трезорски
налози од пратка бр. X за ден": header company name (`init.naziv`), page, ТРЕЗОРСКИ КОД НА КОРИСНИК (`init.trzkodkor`),
ТРЕЗОРСКА СМЕТКА (`init.trezsmet`), ПОДСМЕТКА НА КОРИСНИК (shipment account `smetbukor`); one row per order: р.бр.,
цел (2 lines), расх. конто, програма, назив на примач + жиро-сметка и подсметка, прих. конто (`konprim`), износ;
„Вкупен износ" and „О д о б р и л". Otherwise (only 62): „Specifikacija" → **QuickRep2** from the stored procedure
`specif(sifsmet, pratka, date)` (per vidobr, konto, programme, bank = first 3 digits of the recipient account: count,
sum; cel = `konta.opis`), „Spisok" → **QuickRep3** landscape „СПИСОК": шифра, име и презиме, трансакциона сметка,
цел, износ. The old „за ден" label never showed the date.

**New app** (`reports.py`): same three print-outs as HTML in the wx print preview (Print button, page setup,
copies, landscape for Список), with the date after „за ден" and page numbers in the footer. The salary specification
is computed from the shipment's own orders: `SPECIF` selected by `valdat` = shipment date and missed orders whose
value date differs (61 unbooked 62 orders in the data). Printing stays allowed for booked shipments.

### Copy (`JvSpeedButton11Click`, `brpr1Exit`, `MaskEdit2Exit`, `JvXPButton3Click`)
Dialog „KOPIRAWE" — „SO OVAA AKCIJA SE VR[I KOPIRAWE NA PODATOCITE OD PRATKATA KOJA ]E JA NAVEDITE !":
Пратка бр. (empty → „ВНЕСЕТЕ БРОЈ НА ПРАТКА!") and Датум на валута (empty → „ВНЕСЕТЕ ДАТУМ", invalid → „НЕИСПРАВЕН ДАТУМ").
The source must be a **booked** shipment (`kniz` row), else „НЕ ПОСТОИ ТАКВА ПРАТКА!".
For every source order (`order by rbr`) an insert copies all columns positionally (the query's field order equals the
insert column order) except: `pratka` = current shipment, `datkniz` = `valdat` = current shipment date,
`datpod` = today, `brkniz` = ''. `datdos`/`dosdat` are not in the insert (copies have no due date). `rbr` is copied as is.

**New app** (`db.copy_shipment`, `ShipmentPanel.copy_refusal`): one transaction; copies are numbered after the current
shipment's last `rbr` (the old copy duplicated numbers); refused when the source belongs to another account
(„ОВАА ПРАТКА Е ОД ДРУГА СМЕТКА"), is the same shipment, has no orders, or would break the 62/70 mixing rule.

### Delete — old behaviour and the fix
Old SQL (`IBUpdateSQL4.DeleteSQL`): `delete from promet where pratka, datkniz, vidobr, iznos, sifprim, sifsmet` match.
In the live data 876 groups of orders are identical on those columns and 308 shipments contain duplicate `rbr`,
so the old delete could remove several orders. **New app:** deletes exactly one row via `RDB$DB_KEY`.

### Booking (`JvXPButton5Click`)
Inputs: Датум на поднесување (`MaskEdit3`), Датум на валута (`MaskEdit4`), Плата (`Edit1`, „Д" or „Н";
otherwise „ВНЕСЕТЕ Д ЗА НАЛОЗИ ОД ПЛАТА ИЛИ Н ЗА ДРУГИ НАЛОЗИ"; empty → „ВНЕСЕТЕ ДАЛИ НАЛОЗИТЕ СЕ ОД ПЛАТА").

1. `yy` = last two digits of **today's** year.
2. `select * from kniz where knizbr like :kkb order by knizbr` with `kkb = '%%%%' + yy`; take the last row.
   If none, or its `knizbr[4:6]` ≠ `yy` → sequence 1, else sequence = int(`knizbr[0:4]`) + 1.
3. `knizbr` = sequence zero-padded to 4 digits + `yy` (e.g. `001226`).
4. `insert into kniz (pratka, datkniz, ddd, vkupnal, iznos, knizbr, sifsmet)` with
   datkniz = new valuta date, ddd = valuta as `yyyymmdd`, vkupnal = number of orders, iznos = total.
5. Message „ПРОКНИЖАНО ПОД БРОЈ 0012-26!".
6. Orders: Плата = Н → `update promet set brkniz, valdat=valuta, datpod=podnes, datkniz=valuta where pratka and datkniz=old shipment date`.
   Плата = Д → same plus `datdos=valuta, dosdat=valuta as yyyymmdd`.
7. Screen resets to an empty header.

The new app does steps 2–6 in one transaction (the old app inserted `kniz` before the message).
