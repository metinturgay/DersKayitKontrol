# -*- coding: utf-8 -*-
"""Yayınlanabilir ÖRNEK pano üretir — tamamen uydurma öğrencilerle.

Neden gerekiyor
---------------
README'de ve ekran görüntülerinde panoyu göstermek istiyoruz. Gerçek
panoda altmış öğrencinin adı, numarası, GANO'su ve bütün notları var;
bir tanesi bile dışarı çıkamaz.

Bu script paneli SIFIRDAN uydurma verilerle kurar:

  * adlar   — aşağıdaki sabit uydurma listeden
  * numara  — bölüm kodu 0000, yani hiçbir gerçek numarayla çakışmaz
  * notlar  — burada elle yazılmış, hiçbir transkriptten alınmamış

`cikti/` klasörüne HİÇ BAKMAZ; oradan tek bayt okumaz. Çıktı
`ornek/danisman_ozeti.html` dosyasıdır ve depoya girer.

Ders adları ve kodları bölümün kendi "Okutulacak Dersler" belgesinden
gelir — bunlar kişisel veri değil, bölümün yayımladığı bilgidir.

    python ornek_uret.py
"""
import os
import sys
from pathlib import Path

BURASI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BURASI)
sys.path.insert(0, os.path.join(BURASI, "testler"))

import ders_kayit as dk                                   # noqa: E402
import ders_programi                                      # noqa: E402
import mufredat                                           # noqa: E402
import ozet                                               # noqa: E402
import rapor                                              # noqa: E402
import eslestirme as es                                    # noqa: E402
import sentetik_transkript as st                          # noqa: E402
import yonetmelik as ym                                   # noqa: E402

CIKTI = Path(BURASI) / "ornek" / "danisman_ozeti.html"

# Uydurma adlar. Gerçek bir öğrenciye benzemesin diye sıfat + meslek
# yapısı seçildi; Türkçe karakterleri göstermek için ç/ğ/ı/ö/ş/ü var.
ADLAR = [
    "AYŞE DEMİRTAŞ", "BURAK ÇELİKKOL", "CEREN ÖZGÜVEN",
    "DENİZ ŞAHİNKAYA", "EMRE GÜNDOĞDU", "FATMA IŞIKLAR",
    "GÖKHAN YILDIRIM", "HİLAL KARAOĞLU",
]

# Numara: YY + 0000 + sıra. Bölüm kodu 0000 olduğu için hiçbir gerçek
# Selçuk numarasıyla çakışmaz; ilk iki hane giriş yılını verdiği için
# kohort kuralları yine işler.
def _no(giris_yili, sira):
    return "%02d0000%03d" % (giris_yili % 100, sira)


# Her öğrenci bir DURUMU temsil ediyor; pano bütün görünümleri
# göstersin diye özellikle çeşitlendirildi.
#
# "eksik" alanı, hedef yarıyılın tam kompozisyonundan NE ÇIKARILACAĞINI
# söyler. Seçimler ELLE YAZILMIYOR: müfredat belgesindeki yarıyıl
# yapısından türetiliyor (bkz. _secim). Elle yazılan kodlar belgeyle
# tutmadığı için herkese "dönem planına girmeyen ders" uyarısı
# çıkıyordu - demoda gerçek bir kusur gibi görünüyordu.
VAKALAR = [
    {"giris": 2023, "yariyillar": (1, 2, 3, 4, 5, 6), "notlar": {},
     "eksik": (), "aciklama": "planına uygun; yalnız çakışması var"},

    {"giris": 2023, "yariyillar": (1, 2, 3, 4, 5, 6),
     "notlar": {"2709303": "FF", "2709304": "FF", "2709403": "FF"},
     "eksik": ("secmeli",),
     "aciklama": "alttan dersleri + eksik seçmeli + çakışma"},

    {"giris": 2023, "yariyillar": (1, 2, 3, 4, 5, 6),
     "notlar": {"2709501": "DC", "2709502": "DC", "2709151": "DC"},
     "eksik": (), "aciklama": "şartlı geçer (DC) dersleri var"},

    {"giris": 2023, "yariyillar": (1, 2, 3, 4),
     "notlar": {"2709401": "FF"},
     "eksik": (), "aciklama": "alttan dersi var ama hepsini seçmiş"},

    {"giris": 2024, "yariyillar": (1, 2, 3, 4), "notlar": {},
     "eksik": (), "aciklama": "2024 girişli, temiz"},

    {"giris": 2024, "yariyillar": (1, 2),
     "notlar": {"2709251": "FF"},
     "eksik": ("zorunlu",),
     "aciklama": "2. sınıf, zorunlu ders seçilmemiş"},

    {"giris": 2023, "yariyillar": (1, 2, 3, 4, 5, 6), "notlar": {},
     "eksik": ("secmeli", "secmeli"),
     "aciklama": "son sınıf, iki seçmeli eksik"},

    {"giris": 2022, "yariyillar": (1, 2, 3, 4, 5, 6),
     "notlar": {"2709601": "FF", "2709602": "FF"},
     "eksik": (), "aciklama": "2022 girişli — kohort açığı belirgin"},
]


