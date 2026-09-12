# -*- coding: utf-8 -*-
"""Son yılların müfredat belgelerini yan yana koyar.

Neden
-----
Bugün iki bilgi ELLE koda yazılıyor ve ikisi de bir danışmanın bilemeyeceği
şeyler:

  SONRADAN_EKLENEN_DERSLER   hangi ders hangi girişten itibaren geçerli
  veri/akts_referans.json    hangi dersin hangi kohortta kaç AKTS olduğu

Matematik için bunlar transkriptler karşılaştırılarak ÖLÇÜLDÜ. Başka bir
bölümün danışmanından aynı arkeolojiyi beklemek gerçekçi değil.

Oysa ikisi de zaten bir yerde yazılı: bölümün her yıl yayımladığı
"Okutulacak Dersler" belgesinde. Son 4-5 yılın belgesi yan yana konursa

  * bir yılda ORTAYA ÇIKAN ders            -> sonradan eklenen ders
  * yıldan yıla AKTS'si DEĞİŞEN ders       -> kohort AKTS tabanı
  * bir yılda KAYBOLAN ders                -> kaldırılmış ders

kendiliğinden çıkar. Danışmandan istediğimiz tek şey, elinde zaten olan
birkaç belge.

Nereye konur
------------
    veri/mufredat/2022.docx
    veri/mufredat/2023.docx
    veri/mufredat/2024.docx      <- dosya adı, belgenin geçerli olduğu
    veri/mufredat/2025.docx         GİRİŞ YILI'dır ("2025-2026" de olur)
    veri/mufredat/2026.docx

    python mufredat_arsivi.py           özet
    python mufredat_arsivi.py --json    türetilenleri JSON olarak bas

DİKKAT — uydurma üretmeme kuralı
--------------------------------
Bir ders arşivin EN ESKİ yılında zaten varsa, ondan önce var mıydı
bilemeyiz. Böyle bir dersi "sonradan eklendi" diye işaretlemek, hiç
yaşanmamış bir AKTS açığı uydurmak olurdu. Bu yüzden yalnızca en eski
yıldan SONRA ortaya çıkan dersler sayılır.
"""
import glob
import json
import os
import re
from pathlib import Path

import eslestirme as es
import mufredat
import yollar

def arsiv_klasoru(yazmak_icin=False):
    """Yıllık belgelerin klasörü. Danışmanın verdiği belgeler yerel
    kuruluma kopyalanır; gömülü exe'ye docx gömülmez."""
    return (yollar.veri_yaz("mufredat") if yazmak_icin
            else yollar.veri("mufredat"))


def arsiv_json(yazmak_icin=False):
    return (yollar.veri_yaz("mufredat_arsivi.json") if yazmak_icin
            else yollar.veri("mufredat_arsivi.json"))

# "2024", "2024-2025", "2024_2025 Okutulacak Dersler" -> 2024
_YIL = re.compile(r"(20\d{2})")


def yil_coz(dosya_adi):
    """Dosya adındaki İLK dört haneli yıl. Bulunamazsa None."""
    m = _YIL.search(os.path.basename(dosya_adi))
    return int(m.group(1)) if m else None


def belgeleri_bul(klasor=None):
    """[(giriş yılı, dosya yolu)] — yıla göre sıralı."""
    klasor = Path(klasor or arsiv_klasoru())
    if not klasor.is_dir():
        return []
    bulunan = {}
    for yol in sorted(glob.glob(str(klasor / "*.docx"))):
        if os.path.basename(yol).startswith("~$"):
            continue                      # Word'ün kilit dosyası
        yil = yil_coz(yol)
        if yil is None:
            continue
        # Aynı yıl için birden çok dosya varsa adı en uzun olan (genelde
        # tam adıyla kaydedilmiş olan) kazanır; sessizce birini seçmek
        # yerine bunu ozet() raporluyor.
        onceki = bulunan.get(yil)
        if onceki is None or len(os.path.basename(yol)) > len(os.path.basename(onceki)):
            bulunan[yil] = yol
    return sorted(bulunan.items())


