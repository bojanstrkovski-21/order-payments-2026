-- SQL statements embedded in NOVNAL.exe program code (not in forms).
-- Source: Ghidra string inventory via REA search_strings, application range 0x712000-0x766000.
-- Duplicates removed; the address is the first occurrence. IBX/QuickReport library SQL excluded.
-- See sql_from_forms.sql for the statements stored in the form resources.

-- ===== KORIS (operators / users) =====
-- 0x7124e0
select * from koris order by sifra;
-- 0x712bd0
insert into KORIS (sifra,ime,kod,nivo) values (:sif,:naz,:kd,:niv);
-- 0x7652d8
SELECT * FROM KORIS WHERE SIFRA=:SIF;
-- 0x765414  login check: password compared directly in SQL (plain-text column)
select * from koris where (sifra=:si) and (lozinka=:lo);
-- 0x760e08
update koris set lozinka=:loz where sifra=:sif;
-- 0x7653a8
update koris set lozinka=:loz where (sifra=:sf);

-- ===== INIT (company settings: name, address, tax no., treasury account) =====
-- 0x714c1c
select * from init;
-- 0x71373c
select * from init where sifra=:sif;
-- 0x7151ac
insert into init (naziv,adresa,mesto,telefon,edb,trezsmet,trzkan,trzkodkor,trzinskod) values (:naz,:adr,:mes,:tel,:ed,:trzsm,:trzkan,:trzkodk,:trzinsk);
-- 0x7152e8
UPDATE INIT SET NAZIV=:NAZ, ADRESA=:ADR, MESTO=:MES, TELEFON=:TEL, EDB=:EDBR, TREZSMET=:TRZSM, TRZKAN=:TRZK, TRZKODKOR=:TRKKOR, TRZINSKOD=:TRZINK where NAZIV=:NNAZIV;

-- ===== PARTNERI (business partners) =====
-- 0x75ea00
select * from partneri order by sifra;
-- 0x717688
select * from partneri where sifra=:sif;
-- 0x75f22c
insert into partneri (sifra,naziv,adresa,mesto,telefon,ziro,brlk,embg) values (:sif,:naz,:adr,:mes,:tel,:zir,:brl,:emb);

-- ===== LICA (persons / employees) =====
-- 0x731d3c
select * from lica order by sifra;
-- 0x735858
select * from lica where sifra=:sif;
-- 0x726fd8
select * from lica where embg=:emb;
-- 0x732560
insert into lica (sifra,naziv,adresa,mesto,telefon,transak,brlk,embg) values (:sif,:naz,:adr,:mes,:tel,:tran,:brl,:emb);

-- ===== SMETKI (accounts) =====
-- 0x729e18
select * from smetki order by sifra;
-- 0x72592c
select * from smetki where sifra=:sif;
-- 0x72a3b8
insert into smetki (sifra,smetbukor,podsbukor) values (:sif,:smbkor,:podsmbkor);

-- ===== KONTA (ledger accounts) =====
-- 0x7629ac
select * from konta order by konto;
-- 0x762e14
insert into konta (konto,opis) values (:sif,:opi);

-- ===== KNIZ (booking batches / shipments) =====
-- 0x727b68
select * from kniz where (pratka=:prat) and (datkniz=:dkniz);
-- 0x72dae4
select * from kniz where (datkniz between :pdat and :kdat) and sifsmet=:sifsm order by datkniz;
-- 0x74c094
select * from kniz where knizbr like :kkb order by knizbr;
-- 0x74c12c
insert into kniz (pratka,datkniz,ddd,vkupnal,iznos,knizbr,sifsmet) values (:pratka,:datkniz,:ddd,:vkupnal,:iznos,:knizbr,:sifsmet);

-- ===== SPECIF (stored procedure: batch specification) =====
-- 0x7490c0
select * from specif (:sfsm,:pbr,:dat);

-- ===== PROMET (payment orders) =====
-- 0x719604  (repeated in every order form)
select * from promet where (pratka=:prat) and (datkniz=:dkniz) order by rbr;
-- 0x72f4a0
select * from promet where (brkniz=:bkniz) order by rbr;
-- 0x72f83c
update promet set brkniz=:bkn where (pratka=:pr) and (datkniz=:dkni);
-- 0x74c2c4
update promet set brkniz=:brojkn,valdat=:vdat,datpod=:dpodne,datkniz=:datumval where (pratka=:brprat) and (datkniz=:datkn);
-- 0x74c3c8
update promet set brkniz=:brojkn,valdat=:vdat,datpod=:dpodne,datkniz=:datumval,datdos=:dtdos,dosdat=:dsdat where (pratka=:brprat) and (datkniz=:datkn);

