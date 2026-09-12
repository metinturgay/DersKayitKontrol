# -*- coding: utf-8 -*-
"""Ders programını okuyup çakışan ders çiftlerini çıkarır.

Kaynak: "2026-2027 Güz Yarıyılı Ders Programı.xlsx", "I. Öğretim" sayfası.

Sayfanın yapısı:
  - Her gün için bir blok. Bloğun başında saat başlığı satırı var
    (C..G sabah, I..M öğleden sonra; H sütunu öğle arası boşluğu).
  - A sütunu gün adı, B sütunu sınıf (1-4).
  - Bir hücre "Ders Adı (Derslik)\nÖğretim Üyesi" biçiminde.
  - Aynı gün bloğunda birden çok satır olabilir; farklı satırlarda aynı
    saatte duran dersler PARALEL açılmış demektir, yani çakışırlar.

Çakışma tanımı: iki ders aynı gün aynı saat diliminde ise birlikte
alınamaz (MADDE 9/1-b).
"""
import glob
import json
import re
from pathlib import Path

import bolum
import yollar

def cakisma_json(yazmak_icin=False):
    """Çakışma dosyasının yolu — fonksiyon, çünkü yerel kurulum katmanı
    import'tan sonra devreye giriyor."""
    return (yollar.veri_yaz("cakismalar.json") if yazmak_icin
            else yollar.veri("cakismalar.json"))

# Sayfa düzeni ve istisna dersleri BÖLÜM KARARIDIR: her fakültenin ders
# programı aynı şablonla çizilmiyor, ders saatleri de her yerde aynı
# değil. Hepsi veri/bolum.json -> "program" altında (bkz. bolum.py).
_P = bolum.program_ayarlari()

# Ders programı xlsx'inde hangi sayfa okunacak
SAYFA_ADI = _P["sayfa_adi"]

# Saat sütunları: Excel sütun harfi -> saat aralığı
SAAT_SUTUNLARI = dict(_P["saat_sutunlari"])
GUNLER = tuple(_P["gunler"])

# Ders adı olmayan, programda yer tutan hücreler
YOKSAY = {"", "-", "BÖLÜM BAŞKANI", "DERSLİK", "SAAT"}


class ProgramAnlasilmadi(Exception):
    """Ders programı okundu ama içinden ders çıkmadı.

    Bu sınıfın var olması bilinçli: eskiden saat sütunları beklenen
    yerde olmayan bir dosyada programi_oku() SIFIR ders döndürüyor,
    hiçbir istisna atmıyordu. Sonuç: pano "çakışma yok" diyor ve
    danışman buna inanıyordu. Ölçüldü - bir sütun kaydırılmış gerçek
    programda 41 ders yerine 0 ders okundu, ekranda tek uyarı yok.
    """


# Saat aralığı: "08:30-09:15", "08.30 - 09.15", "0830-0915" hepsi olur.
_SAAT_DESENI = re.compile(
    r"^\s*(\d{1,2})[:.\s]?(\d{2})\s*[-–—/]\s*(\d{1,2})[:.\s]?(\d{2})\s*$")


def saat_mi(deger):
    """Hücre bir saat aralığı mı? Öyleyse 'HH:MM-HH:MM' döner."""
    m = _SAAT_DESENI.match(str(deger or ""))
    if not m:
        return None
    a, b, c, d = (int(x) for x in m.groups())
    if not (0 <= a <= 23 and 0 <= b <= 59 and 0 <= c <= 23 and 0 <= d <= 59):
        return None
    return "%02d:%02d-%02d:%02d" % (a, b, c, d)


def _gun_sutunu_mu(ws, sutun, gunler, azami_satir):
    """Bu sütunda gün adı geçiyor mu? Kaç tane?"""
    sayi = 0
    for r in range(1, azami_satir + 1):
        a = _gun_adi(ws.cell(r, sutun).value)
        if a and any(a.startswith(g[:4]) for g in gunler):
            sayi += 1
    return sayi