def oku(klasor=None):
    """{yıl: müfredat sözlüğü}. Okunamayan belge atlanır ve bildirilir."""
    arsiv, hatalar = {}, []
    for yil, yol in belgeleri_bul(klasor):
        try:
            arsiv[yil] = mufredat.oku(yol)
        except Exception as e:            # noqa: BLE001 - danışmana göster
            hatalar.append((yil, yol, str(e)))
    return arsiv, hatalar


# =========================================================================
#  Yıllar arası ders kimliği
# =========================================================================
# Ders KODU yıldan yıla değişebiliyor (2709508 CEBİR I -> 2709545), ders
# ADI da kısaltılabiliyor. Bu yüzden kimlik iki aşamalı kuruluyor:
# önce kod, tutmazsa ad anahtarı. Eşik eslestirme.py'den geliyor ki
# eşleştirme kuralı tek yerde kalsın.
def _kimlik_haritasi(arsiv):
    """{(yıl, kod): kimlik} ve {kimlik: {"ad":…, "kodlar": {…}}}"""
    kimlikler = {}          # kimlik -> {"ad", "kodlar", "anahtar"}
    nereye = {}             # (yil, kod) -> kimlik
    anahtar_dizini = {}     # ad anahtarı -> kimlik
    kod_dizini = {}         # kod -> kimlik

    for yil in sorted(arsiv):
        for kod, d in sorted((arsiv[yil].get("dersler") or {}).items()):
            ad = d.get("ders_adi") or ""
            anahtar = es.ders_adi_anahtari(ad)
            kimlik = kod_dizini.get(kod) or anahtar_dizini.get(anahtar)
            if kimlik is None:
                # Ad birebir tutmadıysa benzerliğe bak (kısaltmalar)
                en_iyi, oran = None, 0.0
                for mevcut_anahtar, mevcut in anahtar_dizini.items():
                    o = es.ad_benzerligi(anahtar, mevcut_anahtar)
                    if o > oran:
                        en_iyi, oran = mevcut, o
                if oran >= es.BENZERLIK_ESIGI:
                    kimlik = en_iyi
            if kimlik is None:
                kimlik = "K%04d" % (len(kimlikler) + 1)
                kimlikler[kimlik] = {"ad": ad, "anahtar": anahtar,
                                     "kodlar": set(), "yillar": {}}
            k = kimlikler[kimlik]
            k["kodlar"].add(kod)
            k["yillar"][yil] = d
            kod_dizini[kod] = kimlik
            anahtar_dizini.setdefault(anahtar, kimlik)
            nereye[(yil, kod)] = kimlik
    return kimlikler, nereye


# =========================================================================
#  Türetilenler
# =========================================================================
def sonradan_eklenenler(arsiv):
    """{güncel kod: geçerli olduğu EN ERKEN giriş yılı}

    Yalnızca arşivin EN ESKİ yılından SONRA ortaya çıkan dersler. En eski
    yılda zaten olanlar için "daha önce var mıydı" sorusunun cevabı
    elimizde yok; uydurmuyoruz.
    """
    if len(arsiv) < 2:
        return {}
    ilk_yil = min(arsiv)
    kimlikler, _ = _kimlik_haritasi(arsiv)
    sonuc = {}
    for k in kimlikler.values():
        ortaya_cikis = min(k["yillar"])
        if ortaya_cikis <= ilk_yil:
            continue
        # O yıldan itibaren KESİNTİSİZ duruyor mu? Bir yıl var bir yıl
        # yok olan ders "sonradan eklendi" değil, düzensiz açılan derstir.
        beklenen = [y for y in sorted(arsiv) if y >= ortaya_cikis]
        if sorted(k["yillar"]) != beklenen:
            continue
        guncel_kod = k["yillar"][max(k["yillar"])].get("ders_no")
        if guncel_kod:
            sonuc[guncel_kod] = ortaya_cikis
    return sonuc


def kaldirilanlar(arsiv):
    """{kod: son geçerli yıl} — artık açılmayan dersler."""
    if len(arsiv) < 2:
        return {}
    son_yil = max(arsiv)
    kimlikler, _ = _kimlik_haritasi(arsiv)
    sonuc = {}
    for k in kimlikler.values():
        if max(k["yillar"]) >= son_yil:
            continue
        y = max(k["yillar"])
        kod = k["yillar"][y].get("ders_no")
        if kod:
            sonuc[kod] = y
    return sonuc


