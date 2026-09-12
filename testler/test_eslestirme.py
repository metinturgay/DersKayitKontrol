# -*- coding: utf-8 -*-
"""Kayıt sayfasındaki katalog ile transkriptin eşleştirilmesi testi.

Katalog satırları gerçek bir ders kayıt sayfasından alındı.
"""
import os
import sys

BURASI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BURASI))
sys.path.insert(0, BURASI)

import ders_kayit as dk
import yonetmelik as y
import test_transkript as tt

# Gerçek sayfadan: eklenebilir gösterilen bölüm dersleri (kod, ad, akts, secili)
KATALOG = [
    # 1. dönem - OBİS bunları "hiç alınmamış" sayıp eklenebilir gösteriyor
    ("2709163", "FİZİK LABORATUVARI I", 2, False),
    ("2709171", "LİNEER CEBİR I", 6, False),
    ("2709172", "İNGİLİZCE I", 2, False),
    # 5. dönem
    ("2709544", "DİFERENSİYEL GEOMETRİ I", 5, False),
    ("2709545", "CEBİR I", 5, False),
    ("2709546", "SAYILAR TEORİSİ I", 3, False),
    ("2709547", "UYGULAMALI MATEMATİK I", 3, False),
    # 7. dönem - gerçekten yeni dersler, 4'ü seçili
    ("2705760", "YAPAY ZEKAYA GİRİŞ I*", 4, False),
    ("2709734", "MÜZİK VE MATEMATİK I (SEÇ.)", 4, True),
    ("2709735", "LORENTZ GEOMETRİ I (SEÇ)", 4, True),
    ("2709747", "MATEMATİK VE OYUN*", 4, True),
    ("2709753", "MATEMATİK UYGULAMALARI I", 4, True),
]
KATALOG = [{"ders_no": k, "ders_adi": a, "akts": e, "secili": s}
           for k, a, e, s in KATALOG]

ONEM_ETIKET = {"yuksek": "!!!", "orta": " ! ", "bilgi": "   "}


