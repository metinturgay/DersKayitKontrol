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
# DİKKAT: bu yollar FONKSİYONLA çözülüyor. Modül düzeyinde bir kez
# hesaplanırsa yerel kurulum katmanı (yollar.veri_yaz) devreye girdikten
# sonra bile eski yeri gösterirler - exe'de bu, geçici klasöre yazıp
# kaybetmek demek.
def veri_klasoru():
    return yollar.veri()


def mufredat_json(yazmak_icin=False):
    return (yollar.veri_yaz("mufredat.json") if yazmak_icin
            else yollar.veri("mufredat.json"))

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"

ROMEN = {"I": 1, "II": 2, "III": 3, "IV": 4, "V": 5, "VI": 6,
         "VII": 7, "VIII": 8, "IX": 9, "X": 10, "XI": 11, "XII": 12}

# Yarıyıl yazıyla da yazılabiliyor.
YAZIYLA = {
    "BİRİNCİ": 1, "İKİNCİ": 2, "ÜÇÜNCÜ": 3, "DÖRDÜNCÜ": 4, "BEŞİNCİ": 5,
    "ALTINCI": 6, "YEDİNCİ": 7, "SEKİZİNCİ": 8, "DOKUZUNCU": 9,
    "ONUNCU": 10,
}

# Ders adındaki tip işaretleri. Bir bölümün "(Seç.)" yazdığı yere başka
# bir bölüm "(S)", "(SEÇMELİ)" ya da "(Ortak Seçmeli)" yazıyor.
_TIP_IMLERI = (
    (re.compile(r"\(\s*(?:TOS|ORTAK\s*SE[CÇ](?:MEL[İI])?)\s*\)",
                re.IGNORECASE | re.UNICODE), "TOS"),
    (re.compile(r"\(\s*S(?:E[CÇ](?:\.|MEL[İI])?)?\s*\.?\s*\)",
                re.IGNORECASE | re.UNICODE), "Seçmeli"),
    (re.compile(r"\(\s*Z(?:\.|ORUNLU)?\s*\)",
                re.IGNORECASE | re.UNICODE), "Zorunlu"),
)


class BelgeAnlasilmadi(Exception):
    """Belge okundu ama içinden ders çıkmadı ya da yapısı tanınmadı.

    Bu sınıfın VAR OLMASI bilinçli: eskiden oku() böyle bir belgede
    sessizce boş sözlük dönüyordu, kurulum onu "başarı" sayıyor ve
    danışman sıfır dersli bir müfredatla pano üretiyordu.
    """


def ust(metin):
    """Türkçe 'i' tuzağına düşmeyen büyük harf.

    Python'da "Seçmeli".upper() -> "SEÇMELI" (noktasız I). Bu yüzden
    `"SEÇMELİ" in metin.upper()` ölçütü, başlığını başlık-harfle yazan
    bir belgede TUTMUYORDU (ölçüldü).
    """
    return (metin or "").replace("i", "İ").replace("ı", "I").upper()


def _sayiya_cevir(simge):
    """'IV' / '4' / 'DÖRDÜNCÜ' -> 4. Çözemezse None."""
    s = ust(simge).strip(" .")
    if s.isdigit():
        return int(s)
    if s in ROMEN:
        return ROMEN[s]
    return YAZIYLA.get(s)


# Yarıyıl sözcüğünün HEMEN ÖNÜNDEKİ simgeyi arar. "3. SINIF (V. YARIYIL
# SEÇMELİ DERSLER)" gibi başlıklarda doğru olan V'dir, 3 değil.
_YARIYIL_DESENI = re.compile(
    r"([A-ZÇĞİÖŞÜ]+|\d{1,2})\s*[.\-]?\s*(?:YARIYIL|DÖNEM|SÖMESTR)",
    re.UNICODE)
_SINIF_DESENI = re.compile(r"([A-ZÇĞİÖŞÜ]+|\d{1,2})\s*[.\-]?\s*SINIF",
                           re.UNICODE)


