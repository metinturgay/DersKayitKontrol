# -*- coding: utf-8 -*-
"""Sınama için yıllık "Okutulacak Dersler" belgesi (docx) üretir.

Neden gerekiyor
---------------
mufredat_arsivi.py'nin işi yılları KARŞILAŞTIRMAK: hangi ders ortaya
çıkmış, hangisinin AKTS'si değişmiş, hangisi kalkmış. Elimizde tek bir
gerçek belge var (Matematik 2026-2027). Geçmiş yılların belgesini
uydurmak gerçek veriyi tahrif etmek olur.

Bunun yerine UYDURMA BİR BÖLÜMÜN uydurma yıllarını üretiyoruz. Değişimler
önceden bilindiği için türetimin doğruluğu kanıtlanabiliyor. Belgeler
tamamen sentetiktir; veri/ klasörüne yazılmaz, gerçek veriyle
karıştırılmamalıdır.

docx aslında bir zip: içindeki word/document.xml okunuyor (bkz.
mufredat.oku). Word'ün geri kalan parçaları çözümleme için gereksiz,
o yüzden en küçük geçerli iskeleti yazıyoruz.
"""
import io
import os
import zipfile

W = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
ROMEN = {1: "I", 2: "II", 3: "III", 4: "IV",
         5: "V", 6: "VI", 7: "VII", 8: "VIII"}

_ILISKILER = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/'
    '2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/'
    'officeDocument/2006/relationships/officeDocument" '
    'Target="word/document.xml"/></Relationships>')

_TIPLER = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/'
    'content-types">'
    '<Default Extension="xml" ContentType="application/xml"/>'
    '<Override PartName="/word/document.xml" ContentType="application/'
    'vnd.openxmlformats-officedocument.wordprocessingml.document.main'
    '+xml"/></Types>')


