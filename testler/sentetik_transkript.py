# -*- coding: utf-8 -*-
"""Müfredat belgesinden sentetik transkript HTML'i üretir.

Neden gerekiyor
---------------
Elimizde yalnız 2023 girişli öğrencilerin transkriptleri var. 2024
girişli bir öğrencinin sistemden doğru geçtiğini gösterebilmek için
onun transkriptini müfredat belgesinden üretiyoruz: belgedeki 1-4.
yarıyıl derslerinin tamamı, belgedeki GÜNCEL AKTS'lerle, hepsi geçilmiş.

Bu fotoğrafın doğruluğu bağımsız olarak teyit edildi (2026-09):
2024 girişli, hiç dersten kalmamış gerçek bir öğrencinin OBİS ders
kayıt sayfasında "Genel Krd 120" yazıyor; belgeden üretilen transkript
de tam 120 AKTS veriyor.

Sentetik olduğu için gerçek veriyle KARIŞTIRILMAMALI: yalnız testler/
altında kullanılır, cikti/ klasörüne yazılmaz.
"""

BASLIK = """<html><head><meta charset="utf-8"></head><body>
<div class="col-xs-9 col-sm-9">
    <table class="table table-striped table-bordered">
        <tbody>
            <tr><td class="" style="width:20%%"><label>
                &Ouml;&#287;renci No</label></td>
                <td class="blue" colspan="3" style="width:30%%">
                %(no)s</td></tr>
            <tr><td class="" style="width:20%%"><label>
                Ad&#305; Soyad&#305;</label></td>
                <td class="blue" colspan="3" style="width:30%%">
                %(ad)s</td></tr>
            <tr><td class="" style="width:20%%"><label>
                Akademik Ortalama</label></td>
                <td class="blue" colspan="3" style="width:30%%">
                %(gno)s</td></tr>
            <tr><td class="" style="width:20%%"><label>
                Toplam AKTS</label></td>
                <td class="blue" colspan="3" style="width:30%%">
                %(toplam)d</td></tr>
        </tbody>
    </table>
</div>
<div class="col-md-12">
"""

DONEM_BASI = """    <div class='table-header text-center'>%d. D&Ouml;NEM NOTLARI</div>
    <table id="dynamic-table" class="table table-striped table-bordered">
        <thead><tr>
            <th class="text-center">Ders Kodu</th>
            <th class="text-center">Y&#305;l</th>
            <th class="text-center">Ders Ad&#305;</th>
            <th class="text-center">AKTS</th>
            <th class="text-center">Ara S&#305;nav 1</th>
            <th class="text-center">Ara S&#305;nav 2</th>
            <th class="text-center">Genel S&#305;nav</th>
            <th class="text-center">B&#252;t&#252;nleme</th>
            <th class="text-center">Harf</th>
        </tr></thead>
        <tbody>
"""

SATIR = """            <tr %(stil)s>
                <td class="text-center">%(kod)s</td>
                <td class="text-center">%(yil)d</td>
                <td class="text-center">%(ad)s</td>
                <td class="text-center">%(akts)s</td>
                <td class="text-center">70</td>
                <td class="text-center"></td>
                <td class="text-center">70</td>
                <td class="text-center"></td>
                <td class="text-center">%(harf)s</td>
            </tr>
"""

DONEM_SONU = "        </tbody>\n    </table>\n"
SON = "</div>\n</body></html>\n"

KIRMIZI = 'style="color:red;font-weight:bolder"'


def uret(mufredat, no, yariyillar=(1, 2, 3, 4), gno="3,00",
         ad="SENTETIK OGRENCI", notlar=None, baslangic_yili=None):
    """Belgedeki yarıyıl derslerinden transkript HTML'i kurar.

    notlar: {ders_kodu: harf} - verilmeyen derse BB yazılır. Kırmızı
            (OBİS'in saymadığı) satır için harf FF/DZ ya da DC olabilir;
            başarısız harfler otomatik kırmızı işaretlenir.
    """
    notlar = notlar or {}
    belge = mufredat["dersler"]
    ilk_yil = baslangic_yili or (2000 + int(str(no)[:2]) + 1)

    govde, toplam = [], 0
    for yariyil in yariyillar:
        kodlar = [k for k, b in sorted(belge.items())
                  if b.get("yariyil") == yariyil
                  and (b.get("tip") or "").startswith("Zorunlu")]
        if not kodlar:
            continue
        govde.append(DONEM_BASI % yariyil)
        for kod in kodlar:
            b = belge[kod]
            harf = notlar.get(kod, "BB")
            basarisiz = harf in ("FF", "DZ", "FD")
            govde.append(SATIR % {
                "kod": kod, "ad": b["ders_adi"], "akts": b["akts"],
                "harf": harf, "stil": KIRMIZI if basarisiz else "",
                "yil": ilk_yil + (yariyil - 1) // 2,
            })
            toplam += b["akts"] or 0
        govde.append(DONEM_SONU)

    return (BASLIK % {"no": no, "ad": ad, "gno": gno, "toplam": toplam}
            + "".join(govde) + SON)
