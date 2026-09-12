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

VERI = yollar.veri()
CAKISMA_JSON = VERI / "cakismalar.json"

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


def programi_oku(xlsx_yolu=None):
    """{ders adı: {(gün, saat), ...}} ve ders başına ayrıntı döndürür."""
    import openpyxl

    if xlsx_yolu is None:
        adaylar = sorted(glob.glob(str(Path.home() / "Desktop" / "*Ders Program*.xlsx")))
        if not adaylar:
            raise SystemExit("Ders programı xlsx bulunamadı.")
        xlsx_yolu = adaylar[0]

    kitap = openpyxl.load_workbook(xlsx_yolu, data_only=True)
    if SAYFA_ADI not in kitap.sheetnames:
        raise SystemExit(
            "Ders programında %r sayfası yok. Dosyadaki sayfalar: %s\n"
            "Doğru adı veri/bolum.json -> program.sayfa_adi altına yazın."
            % (SAYFA_ADI, ", ".join(kitap.sheetnames)))
    ws = kitap[SAYFA_ADI]

    yerlesim = {}     # ders adı -> {(gün, saat)}
    ayrinti = {}      # ders adı -> {"derslikler": set, "siniflar": set}
    gun = None
    sinif = None

    for r in range(1, ws.max_row + 1):
        a = _gun_adi(ws.cell(r, 1).value)
        if a:
            for g in GUNLER:
                if a.startswith(g[:4]):
                    gun = g
                    break
        b = ws.cell(r, 2).value
        if b is not None and str(b).strip().isdigit():
            sinif = int(str(b).strip())

        # Saat başlığı satırı mı? (C sütununda saat yazıyorsa)
        if str(ws.cell(r, 3).value or "").strip() in SAAT_SUTUNLARI.values():
            continue
        if gun is None:
            continue

        for sutun_no in range(3, 14):
            harf = _sutun_harfi(sutun_no)
            saat = SAAT_SUTUNLARI.get(harf)
            if not saat:
                continue
            ad, derslik, grup = _ders_adi(ws.cell(r, sutun_no).value)
            if not ad or ad.upper() in YOKSAY:
                continue
            yerlesim.setdefault(ad, {}).setdefault(grup or "", set()).add(
                (gun, saat))
            bilgi = ayrinti.setdefault(ad, {"derslikler": set(), "siniflar": set()})
            if derslik:
                bilgi["derslikler"].add(derslik)
            if sinif:
                bilgi["siniflar"].add(sinif)

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
    cikti = Path(cikti) if cikti else CAKISMA_JSON
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
    yol = Path(yol) if yol else CAKISMA_JSON
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