def yariyil_coz(metin):
    """Paragraf bir yarıyıl başlığı mı? -> (yarıyıl no, kalan metin)

    Desteklenen biçimler ölçülerek belirlendi; eskiden yalnız satır
    BAŞINDA romen rakamı tanınıyordu:

        I. YARIYIL · 1. YARIYIL · BİRİNCİ YARIYIL · I. Yarıyıl
        VIII. YARIYIL SEÇMELİ DERSLER · 4. SINIF (VIII. YARIYIL)
        3. SINIF (V. YARIYIL SEÇMELİ DERSLER)
        2. SINIF GÜZ YARIYILI   (sınıf + mevsimden hesaplanır)

    Yarıyıl numarası çözülemezse (None, "") döner ve ÇAĞIRAN bunu
    başlık saymaz - eskiden çözülemeyen başlıkta önceki yarıyıl
    değişkeni olduğu gibi kalıyor ve dersler YANLIŞ yarıyıla yazılıyordu.
    """
    if not metin:
        return None, ""
    u = ust(metin)
    for m in _YARIYIL_DESENI.finditer(u):
        no = _sayiya_cevir(m.group(1))
        if no:
            return no, u[m.end():]

    # "2. SINIF GÜZ YARIYILI": yarıyıl sözcüğünden önceki simge mevsim.
    if "YARIYIL" in u or "DÖNEM" in u:
        sm = _SINIF_DESENI.search(u)
        sinif = _sayiya_cevir(sm.group(1)) if sm else None
        if sinif:
            if "GÜZ" in u:
                return 2 * sinif - 1, u
            if "BAHAR" in u or "İLKBAHAR" in u:
                return 2 * sinif, u
    return None, ""


# --- Tablo sütunlarını BAŞLIKTAN eşle ------------------------------------
# Sütunlar eskiden sabit indeksle okunuyordu (0=kod, 1=ad, 5=AKTS).
# Ölçüldü: "Kod | Ad | AKTS | T | U | K" sıralı bir belgede AKTS,
# kredi sütunundan okunuyor ve hiçbir uyarı çıkmıyordu. AKTS bu aracın
# TEK DOĞRU KAYNAĞI olduğu için bu, en pahalı sessiz yanlıştı.
_SUTUN_ESLERI = (
    ("kod", ("DERSİN KODU", "DERS KODU", "DERSKODU", "DERSİNKODU", "KOD",
             "KODU", "DERS KOD")),
    ("ad", ("DERSİN ADI", "DERS ADI", "DERSİNADI", "DERSADI", "AD", "ADI",
            "DERSİN ADI VE İÇERİĞİ", "DERS")),
    ("akts", ("AKTS", "AKTS KREDİSİ", "AKTS KREDISI", "ECTS", "AKTS/ECTS",
              "KREDİ (AKTS)", "AKTS KREDİ")),
    ("teorik", ("T", "TEORİK", "TEORI", "TEORİK SAAT", "T.")),
    ("uygulama", ("U", "UYGULAMA", "UYG", "UYGULAMA SAAT", "U.")),
    ("kredi", ("K", "KREDİ", "KREDI", "ULUSAL KREDİ", "YEREL KREDİ",
               "KREDİSİ", "K.")),
)


def _etiketle(satirlar):
    """İlk iki satırı BİRLEŞTİREREK sütun etiketlerini kurar.

    Alt satır doluysa o kazanır (T/U/K), boşsa üst satırın etiketi
    devam eder ("Kredisi" üç sütunu kapsıyorsa üçünde de görünür).
    """
    if not satirlar:
        return []
    genislik = max(len(s) for s in satirlar[:3]) if satirlar else 0
    def al(satir, i):
        return satir[i] if i < len(satir) else ""
    ust_satir = satirlar[0]
    alt_satir = satirlar[1] if len(satirlar) > 1 else []
    return [(al(alt_satir, i) or al(ust_satir, i)) for i in range(genislik)]


def _baslik_haritasi(satirlar):
    """Tablonun başlık satır(lar)ından {alan: sütun indeksi} çıkarır.

    Önce tek satır, tutmazsa iki satır birleştirilerek denenir: bazı
    belgelerde "Kredisi" üst başlığı T/U/K'yi kapsar ve alan adları
    ikinci satırdadır (gerçek Matematik belgesi böyle).

    En az 'kod', 'ad' ve 'akts' bulunamazsa None döner; çağıran o zaman
    tabloyu okumaz ve bunu TANI raporuna yazar. Sabit indekse ASLA
    düşülmez.
    """
    adaylar = [satirlar[0]] if satirlar else []
    if len(satirlar) > 1:
        adaylar.append(_etiketle(satirlar))

    def coz(satir):
        harita, kullanilan = {}, set()
        for i, hucre in enumerate(satir):
            h = " ".join(ust(hucre).split()).strip(" .:")
            if not h:
                continue
            for alan, esler in _SUTUN_ESLERI:
                if alan in harita:
                    continue
                if h in esler and i not in kullanilan:
                    harita[alan] = i
                    kullanilan.add(i)
                    break
        return harita

    # EN ÇOK alanı çözen aday kazanır. Önce "asgari koşulu sağlayan ilk
    # aday" seçiliyordu: gerçek belgede tek satırlık başlık kod+ad+akts
    # için yetiyor ve döngü orada duruyordu; T/U sütunları hiç
    # eşleşmiyor, üstelik "Kredisi" birleşik başlığı T sütununa
    # bakıyordu. Ölçüldü ve bilinen doğru çözümlemeyle karşılaştırılarak
    # yakalandı - makullik kapısı bunu göremezdi (115 ders okunuyordu).
    en_iyi = None
    for satir in adaylar:
        harita = coz(satir)
        if not all(x in harita for x in ("kod", "ad", "akts")):
            continue
        if en_iyi is None or len(harita) > len(en_iyi):
            en_iyi = harita
    return en_iyi


