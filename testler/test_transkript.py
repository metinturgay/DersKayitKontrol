# -*- coding: utf-8 -*-
"""Gerçek bir transkriptin HTML yapısıyla testi.

Veri gerçek bir öğrenciden alındı ama ad/numara yer tutucuyla
değiştirildi: bu dosya başka danışmanlara da gidiyor.

Yapı, kullanıcının gönderdiği /Personel/OgrenciNot çıktısından birebir
alındı: kapanmayan <div>'ler, ilk tablodaki özet kutusu, dönem başlıkları
ve OBİS'in eski denemeleri kırmızıya boyaması dahil.
"""
import io
import os
import sys

BURASI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BURASI))

import ders_kayit as dk

OZET = [
    ("Öğrenci No", "230000003"),
    ("Adı Soyadı", "ÖRNEK ÖĞRENCİ"),
    ("Akademik Ortalama", "2,8"),
    ("Toplam AKTS", "179"),
    ("Son Dönem Ortalaması", "2,73"),
    ("Son Dönem AKTS Toplamı", "45"),
]

# (kod, yil, ad, akts, v1, v2, final, but, harf, kirmizi)
DONEMLER = [
    (1, [
        ("2709151", 2024, "ANALİZ I", 8, "58", "", "25", "62", "CC", False),
        ("2709152", 2024, "FİZİK I", 5, "65", "", "78", "", "BB", False),
        ("2709153", 2024, "SOYUT MATEMATİK I", 4, "90", "", "95", "", "AA", False),
        ("2709155", 2024, "LİNEER CEBİR I", 6, "85", "", "70", "", "BB", False),
        ("2709157", 2024, "İNGİLİZCE 1", 3, "76", "", "60", "", "CB", False),
        ("2709161", 2024, "TÜRK DİLİ 1", 2, "84", "", "84", "", "BA", False),
        ("2709162", 2024, "ATATÜRK İLKELERİ VE İNKILAP TARİHİ 1", 2, "60", "", "60", "", "CC", False),
    ]),
    (2, [
        ("2709251", 2024, "ANALİZ II", 8, "24", "", "70", "45", "FF", True),
        ("2709251", 2025, "ANALİZ II", 8, "94", "", "83", "", "BA", False),
        ("2709252", 2024, "FİZİK II", 5, "37", "", "72", "", "DC", True),
        ("2709252", 2025, "FİZİK II", 4, "51", "", "58", "57", "DC", False),
        ("2709253", 2024, "SOYUT MATEMATİK II", 4, "60", "", "99", "", "BA", False),
        ("2709255", 2024, "LİNEER CEBİR II", 6, "100", "", "80", "", "AA", False),
        ("2709257", 2024, "İNGİLİZCE 2", 3, "32", "", "44", "40", "FF", True),
        ("2709257", 2025, "İNGİLİZCE 2", 3, "52", "", "48", "32", "FF", True),
        ("2709257", 2026, "İNGİLİZCE 2", 3, "48", "", "52", "", "DC", False),
        ("2709261", 2024, "TÜRK DİLİ 2", 2, "56", "", "80", "", "CB", False),
        ("2709262", 2024, "ATATÜRK İLKELERİ VE İNKILAP TARİHİ 2", 2, "44", "", "44", "56", "DC", True),
        ("2709262", 2025, "ATATÜRK İLKELERİ VE İNKILAP TARİHİ 2", 2, "56", "", "56", "60", "DC", False),
    ]),
    (3, [
        ("2709301", 2025, "ANALİZ III", 5, "69", "", "54", "", "CC", False),
        ("2709303", 2025, "DIFERANSIYEL DENK.I", 6, "50", "", "78", "", "CB", False),
        ("2709304", 2025, "TOPOLOJI I", 6, "65", "", "58", "", "CC", False),
        ("2709305", 2025, "OLASILIK VE İSTATİSTİK I", 3, "100", "", "100", "", "AA", False),
        ("2709306", 2025, "BILGISAYAR PROGRAMLAMA I", 3, "78", "", "100", "", "AA", False),
        ("2709308", 2025, "ANALİTİK GEOMETRİ I", 5, "79", "", "76", "", "BB", False),
        ("2709309", 2025, "İNGİLİZCE III", 2, "100", "", "75", "", "BA", False),
    ]),
    (4, [
        ("2709401", 2025, "ANALİZ IV", 5, "98", "", "68", "", "BA", False),
        ("2709403", 2025, "DIFERANSIYEL DENK. II", 6, "80", "", "78", "", "BB", False),
        ("2709404", 2025, "TOPOLOJI II", 6, "80", "", "60", "", "CB", False),
        ("2709405", 2025, "OLASILIK VE İSTATİSTİK II", 3, "100", "", "100", "", "AA", False),
        ("2709406", 2025, "BİLGİSAYAR PROGRAMLAMA II", 3, "100", "", "98", "", "AA", False),
        ("2709408", 2025, "ANALİTİK GEOMETRİ II", 5, "70", "", "50", "59", "CC", False),
        ("2709409", 2026, "İNGİLİZCE IV", 2, "100", "", "100", "", "AA", False),
    ]),
    (5, [
        ("2709502", 2026, "DIFERANSIYEL GEOMETRI I", 6, "43", "", "75", "", "CC", False),
        ("2709505", 2026, "KOMPLEKS ANALİZ I", 6, "98", "", "100", "", "AA", False),
        ("2709507", 2026, "FONKSİYONEL ANALİZ I", 4, "100", "", "65", "", "BB", False),
        ("2709508", 2026, "CEBİR I", 6, "30", "", "85", "", "CC", False),
        ("2709510", 2026, "SAYILAR TEORİSİ I", 4, "90", "", "40", "", "CC", False),
        ("2709537", 2026, "FUZZY TOPOLOJİ I", 4, "90", "", "85", "", "BA", False),
    ]),
    (6, [
        ("2709602", 2026, "DİFERANSİYEL GEOMETRİ II", 6, "46", "", "60", "75", "CC", False),
        ("2709605", 2026, "KOMPLEKS ANALİZ II", 6, "59", "", "70", "", "CB", False),
        ("2709607", 2026, "FONKSİYONEL ANALİZ II", 4, "71", "", "61", "", "CC", False),
        ("2709608", 2026, "CEBİR II", 6, "45", "", "70", "", "CC", False),
        ("2709610", 2026, "SAYILAR TEORİSİ II", 4, "70", "", "87", "", "BA", False),
        ("2709637", 2026, "FUZZY TOPOLOJİ II", 4, "90", "", "83", "", "BA", False),
    ]),
]

