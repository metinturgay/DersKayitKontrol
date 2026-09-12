# -*- coding: utf-8 -*-
"""Yeni bir bölüm için kurulum sihirbazı.

Bu araç Matematik bölümü için yazıldı ama içindeki kuralların büyük
bölümü Selçuk Üniversitesi'nin TAMAMI için aynı: not tablosu, AKTS
limiti, azami süre, devam koşulu, mezuniyet asgarisi. Bölümden bölüme
değişen şeyler bir avuç:

    yarıyıl AKTS planı · TOS ders listesi · dönem kompozisyonu ·
    müfredata sonradan eklenmiş dersler · ders programının sayfa düzeni

Sihirbazın işi bunları TÜRETMEK ve yalnız türetilemeyeni sormak.

    python kurulum.py --belgeler    danışmandan ne isteniyor
    python kurulum.py --denetle     elde ne var, ne eksik
    python kurulum.py               sihirbaz (soru-cevap)
    python kurulum.py --otomatik    soru sormadan türetilebileni yaz

Tasarım kuralı
--------------
Türetemediğimiz hiçbir şeyi UYDURMAYIZ. Matematik'in değerini başka bir
bölüme varsayılan diye koymak, sessizce yanlış AKTS hesaplamak demektir.
Eksik kalan her alan raporda açıkça "SİZ DOLDURUN" diye durur.
"""
import io
import json
import os
import sys
from pathlib import Path

import bolum
import eslestirme as es
import mufredat_arsivi as ma
import yollar

VERI = yollar.veri()
ARSIV = VERI / "mufredat"
PROGRAM_XLSX = VERI / "ders_programi.xlsx"


# =========================================================================
#  1. Danışmandan istenenler
# =========================================================================
BELGE_LISTESI = u"""
DANIŞMANDAN İSTENENLER
======================

1) "Okutulacak Dersler" belgeleri — son 4-5 yıl              [ZORUNLU]

   Nereden : Bölüm başkanlığı ya da bölümün web sayfası. Her öğretim
             yılı için bir Word belgesi.
   Nereye  : veri/mufredat/2022.docx
             veri/mufredat/2023.docx
             ...
             Dosya adındaki yıl, o belgenin geçerli olduğu GİRİŞ
             YILI'dır. "2024-2025 Okutulacak Dersler.docx" da olur;
             baştaki yıl okunur.

   Ne çözüyor:
       · yarıyıl AKTS planı (1. yarıyıl 30, 7. yarıyıl 32 ...)
       · zorunlu / seçmeli / TOS ayrımı ve dönem kompozisyonu
       · YILLAR İÇİNDE AKTS'Sİ DEĞİŞEN dersler
       · MÜFREDATA SONRADAN EKLENMİŞ dersler

   Son iki madde bu aracın en pahalı bilgisidir. Matematik'te
   transkriptler tek tek karşılaştırılarak ölçüldü; belgeler yan yana
   konunca kendiliğinden çıkıyor.

   TEK YIL verirseniz: araç yine çalışır, ama AKTS kaybı ve kohort
   açığı HESAPLANAMAZ — çünkü karşılaştıracak yıl yoktur. En az iki
   yıl gerekir, dört-beş yıl tam sonuç verir.

2) Bu yarıyılın ders programı (xlsx)                    [İSTEĞE BAĞLI]

   Nereye  : veri/ders_programi.xlsx
   Ne çözüyor: aynı saate düşen dersler (MADDE 9/1-b). Yoksa yalnız
             çakışma denetimi kapanır, geri kalan her şey çalışır.

3) Birkaç soru                                               [ZORUNLU]

   · Fakülte ve bölüm adı; program kaç yıllık (2 / 4 / 5)
   · Müfredata sonradan eklenmiş ders varsa: eski kohortun eksik
     kalan AKTS'si HANGİ yarıyılın seçmeli havuzundan kapatılıyor?
     (bölüm kararıdır, belgede yazmaz)
   · Ders programında sabit buluşma saati OLMAYAN dersler hangileri?
     (asenkron yürütülen ortak zorunlular, öğrenciyle ayarlanan
     uygulama dersleri) — bunlar çakışma üretmez
   · Hangi dersler laboratuvar/uygulama? Devamsızlık hakları %30
     değil %20'dir (MADDE 10/1)

NE İSTEMİYORUZ
--------------
Öğrenci listesi, transkript, not dökümü istemiyoruz. Öğrenci verisi
yalnız OBİS'ten, danışmanın kendi oturumuyla okunur ve bilgisayardan
dışarı çıkmaz.
"""


