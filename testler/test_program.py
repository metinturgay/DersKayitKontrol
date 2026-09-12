# -*- coding: utf-8 -*-
"""Ders programı çözümleyicisi ve çakışma tespiti testi.

Gerçek programdan (veri/cakismalar.json) doğrulanmış vakalar.
"""
import os
import sys

BURASI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BURASI))
sys.path.insert(0, BURASI)

import ders_programi as dp

OK = []


def kontrol(ad, beklenen, gelen):
    tamam = beklenen == gelen
    print(("  [OK]  " if tamam else "  [HATA] ") + ad +
          ("" if tamam else "\n          beklenen=%r\n          gelen   =%r"
           % (beklenen, gelen)))
    OK.append(tamam)


def main():
    v = dp.yukle()
    if not v:
        print("  veri/cakismalar.json yok. Önce: python ders_programi.py")
        return 1

    d = v["dersler"]
    dizin = dp.cakisma_dizini(v)

    print("  === Ders adı ayrıştırma ===")
    # "Fuzzy Topoloji 1 (M4)   Prof. Dr. ..." tek satırda geliyor
    kontrol("derslik ve hoca ada karışmıyor", True, "Fuzzy Topoloji 1" in d)
    kontrol("  parantezli artık yok", [],
            [a for a in d if "(" in a])
    kontrol("imza hücresi ders sayılmadı", False, "Bölüm Başkanı" in d)

    print("")
    print("  === Asenkron ortak zorunlu dersler (dipnot) ===")
    for ad in ("Türk Dili 1", "Atatürk İlk. ve İnk. Tarihi 1", "İngilizce 1"):
        kontrol("%s asenkron" % ad, True, d[ad]["asenkron"])
        kontrol("  hiç çakışması yok", 0, len(dizin.get(ad, {})))
    # İngilizce 3 dipnotta yok, senkron
    kontrol("İngilizce 3 asenkron DEĞİL", False, d["İngilizce 3"]["asenkron"])

    print("")
    print("  === Gruplu ders (Fizik Lab. A/B) ===")
    kontrol("iki grup okundu", ["A", "B"], d["Fizik Laboratuvarı 1"]["gruplar"])

    print("")
    print("  === Doğrulanmış çakışmalar ===")
    # Perşembe r26 (Olasılık) ve r29 (Dinamik Sistemler) aynı saatlerde
    kontrol("Olasılık ve İstatistik 1 <-> Dinamik Sistemler 1", True,
            "Dinamik Sistemler 1" in dizin.get("Olasılık ve İstatistik 1", {}))
    kontrol("  3 saat çakışıyor", 3,
            len(dizin["Olasılık ve İstatistik 1"]["Dinamik Sistemler 1"]))
    # Çarşamba r22/r23 paralel
    kontrol("Topolojik Gruplar <-> Bağlantılı Uzaylar", True,
            "Bağlantılı Uzaylar" in dizin.get("Topolojik Gruplar", {}))
    kontrol("Fark Denklemleri 1 <-> Sonlu Farklar Yöntemi", True,
            "Sonlu Farklar Yöntemi" in dizin.get("Fark Denklemleri 1", {}))

    print("")
    print("  === TOS bloğu ===")
    kontrol("TOS programda tek blok", True, "TOS" in d)
    kontrol("  Salı öğleden sonra", ["SALI 13:15-14:00", "SALI 14:10-14:55"],
            d["TOS"]["saatler"])
    # Aynı saatteki 3. sınıf dersleriyle çakışıyor
    kontrol("TOS <-> Fuzzy Topoloji 1", True,
            "Fuzzy Topoloji 1" in dizin.get("TOS", {}))
    kontrol("TOS <-> Matris Matematiği 1", True,
            "Matris Matematiği 1" in dizin.get("TOS", {}))

    print("")
    print("  === Katalog eşleştirmesi ===")
    katalog = [
        {"ders_no": "2709719", "ders_adi": "SPEKTRAL GRAF TEORİSİ I (SEÇ)"},
        {"ders_no": "2709753", "ders_adi": "MATEMATİK UYGULAMALARI I"},
        {"ders_no": "2709746", "ders_adi": "ÖĞRENME PSİKOLOJİSİ*"},
        {"ders_no": "2615580", "ders_adi": "ARKEOLOJİ VE ARKEOMETRİ I"},
    ]
    h = dp.program_eslestir(katalog, v)
    kontrol("hepsi eşleşti", 4, len(h))
    kontrol("ad farklıysa benzerlikle bulur", "Spektral Graf Teori 1",
            h["2709719"]["program_adi"])
    kontrol("TOS dersi TOS bloğuna bağlanır", "TOS",
            h["2709746"]["program_adi"])
    kontrol("katalogda olmayan TOS da bağlanır", "TOS",
            h["2615580"]["program_adi"])
    kontrol("  bağlanma tipi işaretli", "tos_blogu", h["2615580"]["tip"])

    print("")
    print("  === Matematik Uygulamaları 1 (esnek ders) ===")
    # 4. sınıfın zorunlu uygulama dersi. Tabloda 27 saate yayılmış ama
    # sabit buluşma saati yok; danışman kararıyla çakışma analizinden
    # çıkarıldı.
    mu = d["Matematik Uygulamaları 1"]
    kontrol("esnek olarak işaretli", True, mu["esnek"])
    kontrol("tabloda çok saate yayılmış", True, mu["saat_sayisi"] > 20)
    kontrol("hiç çakışma üretmiyor", 0,
            len(dizin.get("Matematik Uygulamaları 1", {})))
    kontrol("başka hiçbir dersin listesinde yok", [],
            [a for a, x in dizin.items()
             if "Matematik Uygulamaları 1" in x])

    print("")
    print("  %d/%d kontrol geçti." % (sum(OK), len(OK)))
    return 0 if all(OK) else 1


if __name__ == "__main__":
    sys.exit(main())
