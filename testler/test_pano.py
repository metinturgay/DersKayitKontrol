# -*- coding: utf-8 -*-
"""Danışman özeti ve HTML panosunun testi.

Danışmanın gerçek ders kayıt sayfası (cikti/ altında, varsa)
varsa onunla, yoksa test kataloğuyla çalışır. Ayrıca uyarıların tetiklendiğini
görmek için sentetik bir "sorunlu öğrenci" üretir.
"""
import io
import json
import re
import os
import sys
from pathlib import Path

BURASI = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(BURASI)
sys.path.insert(0, KOK)
sys.path.insert(0, BURASI)

import ders_kayit as dk
import mufredat
import ozet
import rapor
import yonetmelik as ym
import test_transkript as tt
import test_eslestirme as te

OK = []


def kontrol(ad, beklenen, gelen):
    tamam = beklenen == gelen
    print(("  [OK]  " if tamam else "  [HATA] ") + ad +
          ("" if tamam else "\n          beklenen=%r gelen=%r"
           % (beklenen, gelen)))
    OK.append(tamam)


def _tirnak_hatalari(html):
    """Panonun JS bloğunda kapanmamış tek tırnak arar.

    Satır bazında kaçışsız ' sayar; tek sayıysa o satırdaki bir string
    kapanmamış demektir (yorum satırları ve çift tırnaklı metinler hariç).
    Kaba ama bu hata sınıfını yakalamaya yetiyor.
    """
    blok = html.split('<script>', 1)[-1].split('</script>', 1)[0]
    hatali = []
    for sira, satir in enumerate(blok.split("\n"), 1):
        kirpik = satir.strip()
        if kirpik.startswith("//") or not kirpik:
            continue
        temiz = kirpik.replace("\\'", "")          # kaçırılmışları at
        temiz = re.sub(r'"[^"]*"', "", temiz)      # çift tırnaklıları at
        if temiz.count("'") % 2:
            hatali.append((sira, kirpik[:70]))
    return hatali


def ornek_kayit():
    """Gerçek sayfa varsa onu kullan, yoksa test kataloğundan kur."""
    # Sabit bir ogrenci numarasi YAZILMIYOR: depo herkese acik ve
    # numara kisisel veridir. cikti/ altindaki HERHANGI bir sayfa ayni
    # isi goruyor; yoksa gomulu sentetik veriye dusuluyor.
    adaylar = sorted((Path(KOK) / "cikti").glob("ders_sayfasi_*.html"))
    gercek = adaylar[0] if adaylar else Path(KOK) / "cikti" / "yok.html"
    if gercek.exists():
        kayit = dk.ders_kaydini_coz(gercek.read_text(encoding="utf-8"))
        kaynak = "gerçek sayfa"
    else:
        kayit = {
            "no": "230000003", "ad": "ÖRNEK ÖĞRENCİ",
            "durum": "ONAY BEKLENİYOR", "genel_ort": 2.8, "genel_kredi": 179,
            "ders_sayisi": 4, "toplam_akts": 16, "maks_akts": 30,
            "katalog": [dict(d, donem="7. Dönem Dersleri", eklenebilir=True,
                             doldu=False, yesil_yazi=False)
                        for d in te.KATALOG],
            "secili_dersler": [
                {"ders_no": "2709734", "ders_adi": "MÜZİK VE MATEMATİK I (SEÇ.)",
                 "aciklama": "Ders ilk kez alınıyor"},
                {"ders_no": "2709735", "ders_adi": "LORENTZ GEOMETRİ I (SEÇ)",
                 "aciklama": "Ders ilk kez alınıyor"},
                {"ders_no": "2709747", "ders_adi": "MATEMATİK VE OYUN*",
                 "aciklama": "Ders ilk kez alınıyor"},
                {"ders_no": "2709753", "ders_adi": "MATEMATİK UYGULAMALARI I",
                 "aciklama": "Ders ilk kez alınıyor"},
            ],
        }
        kaynak = "test kataloğu"
    kayit["transkript"] = dk.transkripti_coz(tt.fixture())
    return kayit, kaynak


def sorunlu_ogrenci():
    """Uyarıların tetiklendiğini görmek için sentetik vaka.

    2. sınıf (hiç 5. dönem almamış), alttan dersi var, alttan dersi
    seçmemiş, üstelik 7. dönemden ders seçmiş.
    """
    transkript = dk.transkripti_coz(tt.fixture())
    # 5. ve 6. dönemi sil -> öğrenci hiç 5. dönem almamış olsun
    for anahtar in ("denemeler", "gecilen", "kalinan", "dc_dersler"):
        transkript[anahtar] = [d for d in transkript[anahtar]
                               if (d.get("donem") or 0) < 5]
    transkript["son_durum"] = {k: v for k, v in transkript["son_durum"].items()
                               if (v.get("donem") or 0) < 5}
    # 3. dönemden bir dersi başarısız yap
    for d in transkript["denemeler"]:
        if d["ders_kodu"] == "2709303":
            d["harf"], d["sonuc"] = "FF", "kaldi"
            transkript["son_durum"]["2709303"] = d
            transkript["kalinan"] = [d]
            transkript["gecilen"] = [g for g in transkript["gecilen"]
                                     if g["ders_kodu"] != "2709303"]
    transkript["kalinan_akts"] = 6
    transkript["gecilen_akts"] = sum(g["akts"] for g in transkript["gecilen"])

    return {
        "no": "240000099", "ad": "TEST ÖĞRENCİ", "durum": "ONAY BEKLENİYOR",
        "genel_ort": 1.80, "ders_sayisi": 1, "toplam_akts": 4,
        "maks_akts": 30,
        "katalog": [
            {"ders_no": "2709303", "ders_adi": "DIFERANSIYEL DENK.I", "akts": 5,
             "donem": "3. Dönem Dersleri", "eklenebilir": True, "doldu": False,
             "yesil_yazi": False, "secili": False, "ilk_bayrak": True},
            {"ders_no": "2705760", "ders_adi": "YAPAY ZEKAYA GİRİŞ I*",
             "akts": 4, "donem": "7. Dönem Dersleri", "eklenebilir": True,
             "doldu": False, "yesil_yazi": False, "secili": True},
        ],
        "secili_dersler": [
            {"ders_no": "2705760", "ders_adi": "YAPAY ZEKAYA GİRİŞ I*",
             "aciklama": "Ders ilk kez alınıyor"}],
        "transkript": transkript,
    }