def akts_gecmisi(arsiv):
    """[{"ad", "kodlar", "degerler": {yıl: akts}}] — AKTS'si DEĞİŞENLER."""
    kimlikler, _ = _kimlik_haritasi(arsiv)
    degisenler = []
    for k in kimlikler.values():
        degerler = {y: (d.get("akts")) for y, d in k["yillar"].items()}
        farkli = {v for v in degerler.values() if v is not None}
        if len(farkli) < 2:
            continue
        degisenler.append({
            "ad": k["yillar"][max(k["yillar"])].get("ders_adi") or k["ad"],
            "kodlar": sorted(k["kodlar"]),
            "guncel_kod": k["yillar"][max(k["yillar"])].get("ders_no"),
            "degerler": {str(y): degerler[y] for y in sorted(degerler)},
        })
    return sorted(degisenler, key=lambda d: d["ad"])


def kohort_akts(arsiv, giris_yili):
    """{kod: AKTS} — o giriş yılının belgesindeki değerler.

    Giriş yılının belgesi yoksa ondan ÖNCEKİ en yakın yıl kullanılır
    (öğrenci girdiğinde yürürlükte olan belge odur). Ondan da öncesi
    yoksa boş döner — tahmin yürütmüyoruz.
    """
    uygun = [y for y in arsiv if y <= giris_yili]
    if not uygun:
        return {}
    y = max(uygun)
    return {kod: d.get("akts")
            for kod, d in (arsiv[y].get("dersler") or {}).items()}


def donem_plani(arsiv):
    """{yarıyıl: AKTS} — EN GÜNCEL belgedeki yarıyıl toplamları."""
    if not arsiv:
        return {}
    y = arsiv[max(arsiv)]
    plan = {}
    for yariyil, bilgi in (y.get("yariyillar") or {}).items():
        if bilgi.get("toplam_akts"):
            plan[int(yariyil)] = bilgi["toplam_akts"]
    return plan


def tos_dersleri(arsiv):
    """{kod: ad} — TÜM yılların (TOS) işaretli derslerinin birleşimi.

    Birleşim alıyoruz çünkü eski kohorttaki bir öğrenci hâlâ eski TOS
    dersini taşıyor olabilir.
    """
    sonuc = {}
    for yil in sorted(arsiv):
        for kod, d in (arsiv[yil].get("dersler") or {}).items():
            if d.get("tip") == "TOS":
                sonuc[kod] = (d.get("ders_adi") or "").upper()
    return sonuc


def tos_akts(arsiv):
    """TOS derslerinin tipik AKTS'si (en güncel belgeye göre)."""
    if not arsiv:
        return None
    d = (arsiv[max(arsiv)].get("dersler") or {})
    degerler = [v.get("akts") for v in d.values()
                if v.get("tip") == "TOS" and v.get("akts")]
    return max(set(degerler), key=degerler.count) if degerler else None


def kohort_tabanlari(arsiv):
    """{giriş yılı: {kod: AKTS}} — her yılın kendi belgesindeki değerler.

    Bu, akts_degisimi'nin "eski değer" arayışındaki belgesel kaynaktır:
    öğrenci girdiğinde yürürlükte olan müfredat ne diyordu?
    """
    return {str(yil): {kod: d.get("akts")
                       for kod, d in (arsiv[yil].get("dersler") or {}).items()
                       if d.get("akts") is not None}
            for yil in sorted(arsiv)}


def turet(arsiv):
    """Profil için türetilebilen her şey, tek sözlükte."""
    return {
        "yillar": sorted(arsiv),
        # Kohort tabanlari JSON'a da giriyor: exe'ye docx'ler degil bu
        # dosya gomuluyor, AKTS kaybi hesabi da buradan okuyor.
        "kohort_akts": kohort_tabanlari(arsiv),
        "donem_akts": donem_plani(arsiv),
        "tos_dersleri": tos_dersleri(arsiv),
        "tos_akts": tos_akts(arsiv),
        "sonradan_eklenen_dersler": sonradan_eklenenler(arsiv),
        "kaldirilan_dersler": kaldirilanlar(arsiv),
        "akts_degisenler": akts_gecmisi(arsiv),
    }


