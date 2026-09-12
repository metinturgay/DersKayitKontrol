# -*- coding: utf-8 -*-
"""Çok yıllı müfredat arşivi testleri.

Neyi koruyor
------------
Arşivin tek işi yılları karşılaştırıp şunları TÜRETMEK:

    sonradan eklenen ders · AKTS değişimi · kalkan ders · kohort tabanı

Bunlar bugüne kadar elle koda yazılıyordu; artık belgelerden çıkıyor.
Türetim sessizce yanlış çalışırsa kimse fark etmez, çünkü sonuç yine
makul görünür. Bu yüzden DEĞİŞİMLERİ ÖNCEDEN BİLDİĞİMİZ uydurma bir
bölümün belgeleri üretilip sonuç birebir sınanıyor
(bkz. sentetik_mufredat.py).

En kritik iki kural:
  * Ders KODU değişince ders "kalktı + yenisi eklendi" sayılmamalı.
  * Arşivin EN ESKİ yılında zaten duran bir ders "sonradan eklendi"
    sayılmamalı — ondan öncesini bilmiyoruz, uydurmuyoruz.
"""
import io
import os
import shutil
import sys
import tempfile

BURASI = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(BURASI)
sys.path.insert(0, KOK)
sys.path.insert(0, BURASI)

import akts_degisimi as ad                                # noqa: E402
import mufredat_arsivi as ma                              # noqa: E402
import sentetik_mufredat as sm                            # noqa: E402

OK = []


def kontrol(ad, beklenen, gelen):
    tamam = beklenen == gelen
    print(("  [OK]  " if tamam else "  [HATA] ") + ad +
          ("" if tamam else "\n          beklenen=%r\n          gelen   =%r"
           % (beklenen, gelen)))
    OK.append(tamam)


def _kaybi_besliyor_mu():
    """Arşiv, AKTS kaybı hesabına gerçekten bağlı mı?

    Arşiv doğru türetip sonra kimse kullanmasa hiçbir şey patlamaz;
    yeni bir bölümde AKTS kaybı SESSİZCE hep sıfır çıkar. Zincirin
    bağlı olduğunu görmek için iki şey sınanıyor:

      * ölçülmüş kayıt YOKKEN taban belgeden geliyor mu,
      * ölçülmüş kayıt VARKEN belgenin önüne geçiyor mu.

    İkincisi önemli: bir öğrencinin transkriptindeki AKTS, belgenin ne
    yazdığından daha güçlü kanıttır.
    """
    print("")
    print("  === Arşiv, AKTS kaybı hesabını besliyor mu? ===")

    # --- (a) JSON'dan okuma ------------------------------------------
    klasor = tempfile.mkdtemp(prefix="dkk_arsivref_")
    try:
        yol = os.path.join(klasor, "arsiv.json")
        io.open(yol, "w", encoding="utf-8").write(
            '{"kohort_akts": {"2023": {"9801101": 6}, '
            '"2026": {"9801101": 5, "9801102": null}}}')
        r = ad.arsiv_referanslari(yol)
        kontrol("JSON'dan kohort tabanı okunuyor",
                {2023: {"9801101": 6}, 2026: {"9801101": 5}}, r)
        kontrol("arşiv yoksa boş dönüyor", {},
                ad.arsiv_referanslari(os.path.join(klasor, "yok.json")))
        kontrol("giriş yılının belgesi seçiliyor", (6, 2023),
                ad._arsiv_degeri(r, 2023, "9801101"))
        kontrol("belgesiz yıl öncekine düşüyor", (6, 2023),
                ad._arsiv_degeri(r, 2025, "9801101"))
        kontrol("arşivden önceki giriş için taban yok", (None, None),
                ad._arsiv_degeri(r, 2019, "9801101"))
    finally:
        shutil.rmtree(klasor, ignore_errors=True)

    # --- (b) hesapla() bu tabanı kullanıyor mu? ----------------------
    mufredat = {"dersler": {
        "9801101": {"ders_no": "9801101", "ders_adi": "Analiz I",
                    "akts": 5, "yariyil": 1, "tip": "Zorunlu"}}}

    def deneme(no, yil, akts):
        return {no: {"denemeler": [{"ders_kodu": "9801101",
                                    "ders_adi": "Analiz I", "donem": 1,
                                    "yil": yil, "akts": akts}],
                     "kalinan": []}}

    asil = ad.arsiv_referanslari
    ad.arsiv_referanslari = lambda yol=None: {2023: {"9801101": 6}}
    try:
        # 2026 girişlinin kaydı var, 2023 girişlinin YOK: 2023'ün tabanı
        # yalnız belgeden gelebilir.
        t = {}
        t.update(deneme("260000001", "2026-2027", 5))
        t["230000001"] = {"denemeler": [], "kalinan": []}
        sonuc = ad.hesapla(t, mufredat)
        satir = [d for d in sonuc["dersler"]
                 if d.get("yeni_kod") == "9801101"]
        kontrol("ders satırı üretildi", 1, len(satir))
        if satir:
            kh = satir[0]["kohortlar"]
            kontrol("2023 tabanı belgeden geldi", 6, kh[2023]["eski_akts"])
            kontrol("kaynağı belge olarak yazıldı", True,
                    "belgesi" in kh[2023]["eski_kaynak"])
            # Belgede 6, güncel 5: kohort 1 AKTS kaybediyor.
            kontrol("kayıp hesaplandı", -1, kh[2023]["fark"])
        # Arşiv tabanı verdiğine göre "veri yok" uyarısı YAZILMAMALI
        kontrol("gereksiz 'veri yok' uyarısı yok", [],
                [u for u in sonuc["uyarilar"] if "değişmemiş kabul" in u])

        # Şimdi 2023 girişlinin de KAYDI olsun: ölçülmüş değer belgenin
        # önüne geçmeli (belge 6 diyor, transkript 4 diyor -> 4).
        t2 = {}
        t2.update(deneme("260000001", "2026-2027", 5))
        t2.update(deneme("230000001", "2023-2024", 4))
        sonuc2 = ad.hesapla(t2, mufredat)
        satir2 = [d for d in sonuc2["dersler"]
                  if d.get("yeni_kod") == "9801101"]
        if satir2:
            kh2 = satir2[0]["kohortlar"]
            kontrol("ölçülmüş kayıt belgenin önüne geçiyor", 4,
                    kh2[2023]["eski_akts"])
            kontrol("kaynağı transkript olarak yazıldı", True,
                    "kayd" in kh2[2023]["eski_kaynak"])
    finally:
        ad.arsiv_referanslari = asil