def _kacar(m):
    return (str(m).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def _p(metin):
    return ('<w:p><w:r><w:t xml:space="preserve">%s</w:t></w:r></w:p>'
            % _kacar(metin))


def _satir(hucreler):
    tc = "".join("<w:tc>%s</w:tc>" % _p(h) for h in hucreler)
    return "<w:tr>%s</w:tr>" % tc


def _tablo(dersler, toplam):
    satirlar = [_satir(("DersinKodu", "Dersin Adı", "T", "U", "K", "AKTS"))]
    for d in dersler:
        ad = d["ad"]
        if d.get("tip") == "TOS":
            ad += " (TOS)"
        elif d.get("tip") == "Seçmeli":
            ad += " (Seç.)"
        satirlar.append(_satir((d["kod"], ad, d.get("teorik", 3),
                                d.get("uygulama", 0), d.get("kredi", 3),
                                d["akts"])))
    satirlar.append(_satir(("", "TOPLAM KREDİ", "", "", "", toplam)))
    return "<w:tbl>%s</w:tbl>" % "".join(satirlar)


def belge_yaz(yol, yariyillar, genel_toplam=None):
    """yariyillar: {yarıyıl no: [ders sözlüğü, ...]}

    Ders sözlüğü: {"kod", "ad", "akts", "tip"?}. tip verilmezse "Zorunlu".
    Seçmeli/TOS dersleri ayrı bir "SEÇMELİ" tablosuna konur; gerçek
    belgede de öyle duruyorlar.
    """
    govde = []
    toplam_hepsi = 0
    for y in sorted(yariyillar):
        dersler = yariyillar[y]
        toplam = sum(d["akts"] for d in dersler)
        toplam_hepsi += toplam
        zorunlu = [d for d in dersler if d.get("tip", "Zorunlu") == "Zorunlu"]
        digerleri = [d for d in dersler
                     if d.get("tip", "Zorunlu") != "Zorunlu"]
        govde.append(_p("%s. YARIYIL" % ROMEN[y]))
        govde.append(_tablo(zorunlu, toplam))
        if digerleri:
            govde.append(_p("%s. YARIYIL SEÇMELİ DERSLER" % ROMEN[y]))
            govde.append(_tablo(digerleri, ""))
    govde.append(_p("TOPLAM AKTS: %d"
                    % (genel_toplam if genel_toplam is not None
                       else toplam_hepsi)))

    belge = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<w:document xmlns:w="%s"><w:body>%s</w:body></w:document>'
             % (W, "".join(govde)))

    klasor = os.path.dirname(os.path.abspath(yol))
    if klasor and not os.path.isdir(klasor):
        os.makedirs(klasor)
    with zipfile.ZipFile(yol, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", _TIPLER)
        z.writestr("_rels/.rels", _ILISKILER)
        z.writestr("word/document.xml", belge.encode("utf-8"))
    return yol


# =====================================================================
#  Sınama bölümü: "Sınama Mühendisliği", dört yıl, bilinen değişimler
# =====================================================================
#   2023 -> 2024 : ANALİZ I  6 -> 5 AKTS  ve yeni ders UYGULAMA I (1)
#   2024 -> 2025 : ders kodu değişikliği  9801301 -> 9801311 (aynı ders)
#   2025 -> 2026 : ESKİ SEÇMELİ kalkıyor
def sinama_arsivi(klasor):
    """{yıl: yol} — dört yıllık uydurma arşiv üretir."""

    def yariyil(y, ekler=()):
        temel = [
            {"kod": "980%d101" % y, "ad": "Zorunlu %d-A" % y, "akts": 8},
            {"kod": "980%d102" % y, "ad": "Zorunlu %d-B" % y, "akts": 8},
            {"kod": "980%d103" % y, "ad": "Zorunlu %d-C" % y, "akts": 7},
            {"kod": "980%d104" % y, "ad": "Zorunlu %d-D" % y, "akts": 7},
        ]
        return temel + list(ekler)

    yillar = {}
    for yil in (2023, 2024, 2025, 2026):
        y = {}
        for no in range(1, 9):
            y[no] = yariyil(no)
        # 1. yarıyıl: ANALİZ I ve (2024'ten sonra) UYGULAMA I
        y[1] = [
            {"kod": "9801101", "ad": "Analiz I",
             "akts": 6 if yil < 2024 else 5},
            {"kod": "9801102", "ad": "Fizik I", "akts": 6},
            {"kod": "9801103", "ad": "Kimya I", "akts": 6},
            {"kod": "9801104", "ad": "Türk Dili I", "akts": 6},
            {"kod": "9801105", "ad": "İngilizce I", "akts": 6},
        ]
        if yil >= 2024:
            y[1].append({"kod": "9801163", "ad": "Uygulama I", "akts": 1})
        # 3. yarıyıl: kodu değişen ders
        y[3] = [
            {"kod": "9801301" if yil < 2025 else "9801311",
             "ad": "Cebir I", "akts": 10},
            {"kod": "9801302", "ad": "Analiz III", "akts": 10},
            {"kod": "9801303", "ad": "Diferansiyel Denklemler I",
             "akts": 10},
        ]
        # 5. yarıyıl: kalkan seçmeli + TOS
        y[5] = [
            {"kod": "9801501", "ad": "Kompleks Analiz I", "akts": 10},
            {"kod": "9801502", "ad": "Nümerik Analiz I", "akts": 10},
            {"kod": "9801591", "ad": "Sınama Seçmeli I", "akts": 10,
             "tip": "Seçmeli"},
        ]
        if yil < 2026:
            y[5].append({"kod": "9801592", "ad": "Eski Seçmeli",
                         "akts": 10, "tip": "Seçmeli"})
        y[7] = [
            {"kod": "9801701", "ad": "Bitirme Çalışması I", "akts": 20},
            {"kod": "9801746", "ad": "Ortak Seçmeli I", "akts": 5,
             "tip": "TOS"},
            {"kod": "9801747", "ad": "Ortak Seçmeli II", "akts": 5,
             "tip": "TOS"},
        ]
        yillar[yil] = belge_yaz(os.path.join(klasor, "%d.docx" % yil), y)
    return yillar


if __name__ == "__main__":
    import sys
    import tempfile

    hedef = sys.argv[1] if len(sys.argv) > 1 else tempfile.mkdtemp()
    for yil, yol in sorted(sinama_arsivi(hedef).items()):
        print("%d  %s  %d bayt" % (yil, yol, os.path.getsize(yol)))
