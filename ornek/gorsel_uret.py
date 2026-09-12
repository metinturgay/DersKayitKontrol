# -*- coding: utf-8 -*-
"""Örnek panonun ekran görüntülerini üretir (README için).

Önce `python ornek_uret.py` çalıştırılmış olmalı: görüntüler
`ornek/danisman_ozeti.html` dosyasından alınır ve o dosyada **gerçek
öğrenci verisi yoktur**. cikti/ klasörüne hiç bakılmaz.

    python ornek/gorsel_uret.py

Sonuç: ornek/gorseller/*.png

OBİS'e girmez, ağa çıkmaz; yalnız yereldeki HTML dosyasını açar.
Chrome'un kendi profili KULLANILMAZ (çerez/oturum taşımasın diye
geçici bir profil açılır).
"""
import os
import shutil
import sys
import tempfile
import time

BURASI = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(BURASI)
sys.path.insert(0, KOK)

PANO = os.path.join(BURASI, "danisman_ozeti.html")
HEDEF = os.path.join(BURASI, "gorseller")

# (dosya adı, açıklama, sayfayı hazırlayan JavaScript)
KARELER = [
    ("01-ogrenci.png",
     "Öğrenci sayfası: ilerleme çubuğu ve yarıyıl şeridi",
     "sec(OGRENCILER[3].no); document.getElementById('ana').scrollTop=0;"),
    ("02-yonetici.png",
     "Yönetici özeti: dağılımlar ve kontenjan planı",
     "document.getElementById('yonetici-dugme').click();"),
    ("03-transkript.png",
     "Transkript sekmesi",
     "sec(OGRENCILER[1].no); detaySekme='transkript';"
     " detayCiz(OGRENCILER[1]);"),
    ("04-cakisma.png",
     "Çakışma tablosu",
     "document.getElementById('cakisma-dugme').click();"),
    ("05-koyu.png",
     "Koyu tema",
     "sec(OGRENCILER[3].no); document.getElementById('ana').scrollTop=0;"),
]


def main():
    if not os.path.exists(PANO):
        print("Örnek pano yok. Önce: python ornek_uret.py")
        return 1
    try:
        from selenium import webdriver
    except ImportError:
        print("selenium kurulu değil: pip install selenium")
        return 1

    if os.path.isdir(HEDEF):
        shutil.rmtree(HEDEF)
    os.makedirs(HEDEF)

    profil = tempfile.mkdtemp(prefix="dkk_ss_")
    s = webdriver.ChromeOptions()
    s.add_argument("--headless=new")
    s.add_argument("--window-size=1440,1000")
    s.add_argument("--hide-scrollbars")
    s.add_argument("--force-device-scale-factor=1.5")   # keskin görüntü
    s.add_argument("--user-data-dir=" + profil)
    s.add_argument("--log-level=3")
    s.add_argument("--allow-file-access-from-files")
    d = webdriver.Chrome(options=s)
    try:
        for ad, aciklama, betik in KARELER:
            koyu = ad.startswith("05")
            if koyu:
                d.execute_cdp_cmd("Emulation.setEmulatedMedia", {
                    "features": [{"name": "prefers-color-scheme",
                                  "value": "dark"}]})
            d.get("file:///" + PANO.replace("\\", "/"))
            time.sleep(0.6)
            d.execute_script(betik)
            time.sleep(0.5)
            d.save_screenshot(os.path.join(HEDEF, ad))
            print("  %-16s %s" % (ad, aciklama))
            if koyu:
                d.execute_cdp_cmd("Emulation.setEmulatedMedia",
                                  {"features": []})
    finally:
        d.quit()
        shutil.rmtree(profil, ignore_errors=True)

    print("")
    print("Görüntüler: %s" % HEDEF)
    print("Hepsi uydurma verilerle üretildi.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
