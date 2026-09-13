# -*- coding: utf-8 -*-
"""Yönetmelik kurallarının testi (yonetmelik.py).

Senaryolar gerçek öğrenci verisinden ve danışman kararlarından
türetildi.
"""
import os
import sys

BURASI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BURASI))
sys.path.insert(0, BURASI)

import yonetmelik as y

OK = []


def kontrol(ad, beklenen, gelen):
    tamam = beklenen == gelen
    print(("  [OK]  " if tamam else "  [HATA] ") + ad +
          ("" if tamam else "\n          beklenen=%r\n          gelen   =%r"
           % (beklenen, gelen)))
    OK.append(tamam)


# 7. dönemden alınabilir dersler (gerçek sayfadan, kontenjanı dolu olmayanlar)
YEDINCI_DONEM = [
    {"ders_no": "2705760", "ders_adi": "YAPAY ZEKAYA GİRİŞ I*", "akts": 4},
    {"ders_no": "2709747", "ders_adi": "MATEMATİK VE OYUN*", "akts": 4},
    {"ders_no": "2709753", "ders_adi": "MATEMATİK UYGULAMALARI I", "akts": 4},
]

KATALOG = [
    # 5. dönem - ilk dördü zorunlu (siyah), kalanı seçmeli (yeşil)
    {"ders_no": "2709544", "ders_adi": "DİFERENSİYEL GEOMETRİ I", "akts": 5,
     "donem": "5. Dönem Dersleri", "yesil_yazi": False, "doldu": False},
    {"ders_no": "2709545", "ders_adi": "CEBİR I", "akts": 5,
     "donem": "5. Dönem Dersleri", "yesil_yazi": False, "doldu": False},
    {"ders_no": "2709503", "ders_adi": "KISMI TÜREVLİ.DIF.DENK. I(SEÇ)",
     "akts": 4, "donem": "5. Dönem Dersleri", "yesil_yazi": True,
     "doldu": True},
    {"ders_no": "2709504", "ders_adi": "NÜMERİK ANALİZ I", "akts": 4,
     "donem": "5. Dönem Dersleri", "yesil_yazi": True, "doldu": False},
    {"ders_no": "2709536", "ders_adi": "EĞRİLER TEORİSİ (SEÇ.)", "akts": 4,
     "donem": "5. Dönem Dersleri", "yesil_yazi": True, "doldu": False},
    # 7. dönem
    {"ders_no": "2709735", "ders_adi": "LORENTZ GEOMETRİ I (SEÇ)", "akts": 4,
     "donem": "7. Dönem Dersleri", "yesil_yazi": True, "doldu": True},
    {"ders_no": "2705760", "ders_adi": "YAPAY ZEKAYA GİRİŞ I*", "akts": 4,
     "donem": "7. Dönem Dersleri", "yesil_yazi": False, "doldu": False},
]


