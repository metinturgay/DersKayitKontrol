# -*- coding: utf-8 -*-
"""Bölüm müfredatını (okutulacak dersler docx) okur.

Kaynak: bölümün "... Okutulacak Dersler ... .docx" belgesi; yarıyıl
yarıyıl ders listesi. Hangi bölüm olduğu veri/bolum.json'da yazar.

Son 4-5 yılın belgesi veri/mufredat/<yıl>.docx olarak konursa
mufredat_arsivi.py yıllar arası değişimleri de çıkarır.

Bu belge AKTS için TEK DOĞRU KAYNAKTIR: kalınan ya da eksik bir ders
yeni dönemde alındığında buradaki AKTS geçerli olur. OBİS katalogundaki
değer farklıysa bu belge esas alınır.

Belge yapısı:
  "1. SINIF" / "I. YARIYIL" başlıkları, ardından bir tablo.
  Tablo sütunları: DersinKodu | Dersin Adı | T | U | K | AKTS
  Son satır "TOPLAM KREDİ", altında da bir "Not:" satırı olabiliyor.
  5-8. yarıyıllarda zorunlu tablosunun yanında ayrı bir seçmeli tablosu
  var; ikisi de aynı yarıyıla ait.

    python mufredat.py
"""
import glob
import json
import re
from pathlib import Path
from xml.etree import ElementTree as ET
import zipfile

import yollar

# Exe'ye derlendiginde veri/ exe'nin ICINDE olur; yollar.py ikisini ayirir.
VERI = yollar.veri()
MUFREDAT_JSON = VERI / "mufredat.json"

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

ROMEN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
         "VI": 6, "VII": 7, "VIII": 8}

# Ders adının sonundaki tip işaretleri
_TIP_IMLERI = (
    (re.compile(r"\(\s*TOS\s*\)", re.IGNORECASE), "TOS"),
    (re.compile(r"\(\s*Se[cç]\.?\s*\)", re.IGNORECASE), "Seçmeli"),
    (re.compile(r"\(\s*Z\s*\)", re.IGNORECASE), "Zorunlu"),
)


def _metin(el):
    return " ".join(("".join(t.text or "" for t in el.iter(W + "t"))).split())


def _docx_bul(yol=None):
    if yol:
        return yol
    for kalip in (str(VERI / "*Okutulacak Dersler*.docx"),
                  str(VERI / "mufredat.docx"),
                  str(Path.home() / "Desktop" / "*Okutulacak Dersler*.docx")):
        adaylar = sorted(glob.glob(kalip))
        if adaylar:
            return adaylar[0]
    raise SystemExit("Müfredat docx bulunamadı (veri/ ya da Masaüstü).")


def _sayi(metin):
    metin = (metin or "").replace(",", ".").strip()
    try:
        deger = float(metin)
    except ValueError:
        return None
    return int(deger) if deger == int(deger) else deger


def _tip_ve_ad(ham_ad, varsayilan):
    """'Cebir I (Z)' -> ('Cebir I', 'Zorunlu')"""
    tip = varsayilan
    ad = ham_ad
    for kalip, etiket in _TIP_IMLERI:
        if kalip.search(ad):
            tip = etiket
            ad = kalip.sub("", ad)
            break
    return " ".join(ad.split()).strip(" -"), tip


