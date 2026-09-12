# -*- coding: utf-8 -*-
"""Müfredat belgesi (okutulacak dersler docx) testleri.

Belge AKTS için tek doğru kaynak. Kodladığımız bölüm parametreleri
belgeyle uyuşmalı; uyuşmazsa burada patlar.
"""
import os
import sys

BURASI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BURASI))
sys.path.insert(0, BURASI)

import mufredat as mf
import yonetmelik as ym

OK = []


def kontrol(ad, beklenen, gelen):
    tamam = beklenen == gelen
    print(("  [OK]  " if tamam else "  [HATA] ") + ad +
          ("" if tamam else "\n          beklenen=%r\n          gelen   =%r"
           % (beklenen, gelen)))
    OK.append(tamam)


def main():
    v = mf.yukle()
    if not v:
        print("  veri/mufredat.json yok. Önce: python mufredat.py")
        return 1
    d = v["dersler"]

    print("  === Belge çözümlemesi ===")
    kontrol("8 yarıyıl okundu", [1, 2, 3, 4, 5, 6, 7, 8],
            sorted(v["yariyillar"]))
    kontrol("ders sayısı makul", True, 100 <= len(d) <= 130)
    kontrol("belgedeki genel toplam 244", 244, v["genel_toplam_akts"])
    kontrol("her dersin AKTS'si okundu", [],
            [k for k, x in d.items() if x["akts"] is None])
    kontrol("her dersin yarıyılı var", [],
            [k for k, x in d.items() if not x["yariyil"]])

    print("")
    print("  === Dönem planı belgeyle uyumlu ===")
    for y in sorted(v["yariyillar"]):
        kontrol("%d. yarıyıl AKTS" % y, v["yariyillar"][y]["toplam_akts"],
                ym.VARSAYILAN_DONEM_PLANI.get(y))
    kontrol("plan toplamı = belge toplamı", v["genel_toplam_akts"],
            ym.plan_toplami())
    kontrol("AKTS kaybı eşiği (244-240+1)", 5, ym.akts_kaybi_esigi())

    print("")
    print("  === 7. dönem kompozisyonu ===")
    y7 = v["yariyillar"][7]
    kontrol("belgede tek zorunlu ders", 1, len(y7["zorunlu"]))
    kontrol("  o ders Matematik Uygulamaları I", "2709753", y7["zorunlu"][0])
    kontrol("kodladığımız zorunlu ile aynı", tuple(y7["zorunlu"]),
            ym.DONEM_KOMPOZISYONU[7]["zorunlu_kodlar"])
    # Belgedeki not: M.U. I + 6 seçmeli + 1 TOS = 4 + 24 + 4 = 32
    mu = d["2709753"]["akts"]
    tos = ym.TOS_AKTS
    kontrol("M.U. I 4 AKTS", 4, mu)
    kontrol("hesap tutuyor: 4 + 6x4 + 4 = 32", y7["toplam_akts"],
            mu + 6 * 4 + tos)
    notlar7 = [n for yy, n in v["notlar"] if yy == 7]
    kontrol("7. yarıyıl notu var", 1, len(notlar7))
    kontrol("  not 6 seçmeli diyor", True, "altı (6)" in notlar7[0])
    kontrol("  not 1 TOS diyor", True, "bir (1) tane T.O.S" in notlar7[0])

    print("")
    print("  === TOS listesi ===")
    belge_tos = {k for k, x in d.items() if x["tip"] == "TOS"}
    kontrol("belgedeki TOS derslerinin hepsi listemizde", set(),
            belge_tos - set(ym.TOS_DERSLERI))
    kontrol("TOS dersleri 4 AKTS", [],
            [k for k in belge_tos if d[k]["akts"] != ym.TOS_AKTS])
    kontrol("TOS bölüm içi seçmeli sayılmıyor", False,
            ym.secmeli_mi({"ders_no": "2709747",
                           "ders_adi": d["2709747"]["ders_adi"]}))

    print("")
    print("  === Dönem yapısı SEKİZ yarıyıl için türetiliyor ===")
    # Sistem yalnızca 4. sınıf danışmanında değil, her sınıfta çalışmalı.
    # Kompozisyon denetimi yapıyı belgeden türetiyor; sekizi de gelmeli.
    for yy in range(1, 9):
        yapi = ym.donem_yapisi(yy, v)
        kontrol("%d. yarıyıl yapısı türetildi" % yy, True, bool(yapi))
        if not yapi:
            continue
        hesap = (sum(d[k]["akts"] or 0 for k in yapi["zorunlu_kodlar"])
                 + yapi["tos_adedi"] * ym.TOS_AKTS
                 + yapi["secmeli_adedi"] * (yapi["secmeli_akts"] or 0))
        kontrol("  %d. yarıyıl AKTS toplamı tutuyor" % yy,
                v["yariyillar"][yy]["toplam_akts"], hesap)
    kontrol("1-4. yarıyıl tamamen zorunlu", True,
            all(ym.donem_yapisi(yy, v)["secmeli_adedi"] == 0
                and ym.donem_yapisi(yy, v)["tos_adedi"] == 0
                for yy in (1, 2, 3, 4)))
    kontrol("5-6. yarıyılda 1 seçmeli", True,
            all(ym.donem_yapisi(yy, v)["secmeli_adedi"] == 1
                for yy in (5, 6)))
    kontrol("7-8. yarıyılda 6 seçmeli + 1 TOS", True,
            all(ym.donem_yapisi(yy, v)["secmeli_adedi"] == 6
                and ym.donem_yapisi(yy, v)["tos_adedi"] == 1
                for yy in (7, 8)))
    kontrol("belge yoksa elle kodlanana düşer", True,
            ym.donem_yapisi(7, None) is not None)

    print("")
    print("  === AKTS sorgusu ===")
    kontrol("2709753 -> 4", 4, mf.akts(v, "2709753"))
    kontrol("2709544 Dif.Geo I -> 5", 5, mf.akts(v, "2709544"))
    kontrol("2709546 Sayılar Teorisi I -> 3", 3, mf.akts(v, "2709546"))
    kontrol("bilinmeyen kodda varsayılan döner", 99,
            mf.akts(v, "9999999", 99))
    kontrol("belge yoksa varsayılan döner", 7, mf.akts(None, "2709753", 7))

    print("")
    print("  === Katalog AKTS'leri belgeyle uyumlu ===")
    from pathlib import Path
    import ders_kayit as dk
    cikti = Path(os.path.dirname(BURASI)) / "cikti"
    sayfalar = sorted(cikti.glob("ders_sayfasi_*.html"))
    if not sayfalar:
        print("  (cikti/ boş, atlandı)")
    else:
        katalog = {}
        for yol in sayfalar:
            for c in dk.ders_kaydini_coz(yol.read_text(encoding="utf-8"))["katalog"]:
                if c.get("sekme") == "Bölüm Dersleri":
                    katalog.setdefault(c["ders_no"], c)
        farkli = [(k, c["akts"], d[k]["akts"]) for k, c in katalog.items()
                  if k in d and d[k]["akts"] is not None
                  and c["akts"] != d[k]["akts"]]
        kontrol("OBİS katalogu ile belge arasında AKTS farkı yok", [], farkli)
        print("        (%d katalog dersi karşılaştırıldı)" % len(katalog))

    print("")
    print("  %d/%d kontrol geçti." % (sum(OK), len(OK)))
    return 0 if all(OK) else 1


if __name__ == "__main__":
    sys.exit(main())