BASLIK = (
    '<thead><tr>'
    '<th class="text-center" width="8%">Ders Kodu</th>'
    '<th class="text-center" width="7%">Yıl</th>'
    '<th class="text-center" width="15%">Ders Adı</th>'
    '<th class="text-center" width="5%">AKTS</th>'
    '<th class="text-center" width="10%">Ara<br>Sınav1</th>'
    '<th class="text-center" width="10%">Ara<br>Sınav2</th>'
    '<th class="text-center" width="10%">Genel<br>Sınav</th>'
    '<th class="text-center" width="10%">Bütünleme</th>'
    '<th class="text-center" width="10%">Harf</th>'
    '</tr></thead>'
)


def fixture():
    p = ['<div class="row"><div class="col-md-12"><div class="col-xs-9 col-sm-9">',
         '<table class="table table-striped table-bordered"><tbody>']
    for etiket, deger in OZET:
        p.append('<tr><td class="" style="width:20%%"><label>%s</label></td>'
                 '<td class="blue" colspan="3" style="width:30%%">%s</td></tr>'
                 % (etiket, deger))
    p.append('</tbody></table></div></div><div class="col-md-12">')

    for donem, satirlar in DONEMLER:
        p.append('<div class="table-header text-center">%d. DÖNEM NOTLARI</div>'
                 % donem)
        p.append('<div><table id="dynamic-table" '
                 'class="table table-striped table-bordered">' + BASLIK + '<tbody>')
        for kod, yil, ad, akts, v1, v2, fin, but, harf, kirmizi in satirlar:
            stil = ' style="color:red;font-weight:bolder"' if kirmizi else ''
            p.append('<tr%s>' % stil)
            for h in (kod, yil, ad, akts, v1, v2, fin, but, harf):
                p.append('<td class="text-center">%s</td>' % h)
            p.append('</tr>')
        # Gerçek çıktıdaki gibi: tablo kapanıyor, div'ler kapanmıyor.
        p.append('</tbody></table><hr>')
    p.append('</div></div></div></div>')
    return "".join(p)


def kontrol(ad, beklenen, gelen):
    tamam = beklenen == gelen
    print(("  [OK]  " if tamam else "  [HATA] ") + ad +
          ("" if tamam else "  beklenen=%r gelen=%r" % (beklenen, gelen)))
    return tamam