def oku(docx_yolu=None):
    """Belgeyi çözer: {"dersler": {...}, "yariyillar": {...}, "notlar": [...]}"""
    yol = _docx_bul(docx_yolu)
    kok = ET.fromstring(
        zipfile.ZipFile(yol).read("word/document.xml").decode("utf-8"))
    govde = kok.find(W + "body")

    dersler = {}          # kod -> kayıt
    yariyillar = {}       # yarıyıl no -> {"toplam_akts", "zorunlu", "secmeli"}
    notlar = []
    yariyil = None
    secmeli_tablosu = False

    for cocuk in govde:
        etiket = cocuk.tag.replace(W, "")

        if etiket == "p":
            metin = _metin(cocuk)
            esleme = re.match(r"^\s*([IVX]+)\.\s*YARIYIL(.*)$", metin,
                              re.IGNORECASE)
            if not esleme:
                esleme = re.search(r"\(\s*([IVX]+)\.\s*YARIYIL\s*\)", metin,
                                   re.IGNORECASE)
                if esleme:
                    esleme = re.match(r"()([IVX]+)()", "")  # aşağıda ayrı ele
                    esleme = None
                    ic = re.search(r"\(\s*([IVX]+)\.\s*YARIYIL\s*\)", metin,
                                   re.IGNORECASE)
                    yariyil = ROMEN.get(ic.group(1).upper())
                    secmeli_tablosu = False
                    continue
            if esleme:
                yariyil = ROMEN.get(esleme.group(1).upper())
                secmeli_tablosu = "SEÇMELİ" in esleme.group(2).upper()
            continue

        if etiket != "tbl" or yariyil is None:
            continue

        varsayilan_tip = "Seçmeli" if secmeli_tablosu else "Zorunlu"
        bilgi = yariyillar.setdefault(yariyil, {
            "toplam_akts": None, "zorunlu": [], "secmeli": [], "tos": []})

        for satir in cocuk.iter(W + "tr"):
            hucreler = [_metin(tc) for tc in satir.iter(W + "tc")]
            # "Not: ..." satırı tek birleşik hücre olarak geliyor, 6
            # sütunluk kalıba uymuyor; ayrıca yakalıyoruz.
            birlesik = " ".join(h for h in hucreler if h).strip()
            if birlesik.upper().startswith("NOT"):
                if (yariyil, birlesik) not in notlar:
                    notlar.append((yariyil, birlesik))
                continue
            if len(hucreler) < 6:
                continue
            kod, ham_ad = hucreler[0].strip(), hucreler[1].strip()
            akts = _sayi(hucreler[5])

            if "TOPLAM" in (kod + " " + ham_ad).upper():
                if akts is not None:
                    bilgi["toplam_akts"] = akts
                continue
            if kod.upper().startswith("NOT"):
                notlar.append((yariyil, kod))
                continue
            if not re.fullmatch(r"\d{6,9}", kod):
                continue                      # "Seçmeli 3" gibi yer tutucular

            ad, tip = _tip_ve_ad(ham_ad, varsayilan_tip)
            onceki = dersler.get(kod)
            kayit = {
                "ders_no": kod, "ders_adi": ad, "tip": tip,
                "akts": akts, "yariyil": yariyil,
                "teorik": _sayi(hucreler[2]), "uygulama": _sayi(hucreler[3]),
                "kredi": _sayi(hucreler[4]),
            }
            if onceki and onceki != kayit:
                # Aynı ders iki tabloda geçebiliyor (TOS dersleri hem
                # zorunlu tablosunda hem seçmeli tablosunda). Çelişki
                # varsa AKTS'yi karşılaştırıp bildiriyoruz.
                if onceki["akts"] != kayit["akts"]:
                    notlar.append(
                        (yariyil, "ÇELİŞKİ %s: AKTS %s ve %s"
                         % (kod, onceki["akts"], kayit["akts"])))
                if onceki["tip"] == "TOS":
                    kayit["tip"] = "TOS"
            dersler[kod] = kayit

            liste = ("tos" if kayit["tip"] == "TOS"
                     else "secmeli" if kayit["tip"] == "Seçmeli"
                     else "zorunlu")
            if kod not in bilgi[liste]:
                bilgi[liste].append(kod)

    # Belge sonundaki genel toplam
    genel = None
    for cocuk in govde.iter(W + "p"):
        m = re.search(r"TOPLAM\s+AKTS\s*:\s*(\d+)", _metin(cocuk), re.I)
        if m:
            genel = int(m.group(1))
    return {"kaynak": str(yol), "dersler": dersler,
            "yariyillar": yariyillar, "notlar": notlar,
            "genel_toplam_akts": genel}


def kaydet(docx_yolu=None, cikti=None):
    veri = oku(docx_yolu)
    cikti = Path(cikti) if cikti else MUFREDAT_JSON
    cikti.parent.mkdir(parents=True, exist_ok=True)
    cikti.write_text(json.dumps(veri, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    return cikti, veri


def yukle(yol=None):
    yol = Path(yol) if yol else MUFREDAT_JSON
    if not yol.exists():
        return None
    veri = json.loads(yol.read_text(encoding="utf-8"))
    # JSON anahtarları metne dönüşüyor; yarıyıl numaralarını geri alıyoruz.
    veri["yariyillar"] = {int(k): v for k, v in veri["yariyillar"].items()}
    return veri


def akts(mufredat, ders_no, varsayilan=None):
    """Bir dersin GEÇERLİ AKTS'si. Belge yoksa varsayılana düşer."""
    if not mufredat:
        return varsayilan
    kayit = (mufredat.get("dersler") or {}).get(str(ders_no))
    return kayit["akts"] if kayit and kayit["akts"] is not None else varsayilan


if __name__ == "__main__":
    yol, veri = kaydet()
    print("Kaynak : " + veri["kaynak"])
    print("Ders   : %d" % len(veri["dersler"]))
    print("Kayıt  : %s" % yol)
    print("")
    print("%-8s %6s %8s %8s %6s" % ("Yarıyıl", "Zor.", "Seçmeli", "TOS",
                                    "Toplam"))
    toplam = 0
    for y in sorted(veri["yariyillar"]):
        b = veri["yariyillar"][y]
        print("%-8d %6d %8d %8d %6s" % (y, len(b["zorunlu"]),
                                        len(b["secmeli"]), len(b["tos"]),
                                        b["toplam_akts"]))
        toplam += b["toplam_akts"] or 0
    print("%-8s %6s %8s %8s %6d" % ("TOPLAM", "", "", "", toplam))
    print("Belgedeki genel toplam: %s" % veri["genel_toplam_akts"])
    if veri["notlar"]:
        print("")
        print("Notlar:")
        for y, n in veri["notlar"]:
            print("  [%s. yarıyıl] %s" % (y, n))
