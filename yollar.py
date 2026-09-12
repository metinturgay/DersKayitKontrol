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
import json
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


# =========================================================================
#  YEREL KURULUM KATMANI
# =========================================================================
# Danışman kendi belgelerini verdiğinde çözülmüş dosyalar BURAYA yazılır:
# exe'nin YANINDA, kalıcı. Gömülü veri/ ise salt okunur bir yedek olarak
# kalır (exe'yi derleyen bölümün verisi).
#
# TÜMÜ-YA-DA-HİÇ: yerel kurulum tamamsa, kurulumun ÜRETTİĞİ her dosya
# oradan okunur; biri eksikse gömülüye DÜŞÜLMEZ. Dosya başına düşmek,
# "kullanıcının planı + başka bölümün ders kataloğu" gibi karışık bir
# yapılandırma üretirdi ve hiçbir denetim bunu yakalayamazdı.
YEREL_KLASOR = "veri-yerel"
DAMGA = "kurulum_tamam.json"

_damga_onbellek = None


def yerel_veri_kok():
    """Danışmanın kendi kurulumunun klasörü (yazılır)."""
    return yazilan_kok() / YEREL_KLASOR


def yerel_damga(zorla=False):
    """Yerel kurulum tamamlanmış mı? Damga sözlüğü ya da None."""
    global _damga_onbellek
    if _damga_onbellek is not None and not zorla:
        return _damga_onbellek or None
    yol = yerel_veri_kok() / DAMGA
    veri = None
    if yol.exists():
        try:
            veri = json.loads(yol.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            veri = None
    _damga_onbellek = veri or {}
    return veri


def yerel_hazir_mi():
    return yerel_damga() is not None


def yerel_dosyalar():
    """Yerel kurulumun SAHİP OLDUĞU dosya adları."""
    d = yerel_damga() or {}
    return set(d.get("dosyalar") or ())


def damga_yaz(bilgi):
    """Yerel kurulumu 'tamam' diye işaretler. EN SON çağrılmalı.

    Damga yazılmadan önce yerel klasör yok sayılır; yarım kalmış bir
    kurulum (Ctrl+C, disk dolması, bozuk belge) sessizce devreye
    giremez.
    """
    global _damga_onbellek
    kok = yerel_veri_kok()
    kok.mkdir(parents=True, exist_ok=True)
    (kok / DAMGA).write_text(
        json.dumps(bilgi, ensure_ascii=False, indent=1), encoding="utf-8")
    _damga_onbellek = None
    return kok / DAMGA


def yerel_kaldir():
    """Damgayı siler: yerel kurulum devre dışı kalır (dosyalar durur)."""
    global _damga_onbellek
    yol = yerel_veri_kok() / DAMGA
    if yol.exists():
        yol.unlink()
    _damga_onbellek = None


def veri(*parcalar):
    """OKUNACAK veri dosyası. Yerel kurulum varsa oradan, yoksa gömülü.

    Yazmak için veri_yaz() kullanın: bu fonksiyon exe'de SALT OKUNUR
    bir geçici klasöre çıkabilir.
    """
    if parcalar and yerel_hazir_mi() and parcalar[0] in yerel_dosyalar():
        return yerel_veri_kok().joinpath(*parcalar)
    return okunan_kok().joinpath("veri", *parcalar)


def veri_yaz(*parcalar):
    """YAZILACAK veri dosyası — her zaman exe'nin yanındaki yerel klasör.

    Gömülü köke asla yazılmaz: orası exe'de geçici bir klasördür ve
    program kapanınca silinir.
    """
    yol = yerel_veri_kok().joinpath(*parcalar)
    yol.parent.mkdir(parents=True, exist_ok=True)
    return yol


def veri_kaynagi(*parcalar):
    """Bu dosya NEREDEN okunuyor? ('yerel kurulum' / 'gömülü')"""
    p = veri(*parcalar)
    try:
        p.relative_to(yerel_veri_kok())
        return "yerel kurulum"
    except ValueError:
        return "gömülü"


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
    d = yerel_damga()
    return {
        "donmus": donmus(),
        "okunan_kok": str(okunan_kok()),
        "yazilan_kok": str(yazilan_kok()),
        "veri (gömülü)": str(okunan_kok() / "veri"),
        "veri (yerel)": ("%s  [%d dosya, %s]"
                         % (yerel_veri_kok(), len(yerel_dosyalar()),
                            d.get("tarih", "?"))
                         if d else "%s  (yok - gömülü kullanılıyor)"
                         % yerel_veri_kok()),
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