def duzen_coz(ws, gunler=None):
    """Sayfanın yerleşimini DOSYADAN çıkarır.

    Döner: {"saat_sutunlari": {sütun no: saat}, "gun_sutunu": n,
            "sinif_sutunu": n, "saat_satirlari": {satır no}}

    Neden dosyadan: saat sütunlarının hangi harfte olduğu bölüme göre
    değişiyor. Profilden okunduğunda, bir sütun kaymış bir dosyada her
    hücre atlanıyor ve sonuç SESSİZCE sıfır çakışma oluyordu. Dosyanın
    kendi saat başlığı satırı zaten doğruyu söylüyor; ona bakmamak için
    sebep yok.
    """
    gunler = tuple(gunler or GUNLER)
    azami_satir = min(ws.max_row, 400)
    azami_sutun = min(ws.max_column, 60)

    # 1. Saat başlıklarını tara: hangi sütun, hangi satır
    sutun_saat = {}       # sütun no -> {saat: kaç kez}
    saat_satirlari = set()
    for r in range(1, azami_satir + 1):
        satirda = 0
        for c in range(1, azami_sutun + 1):
            saat = saat_mi(ws.cell(r, c).value)
            if not saat:
                continue
            sutun_saat.setdefault(c, {})
            sutun_saat[c][saat] = sutun_saat[c].get(saat, 0) + 1
            satirda += 1
        if satirda >= 3:          # saat başlığı satırı
            saat_satirlari.add(r)

    # Her sütun için EN SIK görülen saat etiketi geçerlidir.
    saat_sutunlari = {}
    for c, sayimlar in sutun_saat.items():
        saat_sutunlari[c] = max(sayimlar.items(), key=lambda x: x[1])[0]

    # 2. Gün sütunu: gün adı en çok hangi sütunda geçiyor?
    gun_sutunu, en_cok = None, 0
    for c in range(1, min(azami_sutun, 8) + 1):
        n = _gun_sutunu_mu(ws, c, gunler, azami_satir)
        if n > en_cok:
            gun_sutunu, en_cok = c, n

    # 3. Sınıf sütunu: gün sütununun hemen sağında, küçük tam sayılar
    sinif_sutunu = None
    if gun_sutunu:
        for c in (gun_sutunu + 1, gun_sutunu + 2):
            if c in saat_sutunlari or c > azami_sutun:
                continue
            sayi = 0
            for r in range(1, azami_satir + 1):
                v = str(ws.cell(r, c).value or "").strip()
                if v.isdigit() and 1 <= int(v) <= 9:
                    sayi += 1
            if sayi >= 2:
                sinif_sutunu = c
                break

    return {"saat_sutunlari": saat_sutunlari, "gun_sutunu": gun_sutunu,
            "sinif_sutunu": sinif_sutunu, "saat_satirlari": saat_satirlari}


def _sayfa_sec(kitap):
    """Hangi sayfa okunacak? Profildeki ad varsa o, yoksa EN ÇOK saat
    başlığı taşıyan sayfa - ve hangisi seçildiği yazdırılır."""
    if SAYFA_ADI in kitap.sheetnames:
        return kitap[SAYFA_ADI], SAYFA_ADI, False
    en_iyi, en_cok = None, 0
    for ad in kitap.sheetnames:
        ws = kitap[ad]
        n = len(duzen_coz(ws)["saat_sutunlari"])
        if n > en_cok:
            en_iyi, en_cok = ad, n
    if not en_iyi:
        raise ProgramAnlasilmadi(
            "Ders programında saat başlığı olan bir sayfa bulunamadı.\n"
            "Dosyadaki sayfalar: %s\n"
            "Beklenen: hücrelerinde '08:30-09:15' gibi saat aralıkları "
            "olan bir sayfa." % ", ".join(kitap.sheetnames))
    return kitap[en_iyi], en_iyi, True

# Programda TOS dersleri tek tek yazılmamış, ortak bir "TOS" bloğu var.
# Hangi TOS dersi alınırsa alınsın o saatte olacağı için tüm TOS kodları
# bu bloğa bağlanıyor. Bu blok, aynı saatteki 3. sınıf dersleriyle
# çakışıyor — alttan dersi olan öğrenci için önemli.
TOS_BLOK_ADI = _P["tos_blok_adi"]

# Programın altındaki dipnot:
#   "Ortak Zorunlu Dersler (Türk Dili-1, Atatürk İ.İ.T-1, İngilizce-1)
#    ASENKRON olarak sürdürülecektir."
# Bu dersler tabloda bir saate yazılmış olsa da gerçekte senkron
# yapılmıyor; hiçbir dersle çakışmazlar.
ASENKRON_DERSLER = set(_P["asenkron_dersler"])

# Esnek yürütülen dersler. Programda çok sayıda saate yazılmış olsalar da
# sabit bir buluşma saatleri yok; öğrenciyle ayarlanıyor. Bu yüzden
# çakışma üretmezler.
#   Matematik Uygulamaları 1: 4. sınıfın zorunlu uygulama dersi, tabloda
#   haftada 27 saate yayılmış durumda (boş kalan tüm slotlar). Gerçek bir
#   blok olmadığı için çakışma analizinden çıkarıldı (danışman kararı).
ESNEK_DERSLER = set(_P["esnek_dersler"])