def main():
    klasor = tempfile.mkdtemp(prefix="dkk_arsiv_")
    try:
        sm.sinama_arsivi(klasor)

        print("  === Belgeler bulunuyor mu? ===")
        belgeler = ma.belgeleri_bul(klasor)
        kontrol("dört yıl bulundu", [2023, 2024, 2025, 2026],
                [y for y, _ in belgeler])
        kontrol("dosya adından yıl çözülüyor", 2024,
                ma.yil_coz("2024-2025 Okutulacak Dersler.docx"))
        kontrol("yılsız dosya atlanıyor", None,
                ma.yil_coz("Okutulacak Dersler.docx"))

        arsiv, hatalar = ma.oku(klasor)
        kontrol("hepsi okundu", [], hatalar)
        kontrol("ders sayıları makul", True,
                all(len(arsiv[y]["dersler"]) > 25 for y in arsiv))

        print("")
        print("  === Sonradan eklenen ders ===")
        se = ma.sonradan_eklenenler(arsiv)
        kontrol("yalnız 2024'te ortaya çıkan ders", {"9801163": 2024}, se)
        # En eski yılda zaten duranlar sayılmamalı
        kontrol("en eski yılın dersleri 'sonradan eklendi' değil", False,
                any(k.startswith("9801101") for k in se))
        # Kodu değişen ders yeni ders sayılmamalı
        kontrol("kodu değişen ders yeni sayılmıyor", False,
                "9801311" in se)

        print("")
        print("  === Kalkan ders ===")
        kd = ma.kaldirilanlar(arsiv)
        kontrol("yalnız 2025'ten sonra kalkan seçmeli",
                {"9801592": 2025}, kd)
        kontrol("kodu değişen ders kalkmış sayılmıyor", False,
                "9801301" in kd)

        print("")
        print("  === AKTS değişimi ===")
        deg = ma.akts_gecmisi(arsiv)
        kontrol("tek ders değişmiş", 1, len(deg))
        kontrol("değişen ders Analiz I", "Analiz I", deg[0]["ad"])
        kontrol("seyri doğru",
                {"2023": 6, "2024": 5, "2025": 5, "2026": 5},
                deg[0]["degerler"])
        kontrol("kod değişikliği AKTS değişimi sayılmıyor", False,
                any("Cebir" in d["ad"] for d in deg))

        print("")
        print("  === Kohort AKTS tabanı ===")
        kontrol("2023 girişli için Analiz I 6 AKTS", 6,
                ma.kohort_akts(arsiv, 2023).get("9801101"))
        kontrol("2025 girişli için Analiz I 5 AKTS", 5,
                ma.kohort_akts(arsiv, 2025).get("9801101"))
        # Belgesi olmayan ARA yıl: kendinden önceki belge geçerlidir
        kontrol("belgesiz yıl önceki belgeye düşüyor", 5,
                ma.kohort_akts(arsiv, 2024).get("9801101"))
        # Arşivden ÖNCEKİ giriş: tahmin yok
        kontrol("arşivden önceki giriş için taban yok", {},
                ma.kohort_akts(arsiv, 2019))

        print("")
        print("  === Kohort tabanları arşiv JSON'una giriyor mu? ===")
        # akts_degisimi bu tabloyu docx'e hiç dokunmadan okuyor; exe'ye
        # de belgeler degil bu JSON gomuluyor. Tablo eksik kalirsa yeni
        # bir bolumde AKTS kaybi tespiti SESSIZCE calismaz.
        tb = ma.kohort_tabanlari(arsiv)
        kontrol("dört yılın tabanı var", ["2023", "2024", "2025", "2026"],
                sorted(tb))
        kontrol("2023 tabanında Analiz I 6 AKTS", 6, tb["2023"]["9801101"])
        kontrol("2026 tabanında Analiz I 5 AKTS", 5, tb["2026"]["9801101"])
        kontrol("turet() tabloyu taşıyor", tb, ma.turet(arsiv)["kohort_akts"])

        print("")
        print("  === Profil için türetilenler ===")
        t = ma.turet(arsiv)
        kontrol("yarıyıl planı sekiz yarıyıl", list(range(1, 9)),
                sorted(t["donem_akts"]))
        kontrol("plan toplamı 240", 240, sum(t["donem_akts"].values()))
        kontrol("TOS dersleri bulundu", ["9801746", "9801747"],
                sorted(t["tos_dersleri"]))
        kontrol("TOS AKTS'si", 5, t["tos_akts"])

        print("")
        print("  === Tek belge: uydurma üretmiyor ===")
        tek = tempfile.mkdtemp(prefix="dkk_arsiv_tek_")
        try:
            shutil.copy2(os.path.join(klasor, "2026.docx"),
                         os.path.join(tek, "2026.docx"))
            a1, _ = ma.oku(tek)
            kontrol("tek yıl okundu", [2026], sorted(a1))
            kontrol("sonradan eklenen ÇIKARILMIYOR", {},
                    ma.sonradan_eklenenler(a1))
            kontrol("kalkan ders ÇIKARILMIYOR", {}, ma.kaldirilanlar(a1))
            kontrol("plan yine de çıkıyor", 240,
                    sum(ma.donem_plani(a1).values()))
        finally:
            shutil.rmtree(tek, ignore_errors=True)

        print("")
        print("  === Boş arşiv ===")
        bos = tempfile.mkdtemp(prefix="dkk_arsiv_bos_")
        try:
            kontrol("belge yok", [], ma.belgeleri_bul(bos))
            a0, _ = ma.oku(bos)
            kontrol("türetim boş ama çökmeyen sonuç veriyor",
                    {"yillar": [], "kohort_akts": {}, "donem_akts": {},
                     "tos_dersleri": {}, "tos_akts": None,
                     "sonradan_eklenen_dersler": {},
                     "kaldirilan_dersler": {}, "akts_degisenler": []},
                    ma.turet(a0))
        finally:
            shutil.rmtree(bos, ignore_errors=True)
    finally:
        shutil.rmtree(klasor, ignore_errors=True)

    _kaybi_besliyor_mu()

    print("")
    print("  %d/%d kontrol geçti." % (sum(OK), len(OK)))
    return 0 if all(OK) else 1


if __name__ == "__main__":
    sys.exit(main())
