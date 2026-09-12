# -*- coding: utf-8 -*-
"""Kurulum sihirbazı testleri — yeni bir bölüm sıfırdan kurulabiliyor mu?

Neyi koruyor
------------
Aracın Matematik dışında da işe yaraması TEK bir şeye bağlı: bölüme özgü
her sayının belgeden türetilebilmesi ya da danışmana açıkça sorulması.
Arada kalan üçüncü bir ihtimal var ve asıl tehlike o: değerin sessizce
Matematik'ten miras alınması. O zaman araç çalışır, pano dolar, sayılar
makul görünür ve hepsi yanlıştır.

Bu yüzden testler uydurma bir bölümün belgeleriyle SIFIRDAN kurulum
yapıp şunlara bakıyor:

  * türetilenler doğru mu (plan, TOS, sonradan eklenen ders)
  * insana sorulması gereken alanlar BOŞ mu bırakılmış
  * boş bırakılan alanla profil AÇILMIYOR mu (sessiz varsayılan yok)
  * --otomatik çalışan profilin üstüne yazmıyor mu

Ayrıca bağımsız bir doğrulama: ders programının saat sütunları elle
kodlanmıştı; sihirbazın xlsx'ten okuduğu düzen onunla BİREBİR tutuyor mu?
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

import bolum                                              # noqa: E402
import ders_programi as dp                                # noqa: E402
import kurulum                                            # noqa: E402
import sentetik_mufredat as sm                            # noqa: E402

OK = []


def kontrol(ad, beklenen, gelen):
    tamam = beklenen == gelen
    print(("  [OK]  " if tamam else "  [HATA] ") + ad +
          ("" if tamam else "\n          beklenen=%r\n          gelen   =%r"
           % (beklenen, gelen)))
    OK.append(tamam)


# Kurulumu AYRI bir süreçte, uydurma bir veri klasörüyle çalıştırıyoruz;
# gerçek veri/ klasörüne dokunulmuyor.
BETIK = u'''# -*- coding: utf-8 -*-
import sys
from pathlib import Path
sys.path.insert(0, %(kok)r)
import yollar
_veri = Path(%(veri)r)
yollar.veri = lambda *p: _veri.joinpath(*p)
import kurulum
kurulum.VERI = _veri
kurulum.ARSIV = _veri / "mufredat"
kurulum.PROGRAM_XLSX = _veri / "ders_programi.xlsx"
sys.exit(kurulum.main(%(argv)r))
'''


def _calistir(veri, argv):
    klasor = tempfile.mkdtemp(prefix="dkk_kur_betik_")
    try:
        betik = os.path.join(klasor, "kos.py")
        with io.open(betik, "w", encoding="utf-8") as f:
            f.write(BETIK % {"kok": KOK, "veri": veri, "argv": argv})
        c = subprocess.run([sys.executable, betik], capture_output=True,
                           text=True, encoding="utf-8", errors="replace",
                           env=dict(os.environ, PYTHONIOENCODING="utf-8"))
        return c.returncode, c.stdout, c.stderr
    finally:
        shutil.rmtree(klasor, ignore_errors=True)


def _yeni_bolum_kurulumu():
    print("")
    print("  === Yeni bölüm: sıfırdan kurulum ===")
    kok = tempfile.mkdtemp(prefix="dkk_yenibolum_")
    veri = os.path.join(kok, "veri")
    os.makedirs(os.path.join(veri, "mufredat"))
    try:
        sm.sinama_arsivi(os.path.join(veri, "mufredat"))

        kod, cikti, hata = _calistir(veri, ["--denetle"])
        kontrol("profilsiz --denetle sıfırdan farklı dönüyor", True,
                kod != 0)
        kontrol("profilin yokluğu bildiriliyor", True,
                "YOK" in cikti)
        kontrol("dört belge görülüyor", True,
                all(str(y) in cikti for y in (2023, 2024, 2025, 2026)))

        kod, cikti, hata = _calistir(veri, ["--otomatik"])
        kontrol("--otomatik çalışıyor", 0, kod)
        taslak_yolu = os.path.join(veri, "bolum.taslak.json")
        kontrol("taslak yazıldı", True, os.path.exists(taslak_yolu))
        kontrol("gerçek profile DOKUNULMADI", False,
                os.path.exists(os.path.join(veri, "bolum.json")))

        p = json.load(io.open(taslak_yolu, encoding="utf-8"))
        kontrol("plan belgeden çıktı", 240,
                sum(p["plan"]["donem_akts"].values()))
        kontrol("TOS dersleri çıktı", ["9801746", "9801747"],
                sorted(p["tos"]["dersler"]))
        kontrol("sonradan eklenen ders çıktı", {"9801163": 2024},
                p["kohort"]["sonradan_eklenen_dersler"])
        kontrol("Matematik'in TOS dersi sızmadı", False,
                any(k.startswith("2709") for k in p["tos"]["dersler"]))
        kontrol("Matematik'in planı sızmadı", False,
                32 in p["plan"]["donem_akts"].values())

        # İnsana sorulması gerekenler BOŞ olmalı - uydurulmamalı
        kontrol("program yılı boş bırakıldı", None,
                p["bolum"]["program_yili"])
        kontrol("bölüm adı boş bırakıldı", "", p["bolum"]["ad"])
        kontrol("açık kapatma yarıyılı boş bırakıldı", None,
                p["kohort"]["acik_kapatma_yariyili"])

        # ...ve böyle bir dosya profil olarak KULLANILAMAZ
        agir = [m for s, m in bolum.denetle(p) if s == "HATA"]
        kontrol("yarım taslak profil olarak açılmıyor", True, bool(agir))

        # Danışman boşlukları doldurunca açılıyor
        p["bolum"]["ad"] = "Sınama"
        p["bolum"]["program_yili"] = 4
        p["kohort"]["acik_kapatma_yariyili"] = 3
        p["tos"]["azami_adet"] = 1
        kontrol("boşluklar dolunca profil geçerli", [],
                [m for s, m in bolum.denetle(p) if s == "HATA"])

        # --otomatik GEÇERLİ bir profilin üstüne yazmamalı
        with io.open(os.path.join(veri, "bolum.json"), "w",
                     encoding="utf-8") as f:
            f.write(json.dumps(p, ensure_ascii=False))
        imza = io.open(os.path.join(veri, "bolum.json"),
                       encoding="utf-8").read()
        kod, cikti, _ = _calistir(veri, ["--otomatik"])
        kontrol("--otomatik yine taslağa yazdı", 0, kod)
        kontrol("çalışan profil bozulmadı", imza,
                io.open(os.path.join(veri, "bolum.json"),
                        encoding="utf-8").read())

        # Artık --denetle temiz
        kod, cikti, _ = _calistir(veri, ["--denetle"])
        kontrol("kurulum tamam raporu", 0, kod)
        kontrol("eksik kalmadı", True, "yok — kurulum tamam" in cikti)
        kontrol("dört yıllık çıkarım gücü bildiriliyor", True,
                "2023-2026 girişleri için" in cikti)
    finally:
        shutil.rmtree(kok, ignore_errors=True)


def _belge_listesi_kontrolu():
    print("")
    print("  === Danışmandan istenenler listesi ===")
    m = kurulum.BELGE_LISTESI
    kontrol("müfredat belgesi isteniyor", True, "Okutulacak Dersler" in m)
    kontrol("nereye konacağı yazıyor", True, "veri/mufredat/" in m)
    kontrol("ders programı isteniyor", True, "ders_programi.xlsx" in m)
    kontrol("tek yılın yetmediği söyleniyor", True,
            "En az iki" in m)
    kontrol("öğrenci verisi İSTENMEDİĞİ yazıyor", True,
            "NE İSTEMİYORUZ" in m)


def _program_duzeni_kontrolu():
    """Sihirbazın xlsx'ten okuduğu düzen, elle kodlananla tutuyor mu?

    Bu bağımsız bir doğrulama: saat sütunları Matematik için elle
    yazılmıştı. Sihirbaz aynı dosyadan aynı düzeni çıkarıyorsa okuma
    mantığı doğrudur ve başka bölümün programında da işe yarar.
    """
    print("")
    print("  === Ders programı düzeni kendiliğinden çıkıyor mu? ===")
    d = kurulum.program_duzeni()
    if not d:
        print("  veri/ders_programi.xlsx yok, atlandı")
        return
    if d.get("hata"):
        print("  " + d["hata"] + " — atlandı")
        return
    kontrol("doğru sayfa seçildi", dp.SAYFA_ADI, d["sayfa_adi"])
    kontrol("saat sütunları elle kodlananla aynı", dp.SAAT_SUTUNLARI,
            d["saat_sutunlari"])


def main():
    _belge_listesi_kontrolu()
    _yeni_bolum_kurulumu()
    _program_duzeni_kontrolu()
    print("")
    print("  %d/%d kontrol geçti." % (sum(OK), len(OK)))
    return 0 if all(OK) else 1


if __name__ == "__main__":
    sys.exit(main())