def main():
    print("  === MADDE 9/1-c: taban AKTS limiti ===")
    kontrol("GANO 1,20 -> 30 AKTS", 30, y.azami_akts(1.20))
    kontrol("GANO 1,50 -> 45 AKTS", 45, y.azami_akts(1.50))
    kontrol("GANO 2,80 -> 45 AKTS", 45, y.azami_akts(2.80))

    print("")
    print("  === Öğrencinin sınıfı ve hedef dönemi ===")
    # Örnek: 1..6. dönemlerden ders almış, tek olanların en yükseği 5
    g = y.ogrenci_donem_durumu([1, 2, 3, 4, 5, 6])
    kontrol("en yüksek alınan tek dönem", 5, g["en_yuksek_alinan"])
    kontrol("  3. sınıf", 3, g["sinif"])
    kontrol("  hedef dönem 7", 7, g["hedef_donem"])

    # Hiç 5. dönemden ders almamış -> 2. sınıf, hedef 5
    ik = y.ogrenci_donem_durumu([1, 2, 3, 4])
    kontrol("hiç 5. dönem almamış -> 2. sınıf", 2, ik["sinif"])
    kontrol("  hedef dönem 5", 5, ik["hedef_donem"])

    # Hiç 3. dönemden ders almamış -> 1. sınıf, hedef 3
    bir = y.ogrenci_donem_durumu([1, 2])
    kontrol("hiç 3. dönem almamış -> 1. sınıf", 1, bir["sinif"])
    kontrol("  hedef dönem 3", 3, bir["hedef_donem"])

    print("")
    print("  === Alt dönem yükü (MADDE 9/1-a önceliği) ===")
    # Örnek: 1., 3. ve 5. dönemden 30'ar AKTS geçmiş -> eksik yok
    gecilen_tam = ([{"donem": 1, "akts": 30}] + [{"donem": 3, "akts": 30}] +
                   [{"donem": 5, "akts": 30}])
    yuk, ayrinti = y.alt_donem_yuku(gecilen_tam, 7)
    kontrol("alt dönem eksiği yok", 0, yuk)

    # 3. dönemden 8 AKTS eksik kalmış bir öğrenci
    gecilen_eksik = [{"donem": 1, "akts": 30}, {"donem": 3, "akts": 22},
                     {"donem": 5, "akts": 30}]
    yuk2, _ = y.alt_donem_yuku(gecilen_eksik, 7)
    kontrol("3. dönemden 8 AKTS eksik", 8, yuk2)

    # Ders geçilmiş ama AKTS'si düşmüşse bu "alttan ders" değil, AKTS kaybı
    gecilen_akts_kaybi = [{"donem": 1, "akts": 30}, {"donem": 3, "akts": 30},
                          {"donem": 5, "akts": 29}]
    yuk3, ay3 = y.alt_donem_yuku(gecilen_akts_kaybi, 7, kalinan_dersler=[])
    kontrol("kalınan ders yoksa 1 AKTS eksik yük sayılmaz", 0, yuk3)
    kontrol("  ama AKTS kaybı olarak işaretlenir", "akts_kaybi",
            [a for a in ay3 if a["donem"] == 5][0]["tip"])
    yuk4, _ = y.alt_donem_yuku(gecilen_akts_kaybi, 7,
                               kalinan_dersler=[{"donem": 5}])
    kontrol("5. dönemde kalınan ders varsa yük sayılır", 1, yuk4)

    print("")
    print("  === Bölüm planı ve AKTS kaybı eşiği ===")
    kontrol("plan toplamı 244", 244, y.plan_toplami())
    kontrol("AKTS kaybı eşiği plandan türetiliyor (244-240+1)", 5,
            y.akts_kaybi_esigi())

    # Örnek: FİZİK II 5 AKTS iken kalmış, 4 AKTS ile geçmiş -> 1 kayıp
    gizem = {
        "tekrar_edilen": [
            {"ders_kodu": "2709251", "ders_adi": "ANALİZ II",
             "aktsler": [8, 8], "guncel": {"akts": 8}},
            {"ders_kodu": "2709252", "ders_adi": "FİZİK II",
             "aktsler": [5, 4], "guncel": {"akts": 4}},
            {"ders_kodu": "2709257", "ders_adi": "İNGİLİZCE 2",
             "aktsler": [3, 3, 3], "guncel": {"akts": 3}},
            {"ders_kodu": "2709262", "ders_adi": "ATATÜRK 2",
             "aktsler": [2, 2], "guncel": {"akts": 2}},
        ],
    }
    k = y.akts_kaybi(gizem)
    kontrol("toplam AKTS kaybı 1", 1, k["toplam_kayip"])
    kontrol("  beklenen mezuniyet AKTS'si 243", 243,
            k["beklenen_mezuniyet_akts"])
    kontrol("  240'ın üstünde, risk yok", False, k["riskli"])
    kontrol("  kaybın kaynağı FİZİK II", ["2709252"],
            [g["ders_kodu"] for g in k["gerceklesmis"]])

    # 5 AKTS kaybeden öğrenci 239'a düşer -> mezun olamaz
    riskli = {"tekrar_edilen": [
        {"ders_kodu": "X", "ders_adi": "X", "aktsler": [10, 5],
         "guncel": {"akts": 5}}]}
    kr = y.akts_kaybi(riskli)
    kontrol("5 AKTS kayıp -> riskli", True, kr["riskli"])
    kontrol("  mezuniyet AKTS'si 239", 239, kr["beklenen_mezuniyet_akts"])

    print("")
    print("  === MADDE 10/2: devam muafiyeti ===")
    kontrol("FF almış -> devam sağlanmış", True, y.devam_saglanmis_mi("FF"))
    kontrol("F almış -> devam sağlanmamış", False, y.devam_saglanmis_mi("F"))
    kontrol("not girilmemiş -> bilinmiyor", None, y.devam_saglanmis_mi(""))

    # Kodu değişmiş, eski kodla FF almış (yani devam etmiş) bir alttan ders.
    # OBİS yeni kodu "ilk kez alınıyor" sayacağı için devamı zorunlu
    # gösterecek; oysa öğrencinin devam zorunluluğu yok.
    kod_degisti = [{
        "ders": {"ders_no": "2709545", "ders_adi": "CEBİR I", "akts": 5,
                 "secili": True, "ilk_bayrak": True},
        "eslesme": {"ders_kodu": "2709508", "ders_adi": "CEBİR I",
                    "harf": "FF", "yil": 2026, "akts": 6},
        "tip": "ad", "benzerlik": 1.0, "aday": None,
    }]
    u = y.danisman_uyarilari(kod_degisti, {"tekrar_edilen": []})
    basliklar = [x["baslik"] for x in u]
    kontrol("alttan ders uyarısı var", True, "ALTTAN ders" in basliklar)
    kontrol("devam muafiyeti uyarısı var", True,
            "DEVAM MUAFİYETİ - OBİS görmeyecek" in basliklar)
    kontrol("alttan derste AKTS düşüşü 'yüksek' uyarı", True,
            "AKTS DEĞİŞMİŞ - alttan ders" in basliklar)
    for x in u:
        if x["baslik"].startswith("DEVAM"):
            print("          " + x["aciklama"])

    # Devamsızlıktan kalmışsa (F) muafiyet YOK, devam zorunlu
    devamsiz = [dict(kod_degisti[0])]
    devamsiz[0]["eslesme"] = dict(kod_degisti[0]["eslesme"], harf="F")
    u2 = y.danisman_uyarilari(devamsiz, {"tekrar_edilen": []})
    kontrol("F almışsa devam muafiyeti uyarısı YOK", False,
            any(x["baslik"].startswith("DEVAM") for x in u2))

    print("")
    print("  === Son sınıf: KAPI 1 (hedef dönem) ===")
    # 5. dönemden İLK KEZ ders alan öğrenci: AKTS'si yetse bile olmaz
    ilk_kez = y.son_sinif_degerlendir(3.50, ik, 0, YEDINCI_DONEM)
    kontrol("5. dönemi ilk kez alan -> son sınıf DEĞİL", False,
            ilk_kez["son_sinif"])
    kontrol("  üst dönem durumuna girer", True, ilk_kez["ust_donem_durumu"])
    kontrol("  GANO 3,50 olsa bile limit 45'te kalır", 45,
            y.yariyil_akts_limiti(3.50, ilk_kez["son_sinif"]))
    print("          gerekçe: " + ilk_kez["sebep"])

    print("")
    print("  === Son sınıf: KAPI 2 (bütçe) ===")
    # Örnek: GANO 2,8 -> 45 AKTS, alt dönem eksiği 0
    s = y.son_sinif_degerlendir(2.80, g, 0, YEDINCI_DONEM)
    kontrol("son sınıf", True, s["son_sinif"])
    kontrol("  taban limit 45", 45, s["taban_limit"])
    kontrol("  son sınıfta limit kalkar", None,
            y.yariyil_akts_limiti(2.80, s["son_sinif"]))
    print("          gerekçe: " + s["sebep"])

    # 5. dönemi almış ama alt dönem eksiği ağır: bütçe yetmiyor
    d = y.son_sinif_degerlendir(1.20, g, 28, YEDINCI_DONEM)
    kontrol("GANO 1,20 + 28 AKTS eksik -> son sınıf DEĞİL", False,
            d["son_sinif"])
    kontrol("  kalan kapasite 2", 2, d["kalan_kapasite"])
    kontrol("  limit 30 olarak kalır", 30,
            y.yariyil_akts_limiti(1.20, d["son_sinif"]))
    print("          gerekçe: " + d["sebep"])

    # Aynı öğrenci GANO 1,50 olsa: 45-28=17, 4 AKTS sığar
    e = y.son_sinif_degerlendir(1.50, g, 28, YEDINCI_DONEM)
    kontrol("GANO 1,50 + 28 AKTS eksik -> son sınıf", True, e["son_sinif"])

    # 7. dönemde alınabilir ders yoksa
    f = y.son_sinif_degerlendir(2.80, g, 0, [])
    kontrol("7. dönemde ders yok -> son sınıf değil", False, f["son_sinif"])

    print("")
    print("  === MADDE 9/1-ç: üst dönemden ders ===")
    u1 = y.ust_yariyil_degerlendir(3.20, kalinan_ders_sayisi=0,
                                   gecen_yariyil_sayisi=4)
    kontrol("GANO 3,20 + hiç kalmamış -> 6 AKTS hak", 6, u1["hak_akts"])
    u2 = y.ust_yariyil_degerlendir(2.80, kalinan_ders_sayisi=0,
                                   gecen_yariyil_sayisi=4)
    kontrol("GANO 2,80 -> hak yok", 0, u2["hak_akts"])
    u3 = y.ust_yariyil_degerlendir(3.50, kalinan_ders_sayisi=2,
                                   gecen_yariyil_sayisi=4)
    kontrol("alttan dersi var -> hak yok", 0, u3["hak_akts"])
    print("          " + u3["sebep"])

    print("")
    print("  === MADDE 9/1-a: seçmeli gruplar (dönem bazlı) ===")
    kontrol("'(SEÇ)' ibaresi seçmeli sayılır", True,
            y.secmeli_mi({"ders_adi": "EĞRİLER TEORİSİ (SEÇ.)"}))
    kontrol("yeşil satır seçmeli sayılır", True,
            y.secmeli_mi({"ders_adi": "NÜMERİK ANALİZ I", "yesil_yazi": True}))
    kontrol("zorunlu ders seçmeli değil", False,
            y.secmeli_mi({"ders_adi": "CEBİR I", "yesil_yazi": False}))

    gruplar = y.secmeli_gruplari(KATALOG)
    kontrol("gruplar dönem bazlı", [5, 7], sorted(gruplar))
    kontrol("5. dönem seçmeli sayısı", 3, len(gruplar[5]))

    # 2709503'ten kalmış varsayalım: aynı dönemin diğer seçmelileri alternatif
    alt = y.secmeli_alternatifleri(5, KATALOG, haric_kodlar=["2709503"])
    kontrol("5. dönem alternatifleri (dolu olan elenir)",
            ["2709504", "2709536"], sorted(d["ders_no"] for d in alt))

    print("")
    print("  === Dönem kompozisyonu: zorunlu + TOS + bölüm içi seçmeli ===")
    kontrol("TOS kodla tanınır", True, y.tos_mu({"ders_no": "2615580"}))
    kontrol("TOS (*) ile tanınır", True,
            y.tos_mu({"ders_no": "9999999", "ders_adi": "BİR DERS*"}))
    kontrol("TOS bölüm içi seçmeli SAYILMAZ", False,
            y.secmeli_mi({"ders_no": "2709747",
                          "ders_adi": "MATEMATİK VE OYUN*"}))
    kontrol("(SEÇ) bölüm içi seçmeli", True,
            y.secmeli_mi({"ders_no": "2709735",
                          "ders_adi": "LORENTZ GEOMETRİ I (SEÇ)"}))

    # Gerçek bir 7. dönem seçimi: 2 bölüm seçmeli + 1 TOS + 1 zorunlu.
    # ADSIZ: bu dosya yayımlanıyor ve 60 kişilik bir bölümde ad +
    # dönem + ders listesi kişiyi doğrudan tanınır kılar.
    kat7 = [
        {"ders_no": "2709753", "ders_adi": "MATEMATİK UYGULAMALARI I",
         "akts": 4, "donem": "7. Dönem Dersleri", "yesil_yazi": False},
        {"ders_no": "2709746", "ders_adi": "ÖĞRENME PSİKOLOJİSİ*",
         "akts": 4, "donem": "7. Dönem Dersleri", "yesil_yazi": False},
        {"ders_no": "2709747", "ders_adi": "MATEMATİK VE OYUN*",
         "akts": 4, "donem": "7. Dönem Dersleri", "yesil_yazi": False},
        {"ders_no": "2709720", "ders_adi": "YAKLAŞIM KÜMELER TEORİSİ I (SEÇ)",
         "akts": 4, "donem": "7. Dönem Dersleri", "yesil_yazi": True},
        {"ders_no": "2709735", "ders_adi": "LORENTZ GEOMETRİ I (SEÇ)",
         "akts": 4, "donem": "7. Dönem Dersleri", "yesil_yazi": True},
    ]
    secim7 = [{"ders_no": k} for k in
             ("2709720", "2709735", "2709746", "2709753")]
    c = y.donem_kompozisyonu_denetle(7, secim7, kat7)
    kontrol("16/32 AKTS", (16, 32), (c["secilen_akts"], c["toplam_akts"]))
    kontrol("  zorunlu tamam", [], c["zorunlu_eksik"])
    kontrol("  TOS 1 seçilmiş, eksik yok", (1, 0),
            (len(c["tos_secilen"]), c["tos_eksik"]))
    kontrol("  bölüm içi seçmeli 6 gerek, 2 var", (6, 2),
            (c["secmeli_gereken"], len(c["secmeli_secilen"])))
    kontrol("  4 seçmeli eksik", 4, c["secmeli_eksik"])

    # İki TOS seçmiş öğrenci
    iki_tos = [{"ders_no": k} for k in ("2709746", "2709747", "2709753")]
    c2 = y.donem_kompozisyonu_denetle(7, iki_tos, kat7)
    kontrol("iki TOS -> fazla 1", 1, c2["tos_fazla"])

    # Zorunlu dersi seçmemiş
    c3 = y.donem_kompozisyonu_denetle(7, [{"ders_no": "2709720"}], kat7)
    kontrol("zorunlu seçilmemiş -> eksik", ["2709753"],
            [z["ders_no"] for z in c3["zorunlu_eksik"]])
    kontrol("TOS de yok -> eksik 1", 1, c3["tos_eksik"])
    # Zorunlu daha önce geçilmişse istenmez
    c4 = y.donem_kompozisyonu_denetle(7, [{"ders_no": "2709720"}], kat7,
                                      gecilen_kodlar=["2709753"])
    kontrol("zorunlu geçilmişse istenmez", [], c4["zorunlu_eksik"])

    print("")
    print("  === Geçmişe dönük yönetmelik UYGULANMIYOR (bağıl sistem) ===")
    kontrol("DC transkriptte geçti sayılır", "gecti",
            y.transkript_harf_durumu("DC"))
    kontrol("DD (bağıl sistem) geçti sayılır", "gecti",
            y.transkript_harf_durumu("DD"))
    kontrol("FD (bağıl sistem) kaldı sayılır", "kaldi",
            y.transkript_harf_durumu("FD"))
    kontrol("FF kaldı", "kaldi", y.transkript_harf_durumu("FF"))
    kontrol("F (devamsız) kaldı", "kaldi", y.transkript_harf_durumu("F"))
    kontrol("M muaf", "muaf", y.transkript_harf_durumu("M"))
    kontrol("tanınmayan harf bildirilir", "bilinmiyor",
            y.transkript_harf_durumu("ZZ"))
    # Bu dönemki karar için YANO'lu değerlendirme hâlâ mevcut
    kontrol("bu dönem için DC + YANO 2,20 -> kalır", "sartli_kaldi",
            y.harf_durumu("DC", 2.20))

    print("")
    print("  === MADDE 9/1-d: not yükseltme ===")
    kontrol("CC yükseltilebilir", True, y.not_yukseltilebilir_mi("CC"))
    kontrol("BB yükseltilemez", False, y.not_yukseltilebilir_mi("BB"))
    kontrol("AA yükseltilemez", False, y.not_yukseltilebilir_mi("AA"))

    print("")
    print("  === MADDE 16: azami süre ===")
    a = y.azami_sure_durumu("230000003", 2026, 4)
    kontrol("2023 girişli, 2026'da 3. yılında", 3, a["gecen_yil"])
    kontrol("azami 7 yıl, 4 yıl kalmış", 4, a["kalan_yil"])
    kontrol("süre aşılmamış", False, a["asildi"])

    print("")
    print("  === MADDE 10/1 devamsızlık hakkı ===")
    # Teorikte %30, uygulamada %20 devamsızlık hakkı
    kontrol("4 saatlik teorik derste hak 1.2 saat", 1.2,
            round(y.devamsizlik_hakki(4), 2))
    kontrol("3 saatlik teorik derste hak 0.9 saat", 0.9,
            round(y.devamsizlik_hakki(3), 2))
    kontrol("4 saatlik uygulamada hak 0.8 saat", 0.8,
            round(y.devamsizlik_hakki(4, uygulama=True), 2))

    # Çakışma hakka sığıyor mu? (ortak <= a_hak + b_hak)
    d = y.cakisma_devamsizliga_sigar_mi(4, 3, 1)
    kontrol("4+3 saatlik derste 1 saat çakışma sığar", True, d["sigar"])
    kontrol("  tek derse yığılabilir (1 <= 1.2)", True,
            d["tek_derse_yigilabilir"])
    d = y.cakisma_devamsizliga_sigar_mi(4, 4, 2)
    kontrol("4+4 saatlik derste 2 saat çakışma sığar", True, d["sigar"])
    kontrol("  ama tek derse yığılamaz (2 > 1.2)", False,
            d["tek_derse_yigilabilir"])
    kontrol("  kalan pay 0.4 saat", 0.4, d["kalan_pay"])
    d = y.cakisma_devamsizliga_sigar_mi(3, 3, 2)
    kontrol("3+3 saatlik derste 2 saat çakışma SIĞMAZ", False, d["sigar"])
    d = y.cakisma_devamsizliga_sigar_mi(3, 3, 3)
    kontrol("tam örtüşme hiç sığmaz", False, d["sigar"])
    d = y.cakisma_devamsizliga_sigar_mi(4, 3, 1, a_uygulama=True)
    kontrol("uygulama dersinde hak daralır (0.8+0.9 >= 1)", True, d["sigar"])
    d = y.cakisma_devamsizliga_sigar_mi(2, 2, 1, a_uygulama=True,
                                        b_uygulama=True)
    kontrol("iki uygulama, 1 saat çakışma sığmaz (0.4+0.4)", False,
            d["sigar"])

    print("")
    print("  === Kohort açığı: yarıyıl plana ulaşabiliyor mu? ===")
    # Gerçek vaka (5. yarıyıl): Cebir 6->5, DifGeo 6->5, Sayılar 4->3
    # düşürüldü, düşen 3 AKTS YENİ "Uygulamalı Matematik I" (3) dersine
    # taşındı. O ders 2023 girişlinin planında yok; eski beşliyi
    # tamamlayan öğrenci 27'de kalıyor ve bu açık yarıyıl içinde
    # KAPANMIYOR.
    sahte_muf = {
        "yariyillar": {5: {"toplam_akts": 30}},
        "dersler": {
            "A": {"ders_adi": "Kompleks Analiz I", "akts": 6, "yariyil": 5,
                  "tip": "Zorunlu"},
            "B": {"ders_adi": "Fonksiyonel Analiz I", "akts": 4,
                  "yariyil": 5, "tip": "Zorunlu"},
            "C": {"ders_adi": "Diferensiyel Geometri I", "akts": 5,
                  "yariyil": 5, "tip": "Zorunlu"},
            "D": {"ders_adi": "Cebir I", "akts": 5, "yariyil": 5,
                  "tip": "Zorunlu"},
            "E": {"ders_adi": "Sayılar Teorisi I", "akts": 3, "yariyil": 5,
                  "tip": "Zorunlu"},
            "2709547": {"ders_adi": "Uygulamalı Matematik I", "akts": 3,
                        "yariyil": 5, "tip": "Zorunlu"},
            "S1": {"ders_adi": "Nümerik Analiz I", "akts": 4, "yariyil": 5,
                   "tip": "Seçmeli"},
            "S2": {"ders_adi": "Matris Matematiği I", "akts": 4,
                   "yariyil": 5, "tip": "Seçmeli"},
        }}
    katalog = [{"ders_no": k, "doldu": False} for k in sahte_muf["dersler"]]
    plan5 = {5: 30}

    gecilen = [
        {"ders_adi": "Kompleks Analiz I", "akts": 6, "donem": 5},
        {"ders_adi": "Fonksiyonel Analiz I", "akts": 4, "donem": 5},
        {"ders_adi": "Diferensiyel Geometri I", "akts": 5, "donem": 5},
        {"ders_adi": "Cebir I", "akts": 5, "donem": 5},
        {"ders_adi": "Sayılar Teorisi I", "akts": 3, "donem": 5},
        {"ders_adi": "Nümerik Analiz I", "akts": 4, "donem": 5},
    ]

    # (a) 2023 girişli: yeni ders planında yok, seçmeli kotası dolu ->
    #     3 AKTS KALICI açık.
    r = y.yariyil_acigi(5, gecilen, set(), sahte_muf, plan5, 2023, katalog)
    kontrol("eski ders kümesi 27'de kalıyor", 27, r["sonra"])
    kontrol("eksik 3 AKTS", 3, r["eksik"])
    kontrol("kalıcı açık 3 AKTS", 3, r["kalici"])
    kontrol("açığın sebebi adıyla bildiriliyor", ["Uygulamalı Matematik I"],
            [d["ders_adi"] for d in r["kohort_disi"]])
    kontrol("kohort dışı ders ADAY gösterilmiyor", [],
            [a["ders_no"] for a in r["adaylar"]])

    # (b) 2024 girişli AYNI transkriptle: ders planında VAR, alınca
    #     yarıyıl tam 30'a ulaşıyor - ne açık ne fazla, rapor edilecek
    #     bir şey yok.
    kontrol("2024 girişlide açık yok", None,
            y.yariyil_acigi(5, gecilen, set(), sahte_muf, plan5, 2024,
                            katalog))
    # Fark tam olarak burada: AYNI transkript, AYNI ders kümesi.
    # 2023 girişlinin planında o ders yok, 3 AKTS kalıcı açık doğuyor;
    # 2024 girişli aynı dersi alabildiği için yarıyıl tam kapanıyor.
    kontrol("aynı transkript, kohorta göre farklı sonuç", (3, None),
            (r["kalici"],
             y.yariyil_acigi(5, gecilen, set(), sahte_muf, plan5, 2024,
                             katalog)))
    kontrol("2024'te ders kohort dışı sayılmıyor", [],
            [d["ders_adi"] for d in
             (y.yariyil_acigi(5, gecilen[:5], set(), sahte_muf, plan5, 2024,
                              katalog) or {"kohort_disi": []})["kohort_disi"]])

    # (c) Seçmeliyi henüz almamış öğrenci: standart kota (1 ders, 4 AKTS)
    #     zaten hesaba katıldığı için kalıcı açık DEĞİŞMEZ - 23 + 4 = 27,
    #     yine 3 eksik. Seçmeliyi almış olmak (a) ile almamış olmak (c)
    #     aynı sonucu vermeli; aradaki fark açığın büyüklüğü değil, o
    #     öğrencinin daha kaç ders yazacağı.
    r_bos = y.yariyil_acigi(5, gecilen[:5], set(), sahte_muf, plan5, 2023,
                            katalog)
    kontrol("seçmeliyi almamış olmak kalıcı açığı değiştirmez", 3,
            r_bos["kalici"])
    kontrol("  ama bu dönem eksiği 7 AKTS", 7, r_bos["eksik"])
    kontrol("  standart seçmeli kotası sayılıyor", 4, r_bos["havuz_ile"])

    # (d) AKTS'si ARTAN dersi düşük değerken geçen: Lineer Cebir 6->5->6.
    #     Ders geçildiği için tekrar alınamaz, açık kapanmaz.
    lin_muf = {"yariyillar": {1: {"toplam_akts": 10}},
               "dersler": {
                   "L": {"ders_adi": "Lineer Cebir I", "akts": 6,
                         "yariyil": 1, "tip": "Zorunlu"},
                   "M": {"ders_adi": "Türk Dili I", "akts": 4,
                         "yariyil": 1, "tip": "Zorunlu"}}}
    lin_gec = [{"ders_adi": "Lineer Cebir I", "akts": 5, "donem": 1},
               {"ders_adi": "Türk Dili I", "akts": 4, "donem": 1}]
    rl = y.yariyil_acigi(1, lin_gec, set(), lin_muf, {1: 10}, 2023)
    kontrol("düşük AKTS ile geçilen ders 1 AKTS kalıcı açık", 1,
            rl["kalici"])
    kontrol("  ders adıyla bildiriliyor", "Lineer Cebir I",
            rl["dusuk_gecilen"][0]["ders_adi"])
    kontrol("  eski/yeni değer taşınıyor", (5, 6),
            (rl["dusuk_gecilen"][0]["gecilen_akts"],
             rl["dusuk_gecilen"][0]["guncel_akts"]))

    # (e) Kotanın ÜSTÜNDE ders alınırsa fazla raporlanmalı. Mezuniyet
    #     AKTS'si bir toplamdır: 5. yarıyıldan fazladan alınan ders 1.
    #     yarıyılın açığını da kapatır. Eskiden fazla hiç sayılmıyordu ve
    #     danışman panonun dediğini yapınca sayı kıpırdamıyordu.
    tam = gecilen + [{"ders_adi": "Matris Matematiği I", "akts": 4,
                      "donem": 5}]
    r_fazla = y.yariyil_acigi(5, tam, set(), sahte_muf, plan5, 2023,
                              katalog)
    kontrol("ikinci seçmeli alınınca kalıcı açık kalmıyor", 0,
            r_fazla["kalici"])
    kontrol("plandan fazlası 1 AKTS olarak sayılıyor", 1, r_fazla["fazla"])
    top_fazla = y.kohort_acigi(tam, set(), sahte_muf, plan5, 2023, katalog,
                               yariyillar=(5,))
    kontrol("fazla, net açıktan düşülüyor", -1, top_fazla["net"])
    kontrol("mezuniyet AKTS'si fazlayla yükseliyor", 31,
            top_fazla["mezuniyet_akts"])

    # Tam plana oturan yarıyıl hiç rapor edilmez.
    kontrol("plana tam oturan yarıyılda uyarı yok", None,
            y.yariyil_acigi(5, gecilen[:5] + [
                {"ders_adi": "Nümerik Analiz I", "akts": 4, "donem": 5},
                {"ders_adi": "Matris Matematiği I", "akts": 3, "donem": 5}],
                set(), sahte_muf, plan5, 2023, katalog))

    # (f) kohort_acigi toplamı ve mezuniyet AKTS'si
    top = y.kohort_acigi(gecilen, set(), sahte_muf, plan5, 2023, katalog,
                         yariyillar=(5,))
    kontrol("kohort açığı toplanıyor", 3, top["toplam"])
    kontrol("mezuniyet AKTS'si düşüyor", 27, top["mezuniyet_akts"])

    print("")
    print("  === Azami süre sınırı (MADDE 16/1) ===")
    # Sınır son yılın SONUNDA değil BAŞINDA dolar: 2019 girişli 2026
    # güzünde 8. öğretim yılına başlar, dört yıllık programda azami 7
    # yıl olduğu için o kayıt aşılmıştır. "0 yıl kaldı ama aşılmadı"
    # diye bir durum yoktur - mutasyon denemesinde bu kusuru hiçbir
    # test yakalamamıştı.
    for ogrno, bek_kalan, bek_asildi in (("200000001", 1, False),
                                         ("190000001", 0, True),
                                         ("180000001", -1, True)):
        r = y.azami_sure_durumu(ogrno, 2026)
        kontrol("%s: kalan %d yıl" % (ogrno, bek_kalan),
                bek_kalan, r["kalan_yil"])
        kontrol("  aşıldı mı", bek_asildi, r["asildi"])
    kontrol("kalan 0 ile aşıldı çelişmiyor", True,
            y.azami_sure_durumu("190000001", 2026)["asildi"])

    print("")
    print("  === Not yükseltme kapsamı (MADDE 9/1-d) ===")
    # "BB'den daha düşük not aldığı ders/dersler". DD bağıl sistemden
    # gelir ve GEÇER sayılır, ama BB'nin altındadır - yükseltmeye açık.
    for harf, bek in (("CB", True), ("CC", True), ("DC", True),
                      ("DD", True), ("BB", False), ("BA", False),
                      ("AA", False), ("FF", False)):
        kontrol("%s yükseltilebilir mi" % harf, bek,
                y.not_yukseltilebilir_mi(harf))
    kontrol("DD aynı anda GEÇER sayılıyor", "gecti",
            y.transkript_harf_durumu("DD"))

    print("")
    print("  === Sonradan eklenen dersler / kohort eşleşmesi ===")
    kontrol("2023 girişli Uyg.Mat. I almaz", True,
            y.kohort_disi_mi("2709547", 2023))
    kontrol("2024 girişli alır", False, y.kohort_disi_mi("2709547", 2024))
    kontrol("giriş yılı bilinmiyorsa ders elenmez", False,
            y.kohort_disi_mi("2709547", None))
    kontrol("listede olmayan ders hiç elenmez", False,
            y.kohort_disi_mi("2709151", 2023))
    kontrol("2023'ün almayacağı dört ders", 4,
            len(y.kohort_disi_kodlar(2023)))

    # belge_karsiligi: kod DEĞİŞMİŞSE ada, ad KISALTILMIŞSA koda düşer.
    belge = {"2709171": {"ders_adi": "Lineer Cebir I"},
             "2709162": {"ders_adi": "Atatürk İlk. ve İnk. Tarihi I"}}
    kontrol("kod tutuyorsa kod kullanılır", "2709162",
            y.belge_karsiligi("2709162",
                              "ATATÜRK İLKELERİ VE İNKILAP TARİHİ 1", belge))
    kontrol("kod değişmişse ad benzerliği tutar", "2709171",
            y.belge_karsiligi("2709155", "LİNEER CEBİR I", belge))
    kontrol("hiçbiri tutmazsa None", None,
            y.belge_karsiligi("9999999", "Bambaşka Bir Ders", belge))

    print("")
    print("  %d/%d kontrol geçti." % (sum(OK), len(OK)))
    return 0 if all(OK) else 1


if __name__ == "__main__":
    sys.exit(main())