# Ders kodu bölümden bölüme değişiyor: 2709151 (7 hane), MAT101,
# MAT-101... Sabit bir \d{6,9} kalıbı harfli kodlu bölümde SIFIR ders
# okutuyordu. Bunun yerine "kod gibi duruyor mu" ölçütü kullanılıyor.
_KOD_OLMAYAN = {
    "TOPLAM", "GENEL TOPLAM", "TOPLAM KREDİ", "YEKÛN", "YEKUN", "ARA TOPLAM",
    "NOT", "SEÇMELİ", "SEÇMELI", "SEÇ", "ZORUNLU", "DERSİN KODU", "KOD",
    "DERS KODU", "SIRA", "SIRA NO", "NO",
}


def kod_mu(deger):
    """Bu hücre bir ders kodu olabilir mi?"""
    k = (deger or "").strip()
    if not (2 <= len(k) <= 16):
        return False
    u = ust(k)
    if u in _KOD_OLMAYAN:
        return False
    if any(u.startswith(x) for x in ("TOPLAM", "GENEL", "YEKÛN", "YEKUN")):
        return False
    # "Seçmeli 3" gibi yer tutucular: harf kısmı bir kod değil bir sözcük.
    harfler = re.sub(r"[^A-ZÇĞİÖŞÜ]", "", u)
    if harfler in ("SEÇMELİ", "SEÇMELI", "SEÇ", "ZORUNLU", "DERS"):
        return False
    return bool(re.search(r"\d", k)) and not re.search(r"\s", k)


def _metin(el):
    return " ".join(("".join(t.text or "" for t in el.iter(W + "t"))).split())


def _hucreler(satir):
    """Satırın hücreleri, BİRLEŞİK olanlar genişletilmiş hâlde.

    Word yatay birleşmiş hücreyi tek <w:tc> + <w:gridSpan w:val="3">
    olarak yazar. Genişletmeden okunursa başlık satırı veri satırından
    DAR görünür ve sütun indeksleri kayar: ölçüldü, gerçek belgede
    AKTS indeks 5 yerine 3 sanıldı ve 113 dersin AKTS'si 0 okundu.
    """
    cikti = []
    for tc in satir.iter(W + "tc"):
        metin = _metin(tc)
        kac = 1
        for gs in tc.iter(W + "gridSpan"):
            try:
                kac = max(1, int(gs.get(W + "val") or 1))
            except (TypeError, ValueError):
                kac = 1
            break
        cikti.extend([metin] * kac)
    return cikti