# "Fizik Laboratuvarı 1(A-Grubu)" gibi gruplu dersler: öğrenci yalnızca
# bir gruba giriyor. Bu yüzden iki ders ancak TÜM grup kombinasyonlarında
# çakışıyorsa gerçekten birlikte alınamaz.
_GRUP_IMI = re.compile(r"\(\s*([A-ZÇĞİÖŞÜ])\s*-?\s*Grubu\s*\)", re.IGNORECASE)


def _sutun_harfi(no):
    return chr(64 + no)


def _ders_adi(hucre):
    """'Analiz 1 (M1)\\nProf. Dr. X' -> ('Analiz 1', 'M1')"""
    metin = str(hucre or "").strip()
    if not metin:
        return None, None, None
    ilk = metin.split("\n")[0].strip()

    # Grup bilgisi ders adının içinde: "Fizik Laboratuvarı 1(A-Grubu)"
    grup = None
    g = _GRUP_IMI.search(ilk)
    if g:
        grup = g.group(1).upper()
        ilk = ilk[:g.start()] + ilk[g.end():]

    # Derslik ve öğretim üyesi bazen aynı satırda kalıyor:
    #   "Fuzzy Topoloji 1 (M4)      Prof. Dr. ..."
    # Bu yüzden ilk parantezden itibarasını kesiyoruz; ders adı hep
    # parantezden önce.
    derslik = None
    eslesme = re.search(r"\(([^)]*)\)", ilk)
    if eslesme:
        derslik = eslesme.group(1).strip()
        ilk = ilk[:eslesme.start()]
    ilk = re.sub(r"\s+", " ", ilk).strip()
    return (ilk or None), derslik, grup


def _gun_adi(hucre):
    """Dikey yazılmış 'P\\nA\\nZ...' -> 'PAZARTESİ'"""
    harfler = re.sub(r"\s+", "", str(hucre or ""))
    return harfler.upper() or None


def programi_oku(xlsx_yolu=None, duzen=None):
    """{ders adı: {(gün, saat), ...}} ve ders başına ayrıntı döndürür.

    Yerleşim (hangi sütun hangi saat, gün ve sınıf nerede) DOSYADAN
    çözülür; profildeki program ayarları yalnız yedektir. Eskiden
    yerleşim profilden geliyordu ve bir sütun kaymış bir dosyada her
    hücre sessizce atlanıp SIFIR çakışma üretiliyordu (ölçüldü).
    """
    import openpyxl

    if xlsx_yolu is None:
        adaylar = sorted(glob.glob(str(Path.home() / "Desktop"
                                       / "*Ders Program*.xlsx")))
        if not adaylar:
            raise SystemExit("Ders programı xlsx bulunamadı.")
        xlsx_yolu = adaylar[0]

    kitap = openpyxl.load_workbook(xlsx_yolu, data_only=True)
    ws, sayfa_adi, tahmin = _sayfa_sec(kitap)
    if tahmin:
        print("  (ders programı: %r sayfası bulunamadı, %r kullanılıyor)"
              % (SAYFA_ADI, sayfa_adi))

    d = duzen or duzen_coz(ws)
    saat_sutunlari = d["saat_sutunlari"]
    gun_sutunu = d["gun_sutunu"]
    sinif_sutunu = d["sinif_sutunu"]
    saat_satirlari = d["saat_satirlari"]

    if not saat_sutunlari:
        raise ProgramAnlasilmadi(
            "Ders programında saat başlığı bulunamadı: %s (sayfa %r)\n"
            "Beklenen: '08:30-09:15' gibi saat aralıkları içeren bir "
            "başlık satırı." % (xlsx_yolu, sayfa_adi))
    if not gun_sutunu:
        raise ProgramAnlasilmadi(
            "Ders programında gün sütunu bulunamadı: %s (sayfa %r)\n"
            "Aranan gün adları: %s\n"
            "Gün adları başka yazılıyorsa veri/bolum.json -> "
            "program.gunler altına ekleyin."
            % (xlsx_yolu, sayfa_adi, ", ".join(GUNLER)))

    yerlesim = {}     # ders adı -> {grup: {(gün, saat)}}
    ayrinti = {}      # ders adı -> {"derslikler": set, "siniflar": set}
    gun = None
    sinif = None

    for r in range(1, ws.max_row + 1):
        a = _gun_adi(ws.cell(r, gun_sutunu).value)
        if a:
            for g in GUNLER:
                if a.startswith(g[:4]):
                    gun = g
                    break
        if sinif_sutunu:
            b = ws.cell(r, sinif_sutunu).value
            if b is not None and str(b).strip().isdigit():
                sinif = int(str(b).strip())

        if r in saat_satirlari:      # saat başlığı satırı
            continue
        if gun is None:
            continue

        for sutun_no, saat in saat_sutunlari.items():
            ad, derslik, grup = _ders_adi(ws.cell(r, sutun_no).value)
            if not ad or ad.upper() in YOKSAY:
                continue
            if saat_mi(ad):          # başlık satırı kaçmışsa ders sanma
                continue
            yerlesim.setdefault(ad, {}).setdefault(grup or "", set()).add(
                (gun, saat))
            bilgi = ayrinti.setdefault(ad, {"derslikler": set(),
                                            "siniflar": set()})
            if derslik:
                bilgi["derslikler"].add(derslik)
            if sinif:
                bilgi["siniflar"].add(sinif)

    if not yerlesim:
        raise ProgramAnlasilmadi(
            "Ders programından HİÇ DERS okunamadı: %s (sayfa %r)\n"
            "Saat sütunu %d, gün sütunu %s, sınıf sütunu %s bulundu; "
            "ama hiçbir hücrede ders adı yok.\n"
            "Sayfa doğru mu? Dosyadaki sayfalar: %s"
            % (xlsx_yolu, sayfa_adi, len(saat_sutunlari), gun_sutunu,
               sinif_sutunu, ", ".join(kitap.sheetnames)))

    return yerlesim, ayrinti


