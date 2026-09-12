# -*- coding: utf-8 -*-
"""Giriş yılı (kohort) testleri.

Neden ayrı bir dosya
--------------------
Bir dersin "eski AKTS'si" diye tek bir sayı yok; öğrencinin giriş
yılına bağlı. 2023 girişli Fizik I'i 5 AKTS ile aldı, 2024 girişli 4
ile alıyor. 2023 tabanını 2024 girişliye uygularsak hiç yaşamadığı bir
AKTS kaybı uydururuz ve öğrenciyi boş yere mezuniyet riskinde
gösteririz - ya da tersi, gerçek kaybı gizleriz.

Elimizde gerçek bir 2024 transkripti yok. O yüzden 2024 girişli
öğrenci müfredat belgesinden üretiliyor (sentetik_transkript.py).
Bu fotoğrafın doğruluğu bağımsız olarak teyit edildi: 2024 girişli,
hiç dersten kalmamış gerçek bir öğrencinin OBİS sayfasında
"Genel Krd 120" yazıyor, belgeden üretilen transkript de 120 veriyor.
"""
import glob
import os
import re
import sys

BURASI = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(BURASI)
sys.path.insert(0, KOK)
sys.path.insert(0, BURASI)

import akts_degisimi as ad
import ders_kayit as dk
import ders_programi as dprog
import mufredat as mf
import ozet as oz
import sentetik_transkript as st
import yonetmelik as ym

OK = []


def kontrol(ad_, beklenen, gelen):
    tamam = beklenen == gelen
    print(("  [OK]  " if tamam else "  [HATA] ") + ad_ +
          ("" if tamam else "\n          beklenen=%r\n          gelen   =%r"
           % (beklenen, gelen)))
    OK.append(tamam)


def _gercek_transkriptler():
    cikti = os.path.join(KOK, "cikti")
    cikti_dosyalari = sorted(glob.glob(
        os.path.join(cikti, "transkript_*.html")))
    veri = {}
    for yol in cikti_dosyalari:
        no = re.search(r"transkript_(\d+)\.html", yol).group(1)
        with open(yol, encoding="utf-8") as f:
            veri[no] = dk.transkripti_coz(f.read())
    return veri


