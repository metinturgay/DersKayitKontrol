# -*- coding: utf-8 -*-
"""Ders adlarını karşılaştırılabilir hâle getirir.

Neden ayrı bir dosya
--------------------
Bunlar yönetmelikten gelen kurallar DEĞİL, metin işi: Türkçe harfleri
sadeleştirmek, romen rakamını sayıya çevirmek, "Dif. Denk." ile
"Diferansiyel Denklemler"in aynı ders olduğunu görmek.

Ayrılma sebebi pratik: kurulum sihirbazı bölüm profilini ÜRETMEDEN önce
müfredat belgelerini okumak, dolayısıyla ders adlarını eşleştirmek
zorunda. yonetmelik.py ise profile bağlı. Bu araçlar orada kalsaydı
sihirbaz kendi üreteceği dosyaya ihtiyaç duyardı.

yonetmelik.py bu adları dışarı aynen veriyor; `ym.ad_benzerligi` gibi
mevcut kullanımların hepsi çalışmaya devam eder.
"""
import difflib
import re

_TURKCE_ESLER = {
    "ç": "c", "Ç": "C", "ğ": "g", "Ğ": "G", "ı": "i", "İ": "i",
    "ö": "o", "Ö": "O", "ş": "s", "Ş": "S", "ü": "u", "Ü": "U",
}

# Ders adlarında sık geçen ve eşleştirmede gürültü yapan ekler
_TEMIZLENECEK = re.compile(r"\(.*?\)|\*+|\bSEC\b|\bSECMELI\b", re.IGNORECASE)

_ROMEN = {"I": "1", "II": "2", "III": "3", "IV": "4", "V": "5",
          "VI": "6", "VII": "7", "VIII": "8", "IX": "9", "X": "10"}

# Aynı dersin farklı müfredatlarda farklı yazılmış hâlleri.
# Buraya yalnızca gözle doğrulanmış eşler eklenmeli.
_YAZIM_ESLERI = {
    "DIFERENSIYEL": "DIFERANSIYEL",
    "DIFERANSIYEL": "DIFERANSIYEL",
    "DENK": "DENKLEMLER",
    "DENKLEMLERI": "DENKLEMLER",
    "MAT": "MATEMATIK",
    "GEOMETRI": "GEOMETRI",
}


def _sadelestir(metin):
    duz = "".join(_TURKCE_ESLER.get(h, h) for h in (metin or ""))
    return duz.upper()


def ders_adi_anahtari(ad):
    """Ders adını karşılaştırılabilir bir anahtara çevirir.

    'DİFERENSİYEL GEOMETRİ I'  -> 'DIFERANSIYEL GEOMETRI 1'
    'İNGİLİZCE 1'              -> 'INGILIZCE 1'
    'EĞRİLER TEORİSİ (SEÇ.)'   -> 'EGRILER TEORISI'
    """
    # Not: yaygın seçmeli derslerin birim adı (EDEBİYAT FAKÜLTESİ vb.)
    # ders_kaydini_coz() tarafından ayrı bir alana ("birim") alınıyor,
    # buraya gelmiyor.
    metin = _TEMIZLENECEK.sub(" ", _sadelestir(ad))
    metin = re.sub(r"[^A-Z0-9]+", " ", metin).strip()

    parcalar = []
    for parca in metin.split():
        parca = _YAZIM_ESLERI.get(parca, parca)
        parcalar.append(_ROMEN.get(parca, parca))
    return " ".join(parcalar)


def ders_seviyesi(ad):
    """Ders adının sonundaki seviye numarasını döndürür (I -> 1, II -> 2).

    'DİFERENSİYEL GEOMETRİ I'  -> 1
    'DİFERANSİYEL GEOMETRİ II' -> 2
    'SOYUT MATEMATİK'          -> None
    """
    anahtar = ders_adi_anahtari(ad)
    if not anahtar:
        return None
    son = anahtar.split()[-1]
    return int(son) if son.isdigit() else None


def ad_benzerligi(a, b):
    """İki ders adının 0-1 arası benzerliği.

    Sondaki seviye numarası KESİN ayırıcıdır: 'DİFERANSİYEL GEOMETRİ I' ile
    'DİFERANSİYEL GEOMETRİ II' harf harf %96 benzer, ama farklı derslerdir.
    Seviyesi farklı iki ad hiçbir zaman eşleşmez.
    """
    sa, sb = ders_seviyesi(a), ders_seviyesi(b)
    if sa is not None and sb is not None and sa != sb:
        return 0.0
    return difflib.SequenceMatcher(
        None, ders_adi_anahtari(a), ders_adi_anahtari(b)).ratio()


# Bu eşiğin altındaki benzerlikler hiç raporlanmaz; üstündekiler
# "danışman doğrulasın" diye işaretlenir. Otomatik karar verilmez.
BENZERLIK_ESIGI = 0.88
