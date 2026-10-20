-- TDM.dfm / INIT.SQL
select * from init;

-- TDM.dfm / IBUpdateSQL1.RefreshSQL
select * from init where naziv=:naziv;

-- TDM.dfm / IBUpdateSQL1.ModifySQL
update init set
  naziv=:naziv,
  adresa=:adresa,
  mesto=:mesto,
  telefon=:telefon,
  smetbukor=:smetbukor,
  podsbukor=:podsbukor,
  edb=:edb,
  trezsmet=:trezsmet,
  trzkan=:trzkan,
  trzkodkor=:trzkodkor,
  trzinskod=:trzinskod
where
  naziv=:old_naziv;

-- TDM.dfm / IBUpdateSQL1.InsertSQL
insert into init
  (naziv,adresa,mesto,telefon,smetbukor,podsbukor,edb,trezsmet,trzkan,trzkodkor,trzinskod)
values
  (:naz,:adr,:mes,:tel,:smbkor,psmbkor,:ed,:trzsm,:trzkan,:trzkodk,:trzinsk);

-- TDM.dfm / IBUpdateSQL1.DeleteSQL
delete from init where
  naziv=:old_naziv;

-- TDM.dfm / KORIS.SQL
SELECT * FROM KORIS;

-- TDM.dfm / IBUpdateSQL2.RefreshSQL
select * from koris where sifra=:old_sifra;

-- TDM.dfm / IBUpdateSQL2.ModifySQL
update koris set
  sifra=:sifra,
  ime=:ime,
  lozinka=:lozinka,
  kod=:kod,
  nivo=:nivo
where
  sifra=:old_sifra;

-- TDM.dfm / IBUpdateSQL2.InsertSQL
insert into koris
  (sifra,ime,lozinka,kod,nivo)
values
  (:sif,naz,:loz,kd,nv);

-- TDM.dfm / IBUpdateSQL2.DeleteSQL
delete from koris  where
  sifra=:old_sifra;

-- TDM.dfm / PARTNERI.SQL
SELECT * FROM PARTNERI;

-- TDM.dfm / IBUpdateSQL3.RefreshSQL
select * from partneri where sifra=:sifra;

-- TDM.dfm / IBUpdateSQL3.ModifySQL
update partneri
set
  sifra=:sifra,
  naziv=:naziv,
  adresa=:adresa,
  mesto=:mesto,
  telefon=:telefon,
  ziro=:ziro,
  brlk=:brlk,
  embg=:embg
where
  sifra=:old_sifra;

-- TDM.dfm / IBUpdateSQL3.InsertSQL
insert into partneri
  (sifra,naziv,adresa,mesto,telefon,ziro,brlk,embg)
values
  (:sif,:naz,:adr,:mes,:tel,:zir,:brl,:emb);

-- TDM.dfm / IBUpdateSQL3.DeleteSQL
delete from partneri where
  sifra=:old_sifra;

-- TDM.dfm / PROMET.SQL
select * from promet;

-- TDM.dfm / IBUpdateSQL4.RefreshSQL
select * from promet where (pratka=:pratka) and (datkniz=:datkniz);

-- TDM.dfm / IBUpdateSQL4.ModifySQL
update promet set
  slvid=:slvid,
  rbr=:rbr,
  smetzadolz=:smetzadolz,
  podsmetzadolz=:podsmetzadolz,
  konzadolz=:konzadolz,
  progzadolz=:progzadolz,
  celdoz1=:celdoz1,
  celdoz2=:celdoz2,
  sifra=:sifra,
  iznos=:iznos,
  smetprim=:smetprim,
  nazprim1=:nazprim1,
  nazprim2=:nazprim2,
  podsmetprim=:podsmetprim,
  konprim=:konprim,
  progprim=:progprim,
  povik1=:povik1,
  vidobr=:vidobr,
  nacin=:nacin,
  edb=:edb,
  valdat=:valdat,
  datpod=:datpod,
  mespod=:mespod,
  pratka=:pratka,
  datkniz=:datkniz,
  sifprim=:sifprim,
  brkniz=:brkniz,
  sifsmet=:sifsmet
where
  pratka=:old_pratka and
  datkniz=:old_datkniz;

-- TDM.dfm / IBUpdateSQL4.InsertSQL
insert into promet
  (slvid,rbr,smetzadolz,podsmetzadolz,konzadolz,progzadolz,celdoz1,celdoz2,sifra,iznos,smetprim,nazprim1,nazprim2,podsmetprim,konprim,progprim,povik1,vidobr,nacin,edb,valdat,datpod,mespod,pratka,datkniz,sifprim,brkniz,sifsmet)
values
  (:slvid,:rbr,:smetzadolz,:podsmetzadolz,:konzadolz,:progzadolz,:celdoz1,:celdoz2,:sifra,:iznos,:smetprim,:nazprim1,:nazprim2,:podsmetprim,:konprim,:progprim,:povik1,:vidobr,:nacin,:edb,:valdat,:datpod,:mespod,:pratka,:datkniz,:sifprim,:brkniz,:sifsmet);

-- TDM.dfm / IBUpdateSQL4.DeleteSQL
delete from promet where (pratka=:old_pratka) and (datkniz=:old_datkniz) and (vidobr=:old_vidobr) and (iznos=:old_iznos) and (sifprim=:old_sifprim) and (sifsmet=:old_sifsmet);

-- TDM.dfm / KNIZ.SQL
select * from kniz;