def kaydet(klasor=None, cikti=None):
    arsiv, hatalar = oku(klasor)
    veri = turet(arsiv)
    veri["okunamayan"] = [{"yil": y, "dosya": d, "hata": h}
                          for y, d, h in hatalar]
    yol = Path(cikti) if cikti else arsiv_json(yazmak_icin=True)
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(veri, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    return yol, veri, arsiv


def yukle(yol=None):
    yol = Path(yol) if yol else arsiv_json()
    if not yol.exists():
        return None
    return json.loads(yol.read_text(encoding="utf-8"))


# =========================================================================
def ozet_yaz(klasor=None):
    belgeler = belgeleri_bul(klasor)
    if not belgeler:
        print("Arşivde belge yok: %s" % (klasor or KLASOR))
        print("")
        print("Bölümün son 4-5 yılda yayımladığı 'Okutulacak Dersler'")
        print("belgelerini buraya GİRİŞ YILI adıyla koyun:")
        print("    veri/mufredat/2023.docx")
        print("    veri/mufredat/2024.docx   ...")
        print("")
        print("İki yıl yeterli, dört-beş yıl daha iyi: arada kaç kohort")
        print("varsa o kadarının AKTS tabanı çıkarılabilir.")
        return 1

    arsiv, hatalar = oku(klasor)
    print("Arşiv: %d belge" % len(arsiv))
    for yil, yol in belgeler:
        d = arsiv.get(yil)
        print("  %d  %-46s %s" % (
            yil, os.path.basename(yol)[:46],
            ("%d ders" % len(d["dersler"])) if d else "OKUNAMADI"))
    for yil, yol, hata in hatalar:
        print("  [HATA] %d: %s" % (yil, hata))

    if len(arsiv) < 2:
        print("")
        print("Tek belge var. Karşılaştıracak yıl olmadığı için AKTS")
        print("değişimi ve sonradan eklenen ders ÇIKARILAMAZ. Bu bir")
        print("eksiklik değil; sadece elde veri yok demek.")
        return 0

    t = turet(arsiv)
    print("")
    print("Yarıyıl planı (en güncel belge): %s = %d AKTS"
          % (" + ".join(str(t["donem_akts"][y])
                        for y in sorted(t["donem_akts"])),
             sum(t["donem_akts"].values())))
    print("TOS dersi: %d tanımlı, tipik %s AKTS"
          % (len(t["tos_dersleri"]), t["tos_akts"]))

    print("")
    print("Sonradan eklenen dersler (%d)" % len(t["sonradan_eklenen_dersler"]))
    if not t["sonradan_eklenen_dersler"]:
        print("  yok — %d'ten beri ders listesi büyümemiş" % min(arsiv))
    for kod, yil in sorted(t["sonradan_eklenen_dersler"].items(),
                           key=lambda x: (x[1], x[0])):
        ad = ((arsiv[max(arsiv)]["dersler"].get(kod) or {})
              .get("ders_adi") or "")
        print("  %s  %d ve sonrası   %s" % (kod, yil, ad[:40]))

    print("")
    print("AKTS'si değişen dersler (%d)" % len(t["akts_degisenler"]))
    for d in t["akts_degisenler"]:
        seyir = " -> ".join(
            "%s:%s" % (y, v) for y, v in sorted(d["degerler"].items()))
        print("  %-34s %s" % (d["ad"][:34], seyir))

    if t["kaldirilan_dersler"]:
        print("")
        print("Artık açılmayan dersler (%d)" % len(t["kaldirilan_dersler"]))
        for kod, yil in sorted(t["kaldirilan_dersler"].items()):
            print("  %s  son %d" % (kod, yil))
    return 0


if __name__ == "__main__":
    import sys

    if "--json" in sys.argv:
        yol, veri, _ = kaydet()
        print(json.dumps(veri, ensure_ascii=False, indent=1))
        print("")
        print("Kayıt: %s" % yol)
    else:
        raise SystemExit(ozet_yaz())