def _docx_bul(yol=None):
    if yol:
        return yol
    # Sıra ÖNEMLİ: danışmanın kendi belgesi (yerel kurulum) gömülü
    # belgeden ÖNCE gelmeli. Eskiden gömülü veri/ ilk sıradaydı ve
    # exe'de Matematik'in belgesi kullanıcınınkini hep yeniyordu.
    _yerel = yollar.yerel_veri_kok()
    for kalip in (str(_yerel / "*Okutulacak Dersler*.docx"),
                  str(_yerel / "mufredat.docx"),
                  str(veri_klasoru() / "*Okutulacak Dersler*.docx"),
                  str(veri_klasoru() / "mufredat.docx"),
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
    """Belgeyi çözer. Anlaşılmazsa BelgeAnlasilmadi yükseltir.

    Sütunlar tablonun BAŞLIK satırından eşlenir; sabit indekse asla
    düşülmez. Hiç ders çıkmazsa istisna atılır - eskiden boş sözlük
    dönüyordu ve bu, sıfır dersli bir müfredatla pano üretilmesine
    yol açıyordu.

    Dönen sözlükte ayrıca "tani" var: kaç tablo görüldü, kaçının
    başlığı çözüldü, kaç satır atlandı. Kurulum sihirbazı bunu
    danışmana gösterir.
    """
    yol = _docx_bul(docx_yolu)
    kok = ET.fromstring(
        zipfile.ZipFile(yol).read("word/document.xml").decode("utf-8"))
    govde = kok.find(W + "body")

    dersler = {}          # kod -> kayıt
    yariyillar = {}       # yarıyıl no -> {"toplam_akts", "zorunlu", ...}
    notlar = []
    yariyil = None
    secmeli_tablosu = False
    tani = {"tablo": 0, "basligi_cozulen_tablo": 0, "yariyil_basligi": 0,
            "atlanan_satir": 0, "basliksiz_tablo_ornegi": None,
            "cozulemeyen_baslik": []}

    for cocuk in govde:
        etiket = cocuk.tag.replace(W, "")

        if etiket == "p":
            metin = _metin(cocuk)
            if not metin:
                continue
            no, kalan = yariyil_coz(metin)
            if no:
                yariyil = no
                secmeli_tablosu = "SEÇMEL" in kalan
                tani["yariyil_basligi"] += 1
            elif ("YARIYIL" in ust(metin) or "SINIF" in ust(metin)) \
                    and len(metin) < 80:
                # Yarıyıl başlığına BENZİYOR ama numarası çözülemedi.
                # Sessizce geçmek, sonraki tabloyu ÖNCEKİ yarıyıla
                # yazmak demekti (ölçüldü). Tanıya yazıp bildiriyoruz.
                tani["cozulemeyen_baslik"].append(metin[:60])
            continue

        if etiket != "tbl":
            continue
        tani["tablo"] += 1
        if yariyil is None:
            continue

        satirlar = [_hucreler(satir) for satir in cocuk.iter(W + "tr")]
        harita = _baslik_haritasi(satirlar)
        if not harita:
            if tani["basliksiz_tablo_ornegi"] is None and satirlar:
                tani["basliksiz_tablo_ornegi"] = " | ".join(
                    h for h in satirlar[0] if h)[:120]
            continue
        tani["basligi_cozulen_tablo"] += 1

        varsayilan_tip = "Seçmeli" if secmeli_tablosu else "Zorunlu"
        bilgi = yariyillar.setdefault(yariyil, {
            "toplam_akts": None, "zorunlu": [], "secmeli": [], "tos": []})
        gerekli = max(harita.values()) + 1

        for hucreler in satirlar:
            # ARDIŞIK TEKRARLAR TEKE İNİYOR. _hucreler() gridSpan'i
            # genişletirken birleşik hücrenin metnini kapsadığı HER
            # sütuna kopyalıyor; bu sütun eşleştirmesi için doğru ama
            # metni birleştirirken aynı cümleyi tekrar ettiriyor.
            # Ölçüldü: 6 sütuna yayılan bir "Not:" satırı, notlar
            # listesine cümlesi 6 kez yazılmış hâlde giriyordu.
            parcalar = []
            for h in hucreler:
                if h and (not parcalar or parcalar[-1] != h):
                    parcalar.append(h)
            birlesik = " ".join(parcalar).strip()
            if ust(birlesik).startswith("NOT"):
                if (yariyil, birlesik) not in notlar:
                    notlar.append((yariyil, birlesik))
                continue

            # Yarıyıl toplamı: "TOPLAM", "TOPLAM KREDİ", "YEKÛN"...
            u = ust(birlesik)
            if any(x in u for x in ("TOPLAM", "YEKÛN", "YEKUN")):
                if len(hucreler) >= gerekli:
                    t = _sayi(hucreler[harita["akts"]])
                    if t is not None:
                        bilgi["toplam_akts"] = t
                continue

            if len(hucreler) < gerekli:
                if birlesik:
                    tani["atlanan_satir"] += 1
                continue

            kod = hucreler[harita["kod"]].strip()
            ham_ad = hucreler[harita["ad"]].strip()
            if not kod_mu(kod):
                if birlesik and not _baslik_satiri_mi(hucreler, harita):
                    tani["atlanan_satir"] += 1
                continue

            ad, tip = _tip_ve_ad(ham_ad, varsayilan_tip)
            kayit = {
                "ders_no": kod, "ders_adi": ad, "tip": tip,
                "akts": _sayi(hucreler[harita["akts"]]),
                "yariyil": yariyil,
                "teorik": _alan(hucreler, harita, "teorik"),
                "uygulama": _alan(hucreler, harita, "uygulama"),
                "kredi": _alan(hucreler, harita, "kredi"),
            }
            onceki = dersler.get(kod)
            if onceki and onceki != kayit:
                # Aynı ders iki tabloda geçebiliyor (TOS dersleri hem
                # zorunlu hem seçmeli tablosunda). Çelişki varsa AKTS'yi
                # karşılaştırıp bildiriyoruz.
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
        m = re.search(r"TOPLAM\s+AKTS\s*:?\s*(\d+)", _metin(cocuk), re.I)
        if m:
            genel = int(m.group(1))

    # Yalnız DOSYA ADI yazılıyor, mutlak yol değil. str(yol) yazılıyordu
    # ve mufredat.json yayımlanan bir dosya olduğu için üreten makinenin
    # kullanıcı adını ve klasör ağacını dışarı veriyordu - ölçüldü,
    # GitHub'a gidecek sürümde "C:\Users\...\PROJELER\..." duruyordu.
    # Alanın işi hangi belgeden üretildiğini söylemek; onu ad da söyler.
    veri = {"kaynak": Path(yol).name, "dersler": dersler,
            "yariyillar": yariyillar, "notlar": notlar,
            "genel_toplam_akts": genel, "tani": tani}
    _makul_mu(veri, yol)
    return veri


def _baslik_satiri_mi(hucreler, harita):
    """Bu satır tablonun kendi başlık satırı mı? (atlanan sayılmasın)"""
    return _baslik_haritasi([hucreler]) is not None


def _alan(hucreler, harita, ad):
    """Haritada varsa o sütunun sayısı, yoksa None."""
    i = harita.get(ad)
    return _sayi(hucreler[i]) if i is not None and i < len(hucreler) else None


def _makul_mu(veri, yol):
    """Belge GERÇEKTEN okundu mu? Okunmadıysa gürültülü hata.

    Bu kapı olmadan her şablon farkı sessiz kalıyordu: farklı sütun
    sıralı, arap rakamlı başlıklı ya da harfli kodlu bir belge hiçbir
    istisna atmadan {} dönüyor, kurulum bunu "başarı" sayıyor ve
    danışman sıfır dersli bir müfredatla pano üretiyordu.
    """
    t = veri["tani"]
    dersler, yariyillar = veri["dersler"], veri["yariyillar"]
    sorun = []
    if not dersler:
        sorun.append("Belgeden HİÇ DERS okunamadı.")
    if not yariyillar:
        sorun.append("Belgede yarıyıl başlığı bulunamadı.")
    if t["tablo"] and not t["basligi_cozulen_tablo"]:
        sorun.append(
            "Hiçbir tablonun başlık satırı çözülemedi (%d tablo görüldü)."
            % t["tablo"])
    if not sorun:
        return

    ipucu = []
    if t["basliksiz_tablo_ornegi"]:
        ipucu.append("İlk tablonun ilk satırı: %s"
                     % t["basliksiz_tablo_ornegi"])
        ipucu.append("Beklenen sütun adları: Dersin Kodu / Dersin Adı / "
                     "AKTS (T, U, K isteğe bağlı).")
    if t["cozulemeyen_baslik"]:
        ipucu.append("Yarıyıl başlığına benzeyip çözülemeyen satırlar: "
                     + "; ".join(t["cozulemeyen_baslik"][:3]))
    if t["atlanan_satir"]:
        ipucu.append("%d satır ders satırı sayılmadı (kod sütunu "
                     "tanınmadı)." % t["atlanan_satir"])

    raise BelgeAnlasilmadi(
        "Bu belge çözümlenemedi:\n  %s\n\n%s\n\n"
        "%s\n"
        "Belge bu araca uymuyorsa ya başlık satırı farklıdır ya da "
        "yarıyıl başlıkları beklenen biçimde değildir. Belgeyi "
        "değiştirmek yerine sorunu bildirin: aracın belgeye uyması "
        "gerekir, belgenin araca değil."
        % (yol, "\n  ".join(sorun), "\n  ".join(ipucu)))


def kaydet(docx_yolu=None, cikti=None):
    veri = oku(docx_yolu)
    cikti = Path(cikti) if cikti else mufredat_json(yazmak_icin=True)
    cikti.parent.mkdir(parents=True, exist_ok=True)
    cikti.write_text(json.dumps(veri, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    return cikti, veri


def yukle(yol=None):
    yol = Path(yol) if yol else mufredat_json()
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