def main():
    kayit, kaynak = ornek_kayit()
    print("  Kaynak: " + kaynak)
    o = ozet.ogrenci_ozeti(kayit, icinde_bulunulan_yil=2026)

    print("")
    print("  === %s ===" % kayit.get("ad", "örnek öğrenci"))
    print("  Sınıf %s · hedef dönem %s · AKTS limiti %s"
          % (o["donem_durumu"]["sinif"], o["donem_durumu"]["hedef_donem"],
             o["akts_limiti"]))
    print("  " + o["son_sinif"]["sebep"])
    print("")
    for u in o["uyarilar"]:
        print("  [%-9s] %-38s %s"
              % (u["onem"], u["baslik"][:38], u["ders_no"] or ""))

    print("")
    kontrol("3. sınıf", 3, o["donem_durumu"]["sinif"])
    kontrol("hedef dönem 7", 7, o["donem_durumu"]["hedef_donem"])
    kontrol("son sınıf", True, o["son_sinif"]["son_sinif"])
    kontrol("AKTS limiti sınırsız", None, o["akts_limiti"])
    kontrol("alttan ders yok", 0, len(o["alttan_acik"]))
    kontrol("AKTS kaybı 1", 1, o["akts_kaybi"]["toplam_kayip"])
    kontrol("mezuniyet 243 AKTS", 243,
            o["akts_kaybi"]["beklenen_mezuniyet_akts"])
    kontrol("mezuniyet riski yok", False, o["akts_kaybi"]["riskli"])
    if kaynak == "gerçek sayfa":
        basliklar = [u["baslik"] for u in o["uyarilar"]]
        kontrol("kod değişikliği özet notu var", True,
                "Müfredat kod değişikliği" in basliklar)
        # Örnek öğrenci eski koduyla geçtiği dersleri seçmemiş -> eylem yok
        kontrol("seçilmediği için ÇIKAR uyarısı yok", False,
                any(b.startswith("ÇIKAR") for b in basliklar))

        # --- KAPSAM: yaygın seçmeli havuzu kurallara girmemeli ---------
        # Sayfadaki 2. sekmede başka fakültelerin dersleri var
        # (MADDE 9/1-ı). Bunlar bölümün müfredatı değil; ne eşleştirmeye
        # ne de son sınıf kararına girmeli.
        print("")
        print("  === Kapsam ayrımı ===")
        kontrol("bölüm dersleri kurallara girdi", 33, len(o["eslesmeler"]))
        kontrol("yaygın seçmeli kapsam dışı", 157,
                o["yaygin_secmeli_sayisi"])
        kontrol("eşleşmelerin hepsi bölüm sekmesinden", True,
                all(e["ders"].get("sekme") == ozet.BOLUM_SEKMESI
                    for e in o["eslesmeler"]))
        # Son sınıf kararı bölüm dersi üzerinden verilmeli
        kontrol("son sınıf kararı bölüm dersiyle", True,
                "EDEBİYAT" not in (o["son_sinif"]["sebep"] or ""))
        # Birim adı ders adına karışmamalı
        birimliler = [d for d in kayit["katalog"] if d.get("birim")]
        kontrol("birim adı ayrı alanda", True, len(birimliler) > 100)
        kontrol("birim adı ders adına karışmamış", True,
                all("FAKÜLTESİ" not in (d["ders_adi"] or "")
                    for d in kayit["katalog"]))

    # --- sorunlu öğrenci ---
    s = sorunlu_ogrenci()
    so = ozet.ogrenci_ozeti(s, icinde_bulunulan_yil=2026)
    print("")
    print("  === TEST ÖĞRENCİ (sentetik) ===")
    print("  Sınıf %s · hedef dönem %s · AKTS limiti %s"
          % (so["donem_durumu"]["sinif"], so["donem_durumu"]["hedef_donem"],
             so["akts_limiti"]))
    print("  " + so["son_sinif"]["sebep"])
    if so.get("ust_donem"):
        print("  " + so["ust_donem"]["sebep"])
    print("")
    for u in so["uyarilar"]:
        print("  [%-9s] %-38s %s"
              % (u["onem"], u["baslik"][:38], u["ders_no"] or ""))

    print("")
    basliklar = [u["baslik"] for u in so["uyarilar"]]
    kontrol("2. sınıf", 2, so["donem_durumu"]["sinif"])
    kontrol("hedef dönem 5", 5, so["donem_durumu"]["hedef_donem"])
    kontrol("son sınıf DEĞİL", False, so["son_sinif"]["son_sinif"])
    kontrol("üst dönem durumuna girdi", True,
            so["son_sinif"]["ust_donem_durumu"])
    kontrol("GANO 1,80 -> limit 45", 45, so["akts_limiti"])
    kontrol("alttan ders seçilmemiş uyarısı", True,
            "Alttan ders SEÇİLMEMİŞ" in basliklar)
    kontrol("üst dönem hakkı aşımı uyarısı", True,
            "ÜST DÖNEM HAKKI AŞILMIŞ" in basliklar)
    kontrol("durum rengi yapılacak", "yapilacak", so["durum_rengi"])

    print("")
    print("  === Mezuniyet AKTS hesabı ===")
    p = o["projeksiyon"]
    print("  başarılı %d + kalan yükümlülük %d + girilmemiş dönem %s (%d)"
          " − kayıp %d = %d AKTS"
          % (p["basarili_akts"], p["alt_yukumluluk"], p["kalan_donemler"],
             p["kalan_donem_akts"], p["akts_kaybi"], p["projeksiyon"]))
    kontrol("başarılı AKTS 179", 179, p["basarili_akts"])
    kontrol("girilmiş dönemler 1-6", [1, 2, 3, 4, 5, 6],
            p["girilen_donemler"])
    kontrol("girilmiş dönem planı 180", 180, p["girilen_plan_akts"])
    kontrol("kalan yükümlülük 1 (180-179)", 1, p["alt_yukumluluk"])
    kontrol("girilmemiş dönemler 7 ve 8", [7, 8], p["kalan_donemler"])
    kontrol("girilmemiş dönem AKTS 64 (32+32)", 64, p["kalan_donem_akts"])
    kontrol("mezuniyet projeksiyonu 243", 243, p["projeksiyon"])
    kontrol("asgari 240'ın üstünde", True, p["yeterli"])
    # akts_kaybi yolundan çıkan sonuçla tutmalı (244 - 1 kayıp)
    kontrol("akts_kaybi ile aynı sonuç",
            o["akts_kaybi"]["beklenen_mezuniyet_akts"], p["projeksiyon"])
    # Eksiği olan öğrenci de mezun olabilmeli: kalan yükümlülük sayılmalı
    ps = so["projeksiyon"]
    print("  sorunlu: başarılı %d + yükümlülük %d + girilmemiş %d = %d"
          % (ps["basarili_akts"], ps["alt_yukumluluk"],
             ps["kalan_donem_akts"], ps["projeksiyon"]))
    kontrol("eksiği olan öğrenci de 240'ı geçebiliyor", True, ps["yeterli"])

    print("")
    print("  === Kontenjan planı (yönetici özeti) ===")
    # DİKKAT: burada SABİT sayı beklenmez. Örnek gerçek bir öğrenci ve
    # kayıt dönemi boyunca ders seçimi değişiyor; sabit beklenti her
    # taramadan sonra testi kırar ve kodda hata varmış gibi gösterir.
    # Onun yerine kontenjan planının DEĞİŞMEZLERİ sınanıyor.
    # Hedef dönem SABİT DEĞİL: 3. sınıf danışmanında 5, 4. sınıfta 7.
    # Testin kendisi de sabitlenmemeli, yoksa gerçek veri olmayan temiz
    # bir kurulumda (yeni danışman) durup dururken kırmızı yanar.
    hedefler = sorted({x["donem_ihtiyaci"]["donem"] for x in (o, so)
                       if x.get("donem_ihtiyaci")})
    hedef = hedefler[-1] if hedefler else 7
    kp = ozet.kontenjan_plani([o, so], hedef_donem=hedef)
    di = o["donem_ihtiyaci"]
    kontrol("ihtiyaç = plan - seçilen", max(0, di["plan_akts"] - di["secilen_akts"]),
            di["ihtiyac_akts"])
    kontrol("ihtiyaç dersi = ihtiyaç AKTS / tipik AKTS (yukarı yuvarlak)",
            -(-di["ihtiyac_akts"] // di["tipik_akts"]) if di["tipik_akts"] else 0,
            di["ihtiyac_ders"])
    # Plan yalnız hedef dönemdeki öğrencileri saymalı. Bunu "hepsi aynı
    # dönemde" diye sınamak yanlış: karışık bir listede (3. ve 4. sınıf
    # bir arada) doğru davranışta bile kırılır. Gerçek değişmez şudur:
    # BAŞKA dönemdeki bir öğrenci plana hiç dokunmamalı.
    baska = [x for x in (o, so)
             if (x.get("donem_ihtiyaci") or {}).get("donem") != hedef]
    kontrol("başka dönemdeki öğrenci %d. dönem planını etkilemiyor" % hedef,
            (kp["ogrenci_sayisi"], kp["toplam_kontenjan"]),
            (lambda p: (p["ogrenci_sayisi"], p["toplam_kontenjan"]))(
                ozet.kontenjan_plani([x for x in (o, so) if x not in baska],
                                     hedef_donem=hedef)))
    kontrol("öğrenci sayısı ihtiyacı olanlarla tutuyor",
            len([x for x in (o, so)
                 if (x.get("donem_ihtiyaci") or {}).get("donem") == hedef
                 and x["donem_ihtiyaci"]["ihtiyac_akts"] > 0]),
            kp["ogrenci_sayisi"])
    kontenjanlar = [d["ilave_kontenjan"] for d in kp["dersler"]]
    kontrol("dağıtım toplamı ihtiyaca eşit", kp["toplam_kontenjan"],
            sum(kontenjanlar))
    kontrol("dağıtım dengeli (fark en fazla 1)", True,
            (max(kontenjanlar) - min(kontenjanlar) <= 1) if kontenjanlar
            else kp["toplam_kontenjan"] == 0)
    kontrol("kontenjan negatif değil", True,
            all(x >= 0 for x in kontenjanlar))
    print("  %d öğrenci, %d kontenjan, %d derse dağıtıldı%s"
          % (kp["ogrenci_sayisi"], kp["toplam_kontenjan"], len(kp["dersler"]),
             ("  (en çok %d, en az %d)" % (max(kontenjanlar), min(kontenjanlar)))
             if kontenjanlar else ""))
    if not kp["ogrenci_sayisi"]:
        print("  (bu taramada 7. dönemde eksiği olan öğrenci yok - "
              "kontenjan planı boş, beklenen bir durum)")

    # --- pano ---
    # Katalog öğrenciye göre değişiyor; ders listesi sekmesi için
    # hepsinin birleşimi veriliyor.
    import ders_programi as dprog
    program = dprog.yukle()
    katalog = {}
    for k2 in (kayit, s):
        for d in k2.get("katalog") or []:
            if (d.get("sekme") or ozet.BOLUM_SEKMESI) == ozet.BOLUM_SEKMESI:
                katalog.setdefault(d["ders_no"], d)
    # AKTS değişim sekmesi de gerçek veriyle çizilsin. Fixture'da taban
    # öğrenci yok; modül en eski transkript kaydına düşmeli.
    import akts_degisimi
    degisim = akts_degisimi.hesapla(
        {(k2.get("no") or str(i)): k2.get("transkript")
         for i, k2 in enumerate((kayit, s))},
        mufredat.yukle(), katalog)

    yol = rapor.pano_yaz([(kayit, o), (s, so)],
                         Path(BURASI) / "ornek_pano.html",
                         danisman="12621", kontenjan=kp, program=program,
                         katalog=sorted(katalog.values(),
                                        key=lambda d: d["ders_no"]),
                         akts_degisim=degisim)
    boyut = yol.stat().st_size
    icerik = yol.read_text(encoding="utf-8")
    kontrol("pano yazıldı", True, boyut > 5000)
    # Ad sabit kodlanmaz: gerçek sayfa varsa oradan, yoksa yer
    # tutucudan gelir. İkisinde de panoya gömülmüş olmalı.
    kontrol("veri gömülü", True,
            ('"%s"' % kayit.get("ad", "")) in icerik)
    kontrol("script kaçışı yapıldı", 0, icerik.count('"</script>"'))
    kontrol("iki öğrenci var", True, "TEST ÖĞRENCİ" in icerik)
    kontrol("yönetici özeti gömülü", True, "yonetici-dugme" in icerik)
    kontrol("çakışma sekmesi gömülü", True, "cakisma-dugme" in icerik)
    kontrol("dersler sekmesi gömülü", True, "dersler-dugme" in icerik)
    kontrol("çakışma arama kutusu", True, "cakisma-arama" in icerik)
    kontrol("dersler arama kutusu", True, "dersler-arama" in icerik)
    kontrol("çözülmeli çakışma sekmesi gömülü", True,
            "cozulmeli-dugme" in icerik)
    kontrol("ders alanlar sekmesi gömülü", True, "secim-dugme" in icerik)
    kontrol("ders alanlar arama kutusu", True, "secim-arama" in icerik)
    _bolum_kimligi_kontrolu(icerik)
    # Katalog dönem dönem gruplanmış olmalı
    kat = json.loads(re.search(
        r'id="katalog" type="application/json">(.*?)</script>',
        icerik, re.S).group(1).replace('<\/', '</'))
    # Hangi dönemler görüneceği katalogdaki derse bağlı; gerçek veri
    # yoksa gömülü örnek daha dar. Sabit liste beklemek yerine güz
    # dönemi olduklarını ve boş olmadıklarını sınıyoruz.
    kontrol("katalog dönemlere ayrıldı", True,
            bool(kat) and all(int(d) in ym.GUZ_DONEMLERI for d in kat))
    tipler = sorted({c["tip"] for d in kat.values() for c in d})
    kontrol("ders tipleri ayrıştı", ["Seçmeli", "TOS", "Zorunlu"], tipler)
    # Program saatleri katalog dersine bağlanmış olmalı
    bagli = [c for d in kat.values() for c in d if c["program_adi"]]
    kontrol("çoğu ders programa bağlandı", True,
            len(bagli) >= sum(len(d) for d in kat.values()) - 2)

    # rapor.py'deki SAYFA ham (raw) bir metin DEĞİL; JS içine yazılan
    # \' dizisi Python tarafından ' olarak çözülüp string'i kapatıyor ve
    # tüm script sessizce çalışmıyor. Konsola da hata düşmüyor.
    # Türkçe kesme işareti ("AKTS'nin") bu tuzağa çok kolay düşürüyor.
    kontrol("JS içinde kapanmamış tırnak yok", [], _tirnak_hatalari(icerik))
    kontrol("kontenjan verisi gömülü", True, '"toplam_kontenjan"' in icerik)
    # Sıralama öğrenci numarasına göre olmalı
    i_ornek = icerik.index('"%s"' % kayit["no"])
    i_test = icerik.index('"240000099"')
    kontrol("öğrenciler numaraya göre sıralı", True, i_ornek < i_test)
    _her_sinif_calisiyor_mu()
    _kohort_acigi_kontrolu()
    _transkript_verisi_kontrolu()
    _yol_kontrolu()
    _exe_kapsami_kontrolu()
    _pano_tazeligi_kontrolu()
    _kompozisyon_girdisi_kontrolu()
    _paylasim_kapsami_kontrolu()
    _kisisel_veri_kontrolu()
    _cozulmeli_sekmesi()
    _tek_ogrenci_tazeleme()
    _ders_alanlar_kontrolu()
    _cakisma_devam_kontrolu()
    _sessiz_temiz_var_mi()

    # Tırnak denetimi statik; asıl kanıt sayfayı ÇALIŞTIRMAK. node varsa
    # her görünümü gerçekten çizdirip boş kalmadığını doğruluyoruz.
    _node_ile_ciz(yol)

    print("")
    print("  Pano: %s (%.1f KB)" % (yol, boyut / 1024.0))
    print("  %d/%d kontrol geçti." % (sum(OK), len(OK)))
    return 0 if all(OK) else 1


_GERCEK = None


def _gercek_ogrenciler():
    """cikti/ altındaki gerçek öğrencileri BİR KEZ çözer.

    İki ayrı bölüm aynı veriyi kullanıyor; her biri 60 sayfayı yeniden
    ayrıştırırsa test dakikalarca sürüyor. Sonucu burada tutuyoruz.
    Döndürdüğü: [(kayit, ozet), ...] ya da cikti/ boşsa [].
    """
    global _GERCEK
    if _GERCEK is not None:
        return _GERCEK

    import glob
    import re
    import ders_kayit as dk
    import ders_programi as dprog
    import mufredat as mfr

    cikti = os.path.join(os.path.dirname(BURASI), "cikti")
    sayfalar = sorted(glob.glob(os.path.join(cikti, "ders_sayfasi_*.html")))
    if not sayfalar:
        _GERCEK = []
        return _GERCEK

    program, muf = dprog.yukle(), mfr.yukle()
    toplam = []
    for p in sayfalar:
        no = re.search(r"ders_sayfasi_(\d+)\.html", p).group(1)
        k = dk.ders_kaydini_coz(io.open(p, encoding="utf-8").read())
        tp = os.path.join(cikti, "transkript_%s.html" % no)
        k["transkript"] = dk.transkripti_coz(
            io.open(tp, encoding="utf-8").read() if os.path.exists(tp) else "")
        toplam.append((k, ozet.ogrenci_ozeti(
            k, icinde_bulunulan_yil=2026, program=program, mufredat=muf)))

    # Transkripti okunamayan öğrenci için ogrenci_ozeti KISA bir sözlük
    # döner (yalnız uyarı + transkript_hatasi). Bu doğru davranış: veri
    # yoksa hesap uydurulmaz. Ama analiz testleri tam sözlük bekliyor;
    # burada bir kez süzüp bildiriyoruz. Ölçüldü: tarama yarıda kesilen
    # TEK bir öğrenci bütün testi KeyError ile düşürüyordu.
    okunamayan = [(k, o) for k, o in toplam if "donem_durumu" not in o]
    if okunamayan:
        print("  (%d öğrencinin transkripti okunamamış, analizden "
              "çıkarıldı: %s)"
              % (len(okunamayan),
                 ", ".join(str(o.get("no")) for _k, o in okunamayan[:4])))
        for _k, o in okunamayan:
            if not any(u["baslik"] == "Transkript okunamadı"
                       for u in (o.get("uyarilar") or [])):
                print("  [HATA] %s: okunamayan transkript UYARI ÜRETMİYOR"
                      % o.get("no"))
                OK.append(False)
    _GERCEK = [(k, o) for k, o in toplam if "donem_durumu" in o]
    return _GERCEK


def _exe_kapsami_kontrolu():
    """exe_yap.py GIZLI listesi, baslat.py'den ULAŞILAN her modülü içeriyor mu?

    Exe'de eksik bir modül, taramanın en sonunda - danışman 60 öğrenciyi
    beklemişken - ImportError ile çöker. PyInstaller fonksiyon içindeki
    import'ları bugün buluyor ama garanti değil; liste bu yüzden var ve
    elle tutulduğu için unutulmaya açık.
    """
    import ast
    import re

    print("")
    print("  === Exe kapsamı ===")
    kok = os.path.dirname(BURASI)
    yerel = {a[:-3] for a in os.listdir(kok) if a.endswith(".py")}

    gizli_ham = re.search(r"GIZLI = \[(.*?)\]",
                          io.open(os.path.join(kok, "exe_yap.py"),
                                  encoding="utf-8").read(), re.S).group(1)
    gizli = {x.strip().strip("\"'") for x in gizli_ham.split(",")}
    gizli = {x for x in gizli if x}

    # baslat.py'den geçişli olarak ulaşılan YEREL modüller
    ulasilan, sira = set(), ["baslat"]
    while sira:
        m = sira.pop()
        if m in ulasilan or m not in yerel:
            continue
        ulasilan.add(m)
        agac = ast.parse(io.open(os.path.join(kok, m + ".py"),
                                 encoding="utf-8").read())
        for d in ast.walk(agac):
            if isinstance(d, ast.Import):
                sira += [x.name.split(".")[0] for x in d.names]
            elif isinstance(d, ast.ImportFrom) and d.module:
                sira.append(d.module.split(".")[0])

    eksik = sorted((ulasilan - {"baslat"}) - gizli)
    kontrol("GIZLI listesi ulaşılan her modülü içeriyor", [], eksik)
    print("        (%d modül ulaşılıyor, %d tanesi listede)"
          % (len(ulasilan) - 1, len(gizli & yerel)))


def _yol_kontrolu():
    """Çıktı yolu HİÇBİR yerde __file__'dan türetilmemeli.

    Gerçek hata (2026-09): panoyu_yenile klasörünü __file__'dan
    türetiyordu. Exe'de __file__ PyInstaller'ın geçici açılma klasörünü
    gösterir, ham sayfalar ise exe'nin YANINA yazılır. Tek öğrenci
    tazelendiğinde ham sayfa doğru yere yazılıyor ama pano boş klasöre
    bakıp "ders sayfası yok" deyip çıkıyordu - danışman panonun
    güncellendiğini sanıyordu.

    Bu yüzden iki şey denetleniyor:
      - panoyu_yenile'nin klasörü yollar.cikti() ile AYNI,
      - exe'ye giren modüllerin hiçbirinde __file__'dan türetilmiş bir
        yol sabiti kalmamış (yollar.py hariç - ayrımı yapan tek yer o).
    """
    import re
    import panoyu_yenile
    import yollar

    print("")
    print("  === Dosya yolları (exe güvenliği) ===")
    kontrol("panoyu_yenile, yollar.cikti() kullanıyor",
            yollar.cikti(), panoyu_yenile.CIKTI)

    kok = os.path.dirname(BURASI)
    # exe'ye giren modüller (exe_yap.py GIZLI listesi + giriş noktası)
    moduller = ["baslat.py", "ders_kayit.py", "panoyu_yenile.py",
                "ozet.py", "rapor.py", "mufredat.py", "ders_programi.py",
                "akts_degisimi.py", "yonetmelik.py"]
    suclu = []
    for ad in moduller:
        yol = os.path.join(kok, ad)
        if not os.path.exists(yol):
            continue
        metin = io.open(yol, encoding="utf-8").read()
        # Yorum satırlarını ve dizgi içindeki anlatımı sayma; yalnız
        # gerçek bir atama arıyoruz.
        for satir in metin.splitlines():
            if satir.lstrip().startswith("#"):
                continue
            if re.search(r"=\s*Path\(__file__\)|"
                         r"=\s*os\.path\.dirname\(os\.path\.abspath"
                         r"\(__file__\)", satir):
                suclu.append("%s: %s" % (ad, satir.strip()))
    kontrol("__file__'dan türetilmiş yol sabiti yok", [], suclu)


def _bolum_kimligi_kontrolu(pano_html):
    """Pano hangi bölümün kurallarıyla üretildiğini yazıyor mu?

    Exe bölüme özgüdür: müfredat, ders programı ve bölüm profili içine
    gömülüdür. Matematik için derlenmiş bir exe Fizik danışmanının
    elinde her sayıyı yanlış hesaplar. Panonun kendi kimliğini
    taşımaması, o hatanın fark edilmemesi demek.
    """
    import bolum

    print("")
    print("  === Bölüm kimliği ===")
    kontrol("pano bölüm adını yazıyor", True,
            bolum.tanim() in pano_html)
    kontrol("yer tutucu değiştirilmiş", False, "__BOLUM__" in pano_html)

    import baslat
    imzalar = [i for _, i in baslat.PANO_SEKMELERI]
    kontrol("--tani bölüm adını da arıyor", True, "__BOLUM__" in imzalar)


def _kisisel_veri_kontrolu():
    """Kaynakta GERÇEK biçimli öğrenci numarası var mı?

    Depo herkese açık. Öğrenci numarasının ortasındaki dört hane
    bölüm kodudur; Matematik'inki gerçek numaralarda kullanıldığı için
    kişisel veridir. Örneklerde bölüm kodu 0000 kullanılıyor: biçim
    aynı kalıyor (kohort hesabı ilk iki haneden çıkar) ama hiçbir
    gerçek numarayla çakışamaz.

    NOT: Bu açıklamaya örnek olsun diye gerçek bir numara YAZILMAZ -
    bir kez yazıldı ve tam da bu kontrolü tetikledi.

    Bu kontrol bir kez temizlemek için değil, bir daha KİRLENMESİN
    diye var: örnek yazarken elin gerçek bir numaraya gitmesi çok kolay.
    """
    import re

    print("")
    print("  === Kişisel veri (kaynak) ===")
    kok = os.path.dirname(BURASI)
    atla = ("cikti", "__pycache__", "chrome-projili", "chrome-profili",
            "ornek")
    desen = re.compile(r"(?<!\d)\d{2}2709\d{3}(?!\d)")
    bulgu = []
    for dizin, altlar, dosyalar in os.walk(kok):
        altlar[:] = [a for a in altlar if a not in atla]
        for d in dosyalar:
            if not d.endswith((".py", ".md", ".js")):
                continue
            yol = os.path.join(dizin, d)
            try:
                icerik = io.open(yol, encoding="utf-8").read()
            except (OSError, UnicodeDecodeError):
                continue
            for m in desen.finditer(icerik):
                bulgu.append("%s: %s" % (os.path.relpath(yol, kok),
                                         m.group(0)))
    kontrol("kaynakta gerçek biçimli öğrenci numarası yok", [], bulgu)

    # Gercek transkript/pano fixture'lari depoya girmemeli
    izlenmemesi = ["testler/ornek_transkript.html",
                   "testler/ornek_pano.html"]
    gi = os.path.join(os.path.dirname(kok), ".gitignore")
    if os.path.exists(gi):
        metin = io.open(gi, encoding="utf-8").read()
        eksik = [d for d in izlenmemesi
                 if os.path.basename(d) not in metin]
        kontrol("gerçek fixture'lar .gitignore'da", [], eksik)

    # Ornek pano YAYIMLANIYOR - icinde gercek veri olmamali
    ornek = os.path.join(kok, "ornek", "danisman_ozeti.html")
    if os.path.exists(ornek):
        icerik = io.open(ornek, encoding="utf-8").read()
        kontrol("örnek panoda gerçek numara yok", [],
                sorted(set(desen.findall(icerik))))


def _paylasim_kapsami_kontrolu():
    """paylas.py her modülü ve her testi kopyalıyor mu?

    exe_yap.py için aynı koruma vardı, paylas.py için yoktu. Yeni bir
    modül yazılıp listeye eklenmezse karşı taraf EKSİK bir kopya alır;
    hata da ancak orada, ilk çalıştırmada ortaya çıkar.

    Kopyalanmayacak dosyalar açıkça listede durmalı — "unuttum" ile
    "bilerek bıraktım" ayırt edilebilsin diye.
    """
    print("")
    print("  === Paylaşım kapsamı ===")
    kok = os.path.dirname(BURASI)
    import paylas

    # Paylasilmamasi DOGRU olanlar: kendi baslarina calisan yardimci
    # betikler degil, gelistirme sirasinda uretilen seyler.
    beklenmeyen = set()

    moduller = {d for d in os.listdir(kok)
                if d.endswith(".py") and not d.startswith("_")}
    eksik = sorted(moduller - set(paylas.KOD) - beklenmeyen)
    kontrol("her modül paylaşım listesinde", [], eksik)

    testler = {"testler/" + d for d in os.listdir(os.path.join(kok, "testler"))
               if d.endswith(".py") or d.endswith(".js")}
    eksik_t = sorted(testler - set(paylas.TESTLER))
    kontrol("her test paylaşım listesinde", [], eksik_t)

    # Listede olup DISKTE olmayan dosya: kopyalama sessizce atlar
    hayalet = sorted(d for d in (paylas.KOD + paylas.TESTLER)
                     if not os.path.exists(os.path.join(kok, d)))
    kontrol("listede olmayan dosya yok", [], hayalet)

    # exe'ye giren veri dosyalari paylasima da girmeli
    import exe_yap
    veri_paylasilan = {d.split("/")[-1] for d in paylas.VERI}
    eksik_v = sorted(set(exe_yap.VERI) - veri_paylasilan)
    kontrol("exe'ye giren veri paylaşımda da var", [], eksik_v)

    # Ogrenci verisi tasiyan hicbir sey listede olmamali.
    # Desen ADLARI tek tek sayiyor: "ornek_" alt dizgisi kullanilinca
    # ornek_uret.py (uydurma veri URETEN script) de yakalaniyordu.
    yasak_adlar = ("cikti/", ".env", "chrome-profili",
                   "testler/ornek_pano.html",
                   "testler/ornek_transkript.html",
                   "ornek/danisman_ozeti.html")
    tehlikeli = [d for d in (paylas.KOD + paylas.VERI + paylas.TESTLER)
                 if any(y in d for y in yasak_adlar)]
    kontrol("öğrenci verisi paylaşıma girmiyor", [], tehlikeli)


def _kompozisyon_girdisi_kontrolu():
    """Kompozisyon denetimine KALINAN ders "geçilmiş" diye gitmemeli.

    transkript["son_durum"] DENENMİŞ tüm dersleri tutar, kalınanlar
    dâhil. Bir dönem ozet.py o kümeyi "geçilen kodlar" diye veriyordu;
    hedef dönemin zorunlusundan kalan öğrenci için (a) "ZORUNLU DERS
    SEÇİLMEMİŞ" uyarısı hiç çıkmıyor, (b) zorunlunun AKTS'si kotadan
    düştüğü için fazladan seçmeli yazdırılıyordu.

    Bugünkü veride bu durumdaki öğrenci yok, yani davranış testi boşa
    geçerdi. Bunun yerine KAYNAĞI denetliyoruz: ozet.py kümeyi
    "gecilen"den kurmalı, "son_durum"dan değil. Mutasyon denemesinde
    bu kusuru hiçbir test yakalamamıştı.
    """
    import re

    print("")
    print("  === Kompozisyon girdisi ===")
    kaynak = io.open(os.path.join(os.path.dirname(BURASI), "ozet.py"),
                     encoding="utf-8").read()
    m = re.search(r"gecilen_kodlar\s*=\s*(.+?)\n\s*komp\s*=",
                  kaynak, re.S)
    atama = (m.group(1) if m else "")
    kontrol("gecilen_kodlar 'gecilen'den kuruluyor", True,
            'get("gecilen")' in atama)
    kontrol("gecilen_kodlar 'son_durum'dan KURULMUYOR", False,
            "son_durum" in atama)

    # Ayrıca: fonksiyonun sözleşmesi - verilen kod zorunlu eksikten düşer
    import mufredat as mfr
    import yonetmelik as ym
    muf = mfr.yukle()
    if muf:
        yapi = ym.donem_yapisi(7, muf, 2023) or {}
        kod = (yapi.get("zorunlu_kodlar") or (None,))[0]
        if kod:
            kat = [{"ders_no": kod, "ders_adi": "X", "akts": 4}]
            bos = ym.donem_kompozisyonu_denetle(7, [], kat, set(), None,
                                                mufredat=muf,
                                                giris_yili=2023)
            dolu = ym.donem_kompozisyonu_denetle(7, [], kat, {kod}, None,
                                                 mufredat=muf,
                                                 giris_yili=2023)
            kontrol("geçilmemiş zorunlu eksikte görünüyor", True,
                    any(z["ders_no"] == kod
                        for z in bos["zorunlu_eksik"]))
            kontrol("geçilmiş zorunlu eksikten düşüyor", False,
                    any(z["ders_no"] == kod
                        for z in dolu["zorunlu_eksik"]))


def _pano_tazeligi_kontrolu():
    """Eski pano "hazır" diye sunulmamalı.

    Dosyanın var olması bir şey söylemiyor: önceki taramadan kalan pano
    da oradadır. Tarama ham sayfayı yenileyip panoyu yenileyemezse
    danışman değişikliğini göremez ama ekranda başarı mesajı görürdü.
    """
    import time
    import tempfile
    import shutil
    from pathlib import Path
    import baslat
    import yollar

    print("")
    print("  === Pano tazeliği ===")
    gecici = Path(tempfile.mkdtemp(prefix="dkk_taze_"))
    eski_kok = yollar.yazilan_kok
    try:
        yollar.yazilan_kok = lambda: gecici
        klasor = yollar.cikti()
        klasor.mkdir(parents=True, exist_ok=True)
        pano = klasor / "danisman_ozeti.html"

        kontrol("pano yoksa 'yok'", "yok", baslat.pano_tazeligi(pano)[0])

        pano.write_text("x", encoding="utf-8")
        kontrol("ham sayfa yoksa 'taze'", "taze",
                baslat.pano_tazeligi(pano)[0])

        ham = klasor / "ders_sayfasi_1.html"
        ham.write_text("x", encoding="utf-8")
        time.sleep(0.05)
        kontrol("pano ham sayfayla aynı anda ise 'taze'", "taze",
                baslat.pano_tazeligi(pano)[0])

        # Ham sayfa panodan 10 sn DAHA YENİ: gerçek hatanın imzası.
        simdi = time.time()
        os.utime(str(pano), (simdi - 10, simdi - 10))
        os.utime(str(ham), (simdi, simdi))
        kontrol("ham sayfa panodan yeniyse 'eski'", "eski",
                baslat.pano_tazeligi(pano)[0])
    finally:
        yollar.yazilan_kok = eski_kok
        shutil.rmtree(str(gecici), ignore_errors=True)


def _transkript_verisi_kontrolu():
    """Transkript sekmesine giden veri EKSİKSİZ mi?

    Sekmenin tek işi transkripti olduğu gibi göstermek. Sessizce düşen
    tek bir satır bile danışmanı yanıltır: "bu ders hiç alınmamış"
    sanır. Bu yüzden üç değişmez denetleniyor:

      - transkriptteki her deneme panoya giriyor,
      - dönem dönem geçilen AKTS toplamı, öğrencinin geçilen_akts'ine
        eşit (bağımsız bir çapraz denetim),
      - her öğrencinin transkript verisi üretilmiş.
    """
    import rapor

    print("")
    print("  === Transkript verisi ===")
    gercek = _gercek_ogrenciler()
    if not gercek:
        print("  (cikti/ boş, atlandı)")
        return

    kayip, tutmaz, uretilmeyen = [], [], []
    toplam = 0
    for kayit, o in gercek:
        t = kayit.get("transkript") or {}
        v = rapor._transkript_verisi(t)
        if v is None:
            uretilmeyen.append(o.get("no"))
            continue
        panoda = sum(len(g["dersler"]) for g in v["donemler"])
        toplam += panoda
        ham = len(t.get("denemeler") or [])
        if panoda != ham:
            kayip.append((o.get("no"), ham, panoda))
        akts = sum(g["gecilen_akts"] for g in v["donemler"])
        if akts != (t.get("gecilen_akts") or 0):
            tutmaz.append((o.get("no"), akts, t.get("gecilen_akts")))

    kontrol("her öğrencinin transkripti üretildi", [], uretilmeyen)
    kontrol("hiçbir deneme düşmüyor", [], kayip)
    kontrol("dönem AKTS toplamı geçilen_akts ile tutuyor", [], tutmaz)
    print("        (%d öğrenci, %d transkript kaydı)" % (len(gercek), toplam))


def _kohort_acigi_kontrolu():
    """Kohort açığı hesabı KENDİ BAŞINA kayıp uyduruyor mu?

    En kritik denetim bu: hesap, kohort kuralı KAPALIYKEN (giris_yili
    verilmeden) hiçbir öğrencide açık üretmemeli. Üretirse, gördüğümüz
    açık müfredat farkından değil hesabın kendi hatasından geliyordur -
    ve danışmana 60 öğrenci için yanlış "fazladan ders al" derdik.

    Kural açıkken de iki şey doğrulanıyor:
      - açığın sebebi her zaman adıyla gösteriliyor (kohort dışı ders ya
        da düşük AKTS ile geçilmiş ders), sebepsiz açık olmamalı,
      - projeksiyon tam olarak (plan toplamı - kalıcı açık) olmalı.
    """
    import yonetmelik as ym

    print("")
    print("  === Kohort açığı (müfredat kompozisyonu) ===")
    gercek = _gercek_ogrenciler()
    if not gercek:
        print("  (cikti/ boş, atlandı)")
        return

    import mufredat as mfr
    muf = mfr.yukle()
    uydurma, sebepsiz, tutmayan = [], [], []
    acigi_olan = 0
    for kayit, o in gercek:
        bolum = [d for d in (kayit.get("katalog") or [])
                 if d.get("sekme") == "Bölüm Dersleri"]
        gec = (kayit.get("transkript") or {}).get("gecilen") or []
        sk = {d.get("ders_no") for d in (kayit.get("secili_dersler") or [])}

        # (1) kohort kuralı KAPALI -> açık olmamalı
        kapali = ym.kohort_acigi(gec, sk, muf, None, None, bolum)
        if kapali["toplam"]:
            uydurma.append((o.get("no"), kapali["toplam"]))

        # (2) kural açıkken her kalemin adlandırılmış bir sebebi olmalı
        a = o.get("kohort_acigi") or {}
        if a.get("toplam"):
            acigi_olan += 1
        for k in (a.get("kalemler") or []):
            if not k["kohort_disi"] and not k["dusuk_gecilen"]:
                sebepsiz.append((o.get("no"), k["yariyil"], k["kalici"]))

        # (3) projeksiyon = plan toplamı - NET açık
        #     (net = kalıcı açık eksi kotanın üstünde alınan AKTS)
        pr = (o.get("projeksiyon") or {}).get("projeksiyon")
        if a and pr != ym.plan_toplami() - a["net"]:
            tutmayan.append((o.get("no"), pr, a["net"]))

    kontrol("kural kapalıyken hiç açık uydurulmuyor", [], uydurma)
    kontrol("her açık kaleminin adlandırılmış sebebi var", [], sebepsiz)
    kontrol("projeksiyon = plan - net açık", [], tutmayan)
    print("        (%d öğrencinin %d'inde kohort açığı var)"
          % (len(gercek), acigi_olan))


def _her_sinif_calisiyor_mu():
    """Kontroller yalnızca 4. sınıfta değil, HER hedef dönemde çalışmalı.

    Sistem 7. dönem için yazılmıştı; 3. sınıf danışmanı (hedef 5. dönem)
    çalıştırdığında kompozisyon denetimi hiç işlemiyordu - ZORUNLU DERS
    SEÇİLMEMİŞ dahil. Bu test veride hangi hedef dönemler varsa hepsinde
    denetimlerin çalıştığını doğrular.
    """
    import collections

    print("")
    print("  === Her sınıfta çalışıyor mu? ===")
    gercek = _gercek_ogrenciler()
    if not gercek:
        print("  (cikti/ boş, atlandı)")
        return
    # Transkripti okunamayan öğrenci için ogrenci_ozeti KISA bir sözlük
    # döner (yalnız uyarı + transkript_hatasi). Bu doğru davranış: veri
    # yoksa hesap uydurulmaz. Test bunu ATLAMALI, çökmemeli - ölçüldü,
    # tarama yarıda kesilen tek bir öğrenci bütün testi KeyError ile
    # düşürüyordu.
    grup = collections.defaultdict(list)
    for _, o in gercek:
        grup[o["donem_durumu"]["hedef_donem"]].append(o)

    yapisiz, projeksiyonsuz, ihtiyacsiz = [], [], []
    for d, lst in sorted(grup.items()):
        for o in lst:
            if (o.get("kompozisyon") or {}).get("yapi_bilinmiyor"):
                yapisiz.append((d, o.get("no")))
            if (o.get("projeksiyon") or {}).get("projeksiyon") is None:
                projeksiyonsuz.append((d, o.get("no")))
            if (o.get("donem_ihtiyaci") or {}).get("donem") != d:
                ihtiyacsiz.append((d, o.get("no")))
    kontrol("her hedef dönemde kompozisyon çalışıyor", [], yapisiz)
    kontrol("her hedef dönemde projeksiyon var", [], projeksiyonsuz)
    kontrol("her hedef dönemde dönem ihtiyacı hesaplanıyor", [], ihtiyacsiz)

    # Kontenjan planı sabit bir döneme bağlı olmamalı
    kp = ozet.kontenjan_planlari([o for lst in grup.values() for o in lst])
    kontrol("kontenjan planı tüm hedef dönemleri kapsıyor", True,
            set(kp["donemler"]) <= set(grup)
            and all(p["ogrenci_sayisi"] or p["toplam_kontenjan"]
                    for p in kp["planlar"]))
    print("        (hedef dönemler: %s | kontenjan planı: %s)"
          % (sorted(grup), kp["donemler"]))


def _cozulmeli_sekmesi():
    """"Kesin düzeltilmesi gereken çakışma" sekmesinin verisi.

    Sekme yalnız cozulmeli=true olanları göstermeli. Devamsızlık
    hakkına sığan ya da devam zorunluluğu olmayan çakışmalar oraya
    girerse danışman gereksiz yere ders değiştirtir.
    """
    print("")
    print("  === Çözülmeli çakışma sekmesi ===")
    gercek = _gercek_ogrenciler()
    if not gercek:
        print("  (cikti/ boş, atlandı)")
        return

    zorunlu, hak_ici, serbest = [], 0, 0
    for _, o in gercek:
        kendi = [c for c in (o.get("cakismalar") or []) if c.get("cozulmeli")]
        if kendi:
            zorunlu.append((o["no"], kendi))
        for c in (o.get("cakismalar") or []):
            if c.get("cozulmeli"):
                continue
            if c.get("hak_ici"):
                hak_ici += 1
            else:
                serbest += 1

    kontrol("üç sınıf birbirini dışlıyor", [],
            [(o["no"], c["a_ad"]) for _, o in gercek
             for c in (o.get("cakismalar") or [])
             if c.get("cozulmeli") and c.get("hak_ici")])
    # Zorunlu sayılan her çakışmanın İKİ tarafında da devam şartı olmalı.
    gevsek = [(no, c["a_ad"], c["b_ad"]) for no, liste in zorunlu
              for c in liste if not (c.get("a_devam") and c.get("b_devam"))]
    kontrol("zorunlu çakışmanın iki tarafı da devam gerektiriyor", [],
            gevsek)
    # Her zorunlu çakışma ya öneri ya "zorunlu ders" notu taşımalı;
    # yoksa danışmana "değiştir" deyip çare göstermemiş oluruz.
    caresiz = [(no, c["a_ad"], c["b_ad"]) for no, liste in zorunlu
               for c in liste
               if not c.get("oneriler") and not c.get("a_oneriler")
               and not c.get("a_zorunlu_ders")
               and not c.get("b_zorunlu_ders")]
    kontrol("her zorunlu çakışmada öneri ya da 'zorunlu' notu var", [],
            caresiz)
    print("        (%d öğrenci / %d zorunlu çakışma; ayrıca %d hak içi, "
          "%d devam şartsız)"
          % (len(zorunlu), sum(len(x) for _, x in zorunlu), hak_ici,
             serbest))


def _tek_ogrenci_tazeleme():
    """Bir öğrenciyi tek başına tazeleyebiliyor muyuz?

    Danışman bir kaydı elle düzeltip son durumu görmek istediğinde 60
    kişiyi yeniden taramak zorunda kalmamalı. Mekanizma: o öğrencinin
    ham sayfası yenilenir, pano DİSKTEKİ bütün öğrencilerden yeniden
    kurulur. Burada seçicinin ve tazelik damgasının doğruluğunu
    sınıyoruz; OBİS'e bağlanmıyoruz.
    """
    import ders_kayit as dk

    print("")
    print("  === Tek öğrenci tazeleme ===")

    liste = [
        {"no": "230000003", "ad": "AYŞE YILMAZ", "baglanti": "x"},
        {"no": "230000004", "ad": "AYŞE DEMİR", "baglanti": "x"},
        {"no": "240000006", "ad": "İSMAİL KAYA", "baglanti": "x"},
        {"no": "240000007", "ad": "KAYIT YAPMAMIŞ", "baglanti": None},
    ]
    kontrol("tam numara seçiyor", "230000003",
            (dk.ogrenci_sec(liste, "230000003")[0] or {}).get("no"))
    # Parça yalnız BİR numarada geçmeli; aksi hâlde "belirsiz" sayılır.
    kontrol("numara parçası seçiyor", "230000004",
            (dk.ogrenci_sec(liste, "0004")[0] or {}).get("no"))
    kontrol("ad ile seçiyor", "240000006",
            (dk.ogrenci_sec(liste, "ismail")[0] or {}).get("no"))
    # Türkçe: "İSMAİL", "Ismail", "ismail" aynı sonucu vermeli
    kontrol("Türkçe büyük/küçük harf takılmıyor", True,
            len({(dk.ogrenci_sec(liste, y_)[0] or {}).get("no")
                 for y_ in ("İSMAİL", "Ismail", "ismail", "İsmail")}) == 1)
    secilen, mesaj = dk.ogrenci_sec(liste, "ayşe")
    kontrol("belirsiz arama seçmiyor", None, secilen)
    kontrol("belirsizlikte adaylar yazılıyor", True,
            "230000003" in mesaj and "230000004" in mesaj)
    secilen, mesaj = dk.ogrenci_sec(liste, "boyle biri yok")
    kontrol("bulunamayınca açıklıyor", True,
            secilen is None and "bulunamadı" in mesaj)
    kontrol("boş arama seçmiyor", None, dk.ogrenci_sec(liste, "")[0])

    # --ogrenci bayrağı iki yazımda da okunmalı
    import sys as _sys
    eski_argv = list(_sys.argv)
    try:
        _sys.argv = ["x", "--ogrenci", "230000003"]
        kontrol("--ogrenci <deger>", "230000003",
                dk._bayrak_degeri("--ogrenci"))
        _sys.argv = ["x", "--ogrenci=230000003"]
        kontrol("--ogrenci=<deger>", "230000003",
                dk._bayrak_degeri("--ogrenci"))
        _sys.argv = ["x", "--tumu"]
        kontrol("bayrak yoksa None", None, dk._bayrak_degeri("--ogrenci"))
    finally:
        _sys.argv = eski_argv

    # Tazelik damgası. DİKKAT: damgayı ÜRÜNÜN ürettiği panodan okuyoruz,
    # testin kendi kurduğu kayıttan değil - yoksa yalnız testin doğru
    # olduğunu doğrulamış oluruz. (İlk hâlinde damga sadece
    # panoyu_yenile yolunda vardı, canlı taramada yoktu; bu kontrol
    # onu yakaladı.)
    import datetime
    import glob as _glob
    cikti = os.path.join(os.path.dirname(BURASI), "cikti")
    pano = os.path.join(cikti, "danisman_ozeti.html")
    if not os.path.exists(pano):
        print("  (cikti/danisman_ozeti.html yok, tazelik damgası atlandı)")
        return
    icerik = io.open(pano, encoding="utf-8").read()
    gomulu = json.loads(re.search(
        r'<script id="veri" type="application/json">(.*?)</script>',
        icerik, re.S).group(1).replace('<\\/', '</'))

    damgalar = {}
    for p in sorted(_glob.glob(os.path.join(cikti, "ders_sayfasi_*.html"))):
        no = re.search(r"ders_sayfasi_(\d+)\.html", p).group(1)
        damgalar[no] = datetime.datetime.fromtimestamp(
            os.path.getmtime(p)).strftime("%d.%m.%Y %H:%M")

    eksik = [o["no"] for o in gomulu if not o.get("son_tarama")]
    kontrol("panodaki her öğrencide son_tarama var", [], eksik)
    yanlis = [(o["no"], o["son_tarama"], damgalar.get(o["no"]))
              for o in gomulu
              if o["no"] in damgalar
              and o["son_tarama"] != damgalar[o["no"]]]
    kontrol("son_tarama ham sayfanın zamanıyla aynı", [], yanlis)
    print("        (%d öğrenci, %d farklı okuma zamanı)"
          % (len(gomulu), len({o.get("son_tarama") for o in gomulu})))


def _ders_alanlar_kontrolu():
    """"Hangi dersi kim aldı" sekmesi: ders -> öğrenci çevrimi.

    Çevrimin kendisi panonun JavaScript'inde; burada ÇEVRİLECEK VERİNİN
    doğru olduğunu sınıyoruz. Panonun gerçekten çizdiğini node tarafı
    (pano_calistir.js) doğruluyor.
    """
    import collections

    print("")
    print("  === Ders Alanlar (hangi dersi kim aldı) ===")
    gercek = _gercek_ogrenciler()
    if not gercek:
        print("  (cikti/ boş, atlandı)")
        return
    kayitlar = [k for k, _ in gercek]
    veriler = [rapor._ogrenci_verisi(k, o) for k, o in gercek]

    # Panoya giden secilen_dersler, OBİS sayfasındaki seçimle birebir
    # olmalı; sekme bunun üzerine kuruluyor.
    kayip = [(k.get("no"), len(k.get("secili_dersler") or []),
              len(v["secilen_dersler"]))
             for k, v in zip(kayitlar, veriler)
             if len(k.get("secili_dersler") or []) != len(v["secilen_dersler"])]
    kontrol("her seçim panoya taşındı", [], kayip)

    ders_ogrenci = collections.defaultdict(set)
    for v in veriler:
        for c in v["secilen_dersler"]:
            ders_ogrenci[c["ders_no"]].add(v["no"])
    kontrol("en az bir ders seçilmiş", True, bool(ders_ogrenci))

    toplam_secim = sum(len(v["secilen_dersler"]) for v in veriler)
    kontrol("ders→öğrenci çevrimi seçim sayısını korur", toplam_secim,
            sum(len(x) for x in ders_ogrenci.values()))

    # Aynı öğrenci aynı dersi iki kez seçmiş görünmemeli.
    cift = [(v["no"], c["ders_no"]) for v in veriler
            for c, sayi in collections.Counter(
                x["ders_no"] for x in v["secilen_dersler"]).items()
            if sayi > 1 for c in [{"ders_no": c}]]
    kontrol("aynı ders bir öğrencide tekrarlanmıyor", [], cift)

    # Ders kodu boş olan seçim sekmede anahtarsız kalır.
    kodsuz = [(v["no"], c["ders_adi"]) for v in veriler
              for c in v["secilen_dersler"] if not c.get("ders_no")]
    kontrol("her seçimin ders kodu var", [], kodsuz)

    # "Alması gerekirken seçmemiş" satırı alttan verisinden geliyor.
    eksik = sum(1 for v in veriler for a in v["alttan"]
                if (a.get("durum") or "").startswith("SEÇİLMEMİŞ"))
    print("        (%d ders, %d seçim, %d alması gerekip almayan)"
          % (len(ders_ogrenci), toplam_secim, eksik))


def _cakisma_devam_kontrolu():
    """Çakışma sınıflandırması ve öneri motoru değişmezleri.

    Danışman kuralı: öğrenci dersi daha önce aldıysa (kodu farklı olsa
    bile) ve F HARİCİ bir notla kaldıysa devam zorunluluğu yoktur; böyle
    bir çakışma bildirilir ama değiştirilmesi zorunlu değildir.
    """
    import glob
    import re
    import ders_kayit as dk
    import ders_programi as dprog
    import mufredat as mfr
    import yonetmelik as ymod

    print("")
    print("  === Çakışma / devam muafiyeti / öneriler ===")

    # Devam kuralı: F ve DZ dışındaki her harf devam sağlamış sayılır
    kontrol("FF devam sağlamış sayılır", True, ymod.devam_saglanmis_mi("FF"))
    kontrol("DC devam sağlamış sayılır", True, ymod.devam_saglanmis_mi("DC"))
    kontrol("F devam sağlamamış", False, ymod.devam_saglanmis_mi("F"))
    kontrol("DZ devam sağlamamış", False, ymod.devam_saglanmis_mi("DZ"))

    cikti = os.path.join(os.path.dirname(BURASI), "cikti")
    sayfalar = sorted(glob.glob(os.path.join(cikti, "ders_sayfasi_*.html")))
    if not sayfalar:
        print("  (cikti/ boş, gerçek veri kontrolleri atlandı)")
        return
    program, muf = dprog.yukle(), mfr.yukle()
    if not program:
        print("  (ders programı yok, atlandı)")
        return

    tutarsiz, cozmeyen, yanlis_tur, onerisiz = [], [], [], []
    zorunlu_top = serbest_top = hak_top = 0
    for p in sayfalar:
        no = re.search(r"ders_sayfasi_(\d+)\.html", p).group(1)
        k = dk.ders_kaydini_coz(io.open(p, encoding="utf-8").read())
        tp = os.path.join(cikti, "transkript_%s.html" % no)
        k["transkript"] = dk.transkripti_coz(
            io.open(tp, encoding="utf-8").read() if os.path.exists(tp) else "")
        o = ozet.ogrenci_ozeti(k, icinde_bulunulan_yil=2026,
                               program=program, mufredat=muf)
        kat = {d["ders_no"]: d for d in (k.get("katalog") or [])}
        for c in o.get("cakismalar") or []:
            # 1) cozulmeli <=> iki tarafta devam zorunlu VE cakisma
            #    devamsizlik hakkina sigmiyor (MADDE 10/1)
            beklenen = (c["a_devam"] and c["b_devam"]
                        and not c.get("hak_ici"))
            if c["cozulmeli"] != beklenen:
                tutarsiz.append((no, c["a_ad"], c["b_ad"]))
            # hak_ici yalnizca iki taraf da devam zorunluyken olusur
            if c.get("hak_ici") and not (c["a_devam"] and c["b_devam"]):
                tutarsiz.append((no, "hak_ici ama devam serbest", c["a_ad"]))
            # hak_ici ise devamsizlik hesabi da bulunmali ve sigmali
            if c.get("hak_ici") and not (c.get("devamsizlik") or {}).get("sigar"):
                tutarsiz.append((no, "hak_ici ama sigmiyor", c["a_ad"]))
            if c["cozulmeli"]:
                zorunlu_top += 1
            elif c.get("hak_ici"):
                hak_top += 1
            else:
                serbest_top += 1
                continue
            tum = (c["oneriler"] or []) + (c.get("a_oneriler") or [])
            # 2) hicbir oneri, korunacak dersle cakismamali
            for x in c["oneriler"]:
                if c["a_ad"] in (x["catisma"] or []):
                    cozmeyen.append((no, c["a_ad"], x["ders_adi"]))
            for x in (c.get("a_oneriler") or []):
                if c["b_ad"] in (x["catisma"] or []):
                    cozmeyen.append((no, c["b_ad"], x["ders_adi"]))
            # 3) oneriler ayni turden ve secilebilir olmali
            for x in tum:
                d = kat.get(x["ders_no"])
                if not d or d.get("secili") or d.get("doldu") \
                        or not d.get("eklenebilir"):
                    yanlis_tur.append((no, x["ders_adi"]))
            # 4) iki taraf da zorunlu ders degilse oneri cikmali
            if not tum and not (c["a_zorunlu_ders"] and c["b_zorunlu_ders"]):
                onerisiz.append((no, c["a_ad"], c["b_ad"]))

    kontrol("cozulmeli = iki tarafta da devam zorunlu", [], tutarsiz)
    kontrol("öneri korunacak dersle çakışmıyor", [], cozmeyen)
    kontrol("öneriler seçilebilir durumda", [], yanlis_tur)
    kontrol("seçmeli çakışmada öneri üretiliyor", [], onerisiz)
    print("        (%d öğrenci: %d değiştirilmeli, %d hakka sığıyor, %d devam yok)"
          % (len(sayfalar), zorunlu_top, hak_top, serbest_top))


def _sessiz_temiz_var_mi():
    """Dönem kotası dolmamışken "temiz" görünen öğrenci olmamalı.

    Bu sınıf hata iki kez çıktı: bir öğrenci 7. dönemde 16/32 AKTS,
    bir başkası 5. dönemde 24/30 seçmişti - ikisi de panoda temiz
    görünüyordu. Sessiz kalan bir eksik, yanlış uyarıdan daha
    tehlikeli: danışman bakmadan geçiyor.

    Vakalar ADSIZ anlatılıyor. Burada iki gerçek öğrencinin adı
    yazılıydı ve dosya yayımlandı; 60 kişilik bir bölümde ad + dönem +
    kesin AKTS o kişiyi doğrudan tanınır kılar. Öğrenci numarası
    arayan denetimler bunu göremez - ad deseni yoktur. Yeni bir vaka
    eklerken adı DEĞİL, yalnız sayıyı yazın.

    Sabit sayı beklemiyoruz (öğrenciler kayıt boyunca ders ekliyor);
    değişmezi sınıyoruz: kotası açık VE dolduracak ders varsa, en az bir
    "yapılacak" uyarısı olmalı.
    """
    import glob
    import re
    import ders_kayit as dk
    import ders_programi as dprog
    import mufredat as mfr
    import yonetmelik as ymod

    print("")
    print("  === Sessiz temiz öğrenci var mı? ===")
    cikti = os.path.join(os.path.dirname(BURASI), "cikti")
    sayfalar = sorted(glob.glob(os.path.join(cikti, "ders_sayfasi_*.html")))
    if not sayfalar:
        print("  (cikti/ boş, atlandı)")
        return
    # Ortak yükleyiciyi kullanıyoruz: aynı 60 sayfayı ikinci kez
    # ayrıştırmak testi dakikalarca uzatıyordu, üstelik transkripti
    # okunamayan öğrenci burada da KeyError'a yol açıyordu.
    sessiz = []
    for k, o in _gercek_ogrenciler():
        if o["sayim"].get(ozet.YAPILACAK):
            continue
        komp = o.get("kompozisyon") or {}
        if (komp.get("eksik_akts") or 0) <= 0:
            continue
        hedef = komp.get("donem") or 0
        # AKTS sınırı dolmuşsa "boşluk" fiilen doldurulamaz; sistem de
        # haklı olarak uyarmıyor. Aday, KALAN kapasiteye sığmalı.
        limit = o.get("akts_limiti")
        kalan = (None if limit is None
                 else max(0, limit - (komp.get("secilen_akts") or 0)))
        alinabilir = [d for d in (k.get("katalog") or [])
                      if d.get("sekme") == ozet.BOLUM_SEKMESI
                      and not d.get("secili") and d.get("eklenebilir")
                      and not d.get("doldu")
                      and (ymod.donem_numarasi(d.get("donem")) or 99) <= hedef
                      and (kalan is None or (d.get("akts") or 0) <= kalan)]
        if alinabilir:
            sessiz.append((no, k.get("ad"), hedef, komp.get("secilen_akts"),
                           komp.get("toplam_akts"), len(alinabilir)))
    kontrol("kotası açıkken uyarısız kalan öğrenci yok", [], sessiz)
    print("        (%d öğrenci tarandı)" % len(sayfalar))


def _node_ile_ciz(pano_yolu):
    """pano_calistir.js ile sayfanın JavaScript'ini gerçekten çalıştırır."""
    import shutil
    import subprocess

    print("")
    print("  === Sayfa node ile çizdiriliyor ===")
    if shutil.which("node") is None:
        print("  (node yok, atlandı - tarayıcıda elle bakın)")
        return
    betik = os.path.join(BURASI, "pano_calistir.js")
    if not os.path.exists(betik):
        print("  (pano_calistir.js yok, atlandı)")
        return
    try:
        sonuc = subprocess.run(["node", betik, str(pano_yolu)],
                               capture_output=True, text=True, timeout=120,
                               encoding="utf-8", errors="replace")
    except Exception as hata:                          # noqa: BLE001
        print("  (node çalıştırılamadı: %s)" % str(hata)[:70])
        return
    for satir in (sonuc.stdout or "").splitlines():
        if satir.strip():
            print("  " + satir.strip())
    if sonuc.returncode != 0:
        for satir in (sonuc.stderr or "").splitlines()[:6]:
            print("      " + satir)
    OK.append(sonuc.returncode == 0)


if __name__ == "__main__":
    sys.exit(main())