-- TDM.dfm / IBUpdateSQL5.RefreshSQL
select * from kniz where (pratka=:pratka) and (datkniz=:datkniz);

-- TDM.dfm / IBUpdateSQL5.ModifySQL
update kniz set
  pratka=:pratka,
  datkniz=:datkniz,
  ddd=:ddd,
  vkupnal=:vkupnal,
  iznos=:iznos,
  knizbr=:knizbr,
  sifsmet=:sifsmet
where
  pratka=:old_pratka and
  datkniz=:old_datkniz;

-- TDM.dfm / IBUpdateSQL5.InsertSQL
insert into kniz
  (pratka,datkniz,ddd,vkupnal,iznos,knizbr,sifsmet)
values
  (:pratka,:datkniz,:ddd,:vkupnal,:iznos,:knizbr,:sifsmet);

-- TDM.dfm / IBUpdateSQL5.DeleteSQL
delete from kniz where  (pratka=:old_pratka) and (datkniz=:old_datkniz);

-- TDM.dfm / PROMET1.SQL
select * from promet;

-- TDM.dfm / IBUpdateSQL6.RefreshSQL
select * from promet where;

-- TDM.dfm / IBUpdateSQL6.ModifySQL
update promet set
  slvid=:slvid,
  rbr=:rbr,
  smetzadolz=:smetzadolz,
  podsmetzadolz=:podsmetzadolz,
  konzadolz=:konzadolz,
  progzadolz=:progzadolz,
  celdoz1=:celdoz1,
  celdoz2=:celdoz2,
  sifra=:sifra,
  iznos=:iznos,
  smetprim=:smetprim,
  nazprim1=:nazprim1,
  nazprim2=:nazprim2,
  podsmetprim=:podsmetprim,
  konprim=:konprim,
  progprim=:progprim,
  povik1=:povik1,
  vidobr=:vidobr,
  nacin=:nacin,
  edb=:edb,
  valdat=:valdat,
  datpod=:datpod,
  mespod=:mespod,
  pratka=:pratka,
  datkniz=:datkniz,
  sifprim=:sifprim,
  brkniz=:brkniz
where;

-- TDM.dfm / IBUpdateSQL6.InsertSQL
insert into promet
  (slvid,rbr,smetzadolz,podsmetzadolz,konzadolz,progzadolz,celdoz1,celdoz2,sifra,iznos,smetprim,nazprim1,nazprim2,podsmetprim,konprim,progprim,povik1,vidobr,nacin,edb,valdat,datpod,mespod,pratka,datkniz,sifprim,brkniz)
values
  (:slvid,:rbr,:smetzadolz,:podsmetzadolz,:konzadolz,:progzadolz,:celdoz1,:celdoz2,:sifra,:iznos,:smetprim,:nazprim1,:nazprim2,:podsmetprim,:konprim,:progprim,:povik1,:vidobr,:nacin,:edb,:valdat,:datpod,:mespod,:pratka,:datkniz,:sifprim,:brkniz);

-- TDM.dfm / IBUpdateSQL6.DeleteSQL
delete from promet where;

-- TDM.dfm / SMETKI.SQL
SELECT * FROM SMETKI;

-- TDM.dfm / IBUpdateSQL7.RefreshSQL
select * from smetki where sifra=:sifra;

-- TDM.dfm / IBUpdateSQL7.ModifySQL
update smetki set
  sifra=:sifra,
  smetbukor=:smetbukor,
  podsbukor=:podsbukor
where
  sifra=:old_sifra;

-- TDM.dfm / IBUpdateSQL7.InsertSQL
insert into smetki
  (sifra,smetbukor,podsbukor)
values
  (:sif,:smbkor,:podsmbkor);

-- TDM.dfm / IBUpdateSQL7.DeleteSQL
delete from smetki where
  sifra=:old_sifra;

-- TDM.dfm / LICA.SQL
SELECT * FROM LICA;

-- TDM.dfm / IBUpdateSQL8.RefreshSQL
select * from lica where sifra=:sifra;

-- TDM.dfm / IBUpdateSQL8.ModifySQL
update lica
set
  sifra=:sifra,
  naziv=:naziv,
  adresa=:adresa,
  mesto=:mesto,
  telefon=:telefon,
  transak=:transak,
  brlk=:brlk,
  embg=:embg
where
  sifra=:old_sifra;

-- TDM.dfm / IBUpdateSQL8.InsertSQL
insert into lica
  (sifra,naziv,adresa,mesto,telefon,transak,brlk,embg)
values
  (:sif,:naz,:adr,:mes,:tel,:tran,:brl,:emb);

-- TDM.dfm / IBUpdateSQL8.DeleteSQL
delete from LICA where
  sifra=:old_sifra;

-- TDM.dfm / KONTA.SQL
SELECT * FROM KONTA;

-- TDM.dfm / IBUpdateSQL9.RefreshSQL
select * from konta where konto=:konto;

-- TDM.dfm / IBUpdateSQL9.ModifySQL
update konta set
  konto=:konto,
  opis=:opis
where
  konto=:old_konto;

-- TDM.dfm / IBUpdateSQL9.InsertSQL
insert into konta
  (konto,opis)
values
  (:kon,:opi);

-- TDM.dfm / IBUpdateSQL9.DeleteSQL
DELETE FROM KONTA WHERE KONTO=:OLD_KONTO;

-- TDM.dfm / SPEC.SQL
select o_vidobr,o_cel,o_konz,o_progz,o_banka,o_broj,o_vkupno from specif ('11','1','01.01.0001');