# =========================================================================
#  2. Elde ne var?
# =========================================================================
def durum():
    """Kurulumun neresindeyiz? Rapor için sözlük döndürür."""
    belgeler = ma.belgeleri_bul(ARSIV)
    tek_belge = VERI / "mufredat.docx"
    return {
        "profil_var": bolum.yol().exists(),
        "arsiv_klasoru": ARSIV,
        "arsiv_belgeleri": belgeler,
        "tek_belge": tek_belge if tek_belge.exists() else None,
        "program_xlsx": PROGRAM_XLSX if PROGRAM_XLSX.exists() else None,
    }


def _profil_sorunlari():
    if not bolum.yol().exists():
        return [("HATA", "veri/bolum.json yok.")]
    try:
        ham = json.load(io.open(str(bolum.yol()), encoding="utf-8"))
    except ValueError as e:
        return [("HATA", "veri/bolum.json bozuk: %s" % e)]
    return bolum.denetle(ham)


def denetle_yaz():
    d = durum()
    print("KURULUM DURUMU")
    print("=" * 60)
    print("")
    print("Bölüm profili   : %s"
          % ("var — %s" % bolum.yol() if d["profil_var"] else "YOK"))
    for seviye, mesaj in _profil_sorunlari():
        print("                  [%s] %s" % (seviye, mesaj))

    print("")
    print("Müfredat arşivi : %s" % d["arsiv_klasoru"])
    if d["arsiv_belgeleri"]:
        for yil, yol in d["arsiv_belgeleri"]:
            print("                  %d  %s" % (yil, os.path.basename(yol)))
    else:
        print("                  YOK")
    if d["tek_belge"] and not d["arsiv_belgeleri"]:
        print("                  (tek belge var: %s)"
              % os.path.basename(str(d["tek_belge"])))

    print("")
    print("Ders programı   : %s"
          % (os.path.basename(str(d["program_xlsx"]))
             if d["program_xlsx"] else "YOK (çakışma denetimi kapalı)"))

    print("")
    print("ÇIKARIM GÜCÜ")
    print("-" * 60)
    n = len(d["arsiv_belgeleri"])
    if n >= 2:
        arsiv, _ = ma.oku(ARSIV)
        t = ma.turet(arsiv)
        print("  %d yıllık arşiv var. Şunlar belgeden çıkarılabiliyor:" % n)
        print("    yarıyıl planı            %d yarıyıl, %d AKTS"
              % (len(t["donem_akts"]), sum(t["donem_akts"].values())))
        print("    TOS dersleri             %d ders" % len(t["tos_dersleri"]))
        print("    sonradan eklenen ders    %d"
              % len(t["sonradan_eklenen_dersler"]))
        print("    AKTS'si değişen ders     %d" % len(t["akts_degisenler"]))
        print("    kohort AKTS tabanı       %d-%d girişleri için"
              % (min(arsiv), max(arsiv)))
    elif n == 1 or d["tek_belge"]:
        print("  Tek belge var.")
        print("    ÇIKAR : yarıyıl planı, TOS listesi, kompozisyon")
        print("    ÇIKMAZ: AKTS kaybı, sonradan eklenen ders, kohort açığı")
        print("            (karşılaştıracak ikinci yıl yok)")
    else:
        print("  Hiç müfredat belgesi yok; hiçbir şey çıkarılamıyor.")
        print("  'python kurulum.py --belgeler' ne isteneceğini yazar.")

    eksik = _eksikler()
    print("")
    print("SİZİN DOLDURMANIZ GEREKENLER")
    print("-" * 60)
    if not eksik:
        print("  yok — kurulum tamam.")
    for e in eksik:
        print("  · " + e)
    return 0 if d["profil_var"] and not any(
        s == "HATA" for s, _ in _profil_sorunlari()) else 1