def main():
    muf = mf.yukle()
    if not muf:
        print("  veri/mufredat.json yok. Önce: python mufredat.py")
        return 1

    print("  === giris_yili() ===")
    kontrol("230000003 -> 2023", 2023, ym.giris_yili("230000003"))
    kontrol("240000006 -> 2024", 2024, ym.giris_yili("240000006"))
    kontrol("bos numara -> None", None, ym.giris_yili(""))

    # ---------------------------------------------------------------
    print("")
    print("  === Referans fotoğrafı ===")
    ref = ad.referanslari_yukle()
    kontrol("veri/akts_referans.json okundu", True, bool(ref))
    kontrol("2024 kohortu var", True, 2024 in ref)
    belge = muf["dersler"]
    # Fotoğraf belgeyle çelişirse biri yanlıştır; ikisi de AKTS için
    # kaynak olduğu için sessizce ayrışmalarına izin veremeyiz.
    celiskili = [(k, v, belge[k]["akts"]) for k, v in (ref.get(2024) or
                                                       {}).items()
                 if k in belge and belge[k]["akts"] is not None
                 and belge[k]["akts"] != v]
    kontrol("2024 fotoğrafı müfredat belgesiyle çelişmiyor", [], celiskili)

    # ---------------------------------------------------------------
    print("")
    print("  === Belgeden üretilen 2024 girişli öğrenci ===")
    ham = st.uret(muf, "240000006", ad="SENTETIK 2024")
    t24 = dk.transkripti_coz(ham)
    kontrol("1-4. yarıyıl okundu", [1, 2, 3, 4],
            sorted({d["donem"] for d in t24["denemeler"]}))
    # Gerçek 2024 girişli, hiç kalmamış öğrencinin OBİS'teki genel
    # kredisi 120. Belgeden üretilen transkript de 120 vermeli.
    kontrol("toplam 120 AKTS (gerçek öğrencinin Genel Krd'si)", 120,
            t24["alinan_akts"])
    kontrol("parser kendi AKTS denetiminden geçti", True,
            t24["akts_dogrulama"])
    kontrol("hiç kalınan ders yok", 0, len(t24["kalinan"]))
    for y in (1, 2, 3, 4):
        kontrol("  %d. yarıyıl belgedeki planla aynı" % y,
                muf["yariyillar"][y]["toplam_akts"],
                sum(d["akts"] for d in t24["denemeler"] if d["donem"] == y))

    # ---------------------------------------------------------------
    print("")
    print("  === Kohort tabanı: 2023 ile 2024 karışmıyor ===")
    gercek = _gercek_transkriptler()
    if not gercek:
        print("  (cikti/ boş, karşılaştırma atlandı)")
    else:
        yalniz23 = ad.hesapla(gercek, muf)
        karisik = dict(gercek)
        karisik["240000006"] = t24
        iki_kohort = ad.hesapla(karisik, muf)

        kontrol("saf liste tek kohort görüyor", 1,
                yalniz23["ozet"]["kohort_sayisi"])
        kontrol("karışık liste iki kohort görüyor", 2,
                iki_kohort["ozet"]["kohort_sayisi"])

        # 2024 girişli listeye girince 2023'ün tablosu DEĞİŞMEMELİ.
        onceki = {s["eski_kod"]: (s["eski_akts"], s["fark"])
                  for s in yalniz23["dersler"]}
        sonraki = {s["eski_kod"]: (s["kohortlar"][2023]["eski_akts"],
                                   s["kohortlar"][2023]["fark"])
                   for s in iki_kohort["dersler"]
                   if 2023 in s["kohortlar"]
                   and s["kohortlar"][2023]["ogrenci_sayisi"]}
        kaymis = {k: (onceki[k], sonraki[k]) for k in onceki
                  if k in sonraki and onceki[k] != sonraki[k]}
        kontrol("2024 girişli eklenince 2023 tablosu kaymıyor", {}, kaymis)

        k24 = [c for c in iki_kohort["kohortlar"]
               if c["giris_yili"] == 2024][0]
        kontrol("2024 girişlide AKTS kaybı yok", 0, k24["degisen"])
        k23 = [c for c in iki_kohort["kohortlar"]
               if c["giris_yili"] == 2023][0]
        kontrol("2023 girişlide AKTS kaybı var", True, k23["degisen"] > 0)

        # Aynı kodu iki kohort da taşıyorsa fark açıkça işaretlenmeli.
        farkli = [s for s in iki_kohort["dersler"] if s["kohort_farki"]]
        kontrol("kohortlar arası farklı ders işaretlendi", True,
                bool(farkli))
        for s in farkli:
            kontrol("  %s her kohortta ayrı değer taşıyor" % s["ders_adi"],
                    True,
                    len({c["eski_akts"] for c in s["kohortlar"].values()
                         if c["ogrenci_sayisi"]}) > 1)

    # ---------------------------------------------------------------
    print("")
    print("  === Transkripti olmayan kohort uydurma kayıp üretmiyor ===")
    bos24 = {"2427090%02d" % i: dk.transkripti_coz("") for i in range(1, 6)}
    yalniz_bos = ad.hesapla(dict(gercek, **bos24), muf) if gercek else None
    if yalniz_bos:
        b = [c for c in yalniz_bos["kohortlar"]
             if c["giris_yili"] == 2024][0]
        kontrol("kaydı olmayan 2024 kohortunda değişen ders yok", 0,
                b["degisen"])
        kontrol("kaynağı referans fotoğrafı", "referans fotoğrafı",
                b["kaynak"])

    # ---------------------------------------------------------------
    print("")
    print("  === Uçtan uca: 2024 girişli öğrenci özeti ===")
    sayfalar = sorted(glob.glob(
        os.path.join(KOK, "cikti", "ders_sayfasi_*.html")))
    if not sayfalar:
        print("  (cikti/ boş, atlandı)")
    else:
        with open(sayfalar[0], encoding="utf-8") as f:
            kayit = dk.ders_kaydini_coz(f.read())
        kayit["no"] = "240000006"
        kayit["transkript"] = t24
        s = oz.ogrenci_ozeti(kayit, icinde_bulunulan_yil=2026,
                             program=dprog.yukle(), mufredat=muf)
        pr, ka = s["projeksiyon"], s["akts_kaybi"]
        kontrol("hedef dönem 5", 5, s["donem_durumu"]["hedef_donem"])
        kontrol("AKTS kaybı yok", 0, ka["toplam_kayip"])
        kontrol("alt yükümlülük yok", 0, pr["alt_yukumluluk"])
        kontrol("mezuniyet projeksiyonu tam plan", pr["plan_toplami"],
                pr["projeksiyon"])
        kontrol("mezuniyet yeterli", True, pr["yeterli"])

        # 2024 girişli Fizik I'den kalsa bile AKTS kaybetmez: onun için
        # Fizik I zaten 4 AKTS, düşen bir şey yok.
        kayit2 = dict(kayit)
        kayit2["no"] = "240000007"
        kayit2["transkript"] = dk.transkripti_coz(
            st.uret(muf, "240000007", notlar={"2709152": "FF"}))
        s2 = oz.ogrenci_ozeti(kayit2, icinde_bulunulan_yil=2026,
                              program=dprog.yukle(), mufredat=muf)
        kontrol("Fizik I'den kalan 2024 girişli kalmış sayılıyor", 1,
                len(kayit2["transkript"]["kalinan"]))
        kontrol("kalsa bile AKTS kaybı yok (Fizik I zaten 4)", 0,
                s2["akts_kaybi"]["toplam_kayip"])

    print("")
    print("  %d/%d kontrol geçti." % (sum(OK), len(OK)))
    return 0 if all(OK) else 1


if __name__ == "__main__":
    sys.exit(main())
