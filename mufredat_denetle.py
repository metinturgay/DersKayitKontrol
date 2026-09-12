# -*- coding: utf-8 -*-
"""Sistemi müfredat belgesine karşı doğrular.

Belge (veri/mufredat.docx) AKTS için tek doğru kaynak. Bu script:
  - kodladığımız dönem planını belgenin yarıyıl toplamlarıyla,
  - kodladığımız dönem kompozisyonunu belgenin notlarıyla,
  - TOS listemizi belgedekiyle,
  - OBİS katalogundaki AKTS'leri belgedekiyle,
  - öğrenci transkriptlerindeki AKTS'leri belgedekiyle
karşılaştırıp farkları raporlar.

    python mufredat_denetle.py
"""
import re
from pathlib import Path

import bolum
import mufredat as mf
import yonetmelik as ym

BURASI = Path(__file__).resolve().parent
CIKTI = BURASI / "cikti"


def _katalog_birlesimi():
    import ders_kayit as dk
    sayfalar = sorted(CIKTI.glob("ders_sayfasi_*.html"))
    birlesik = {}
    for yol in sayfalar:
        kayit = dk.ders_kaydini_coz(yol.read_text(encoding="utf-8"))
        for d in kayit["katalog"]:
            if d.get("sekme") == "Bölüm Dersleri":
                birlesik.setdefault(d["ders_no"], d)
    return birlesik


def _transkriptleri_oku():
    """{ogrenci_no: transkripti_coz() sonucu}"""
    import ders_kayit as dk
    toplu = {}
    for yol in sorted(CIKTI.glob("transkript_*.html")):
        no = re.search(r"transkript_(\d+)\.html", yol.name).group(1)
        toplu[no] = dk.transkripti_coz(yol.read_text(encoding="utf-8"))
    return toplu