def _eksikler():
    """Belgeden çıkmayan, insanın söylemesi gereken alanlar."""
    eksik = []
    if not bolum.yol().exists():
        return ["Bölüm profili hiç yok: python kurulum.py"]
    try:
        p = json.load(io.open(str(bolum.yol()), encoding="utf-8"))
    except ValueError:
        return ["Bölüm profili okunamıyor; yeniden üretin."]
    b = p.get("bolum") or {}
    if not b.get("ad"):
        eksik.append("Bölüm adı (bolum.ad)")
    if b.get("program_yili") not in (2, 4, 5):
        eksik.append("Program kaç yıllık (bolum.program_yili: 2/4/5)")
    kohort = p.get("kohort") or {}
    if kohort.get("sonradan_eklenen_dersler") and \
            not kohort.get("acik_kapatma_yariyili"):
        eksik.append("Sonradan eklenen ders var; açık hangi yarıyılın "
                     "seçmeli havuzundan kapatılıyor "
                     "(kohort.acik_kapatma_yariyili)")
    pr = p.get("program") or {}
    if PROGRAM_XLSX.exists() and not pr.get("saat_sutunlari"):
        eksik.append("Ders programının saat sütunları "
                     "(program.saat_sutunlari)")
    if PROGRAM_XLSX.exists() and not pr.get("asenkron_dersler") and \
            not pr.get("esnek_dersler"):
        eksik.append("Sabit saati olmayan dersler varsa "
                     "(program.asenkron_dersler / esnek_dersler) — "
                     "yoksa boş bırakın")
    return eksik


# =========================================================================
#  3. Ders programı xlsx'inden sayfa düzenini çıkar
# =========================================================================
_SAAT = None


def program_duzeni(xlsx=None):
    """xlsx'i açıp sayfa adlarını ve saat sütunlarını tahmin eder."""
    global _SAAT
    if _SAAT is None:
        import re
        _SAAT = re.compile(r"^\s*\d{1,2}[:.]\d{2}\s*-\s*\d{1,2}[:.]\d{2}\s*$")
    yol = Path(xlsx or PROGRAM_XLSX)
    if not yol.exists():
        return None
    try:
        import openpyxl
    except ImportError:
        return {"hata": "openpyxl kurulu değil: pip install openpyxl"}
    kitap = openpyxl.load_workbook(str(yol), data_only=True)
    sonuc = {"dosya": str(yol), "sayfalar": list(kitap.sheetnames),
             "sayfa_adi": None, "saat_sutunlari": {}}

    # En çok saat başlığı taşıyan sayfa, ders programı sayfasıdır.
    en_iyi = (0, None, {})
    for ad in kitap.sheetnames:
        ws = kitap[ad]
        sutunlar = {}
        for r in range(1, min(ws.max_row, 60) + 1):
            for c in range(1, min(ws.max_column, 30) + 1):
                deger = str(ws.cell(r, c).value or "").strip()
                if _SAAT.match(deger):
                    harf = openpyxl.utils.get_column_letter(c)
                    sutunlar.setdefault(harf, deger.replace(".", ":"))
        if len(sutunlar) > en_iyi[0]:
            en_iyi = (len(sutunlar), ad, sutunlar)
    if en_iyi[1]:
        sonuc["sayfa_adi"] = en_iyi[1]
        sonuc["saat_sutunlari"] = dict(sorted(en_iyi[2].items()))
    return sonuc


