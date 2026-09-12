# -*- coding: utf-8 -*-
"""Panoyu diskteki ham sayfalardan yeniden üretir.

--html ile yapılmış bir taramadan sonra cikti/ klasöründe her öğrencinin
ders sayfası ve transkripti duruyor. Kural değiştirdiğimizde OBİS'e tekrar
girmeye, öğrencileri tekrar kilitleyip açmaya gerek yok; pano buradan
yeniden üretilebilir.

    python panoyu_yenile.py
"""
import datetime
import re

import akts_degisimi
import ders_kayit as dk
import ders_programi
import mufredat
import ozet
import rapor
import yollar

# DİKKAT: burayı __file__'dan türetmeyin. Exe'ye derlendiğinde __file__
# exe'nin yanını değil PyInstaller'ın geçici açılma klasörünü gösterir;
# ham sayfalar ise exe'nin YANINA yazılır. Ölçüldü: tek öğrenci
# tazelenince ham sayfa doğru yere yazılıyor ama pano burayı boş bulup
# "ders sayfası yok" deyip çıkıyordu - danışman panonun güncellendiğini
# sanıyordu. Yazılan kökün tek doğru kaynağı yollar.py.
CIKTI = yollar.cikti()


def main():
    sayfalar = sorted(CIKTI.glob("ders_sayfasi_*.html"))
    if not sayfalar:
        print("cikti/ altında ders sayfası yok.")
        print("Önce tarama yapın: python ders_kayit.py --tumu --pano --html")
        return 1

    program = ders_programi.yukle()
    mfr = mufredat.yukle()
    print("Ham sayfa: " + str(len(sayfalar))
          + ("  |  ders programı yüklü" if program else "")
          + ("  |  müfredat yüklü" if mfr else ""))
    toplananlar, atlanan = [], []

    for yol in sayfalar:
        no = re.search(r"ders_sayfasi_(\d+)\.html", yol.name).group(1)
        try:
            kayit = dk.ders_kaydini_coz(yol.read_text(encoding="utf-8"))
        except Exception as hata:                      # noqa: BLE001
            atlanan.append((no, "ders sayfası: " + str(hata)[:60]))
            continue

        t_yolu = CIKTI / ("transkript_" + no + ".html")
        ham = t_yolu.read_text(encoding="utf-8") if t_yolu.exists() else ""
        kayit["transkript"] = dk.transkripti_coz(ham)

        # Ham sayfanın diske yazıldığı an = o öğrencinin OBİS'ten
        # okunduğu an. Tek öğrenci tazelendiğinde (--ogrenci) satırlar
        # farklı zamanlardan gelir; danışman hangisinin güncel
        # olduğunu görebilmeli.
        kayit["son_tarama"] = datetime.datetime.fromtimestamp(
            yol.stat().st_mtime).strftime("%d.%m.%Y %H:%M")

        toplananlar.append(
            (kayit, ozet.ogrenci_ozeti(
                kayit, icinde_bulunulan_yil=datetime.date.today().year,
                program=program, mufredat=mfr)))

    for no, sebep in atlanan:
        print("  ! " + no + " atlandı: " + sebep)

    # Katalog öğrenciye göre değişiyor; ders listesi için hepsinin
    # birleşimini alıyoruz.
    katalog = {}
    for kayit, _ in toplananlar:
        for d in kayit.get("katalog") or []:
            if d.get("sekme") == "Bölüm Dersleri":
                katalog.setdefault(d["ders_no"], d)
    katalog = sorted(katalog.values(), key=lambda d: d["ders_no"])

    # Hedef dönem sabit değil: danışmanın öğrencileri hangi dönemlerdeyse
    # her biri için ayrı plan (3. sınıf danışmanında 5, 4. sınıfta 7).
    kontenjan = ozet.kontenjan_planlari([o for _, o in toplananlar])

    # 2023'ten bu yana AKTS'si değişen dersler: transkriptler (eski değer)
    # ile müfredat belgesi (güncel değer) karşılaştırılır.
    transkriptler = {(k.get("no") or ""): k.get("transkript")
                     for k, _ in toplananlar}
    degisim = akts_degisimi.hesapla(
        transkriptler, mfr, {d["ders_no"]: d for d in katalog})

    yol = rapor.pano_yaz(toplananlar, CIKTI / "danisman_ozeti.html",
                         kontenjan=kontenjan, program=program,
                         katalog=katalog, akts_degisim=degisim)

    yapilacak = [o for _, o in toplananlar if o["sayim"].get("yapilacak")]
    dikkat = [o for _, o in toplananlar
              if not o["sayim"].get("yapilacak") and o["sayim"].get("dikkat")]
    print("")
    print("Pano yenilendi: " + str(yol))
    print("  Müdahale gereken : " + str(len(yapilacak)))
    print("  Kontrol edilecek : " + str(len(dikkat)))
    print("  Temiz            : "
          + str(len(toplananlar) - len(yapilacak) - len(dikkat)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