def main():
    t = dk.transkripti_coz(tt.fixture())
    eslesmeler = y.katalog_eslestir(KATALOG, t["son_durum"])

    print("  === Katalog <-> transkript eşleşmeleri ===")
    print("  %-9s %-30s %-7s %s" % ("KOD", "DERS", "EŞLEŞME", "TRANSKRİPT"))
    for e in eslesmeler:
        d = e["ders"]
        hedef = e["eslesme"] or e["aday"]
        aciklama = "-"
        if hedef:
            aciklama = "%s %s %s (%s AKTS)" % (
                hedef["ders_kodu"], hedef["ders_adi"][:22], hedef["harf"],
                hedef["akts"])
        print("  %-9s %-30s %-7s %s" % (
            d["ders_no"], d["ders_adi"][:30], e["tip"] or "yok", aciklama))

    print("")
    print("  === Danışman uyarıları ===")
    uyarilar = y.danisman_uyarilari(eslesmeler, t, yano=None)
    for u in uyarilar:
        print("  %s %-9s %-28s %s" % (
            ONEM_ETIKET[u["onem"]], u["ders_no"], u["baslik"], u["kaynak"]))
        print("          %s" % u["aciklama"])

    print("")
    print("  === Kontroller ===")
    ok = []

    def kontrol(ad, beklenen, gelen):
        tamam = beklenen == gelen
        print(("  [OK]  " if tamam else "  [HATA] ") + ad +
              ("" if tamam else "  beklenen=%r gelen=%r" % (beklenen, gelen)))
        ok.append(tamam)

    tipler = {e["ders"]["ders_no"]: e["tip"] for e in eslesmeler}
    # Eski koduyla geçilmiş olanlar ad üzerinden yakalanmalı
    kontrol("2709171 LİNEER CEBİR I -> ad eşleşmesi", "ad", tipler["2709171"])
    kontrol("2709172 İNGİLİZCE I -> ad eşleşmesi", "ad", tipler["2709172"])
    kontrol("2709544 DİF. GEOMETRİ I -> ad eşleşmesi", "ad", tipler["2709544"])
    kontrol("2709545 CEBİR I -> ad eşleşmesi", "ad", tipler["2709545"])
    kontrol("2709546 SAYILAR TEORİSİ I -> ad eşleşmesi", "ad", tipler["2709546"])
    # Gerçekten yeni dersler eşleşmemeli
    kontrol("2709163 FİZİK LAB. I -> eşleşme yok", None, tipler["2709163"])
    kontrol("2705760 YAPAY ZEKA -> eşleşme yok", None, tipler["2705760"])
    kontrol("2709734 MÜZİK VE MAT. -> eşleşme yok", None, tipler["2709734"])
    kontrol("2709735 LORENTZ GEO. -> eşleşme yok", None, tipler["2709735"])
    kontrol("2709747 MATEMATİK VE OYUN -> eşleşme yok", None, tipler["2709747"])

    # Eski koduyla geçilmiş dersler SEÇİLMEMİŞSE tek tek uyarı üretmez
    # (59 öğrencide 189 uyarı oluyordu, panel boğuluyordu); tek özet
    # notta toplanır. Bu katalogda hiçbiri seçili değil.
    verme = [u["ders_no"] for u in uyarilar
             if u["baslik"].startswith("ÇIKAR - eski koduyla")]
    kontrol("seçilmemiş kod değişikliği tek tek uyarmıyor", [], sorted(verme))
    ozetler = [u for u in uyarilar if u["baslik"] == "Müfredat kod değişikliği"]
    kontrol("tek özet not var", 1, len(ozetler))
    kontrol("  özet not bilgi seviyesinde", "bilgi", ozetler[0]["onem"])
    kontrol("  5 dersi kapsıyor", True, "5 dersi" in ozetler[0]["aciklama"])

    # Seçilmiş olsaydı eylem gerektirirdi
    secili_katalog = [dict(d, secili=(d["ders_no"] == "2709545"))
                      for d in KATALOG]
    u2 = y.danisman_uyarilari(
        y.katalog_eslestir(secili_katalog, t["son_durum"]), t)
    kontrol("seçilmişse ÇIKAR uyarısı", ["2709545"],
            [x["ders_no"] for x in u2
             if x["baslik"].startswith("ÇIKAR - eski koduyla")])
    kontrol("  yüksek öncelikli", "yuksek",
            [x["onem"] for x in u2
             if x["baslik"].startswith("ÇIKAR - eski koduyla")][0])

    # LİNEER CEBİR I 6->6 aynı; DİF.GEO 6->5, CEBİR 6->5, SAYILAR 4->3,
    # İNGİLİZCE 3->2 değişmiş. Hepsi GEÇİLMİŞ ders olduğu için 'bilgi'
    # seviyesinde: mezuniyette geçtiği AKTS sayılacak (kullanıcı kuralı #6).
    akts_gecilmis = sorted(u["ders_no"] for u in uyarilar
                           if u["baslik"] == "AKTS değişmiş (geçilmiş ders)")
    kontrol("AKTS değişen (geçilmiş) dersler",
            ["2709172", "2709544", "2709545", "2709546"], akts_gecilmis)
    kontrol("geçilmiş AKTS farkları 'bilgi' seviyesinde", ["bilgi"] * 4,
            [u["onem"] for u in uyarilar
             if u["baslik"] == "AKTS değişmiş (geçilmiş ders)"])
    # Alttan ders yok, dolayısıyla 'yüksek' seviyeli AKTS uyarısı da yok
    kontrol("alttan ders AKTS uyarısı yok", [],
            [u["ders_no"] for u in uyarilar
             if u["baslik"] == "AKTS DEĞİŞMİŞ - alttan ders"])

    gecmis_akts = [u["ders_no"] for u in uyarilar
                   if u["baslik"].startswith("AKTS değişmiş (geçmiş")]
    kontrol("Geçmiş denemelerde AKTS değişen (FİZİK II)",
            ["2709252"], gecmis_akts)

    # UYGULAMALI MATEMATİK I ile MATEMATİK UYGULAMALARI I karışmamalı
    kontrol("2709547 UYGULAMALI MAT. I -> eşleşme yok", None, tipler["2709547"])
    kontrol("2709753 MATEMATİK UYG. I -> eşleşme yok", None, tipler["2709753"])

    print("")
    # -----------------------------------------------------------------
    #  Ders seviyesi (I / II) KESİN ayırıcıdır
    # -----------------------------------------------------------------
    # Gerçek bir vaka: "DİFERANSİYEL GEOMETRİ II" ile
    # "DİFERENSİYEL GEOMETRİ I" harf harf %96 benzer. Eşik 0,88 olduğu için
    # yanlış eşleşiyordu; seviye farkı artık eşleşmeyi tamamen keser.
    print("")
    print("  === Ders seviyesi ayırıcı mı? ===")
    kontrol("Dif.Geo II <-> Dif.Geo I eşleşmez", 0.0,
                      y.ad_benzerligi("DİFERANSİYEL GEOMETRİ II",
                                      "DİFERENSİYEL GEOMETRİ I"))
    kontrol("Dif.Geo I <-> Dif.Geo I (yazım farklı) eşleşir", 1.0,
                      y.ad_benzerligi("DIFERANSIYEL GEOMETRI I",
                                      "DİFERENSİYEL GEOMETRİ I"))
    kontrol("Analiz III <-> Analiz IV eşleşmez", 0.0,
                      y.ad_benzerligi("ANALİZ III", "ANALİZ IV"))
    kontrol("Topoloji I <-> Topoloji II eşleşmez", 0.0,
                      y.ad_benzerligi("TOPOLOJI I", "TOPOLOJİ II"))
    kontrol("seviyesizler eskisi gibi", True,
                      y.ad_benzerligi("SOYUT MATEMATİK",
                                      "SOYUT MATEMATIK") > 0.99)
    kontrol("tek tarafta seviye varsa eşik çalışır", True,
                      y.ad_benzerligi("MATEMATİK UYGULAMALARI I",
                                      "MATEMATİK UYGULAMALARI") > 0.88)
    kontrol("seviye okuma: 'DİFERANSİYEL GEOMETRİ II' -> 2", 2,
                      y.ders_seviyesi("DİFERANSİYEL GEOMETRİ II"))
    kontrol("seviye okuma: 'SOYUT MATEMATİK' -> None", None,
                      y.ders_seviyesi("SOYUT MATEMATİK"))

    # -----------------------------------------------------------------
    #  OBİS'in "sayılmıyor" işareti (MADDE 15 şartlı geçer)
    # -----------------------------------------------------------------
    print("")
    print("  === Şartlı geçer (DC) OBİS işaretiyle ===")
    kontrol("DC + OBİS sayıyor -> geçti", "gecti",
                      y.transkript_deneme_durumu("DC", True))
    kontrol("DC + OBİS saymıyor -> şartlı kaldı", "sartli_kaldi",
                      y.transkript_deneme_durumu("DC", False))
    kontrol("DC + işaret yok -> harfe göre geçti", "gecti",
                      y.transkript_deneme_durumu("DC", None))
    kontrol("FF + OBİS saymıyor -> kaldı", "kaldi",
                      y.transkript_deneme_durumu("FF", False))
    kontrol("AA + OBİS sayıyor -> geçti", "gecti",
                      y.transkript_deneme_durumu("AA", True))
    kontrol("şartlı kaldı tekrar gerektirir", True,
                      y.tekrar_gerekir_mi("sartli_kaldi"))
    kontrol("şartlı kaldı başarılı sayılmaz", False,
                      y.basarili_sayilir_mi("sartli_kaldi"))
    kontrol("deneme_sonucu çözülmüş alanı kullanır", "sartli_kaldi",
                      y.deneme_sonucu({"harf": "DC",
                                       "sonuc": "sartli_kaldi"}))
    kontrol("deneme_sonucu alan yoksa harfe düşer", "gecti",
                      y.deneme_sonucu({"harf": "DC"}))

    print("")
    print("  %d/%d kontrol geçti." % (sum(ok), len(ok)))
    return 0 if all(ok) else 1


if __name__ == "__main__":
    sys.exit(main())