# =========================================================================
#  4. Profil kurma
# =========================================================================
def taslak(cevaplar=None, klasor=None):
    """Belgelerden çıkarılabilen her şeyle bir profil taslağı kurar.

    cevaplar: insandan gelen alanlar. Verilmeyen alan BOŞ bırakılır,
    varsayılan UYDURULMAZ.
    """
    c = dict(cevaplar or {})
    arsiv, hatalar = ma.oku(klasor or ARSIV)
    if not arsiv:
        # Arşiv klasörü boşsa tek belgeyi "tek yıllık arşiv" gibi kullan.
        # Yıl anahtarı 0: hangi girişe ait olduğunu bilmiyoruz ve tek
        # yılla zaten karşılaştırma yapılmıyor, plan/TOS çıkıyor.
        tek = VERI / "mufredat.docx"
        if tek.exists():
            try:
                arsiv = {0: ma.mufredat.oku(tek)}
            except Exception as e:        # noqa: BLE001
                hatalar.append((0, str(tek), str(e)))
    t = ma.turet(arsiv)

    program = program_duzeni() or {}
    p = {
        "surum": bolum.SURUM,
        "_aciklama": ("Bölüm profili. 'python kurulum.py' üretti; elle "
                      "de düzenlenebilir. 'python bolum.py --denetle' "
                      "tutarlılığını sınar."),
        "bolum": {
            "universite": c.get("universite") or "Selçuk Üniversitesi",
            "fakulte": c.get("fakulte") or "",
            "ad": c.get("ad") or "",
            "program_yili": c.get("program_yili"),
            "ogretim_yili": c.get("ogretim_yili") or "",
        },
        "plan": {"donem_akts": {str(y): v
                                for y, v in sorted(t["donem_akts"].items())}},
        "tos": {"akts": t["tos_akts"],
                "azami_adet": c.get("tos_azami_adet"),
                "dersler": t["tos_dersleri"]},
        "kohort": {
            "sonradan_eklenen_dersler": t["sonradan_eklenen_dersler"],
            "acik_kapatma_yariyili": c.get("acik_kapatma_yariyili"),
        },
        "donem_kompozisyonu": {},
        "program": {
            "sayfa_adi": (c.get("sayfa_adi") or program.get("sayfa_adi")
                          or "I. Öğretim"),
            "gunler": c.get("gunler") or ["PAZARTESİ", "SALI", "ÇARŞAMBA",
                                          "PERŞEMBE", "CUMA"],
            "saat_sutunlari": program.get("saat_sutunlari") or {},
            "tos_blok_adi": c.get("tos_blok_adi") or "TOS",
            "asenkron_dersler": [es.ders_adi_anahtari(a)
                                 for a in (c.get("asenkron_dersler") or [])],
            "esnek_dersler": [es.ders_adi_anahtari(a)
                              for a in (c.get("esnek_dersler") or [])],
            "uygulamali_dersler": [
                es.ders_adi_anahtari(a)
                for a in (c.get("uygulamali_dersler") or [])],
        },
        "kaynaklar": {
            "mufredat": {"arsiv_klasoru": "veri/mufredat/",
                         "dosya": "veri/mufredat.docx", "zorunlu": True},
            "ders_programi": {"dosya": "veri/ders_programi.xlsx",
                              "zorunlu": False},
        },
    }
    return p, {"arsiv": arsiv, "turetilen": t, "hatalar": hatalar,
               "program": program}