def _hedef_donem(yariyillar):
    """Okunmuş yarıyıllara göre bu güz hangi dönemi alacak?"""
    en_yuksek = max(yariyillar)
    return min(7, en_yuksek + 1 if en_yuksek % 2 == 0 else en_yuksek + 2)


def _programdakiler(program):
    """Ders programında adı geçen derslerin ad anahtarları."""
    return {es.ders_adi_anahtari(a) for a in
            ((program or {}).get("dersler") or {})}


def _secim(muf, hedef, giris_yili, eksik, kalinan_kodlar, programdaki):
    """Hedef yarıyılın kompozisyonunu KURAR, sonra 'eksik'i çıkarır.

    Böylece 'temiz' vaka gerçekten temiz çıkar: zorunlular + TOS kotası
    + gereken sayıda bölüm içi seçmeli.
    """
    yapi = ym.donem_yapisi(hedef, muf, giris_yili) or {}
    dersler = muf["dersler"]
    secim = list(yapi.get("zorunlu_kodlar") or ())

    tos = sorted(k for k, b in dersler.items()
                 if b.get("yariyil") == hedef and b.get("tip") == "TOS")
    secim += tos[:yapi.get("tos_adedi") or 0]

    # Seçmelileri DERS PROGRAMINDA yeri olanlardan seçiyoruz: aksi
    # hâlde örnekte herkese "programda bulunamayan ders" uyarısı
    # çıkıyor ve bu, aracın kusuru gibi görünüyor.
    secmeli = sorted(k for k, b in dersler.items()
                     if b.get("yariyil") == hedef
                     and (b.get("tip") or "") == "Seçmeli")
    oncelikli = [k for k in secmeli
                 if es.ders_adi_anahtari(dersler[k].get("ders_adi") or "")
                 in programdaki]
    sirali = oncelikli + [k for k in secmeli if k not in oncelikli]
    secim += sirali[:yapi.get("secmeli_adedi") or 0]
    secmeli = sirali

    # Alttan kalınan dersler de seçilsin - danışmanın istediği budur.
    secim += [k for k in kalinan_kodlar if k not in secim]

    for ne in eksik:
        aday = None
        if ne == "zorunlu":
            aday = next((k for k in (yapi.get("zorunlu_kodlar") or ())
                         if k in secim), None)
        elif ne == "tos":
            aday = next((k for k in tos if k in secim), None)
        elif ne == "secmeli":
            aday = next((k for k in secmeli if k in secim), None)
        if aday:
            secim.remove(aday)
    return secim


def _gano(transkript):
    """GANO'yu panonun KENDİ kuralıyla hesapla (son denemeler üzerinden).

    Elle bir sayı yazınca ya da başka bir formül kullanınca pano haklı
    olarak "GANO tutmuyor" diyordu - uydurma veride bile tutarsızlık
    uydurmak istemiyoruz. Hesap ders_kayit.transkripti_coz() ile aynı:
    son_durum'daki her dersin AKTS'si x harf katsayısı.
    """
    son = transkript.get("son_durum") or {}
    akts = sum(d["akts"] for d in son.values())
    if not akts:
        return 0.0
    puan = sum(d["akts"] * ym.NOT_KATSAYILARI.get(d["harf"], 0.0)
               for d in son.values())
    return round(puan / akts, 2)