def main():
    veri = mf.yukle()
    if not veri:
        print("veri/mufredat.json yok. Önce: python mufredat.py")
        return 1
    dersler = veri["dersler"]
    sorunlar = []

    print("Belge : %s" % veri["kaynak"])
    print("Ders  : %d  |  genel toplam AKTS: %s"
          % (len(dersler), veri["genel_toplam_akts"]))
    print("")

    # ------------------------------------------------------------------
    print("1. DÖNEM PLANI (yonetmelik.VARSAYILAN_DONEM_PLANI)")
    plan = ym.VARSAYILAN_DONEM_PLANI
    fark = []
    for y in sorted(veri["yariyillar"]):
        belge = veri["yariyillar"][y]["toplam_akts"]
        bizim = plan.get(y)
        isaret = "OK " if belge == bizim else "FARK"
        if belge != bizim:
            fark.append(y)
        print("   %s %d. yarıyıl  belge=%s  kod=%s" % (isaret, y, belge, bizim))
    toplam_belge = sum(veri["yariyillar"][y]["toplam_akts"] or 0
                       for y in veri["yariyillar"])
    print("   %s toplam       belge=%d  kod=%d"
          % ("OK " if toplam_belge == ym.plan_toplami() else "FARK",
             toplam_belge, ym.plan_toplami()))
    if fark:
        sorunlar.append("dönem planı %s. yarıyılda farklı" % fark)
    print("")

    # ------------------------------------------------------------------
    print("2. DÖNEM KOMPOZİSYONU (yonetmelik.DONEM_KOMPOZISYONU)")
    for y, yapi in sorted(ym.DONEM_KOMPOZISYONU.items()):
        b = veri["yariyillar"].get(y) or {}
        zor_belge = set(b.get("zorunlu") or [])
        zor_kod = set(yapi["zorunlu_kodlar"])
        print("   %d. yarıyıl zorunlu: belge=%s  kod=%s  %s"
              % (y, sorted(zor_belge), sorted(zor_kod),
                 "OK" if zor_belge == zor_kod else "FARK"))
        if zor_belge != zor_kod:
            sorunlar.append("%d. yarıyıl zorunlu ders listesi farklı" % y)
        # Belgedeki nottan seçmeli/TOS adedini çıkar
        for yy, n in veri["notlar"]:
            if yy != y:
                continue
            sec = re.search(r"altı\s*\(6\)|bir\s*\(1\)", n)
            tos = "T.O.S" in n.upper()
            print("      not: %s" % n[:96])
            print("      kod: tos_adedi=%d" % yapi["tos_adedi"])
            if tos and yapi["tos_adedi"] != 1:
                sorunlar.append("%d. yarıyıl TOS adedi farklı" % y)
    print("")

    # ------------------------------------------------------------------
    print("3. TOS LİSTESİ (yonetmelik.TOS_DERSLERI)")
    # Belge yalnızca BÖLÜMÜN KENDİ TOS derslerini içeriyor. Başka
    # bölümlerin TOS dersleri belgede yok ama öğrenci onları da alabilir;
    # o kodlar danışmandan geldi. İki kaynağın birleşimini tutuyoruz.
    # Gerçek sorun tek yönlü: belgede olup listemizde OLMAYAN ders.
    belge_tos = {k for k, d in dersler.items() if d["tip"] == "TOS"}
    bizim_tos = set(ym.TOS_DERSLERI)
    eksik = belge_tos - bizim_tos
    disaridan = bizim_tos - belge_tos
    print("   Belgede (%s'in kendi TOS dersleri) : %d"
          % (bolum.ad(), len(belge_tos)))
    print("   Kodda (belge + başka bölümlerden açılanlar): %d" % len(bizim_tos))
    if eksik:
        for k in sorted(eksik):
            print("   EKSİK  %s %-40s (belgede TOS, listemizde yok)"
                  % (k, dersler[k]["ders_adi"][:40]))
        sorunlar.append("%d TOS dersi listemizde yok" % len(eksik))
    else:
        print("   Belgedeki TOS derslerinin hepsi listemizde var.")
    if disaridan:
        print("   Başka bölümlerden, belgede yer almayan %d TOS dersi "
              "(beklenen):" % len(disaridan))
        for k in sorted(disaridan):
            print("     %s %s" % (k, ym.TOS_DERSLERI[k][:44]))
    print("")

    # ------------------------------------------------------------------
    print("4. OBİS KATALOĞU <-> BELGE (AKTS)")
    katalog = _katalog_birlesimi()
    if not katalog:
        print("   cikti/ altında ders sayfası yok, atlandı.")
    else:
        farkli, yok = [], []
        for kod, d in sorted(katalog.items()):
            b = dersler.get(kod)
            if not b:
                yok.append((kod, d["ders_adi"], d.get("akts")))
                continue
            if b["akts"] is not None and d.get("akts") != b["akts"]:
                farkli.append((kod, d["ders_adi"], d.get("akts"), b["akts"]))
        print("   Katalogdaki ders: %d" % len(katalog))
        if farkli:
            print("   AKTS FARKLI (%d) — belge esas alınmalı:" % len(farkli))
            for kod, ad, k_akts, b_akts in farkli:
                print("     %s %-40s OBİS=%s  belge=%s"
                      % (kod, ad[:40], k_akts, b_akts))
            sorunlar.append("%d derste OBİS-belge AKTS farkı" % len(farkli))
        else:
            print("   AKTS farkı yok.")
        if yok:
            print("   Belgede bulunmayan katalog dersi (%d):" % len(yok))
            for kod, ad, a in yok:
                print("     %s %-40s OBİS AKTS=%s" % (kod, ad[:40], a))
    print("")

    # ------------------------------------------------------------------
    # Bu adım akts_degisimi.py üzerinden yürüyor. Eskiden burada yalnızca
    # KOD eşleşmesine bakan bir kontrol vardı; müfredat 11 dersin kodunu da
    # değiştirdiği için o dersleri hiç görmüyor, "Değişen yok" diyordu.
    print("5. TRANSKRİPT <-> BELGE (AKTS)")
    import akts_degisimi

    transkriptler = _transkriptleri_oku()
    if not transkriptler:
        print("   cikti/ altında transkript yok, atlandı.")
    else:
        d = akts_degisimi.hesapla(transkriptler, veri, katalog or None)
        o = d["ozet"]
        print("   Karşılaştırılan ders : %d  (taban öğrenci: %s)"
              % (o["karsilastirilan"], d["taban"] or "yok"))
        print("   AKTS değişen         : %d  (düşen %d, artan %d)"
              % (o["degisen"], o["dusen"], o["artan"]))
        print("   Kodu değişen         : %d" % o["kod_degisen"])
        if d["degisen"]:
            print("   Tekrar alınırsa BELGEDEKİ değer geçerli:")
            for x in sorted(d["degisen"],
                            key=lambda x: (x["yariyil"] or 0, x["ders_adi"])):
                kod = x["eski_kod"]
                if x["kod_degisti"]:
                    kod += " -> " + x["yeni_kod"]
                print("     %d. yy %-22s %-34s %s -> %s  (%d öğrenci kaldı)"
                      % (x["yariyil"] or 0, kod, x["ders_adi"][:34],
                         x["eski_akts"], x["guncel_akts"], x["kalan_sayisi"]))
            sorunlar.append("%d dersin AKTS'si düşmüş" % o["dusen"])
        else:
            print("   Değişen yok.")

        geri = [x for x in d["dersler"] if x.get("geri_alinmis")]
        if geri:
            print("   ARADA DÜŞÜP GERİ ALINMIŞ (%d) — arada düşük değerle "
                  "geçen öğrenci o farkı kaybetti:" % len(geri))
            for x in geri:
                print("     %-34s geçmiş=%s  belge=%s"
                      % (x["ders_adi"][:34],
                         {k: v for k, v in sorted(x["yillar"].items())},
                         x["guncel_akts"]))
        supheli = [x for x in d["dersler"] if x.get("celiski")]
        if supheli:
            print("   TEYİT EDİLMELİ (%d):" % len(supheli))
            for x in supheli:
                print("     %-34s belge=%s  son kayıt=%s"
                      % (x["ders_adi"][:34], x["guncel_akts"], x["son_akts"]))
            sorunlar.append("%d derste belge-transkript çelişkisi"
                            % len(supheli))
        for u in d["uyarilar"]:
            print("   ! " + u)
    print("")

    print("=" * 64)
    if sorunlar:
        print("DİKKAT: " + "; ".join(sorunlar))
    else:
        print("Sistem müfredat belgesiyle uyumlu.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