def yaz(profil, hedef=None):
    yol = Path(hedef or bolum.yol())
    yol.parent.mkdir(parents=True, exist_ok=True)
    yol.write_text(json.dumps(profil, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8")
    return yol


# =========================================================================
#  5. Soru-cevap
# =========================================================================
def _sor(soru, varsayilan=None, secenekler=None, tip=str):
    ek = ""
    if secenekler:
        ek = " [%s]" % "/".join(str(s) for s in secenekler)
    if varsayilan not in (None, ""):
        ek += " (boş = %s)" % varsayilan
    while True:
        try:
            cevap = input("  %s%s: " % (soru, ek)).strip()
        except EOFError:
            return varsayilan
        if not cevap:
            return varsayilan
        if tip is int:
            try:
                cevap = int(cevap)
            except ValueError:
                print("     sayı bekleniyor.")
                continue
        if secenekler and cevap not in secenekler:
            print("     şunlardan biri olmalı: %s"
                  % ", ".join(str(s) for s in secenekler))
            continue
        return cevap


def _liste_sor(soru):
    print("  %s" % soru)
    print("     (her satıra bir ders adı, bitirmek için boş satır)")
    sonuc = []
    while True:
        try:
            satir = input("     > ").strip()
        except EOFError:
            break
        if not satir:
            break
        sonuc.append(satir)
    return sonuc


def sihirbaz():
    print(BELGE_LISTESI)
    print("=" * 60)
    d = durum()
    n = len(d["arsiv_belgeleri"])
    if n:
        print("veri/mufredat/ altında %d belge bulundu: %s"
              % (n, ", ".join(str(y) for y, _ in d["arsiv_belgeleri"])))
    elif d["tek_belge"]:
        print("Arşiv klasörü boş; tek belge kullanılacak: %s"
              % os.path.basename(str(d["tek_belge"])))
    else:
        print("Hiç müfredat belgesi yok. Önce belgeleri veri/mufredat/")
        print("altına koyun, sonra bu sihirbazı tekrar çalıştırın.")
        return 1
    print("")

    if bolum.yol().exists():
        print("UYARI: %s zaten var ve ÜSTÜNE YAZILACAK." % bolum.yol())
        if _sor("Devam edilsin mi", "h", ("e", "h")) != "e":
            print("Vazgeçildi; hiçbir dosyaya dokunulmadı.")
            return 1
        print("")

    c = {}
    print("BÖLÜM")
    c["universite"] = _sor("Üniversite", "Selçuk Üniversitesi")
    c["fakulte"] = _sor("Fakülte", "")
    c["ad"] = _sor("Bölüm", "")
    c["program_yili"] = _sor("Program kaç yıllık", 4, (2, 4, 5), int)
    c["ogretim_yili"] = _sor("Öğretim yılı (örn. 2026-2027)", "")

    # Türetilebilenleri göster, sonra kalanları sor
    p, bilgi = taslak(c)
    t = bilgi["turetilen"]
    print("")
    print("BELGEDEN ÇIKARILANLAR")
    plan = p["plan"]["donem_akts"]
    print("  yarıyıl planı        : %s = %d AKTS"
          % (" + ".join(str(plan[k]) for k in sorted(plan, key=int)),
             sum(plan.values())))
    print("  TOS dersi            : %d (tipik %s AKTS)"
          % (len(t["tos_dersleri"]), t["tos_akts"]))
    print("  sonradan eklenen ders: %d"
          % len(t["sonradan_eklenen_dersler"]))
    for kod, yil in sorted(t["sonradan_eklenen_dersler"].items()):
        print("        %s  %d ve sonrası" % (kod, yil))
    print("  AKTS'si değişen ders : %d" % len(t["akts_degisenler"]))
    for deg in t["akts_degisenler"][:8]:
        print("        %-32s %s" % (
            deg["ad"][:32],
            " -> ".join("%s:%s" % (y, v)
                        for y, v in sorted(deg["degerler"].items()))))
    if len(t["akts_degisenler"]) > 8:
        print("        ... ve %d ders daha"
              % (len(t["akts_degisenler"]) - 8))

    print("")
    print("BÖLÜM KARARLARI (belgede yazmaz)")
    if t["tos_dersleri"]:
        c["tos_azami_adet"] = _sor(
            "Bir dönemde en çok kaç TOS dersi alınabilir", 1, tip=int)
    if t["sonradan_eklenen_dersler"]:
        print("  Sonradan eklenen ders var. Bu dersleri ALMAYACAK eski")
        print("  kohortun eksik kalan AKTS'si hangi yarıyılın seçmeli")
        print("  havuzundan kapatılıyor?")
        c["acik_kapatma_yariyili"] = _sor(
            "Açık kapatma yarıyılı", None, tip=int)

    pr = bilgi["program"]
    print("")
    print("DERS PROGRAMI")
    if not pr:
        print("  veri/ders_programi.xlsx yok; çakışma denetimi kapalı.")
    elif pr.get("hata"):
        print("  " + pr["hata"])
    else:
        print("  sayfalar : %s" % ", ".join(pr["sayfalar"]))
        print("  seçilen  : %s (%d saat sütunu bulundu)"
              % (pr["sayfa_adi"], len(pr["saat_sutunlari"])))
        c["sayfa_adi"] = _sor("Başka sayfa kullanılacaksa adı",
                              pr["sayfa_adi"])
        print("")
        print("  Sabit buluşma saati OLMAYAN dersler çakışma üretmez:")
        c["asenkron_dersler"] = _liste_sor(
            "Asenkron yürütülen dersler (uzaktan, kayıttan izlenen)")
        c["esnek_dersler"] = _liste_sor(
            "Saati öğrenciyle ayarlanan dersler (uygulama, proje)")

    print("")
    print("DEVAM KOŞULU")
    print("  Laboratuvar ve uygulama derslerinde devamsızlık hakkı %30")
    print("  değil %20'dir (MADDE 10/1); ayrıca FF notunun devamsızlıktan")
    print("  mı geldiği belli olmadığı için muafiyet teyit ister.")
    c["uygulamali_dersler"] = _liste_sor(
        "Laboratuvar / uygulama dersleri")

    p, bilgi = taslak(c)
    hedef = yaz(p)
    print("")
    print("=" * 60)
    print("Profil yazıldı: %s" % hedef)
    sorunlar = bolum.denetle(p)
    for seviye, mesaj in sorunlar:
        print("  [%s] %s" % (seviye, mesaj))
    eksik = _eksikler()
    if eksik:
        print("")
        print("Elle doldurmanız gerekenler:")
        for e in eksik:
            print("  · " + e)
    print("")
    print("Sonraki adım:")
    print("  python bolum.py --denetle      profili sına")
    print("  python mufredat.py             müfredatı çöz")
    print("  python ders_programi.py        çakışmaları çıkar")
    print("  python ders_kayit.py --tumu --pano --html")
    return 0 if not any(s == "HATA" for s, _ in sorunlar) else 1


def otomatik(hedef=None):
    """Soru sormadan türetilebileni TASLAK olarak yazar.

    ASLA veri/bolum.json'un üstüne yazmaz. Taslakta insanın vermesi
    gereken alanlar (program yılı, açık kapatma yarıyılı) boştur; böyle
    bir dosya doğrudan kullanılırsa modül açılmaz. Çalışan bir profilin
    üstüne yarım bir dosya koymak, aracı sessizce değil GÜRÜLTÜLÜ ama
    gereksiz yere kırardı; ikisini de istemiyoruz.
    """
    p, bilgi = taslak()
    if not bilgi["arsiv"]:
        print("Müfredat belgesi yok; profil üretilemiyor.")
        print("python kurulum.py --belgeler")
        return 1
    hedef = Path(hedef) if hedef else VERI / "bolum.taslak.json"
    yaz(p, hedef)
    print("Taslak profil yazıldı: %s" % hedef)
    t = bilgi["turetilen"]
    print("  yarıyıl planı         %d yarıyıl, %d AKTS"
          % (len(t["donem_akts"]), sum(t["donem_akts"].values())))
    print("  TOS dersi             %d" % len(t["tos_dersleri"]))
    print("  sonradan eklenen ders %d" % len(t["sonradan_eklenen_dersler"]))
    print("  AKTS'si değişen ders  %d" % len(t["akts_degisenler"]))
    print("")
    for seviye, mesaj in bolum.denetle(p):
        print("  [%s] %s" % (seviye, mesaj))
    print("")
    print("Bu bir TASLAKTIR. Boş kalan alanları doldurup dosyayı")
    print("veri/bolum.json adıyla kaydedin, ya da 'python kurulum.py'")
    print("ile sihirbazı çalıştırın.")
    return 0


def main(argv=None):
    argv = list(argv if argv is not None else sys.argv[1:])
    if "--belgeler" in argv:
        print(BELGE_LISTESI)
        return 0
    if "--denetle" in argv:
        return denetle_yaz()
    if "--otomatik" in argv:
        return otomatik()
    return sihirbaz()


if __name__ == "__main__":
    sys.exit(main())
