# -*- coding: utf-8 -*-
"""Yerel kurulum katmanı testleri.

Neyi koruyor
------------
Danışman kendi belgelerini verdiğinde çözülmüş dosyalar exe'nin YANINA
(veri-yerel/) yazılmalı. Eskiden hepsi `yollar.veri()` ile GÖMÜLÜ köke
yazılıyordu; exe'de gömülü kök PyInstaller'ın geçici klasörüdür ve
oraya yazmak HATA VERMEZ - dosya oluşur, ekran "Kaydedildi" der ve
program kapanınca silinir. Kullanıcı kurulumun tuttuğunu sanır; ertesi
açılışta yine exe'ye gömülü başka bölümün verisi okunur.

İki kural sınanıyor:

  1. YAZMA hiçbir zaman gömülü köke gitmez.
  2. TÜMÜ-YA-DA-HİÇ: yerel kurulum ancak DAMGA yazılınca devreye girer.
     Yarım kalmış bir kurulum (dosyalar var, damga yok) yok sayılır.
     Dosya başına "yoksa gömülüye dön" olsaydı, kullanıcının planı +
     başka bölümün ders kataloğu gibi karışık bir yapılandırma oluşur
     ve hiçbir denetim bunu yakalayamazdı.
"""
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile

BURASI = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(BURASI)
sys.path.insert(0, KOK)
sys.path.insert(0, BURASI)

import yollar                                             # noqa: E402

OK = []


def kontrol(ad, beklenen, gelen):
    tamam = beklenen == gelen
    print(("  [OK]  " if tamam else "  [HATA] ") + ad +
          ("" if tamam else "\n          beklenen=%r\n          gelen   =%r"
           % (beklenen, gelen)))
    OK.append(tamam)


# Ayrı süreçte, uydurma bir "yazılan kök" ile modülleri yükler.
BETIK = u'''# -*- coding: utf-8 -*-
import json, sys
from pathlib import Path
sys.path.insert(0, %(kok)r)
import yollar
_y = Path(%(yaz)r)
yollar.yazilan_kok = lambda: _y
import bolum, mufredat, ders_programi, mufredat_arsivi, akts_degisimi
print(json.dumps({
    "yerel_hazir": yollar.yerel_hazir_mi(),
    "yerel_dosyalar": sorted(yollar.yerel_dosyalar()),
    "profil_kaynagi": bolum.kaynak(),
    "bolum": bolum.ad(),
    "plan_toplami": sum(bolum.donem_plani().values()),
    "mufredat_okuma": str(mufredat.mufredat_json()),
    "mufredat_yazma": str(mufredat.mufredat_json(True)),
    "cakisma_yazma": str(ders_programi.cakisma_json(True)),
    "arsiv_yazma": str(mufredat_arsivi.arsiv_json(True)),
    "profil_yazma": str(bolum.yol(True)),
    "referans": akts_degisimi.referans_yolu(),
}, ensure_ascii=False))
'''


