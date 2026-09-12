# -*- coding: utf-8 -*-
"""Tek dosyalık DanismanOzeti.exe üretir.

    pip install pyinstaller
    python exe_yap.py

Sonuç: masaüstünde `DanismanOzeti.exe`. Tek başına gönderilebilir;
karşı tarafta Python gerekmez.

Neden --add-data
----------------
`veri/` klasörü (müfredat, ders programı, AKTS referansı) exe'nin
İÇİNE gömülüyor. Yanına konursa program onu bulamaz - ölçüldü, sessizce
sıfır ders okuyor. Gömülü olunca danışmanın hiçbir dosyayı yönetmesi
gerekmiyor: tek dosya, çift tık.

Bunun bedeli: müfredat ya da ders programı değişince exe'nin yeniden
derlenmesi gerekir. Bu bilinçli bir seçim - yanlış yere konmuş bir
belgeyle SESSİZCE yanlış AKTS hesaplamaktansa, güncelleme için
buraya dönmek yeğdir.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

BURASI = Path(__file__).resolve().parent
AD = "DanismanOzeti"

# Gömülecek veri dosyaları. mufredat.json ve cakismalar.json çözülmüş
# hâller; docx/xlsx olmadan da çalışsın diye ikisi de giriyor.
VERI = ["bolum.json",
        "mufredat.docx", "mufredat.json",
        "ders_programi.xlsx", "cakismalar.json",
        "akts_referans.json"]

# Varsa gömülür, yoksa derleme durmaz. mufredat_arsivi.json yalnız son
# 4-5 yılın belgesini veren bölümlerde oluşur; Matematik'te tek yıllık
# belge olduğu için hiç üretilmiyor. Zorunlu listeye koymak, arşivi
# olmayan her bölümde derlemeyi sebepsiz yere durdururdu.
ISTEGE_BAGLI = ["mufredat_arsivi.json"]

# PyInstaller bunları kendi bulamıyor: hepsi dolaylı import ediliyor.
#
# panoyu_yenile özellikle önemli: ders_kayit onu FONKSİYON İÇİNDE import
# ediyor (döngüsel içe aktarmayı önlemek için). PyInstaller bugün onu
# yine de buluyor - ölçüldü, PYZ arşivinde var - ama bu listenin var
# olma sebebi o keşfe güvenmemek. Modül düşerse tek öğrenci tazeleme
# taramadan SONRA ImportError ile çöker; en pahalı anda.
GIZLI = ["bs4", "dotenv", "openpyxl", "yollar", "bolum", "eslestirme",
         "yonetmelik", "ozet", "rapor", "mufredat", "mufredat_arsivi",
         "ders_programi", "akts_degisimi", "ders_kayit",
         "panoyu_yenile", "kurulum", "kaynaklar"]


def main():
    try:
        import PyInstaller                                 # noqa: F401
    except ImportError:
        print("PyInstaller kurulu değil:")
        print("    pip install pyinstaller")
        return 1

    eksik = [d for d in VERI if not (BURASI / "veri" / d).exists()]
    if eksik:
        print("veri/ altında eksik dosya var, önce bunları üretin:")
        for d in eksik:
            print("   " + d)
        print("   (python mufredat.py  /  python ders_programi.py)")
        return 1

    hedef = Path(os.path.expanduser("~")) / "Desktop"
    if not hedef.is_dir():
        hedef = BURASI
    # Windows'ta uzun yol derlemeyi kırıyor; kısa bir çalışma klasörü.
    # Klasör süreç numarasıyla AYRIŞTIRILIYOR: sabit bir ad kullanınca
    # iki derleme aynı anda koşarsa biri bitip klasörü silerken öteki
    # hâlâ oraya yazıyor ve "FileNotFoundError: warn-...txt" ile
    # çöküyor - üstelik exe yazılmış oluyor, yani "başarısız" diyen
    # çıktının yanında görünüşte sağlam bir dosya kalıyor.
    calisma = (Path(os.environ.get("TEMP", str(BURASI)))
               / ("dkk_exe_%d" % os.getpid()))

    komut = [sys.executable, "-m", "PyInstaller", "--noconfirm", "--onefile",
             "--name", AD, "--console",
             "--distpath", str(hedef),
             "--workpath", str(calisma / "w"),
             "--specpath", str(calisma),
             "--collect-all", "selenium"]
    gomulecek = list(VERI) + [d for d in ISTEGE_BAGLI
                              if (BURASI / "veri" / d).exists()]
    for d in gomulecek:
        komut += ["--add-data", str(BURASI / "veri" / d) + os.pathsep + "veri"]
    for m in GIZLI:
        komut += ["--hidden-import", m]
    komut.append(str(BURASI / "baslat.py"))

    print("Derleniyor... (birkaç dakika sürebilir)")
    print("Hedef: " + str(hedef / (AD + ".exe")))
    print("")
    exe = hedef / (AD + ".exe")
    onceki = exe.stat().st_mtime if exe.exists() else None

    sonuc = subprocess.run(komut, cwd=str(BURASI))
    if sonuc.returncode:
        print("")
        print("Derleme başarısız (çıkış kodu %d)." % sonuc.returncode)
        # Derleme patlayınca ESKİ exe yerinde kalır ve orada durduğu
        # için "hazır" görünür. Ölçüldü: hedef dosya kilitliyken
        # (virüs taraması yeni yazılan dosyayı açık tutuyordu)
        # PyInstaller "Erişim engellendi" deyip çıktı, masaüstündeki
        # eski exe olduğu gibi kaldı. Kaç saatlik olduğunu söylemezsek
        # eski exe yeniymiş gibi dağıtılır.
        if onceki is not None:
            import datetime
            print("")
            print("DİKKAT: %s hâlâ ESKİ sürüm (%s). Silinmedi ama"
                  % (exe, datetime.datetime.fromtimestamp(onceki)
                     .strftime("%d.%m.%Y %H:%M")))
            print("güncel DEĞİL; dağıtmadan önce derlemeyi tekrarlayın.")
            print("Dosya kilitliyse kapatıp yeniden deneyin (çalışan")
            print("exe, açık bir klasör önizlemesi ya da virüs taraması).")
        return sonuc.returncode

    print("")
    if exe.exists():
        print("Hazır: %s  (%.0f MB)"
              % (exe, exe.stat().st_size / 1024.0 / 1024.0))
        print("")
        print("Karşı tarafta gerekenler: yalnız Google Chrome.")
        print("Exe'yi boş bir klasöre koyup çift tıklamaları yeterli;")
        print("cikti/ klasörünü kendi yanına oluşturur.")
    else:
        print("Exe bulunamadı: " + str(exe))
        return 1

    shutil.rmtree(str(calisma), ignore_errors=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