def _asenkron_mu(ad):
    import yonetmelik as ym
    return ym.ders_adi_anahtari(ad) in ASENKRON_DERSLER


def _esnek_mi(ad):
    import yonetmelik as ym
    return ym.ders_adi_anahtari(ad) in ESNEK_DERSLER


def _cakisabilir_mi(ad):
    """Bu ders çakışma üretebilir mi? Asenkron ve esnek dersler üretmez."""
    return not (_asenkron_mu(ad) or _esnek_mi(ad))


def cakismalari_bul(yerlesim):
    """Birlikte alınamayacak ders çiftlerini çıkarır.

    Gruplu derslerde (Fizik Lab. A/B) öğrenci bir grup seçiyor; bu yüzden
    iki ders ancak TÜM grup kombinasyonlarında çakışıyorsa gerçekten
    birlikte alınamaz. Tek kombinasyon bile boştaysa öğrenci o gruba
    yazılarak çakışmadan kurtulur.

    Asenkron yürütülen ortak zorunlu dersler ve esnek yürütülen
    uygulama dersleri hiç çakışmaz (ASENKRON_DERSLER / ESNEK_DERSLER).
    """
    adlar = [a for a in sorted(yerlesim) if _cakisabilir_mi(a)]
    ciftler = []
    for i, a in enumerate(adlar):
        for b in adlar[i + 1:]:
            kombinasyonlar = [(ga, gb, sa & sb)
                              for ga, sa in yerlesim[a].items()
                              for gb, sb in yerlesim[b].items()]
            if not kombinasyonlar or any(not ortak
                                         for _, _, ortak in kombinasyonlar):
                continue                      # kaçış yolu var, çakışma yok
            # Her kombinasyon çakışıyor: en az çakışanı rapor et.
            ga, gb, ortak = min(kombinasyonlar, key=lambda k: len(k[2]))
            ciftler.append({
                "ders_a": a, "ders_b": b,
                "grup_a": ga or None, "grup_b": gb or None,
                "saat_sayisi": len(ortak),
                "saatler": ["%s %s" % (g, s) for g, s in sorted(ortak)],
            })
    ciftler.sort(key=lambda c: (-c["saat_sayisi"], c["ders_a"], c["ders_b"]))
    return ciftler