def _sor(yazilan_kok):
    klasor = tempfile.mkdtemp(prefix="dkk_yol_")
    try:
        betik = os.path.join(klasor, "sor.py")
        with io.open(betik, "w", encoding="utf-8") as f:
            f.write(BETIK % {"kok": KOK, "yaz": yazilan_kok})
        c = subprocess.run([sys.executable, betik], capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        if c.returncode != 0:
            return None, c.stderr
        return json.loads(c.stdout), ""
    finally:
        shutil.rmtree(klasor, ignore_errors=True)


def _yerel_kur(kok, damgali=True):
    """Uydurma bir yerel kurulum kurar (başka bir bölüm profili)."""
    yerel = os.path.join(kok, yollar.YEREL_KLASOR)
    os.makedirs(yerel, exist_ok=True)
    p = json.load(io.open(os.path.join(KOK, "veri", "bolum.json"),
                          encoding="utf-8"))
    p["bolum"]["ad"] = "Sınama"
    p["bolum"]["fakulte"] = "Mühendislik Fakültesi"
    p["plan"]["donem_akts"] = {str(i): 31 for i in range(1, 9)}
    io.open(os.path.join(yerel, "bolum.json"), "w",
            encoding="utf-8").write(json.dumps(p, ensure_ascii=False))
    shutil.copy2(os.path.join(KOK, "veri", "mufredat.json"),
                 os.path.join(yerel, "mufredat.json"))
    if damgali:
        io.open(os.path.join(yerel, yollar.DAMGA), "w",
                encoding="utf-8").write(json.dumps(
                    {"tarih": "2026-09-12",
                     "dosyalar": ["bolum.json", "mufredat.json",
                                  "cakismalar.json"]},
                    ensure_ascii=False))
    return yerel


def main():
    kok = tempfile.mkdtemp(prefix="dkk_yazilan_")
    try:
        print("  === Yerel kurulum YOKKEN ===")
        g, hata = _sor(kok)
        if not g:
            print("  [HATA] süreç açılmadı:\n%s" % hata[-600:])
            OK.append(False)
            return 1
        kontrol("yerel hazır değil", False, g["yerel_hazir"])
        kontrol("profil gömülüden", "gömülü", g["profil_kaynagi"])
        kontrol("bölüm gömülü profilin bölümü", "Matematik", g["bolum"])
        kontrol("müfredat OKUMA gömülüden", True,
                os.path.join("veri", "mufredat.json") in g["mufredat_okuma"]
                and yollar.YEREL_KLASOR not in g["mufredat_okuma"])

        print("")
        print("  === YAZMA hiçbir zaman gömülü köke gitmiyor ===")
        for ad in ("mufredat_yazma", "cakisma_yazma", "arsiv_yazma",
                   "profil_yazma"):
            kontrol("%s yerel klasöre" % ad, True,
                    g[ad].startswith(os.path.join(kok, yollar.YEREL_KLASOR)))

        print("")
        print("  === Yarım kurulum (dosya var, DAMGA yok) ===")
        _yerel_kur(kok, damgali=False)
        g2, _ = _sor(kok)
        kontrol("yarım kurulum devreye GİRMİYOR", False, g2["yerel_hazir"])
        kontrol("profil hâlâ gömülüden", "gömülü", g2["profil_kaynagi"])
        kontrol("bölüm değişmedi", "Matematik", g2["bolum"])
        kontrol("plan değişmedi", 244, g2["plan_toplami"])

        print("")
        print("  === Damga yazılınca TÜMÜ birden yerele geçiyor ===")
        _yerel_kur(kok, damgali=True)
        g3, _ = _sor(kok)
        kontrol("yerel hazır", True, g3["yerel_hazir"])
        kontrol("profil yerelden", "yerel kurulum", g3["profil_kaynagi"])
        kontrol("bölüm yerel profilin bölümü", "Sınama", g3["bolum"])
        kontrol("plan yerel profilden", 248, g3["plan_toplami"])
        kontrol("müfredat OKUMA da yerelden", True,
                yollar.YEREL_KLASOR in g3["mufredat_okuma"])
        # Damgada OLMAYAN dosya gömülüden okunmalı (akts_referans.json
        # sihirbazın ürettiği bir dosya değil).
        kontrol("damgada olmayan dosya gömülüden", True,
                yollar.YEREL_KLASOR not in g3["referans"])

        print("")
        print("  === Kaynak kontrolü ===")
        kaynak = io.open(os.path.join(KOK, "yollar.py"),
                         encoding="utf-8").read()
        kontrol("veri_yaz gömülü köke bakmıyor", False,
                "okunan_kok" in kaynak.split("def veri_yaz")[1]
                .split("def ")[0])
        for modul, ad in (("mufredat.py", "mufredat_json"),
                          ("ders_programi.py", "cakisma_json"),
                          ("mufredat_arsivi.py", "arsiv_json")):
            k = io.open(os.path.join(KOK, modul), encoding="utf-8").read()
            kontrol("%s yol FONKSİYONLA çözülüyor" % modul, True,
                    ("def %s(" % ad) in k)
        # Modül düzeyinde donmuş yol kalmamalı
        import re
        for modul in ("mufredat.py", "ders_programi.py",
                      "mufredat_arsivi.py", "akts_degisimi.py"):
            k = io.open(os.path.join(KOK, modul), encoding="utf-8").read()
            donmus = [s for s in k.splitlines()
                      if re.match(r"^[A-Z_]+\s*=\s*(str\()?yollar\.veri", s)]
            kontrol("%s modül düzeyinde donmuş yol yok" % modul, [], donmus)
    finally:
        shutil.rmtree(kok, ignore_errors=True)

    print("")
    print("  %d/%d kontrol geçti." % (sum(OK), len(OK)))
    return 0 if all(OK) else 1


if __name__ == "__main__":
    sys.exit(main())