def _katalog(muf, secilen_kodlar):
    """Bu dönem açık ders kataloğu — belgeden üretiliyor."""
    dersler = muf["dersler"]
    katalog = []
    for kod, b in sorted(dersler.items()):
        yy = b.get("yariyil")
        if yy not in ym.GUZ_DONEMLERI:
            continue
        # OBİS katalogunda seçmeliler "(SEÇ)", TOS dersleri "*" ile
        # işaretli gelir; ozet.py ders tipini BU işaretlerden çıkarır
        # (ders tipi alanına güvenilmiyor). Örnek katalog da aynı
        # biçimde olmalı, yoksa seçmeliler kotaya sayılmaz.
        tip = b.get("tip") or ""
        im = "*" if tip == "TOS" else (" (SEÇ)" if tip == "Seçmeli" else "")
        katalog.append({
            "ders_no": kod,
            "ders_adi": (b.get("ders_adi") or "").upper() + im,
            "akts": b.get("akts"),
            "donem": "%d. Dönem Dersleri" % yy,
            "eklenebilir": True,
            # Birkaç dersin kontenjanı dolu olsun ki "ilave kontenjan"
            # görünümü de örnekte yer alsın.
            "doldu": kod in ("2709543", "2709744"),
            "yesil_yazi": False,
            "secili": kod in secilen_kodlar,
            "sekme": ozet.BOLUM_SEKMESI,
        })
    return katalog


def kayitlar(muf, program=None):
    programdaki = _programdakiler(program)
    ogrenciler = []
    for i, v in enumerate(VAKALAR):
        no = _no(v["giris"], i + 1)
        ad = ADLAR[i % len(ADLAR)]
        # Transkripti iki kez kuruyoruz: ilkinde GANO'yu hesaplamak
        # icin, ikincisinde o GANO belgenin icine yazilsin diye.
        ham = st.uret(muf, no, yariyillar=v["yariyillar"], gno="0,00",
                      ad=ad, notlar=v["notlar"])
        gano = _gano(dk.transkripti_coz(ham))
        ham = st.uret(muf, no, yariyillar=v["yariyillar"],
                      gno=("%.2f" % gano).replace(".", ","),
                      ad=ad, notlar=v["notlar"])
        transkript = dk.transkripti_coz(ham)

        hedef = _hedef_donem(v["yariyillar"])
        kalinan = [d["ders_kodu"] for d in (transkript.get("kalinan") or [])
                   if (muf["dersler"].get(d["ders_kodu"]) or {})
                   .get("yariyil") in ym.GUZ_DONEMLERI]
        secilen = set(_secim(muf, hedef, v["giris"], v["eksik"],
                             kalinan, programdaki))

        katalog = _katalog(muf, secilen)
        secili = [{"ders_no": d["ders_no"], "ders_adi": d["ders_adi"],
                   "aciklama": "Ders ilk kez alınıyor"}
                  for d in katalog if d["secili"]]
        ogrenciler.append({
            "no": no, "ad": ad,
            "durum": "ONAY BEKLENİYOR" if i % 3 else "ONAYLANDI",
            "genel_ort": gano,
            "ders_sayisi": len(secili),
            "toplam_akts": sum(d["akts"] or 0 for d in katalog if d["secili"]),
            "maks_akts": ym.azami_akts(gano) or 45,
            "katalog": katalog,
            "secili_dersler": secili,
            "transkript": transkript,
            "son_tarama": "12.09.2026 10:00",
        })
    return ogrenciler


def main():
    muf = mufredat.yukle()
    if not muf:
        print("veri/mufredat.json yok. Önce: python mufredat.py")
        return 1
    program = ders_programi.yukle()

    kayit_listesi = kayitlar(muf, program)
    ciftler = []
    for k in kayit_listesi:
        o = ozet.ogrenci_ozeti(k, mufredat=muf, program=program,
                               icinde_bulunulan_yil=2026)
        ciftler.append((k, o))

    yol = rapor.pano_yaz(
        ciftler, CIKTI,
        danisman="ÖRNEK DANIŞMAN",
        kontenjan=ozet.kontenjan_planlari([o for _, o in ciftler]),
        program=program,
        katalog=kayit_listesi[0]["katalog"])

    print("Örnek pano: %s" % yol)
    print("Öğrenci   : %d (hepsi uydurma)" % len(ciftler))
    for k, o in ciftler:
        s = o.get("sayim") or {}
        print("  %-9s %-20s %d yapılacak / %d dikkat"
              % (k["no"], k["ad"][:20], s.get("yapilacak", 0),
                 s.get("dikkat", 0)))
    print("")
    print("Bu dosyada gerçek öğrenci verisi YOKTUR; cikti/ klasörü hiç")
    print("okunmadı. Yayımlanabilir.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
