# -*- coding: utf-8 -*-
"""Dosya yolları — normal çalışmada ve exe içinde.

Neden ayrı bir modül
--------------------
Python'da `__file__` her şeyi çözer. Exe'ye derlendiğinde çözmez ve
sessizce yanlış yeri gösterir: ölçüldü, `veri/` klasörü exe'nin yanına
konduğunda program **hiç uyarı vermeden sıfır ders** okudu. AKTS
doğruluğu üzerine kurulu bir araçta bu kabul edilemez.

İki AYRI kök var, karıştırılmamalı:

  OKUNAN (veri/)        Müfredat, ders programı, AKTS referansı.
                        Exe'de bunlar exe'nin İÇİNE gömülüdür; PyInstaller
                        çalışırken geçici bir klasöre açar (sys._MEIPASS).
                        Kullanıcı bu klasörü görmez, görmesi de gerekmez.

  YAZILAN (cikti/, chrome-profili/)
                        Pano, ham sayfalar, tarayıcı profili. Bunlar
                        exe'nin YANINA yazılmalı ki danışman bulabilsin.
                        Geçici klasöre yazarsak program kapanınca silinir.

`donmus()` ikisini ayırmanın tek yeri; başka hiçbir modül sys.frozen
bilmek zorunda değil.
"""
import os
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent


def donmus():
    """Exe olarak mı çalışıyoruz? (PyInstaller)"""
    return getattr(sys, "frozen", False)


def okunan_kok():
    """Gömülü veri dosyalarının kökü."""
    if donmus():
        # onefile'da _MEIPASS geçici açılma klasörü, onedir'de _internal.
        return Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
    return BURASI


def yazilan_kok():
    """Çıktının yazılacağı kök - exe'nin yanı, script'in yanı."""
    if donmus():
        return Path(sys.executable).resolve().parent
    return BURASI


def veri(*parcalar):
    """veri/ altındaki bir dosya (okunur)."""
    return okunan_kok().joinpath("veri", *parcalar)


def cikti(*parcalar):
    """cikti/ altındaki bir dosya (yazılır)."""
    return yazilan_kok().joinpath("cikti", *parcalar)


def profil():
    """Chrome'un kalıcı profil klasörü (yazılır)."""
    return yazilan_kok() / "chrome-profili"


def env_dosyasi():
    """Varsa .env dosyasının yolu.

    Exe'nin yanında, sonra depo kökünde aranır. Bulunamazsa None döner;
    o zaman giriş bilgileri kullanıcıya sorulur.
    """
    adaylar = [yazilan_kok() / ".env"]
    if not donmus():
        adaylar.append(BURASI.parent / ".env")
    for aday in adaylar:
        if aday.exists():
            return aday
    return None


def bilgi():
    """Tanılama için: hangi kök neresi?"""
    return {
        "donmus": donmus(),
        "okunan_kok": str(okunan_kok()),
        "yazilan_kok": str(yazilan_kok()),
        "veri": str(veri()),
        "cikti": str(cikti()),
        "env": str(env_dosyasi() or "-"),
    }


if __name__ == "__main__":
    for anahtar, deger in bilgi().items():
        print("%-12s %s" % (anahtar, deger))
    print("")
    print("veri/ içeriği:")
    klasor = veri()
    if klasor.is_dir():
        for dosya in sorted(os.listdir(str(klasor))):
            print("   " + dosya)
    else:
        print("   (klasör yok: %s)" % klasor)