def kaydet(xlsx_yolu=None, cikti=None):
    """Programı çözüp cakismalar.json üretir."""
    yerlesim, ayrinti = programi_oku(xlsx_yolu)
    ciftler = cakismalari_bul(yerlesim)

    def _duz(gruplar):
        return sorted({s for kume in gruplar.values() for s in kume})

    veri = {
        "dersler": {
            ad: {
                "saatler": ["%s %s" % (g, s) for g, s in _duz(gruplar)],
                "saat_sayisi": len(_duz(gruplar)),
                "gruplar": sorted(g for g in gruplar if g),
                "asenkron": _asenkron_mu(ad),
                "esnek": _esnek_mi(ad),
                "derslikler": sorted(ayrinti[ad]["derslikler"]),
                "siniflar": sorted(ayrinti[ad]["siniflar"]),
            } for ad, gruplar in sorted(yerlesim.items())
        },
        "cakismalar": ciftler,
    }
    cikti = Path(cikti) if cikti else cakisma_json(yazmak_icin=True)
    cikti.parent.mkdir(parents=True, exist_ok=True)
    cikti.write_text(json.dumps(veri, ensure_ascii=False, indent=1),
                     encoding="utf-8")
    return cikti, veri


# Programda kısaltılmış yazılan, benzerlik eşiğinin altında kalan adlar.
# Katalog adının anahtarı -> programdaki ad.
EL_ESLESMELERI = {
    "ATATURK ILKELERI VE INKILAP TARIHI 1": "Atatürk İlk. ve İnk. Tarihi 1",
    "ATATURK ILKELERI VE INKILAP TARIHI 2": "Atatürk İlk. ve İnk. Tarihi 2",
}


def program_eslestir(katalog, veri, esik=0.88):
    """Katalog derslerini programdaki derslerle eşler.

    Program dosyası ders KODU içermiyor, yalnızca ad var. Adlar da birebir
    aynı değil ("Spektral Graf Teori 1" / "SPEKTRAL GRAF TEORİSİ I").
    Bu yüzden önce normalize edilmiş ad, sonra benzerlik kullanılıyor.

    Döner: {ders_no: {"program_adi":..., "benzerlik":..., "tip": kesin|benzer}}
    """
    import yonetmelik as ym

    program_anahtarlari = {ym.ders_adi_anahtari(ad): ad for ad in veri["dersler"]}
    tos_var = TOS_BLOK_ADI in veri["dersler"]
    harita = {}
    for ders in katalog:
        kod = ders.get("ders_no")
        if not kod:
            continue
        # TOS dersleri programda tek tek yok, ortak blokta.
        if tos_var and ym.tos_mu(ders):
            harita[kod] = {"program_adi": TOS_BLOK_ADI, "benzerlik": 1.0,
                           "tip": "tos_blogu"}
            continue
        anahtar = ym.ders_adi_anahtari(ders.get("ders_adi", ""))
        if anahtar in program_anahtarlari:
            harita[kod] = {"program_adi": program_anahtarlari[anahtar],
                           "benzerlik": 1.0, "tip": "kesin"}
            continue
        elle = EL_ESLESMELERI.get(anahtar)
        if elle and elle in veri["dersler"]:
            harita[kod] = {"program_adi": elle, "benzerlik": 1.0,
                           "tip": "el"}
            continue
        en_iyi, skor = None, 0.0
        for p_anahtar, p_ad in program_anahtarlari.items():
            import difflib
            s = difflib.SequenceMatcher(None, anahtar, p_anahtar).ratio()
            if s > skor:
                skor, en_iyi = s, p_ad
        if en_iyi and skor >= esik:
            harita[kod] = {"program_adi": en_iyi, "benzerlik": round(skor, 3),
                           "tip": "benzer"}
    return harita


def cakisma_dizini(veri):
    """{program adı: {diğer program adı: [saatler]}} — hızlı sorgu için."""
    dizin = {}
    for c in veri["cakismalar"]:
        dizin.setdefault(c["ders_a"], {})[c["ders_b"]] = c["saatler"]
        dizin.setdefault(c["ders_b"], {})[c["ders_a"]] = c["saatler"]
    return dizin


def yukle(yol=None):
    """Üretilmiş cakismalar.json'u okur. Yoksa None."""
    yol = Path(yol) if yol else cakisma_json()
    if not yol.exists():
        return None
    return json.loads(yol.read_text(encoding="utf-8"))


if __name__ == "__main__":
    yol, veri = kaydet()
    print("Ders sayısı   : %d" % len(veri["dersler"]))
    print("Çakışan çift  : %d" % len(veri["cakismalar"]))
    print("Kaydedildi    : %s" % yol)
    print("")
    print("En çok saat çakışanlar:")
    for c in veri["cakismalar"][:15]:
        print("  %-34s <-> %-34s %d saat"
              % (c["ders_a"][:34], c["ders_b"][:34], c["saat_sayisi"]))