def main():
    html = fixture()
    yol = os.path.join(BURASI, "ornek_transkript.html")
    io.open(yol, "w", encoding="utf-8").write(html)

    t = dk.transkripti_coz(html)
    dk.transkripti_yazdir(t)

    print("")
    print("  === Kontroller ===")
    ok = []
    ok.append(kontrol("özet: öğrenci no", "230000003", t["ozet"].get("no")))
    ok.append(kontrol("özet: ad soyad", "ÖRNEK ÖĞRENCİ", t["ozet"].get("ad_soyad")))
    ok.append(kontrol("özet: GNO", 2.8, t["ozet"].get("gno")))
    ok.append(kontrol("özet: toplam AKTS", 179, t["ozet"].get("toplam_akts")))
    ok.append(kontrol("özet: son dönem ort", 2.73, t["ozet"].get("son_donem_ort")))

    ok.append(kontrol("6 dönem tablosu okundu", 6, len(t["tablo_bilgisi"])))
    ok.append(kontrol("sütunlar başlıktan bulundu", True,
                      all(b["yontem"] == "baslik" for b in t["tablo_bilgisi"])))
    ok.append(kontrol("dönem numaraları", [1, 2, 3, 4, 5, 6],
                      [b["donem"] for b in t["tablo_bilgisi"]]))
    ok.append(kontrol("son dönem no", 6, t["son_donem_no"]))

    ok.append(kontrol("toplam deneme", 45, len(t["denemeler"])))
    ok.append(kontrol("farklı ders", 40, len(t["son_durum"])))
    ok.append(kontrol("geçilen ders", 40, len(t["gecilen"])))
    ok.append(kontrol("GEÇİLEN AKTS = OBİS'in 179'u", 179, t["gecilen_akts"]))
    ok.append(kontrol("AKTS doğrulaması", True, t.get("akts_dogrulama")))
    ok.append(kontrol("alttan ders yok", 0, len(t["kalinan"])))
    ok.append(kontrol("alttan AKTS", 0, t["kalinan_akts"]))
    ok.append(kontrol("son kalma yılı (güncel) yok", None, t["son_kalma_yili"]))

    # OBİS'in kırmızı işareti esas: sayılmamış DC denemeleri de (2709252
    # FİZİK II 2024, 2709262 ATATÜRK 2024) geçmiş başarısızlıktır.
    ok.append(kontrol("geçmiş başarısızlık sayısı (FF + sayılmamış DC)", 5,
                      len(t["basarisiz_denemeler"])))
    ok.append(kontrol("son başarısızlık yılı", 2025, t["son_basarisizlik_yili"]))
    ok.append(kontrol("başarısız dersler",
                      ["2709257", "2709251", "2709252", "2709257", "2709262"],
                      [d["ders_kodu"] for d in t["basarisiz_denemeler"]]))

    ok.append(kontrol("tekrar edilen ders sayısı", 4, len(t["tekrar_edilen"])))
    ok.append(kontrol("tekrar edilen kodlar",
                      ["2709251", "2709252", "2709257", "2709262"],
                      [k["ders_kodu"] for k in t["tekrar_edilen"]]))

    # 2024'te FF, 2025'te BA -> geçmiş sayılmalı
    ok.append(kontrol("ANALİZ II güncel harf", "BA",
                      t["son_durum"]["2709251"]["harf"]))
    ok.append(kontrol("ANALİZ II güncel yıl", 2025,
                      t["son_durum"]["2709251"]["yil"]))
    # 3 deneme, sonuncusu DC
    ok.append(kontrol("İNGİLİZCE 2 güncel harf", "DC",
                      t["son_durum"]["2709257"]["harf"]))
    ok.append(kontrol("İNGİLİZCE 2 güncel yıl", 2026,
                      t["son_durum"]["2709257"]["yil"]))
    # AKTS denemeler arasında 5 -> 4 değişmiş; güncel olan alınmalı
    ok.append(kontrol("FİZİK II güncel AKTS (5 değil 4)", 4,
                      t["son_durum"]["2709252"]["akts"]))
    ok.append(kontrol("FİZİK II dönemi", 2, t["son_durum"]["2709252"]["donem"]))
    # Sınav notları da okunuyor mu
    ok.append(kontrol("ANALİZ I bütünleme notu", "62",
                      t["son_durum"]["2709151"].get("but")))

    ok.append(kontrol("bilinmeyen not harfi yok", {}, t["bilinmeyen_notlar"]))
    ok.append(kontrol("uyarı yok", [], t["uyarilar"]))

    print("")
    print("  %d/%d kontrol geçti." % (sum(ok), len(ok)))
    print("  Fixture: " + yol)
    return 0 if all(ok) else 1


if __name__ == "__main__":
    sys.exit(main())