-- Insert/update variants: each order form type writes a different subset of columns.
-- 0x7191a8
insert into promet (slvid,rbr,smetzadolz,podsmetzadolz,konzadolz,progzadolz,edb,celdoz1,celdoz2,smetprim,nazprim1,nazprim2,podsmetprim,konprim,progprim,iznos,datpod,mespod,nacin,sifra,pratka,datkniz,valdat,vidobr,sifprim,sifsmet,datdos,dosdat) values (:slvid,:rbr,:smetzadolz,:podsmetzadolz,:konzadolz,:progzadolz,:edb,:celdoz1,:celdoz2,:smetprim,:nazprim1,:nazprim2,:podsmetprim,:konprim,:progprim,:iznos,:datpod,:mespod,:nacin,:sifra,:pratka,:datkniz,:valdat,:vidobr,:sifprim,:sifsmet,:datdos,:dosdat);
-- 0x71a23c
update promet set konzadolz=:konzad,progzadolz=:przad,celdoz1=:celdz1,celdoz2=:celd2,smetprim=:smprim,nazprim1=:nazp1,nazprim2=:nazp2,podsmetprim=:podm,konprim=:konpr,progprim=:prprim,iznos=:izn,datpod=:dpod,mespod=:mpod,valdat=:vdat,sifprim=:sprim,datdos=:datdos,dosdat=:dosdat where pratka=:prat and rbr=:rb and datkniz=:dkniz;
-- 0x71ddcc
insert into promet (slvid,rbr,smetzadolz,podsmetzadolz,konzadolz,progzadolz,edb,celdoz1,celdoz2,smetprim,nazprim1,nazprim2,podsmetprim,konprim,iznos,datpod,mespod,nacin,sifra,pratka,datkniz,valdat,vidobr,sifprim,sifsmet) values (:slvid,:rbr,:smetzadolz,:podsmetzadolz,:konzadolz,:progzadolz,:edb,:celdoz1,:celdoz2,:smetprim,:nazprim1,:nazprim2,:podsmetprim,:konprim,:iznos,:datpod,:mespod,:nacin,:sifra,:pratka,:datkniz,:valdat,:vidobr,:sifprim,:sifsmet);
-- 0x71ec34
update promet set konzadolz=:konzad,progzadolz=:progzad,celdoz1=:celdo1,celdoz2=:celdo2,smetprim=:smprim,nazprim1=:nazpr1,nazprim2=:nazpr2,podsmetprim=:podsmpr,konprim=:kprim,iznos=:izn,datpod=:dpod,mespod=:mpod,valdat=:vdat,sifprim=:sprim where pratka=:prat and rbr=:rb and datkniz=:dkniz;
-- 0x722a40  (note: binds :podsmetprim into the edb column)
insert into promet (slvid,rbr,smetzadolz,podsmetzadolz,konzadolz,progzadolz,celdoz1,celdoz2,smetprim,nazprim1,nazprim2,edb,iznos,datpod,mespod,nacin,sifra,pratka,datkniz,valdat,vidobr,sifprim,sifsmet,povik1,datdos,dosdat) values (:slvid,:rbr,:smetzadolz,:podsmetzadolz,:konzadolz,:progzadolz,:celdoz1,:celdoz2,:smetprim,:nazprim1,:nazprim2,:podsmetprim,:iznos,:datpod,:mespod,:nacin,:sifra,:pratka,:datkniz,:valdat,:vidobr,:sifprim,:sifsmet,:pov1,:datdos,:dosdat);
-- 0x723a18
update promet set konzadolz=:konzad,progzadolz=:progzad,celdoz1=:celd1,celdoz2=:celd2,smetprim=:smpri,nazprim1=:nazpr1,nazprim2=:nazpr2,edb=:ed,iznos=:izn,datpod=:datp,mespod=:mesp,valdat=:vdat,sifprim=:sifpr,povik1=:pov1,datdos=:dtdos,dosdat=:dsdat where pratka=:prat and rbr=:rb and datkniz=:dkniz;
-- 0x727d44  (same text also at 0x7373ac)
insert into promet (slvid,rbr,smetzadolz,podsmetzadolz,konzadolz,progzadolz,celdoz1,celdoz2,iznos,smetprim,nazprim1,nazprim2,povik1,datpod,mespod,nacin,sifra,pratka,datkniz,valdat,vidobr,edb,sifprim,sifsmet,datdos,dosdat) values (:slvid,:rbr,:smetzadolz,:podsmetzadolz,:konzadolz,:progzadolz,:celdoz1,:celdoz2,:iznos,:smetprim,:nazprim1,:nazprim2,:povik1,:datpod,:mespod,:nacin,:sifra,:pratka,:datkniz,:valdat,:vidobr,:edb,:sifprim,:sifsmet,:datdos,:dosdat);
-- 0x738390
update promet set konzadolz=:konzadol,progzadolz=:progzadol,celdoz1=:celdo1,celdoz2=:celdo2,smetprim=:smetpri,edb=:edb,nazprim1=:nazpri1,nazprim2=:nazpri2,iznos=:izno,povik1=:povi1,datpod=:datpo,mespod=:mespo,valdat=:valda,sifprim=:sifpri,datdos=:datdos,dosdat=:dosdat where pratka=:prat and rbr=:rb and datkniz=:dkniz;
-- 0x73bf58  (same columns as 0x7191a8)
insert into promet (slvid,rbr,smetzadolz,podsmetzadolz,konzadolz,progzadolz,edb,celdoz1,celdoz2,smetprim,nazprim1,nazprim2,podsmetprim,konprim,progprim,iznos,datpod,mespod,nacin,sifra,pratka,datkniz,valdat,vidobr,sifprim,sifsmet,datdos,dosdat) values (:slvid,:rbr,:smetzadolz,:podsmetzadolz,:konzadolz,:progzadolz,:edb,:celdoz1,:celdoz2,:smetprim,:nazprim1,:nazprim2,:podsmetprim,:konprim,:progprim,:iznos,:datpod,:mespod,:nacin,:sifra,:pratka,:datkniz,:valdat,:vidobr,:sifprim,:sifsmet,:datdos,:dosdat);
-- 0x73d040
update promet set konzadolz=:konzad,progzadolz=:przad,celdoz1=:celdz1,celdoz2=:celd2,smetprim=:smprim,nazprim1=:nazp1,nazprim2=:nazp2,podsmetprim=:podm,konprim=:konpr,progprim=:prprim,iznos=:izn,datpod=:dpod,mespod=:mpod,valdat=:vdat,sifprim=:sprim,smetzadolz=:smzad,datdos=:datdos,dosdat=:dosdat where pratka=:prat and rbr=:rb and datkniz=:dkniz;
-- 0x741884
insert into promet (slvid,rbr,smetzadolz,podsmetzadolz,konzadolz,progzadolz,celdoz1,celdoz2,sifra,iznos,smetprim,nazprim1,nazprim2,podsmetprim,konprim,progprim,povik1,vidobr,nacin,edb,valdat,datpod,mespod,pratka,datkniz,sifsmet,sifprim,datdos,dosdat) values (:slvid,:rbr,:smetzadolz,:podsmetzadolz,:konzadolz,:progzadolz,:celdoz1,:celdoz2,:sifra,:iznos,:smetprim,:nazprim1,:nazprim2,:podsmetprim,:konprim,:progprim,:povik1,:vidobr,:nacin,:edb,:valdat,:datpod,:mespod,:pratka,:datkniz,:sfsmet,:SFPR,:datdos,:dosdat);
-- 0x742bf0
update promet set podsmetzadolz=:podsmetzadolz,konzadolz=:konzadolz,progzadolz=:przad,celdoz1=:celdz1,celdoz2=:celd2,smetprim=:smprim,nazprim1=:nazp1,nazprim2=:nazp2,edb=:edb,podsmetprim=:podm,konprim=:konpr,progprim=:prprim,iznos=:izn,povik1=:pov1, datpod=:dpod,mespod=:mpod,valdat=:vdat,datdos=:datdos,dosdat=:dosdat where pratka=:prat and rbr=:rb and datkniz=:dkniz;
-- 0x74a278  (used when taking over orders; writes brkniz)
insert into promet (slvid,rbr,smetzadolz,podsmetzadolz,konzadolz,progzadolz,celdoz1,celdoz2,sifra,iznos,smetprim,nazprim1,nazprim2,podsmetprim,konprim,progprim,povik1,vidobr,nacin,edb,valdat,datpod,mespod,pratka,datkniz,sifprim,brkniz,sifsmet) values (:slvid,:rbr,:smetzadolz,:podsmetzadolz,:konzadolz,:progzadolz,:celdoz1,:celdoz2,:sifra,:iznos,:smetprim,:nazprim1,:nazprim2,:podsmetprim,:konprim,:progprim,:povik1,:vidobr,:nacin,:edb,:valdat,:datpod,:mespod,:pratka,:datkniz,:sifprim,:brkniz,:sifsmet);
-- 0x75b2c8
insert into promet (slvid,rbr,smetzadolz,podsmetzadolz,konzadolz,progzadolz,celdoz1,celdoz2,iznos,smetprim,nazprim1,nazprim2,povik1,datpod,mespod,nacin,sifra,pratka,datkniz,valdat,vidobr,sifprim,sifsmet,datdos,dosdat) values (:slvid,:rbr,:smetzadolz,:podsmetzadolz,:konzadolz,:progzadolz,:celdoz1,:celdoz2,:iznos,:smetprim,:nazprim1,:nazprim2,:povik1,:datpod,:mespod,:nacin,:sifra,:pratka,:datkniz,:valdat,:vidobr,:sifprim,:sifsmet,:datdos,:dosdat);
-- 0x75c23c
update promet set konzadolz=:konzadol,progzadolz=:progzadol,celdoz1=:celdo1,celdoz2=:celdo2,smetprim=:smetpri,nazprim1=:nazpri1,nazprim2=:nazpri2,iznos=:izno,povik1=:povi1,datpod=:datpo,mespod=:mespo,valdat=:valda,sifprim=:sifpri,datdos=:datdos,dosdat=:dosdat where pratka=:prat and rbr=:rb and datkniz=:dkniz;
