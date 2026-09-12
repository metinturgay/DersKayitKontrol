# -*- coding: utf-8 -*-
"""Başka bir danışmana verilebilecek TEMİZ bir kopya hazırlar.

    python paylas.py                  # masaüstüne DersKayitKontrol_paylasim/
    python paylas.py C:\\hedef\\klasor  # istediğiniz yere

Neden ayrı bir script
---------------------
Klasörü olduğu gibi kopyalamak ÜÇ ŞEYİ SIZDIRIR:

  cikti/          60 öğrencinin adı, numarası, notları, transkripti
  .env            OBİS şifreniz
  chrome-profili/ OBİS oturum çerezleriniz - kopyayı alan kişi sizin
                  adınıza OBİS'e girebilir

Bu script yalnız çalışması gereken dosyaları kopyalar, üçünü de dışarıda
bırakır ve kopyaladığı her şeyi tek tek ekrana yazar ki ne verdiğinizi
görebilesiniz. Hiçbir şeyi silmez, yalnızca kopyalar.
"""
import io
import os
import shutil
import sys

BURASI = os.path.dirname(os.path.abspath(__file__))
DEPO = os.path.dirname(BURASI)

# Çalışması için gereken her şey. Buraya eklemeden önce iki kez düşünün:
# öğrenci verisi taşıyan hiçbir dosya bu listede olmamalı.
KOD = [
    "ders_kayit.py", "ozet.py", "rapor.py", "yonetmelik.py",
    "bolum.py", "kurulum.py", "kaynaklar.py", "eslestirme.py",
    "mufredat_arsivi.py",
    "ornek_uret.py", "ornek/gorsel_uret.py",
    "mufredat.py", "ders_programi.py", "akts_degisimi.py",
    "panoyu_yenile.py", "mufredat_denetle.py", "program_denetle.py",
    "yollar.py", "baslat.py", "exe_yap.py",
    "paylas.py", "KULLANIM.md", "README.md", "LICENSE",
]
VERI = [
    "veri/bolum.json",           # bölüm profili - yönetmelik dışı her şey
    "veri/mufredat.docx",        # AKTS için tek doğru kaynak
    "veri/mufredat.json",        # çözülmüş hâli (belge yoksa da çalışır)
    "veri/ders_programi.xlsx",   # çakışma kontrolü
    "veri/cakismalar.json",      # çözülmüş hâli
    "veri/akts_referans.json",   # giriş yılına göre AKTS fotoğrafları
]
# Varsa kopyalanır, yoksa sorun değil (yalnız çok yıllı arşivi olan
# bölümlerde oluşur).
ISTEGE_BAGLI_VERI = ["veri/mufredat_arsivi.json"]
TESTLER = [
    "testler/test_transkript.py", "testler/test_eslestirme.py",
    "testler/test_kurallar.py", "testler/test_program.py",
    "testler/test_mufredat.py", "testler/test_pano.py",
    "testler/test_kohort.py", "testler/test_bolum.py",
    "testler/test_arsiv.py", "testler/test_kurulum.py",
    "testler/test_yollar.py", "testler/test_kaynaklar.py",
    "testler/sentetik_transkript.py",
    "testler/sentetik_mufredat.py",
    "testler/pano_calistir.js",
]
DEPO_DOSYALARI = [".env.example"]

# --yayin kipinde KOPYALANMAYANLAR: bölümün kendi belgeleri. Çözülmüş
# hâlleri (veri/*.json) zaten gidiyor ve araç onlarla çalışıyor.
# Belgeyi yayımlamak bölümün kararıdır; üstelik .gitignore onları
# dışladığı için kopyalansalar bile izlenmeyen dosya olarak kalırlardı.
YAYIN_DISI = ["veri/mufredat.docx", "veri/ders_programi.xlsx"]

# --yayin kipinde ayrıca kopyalananlar. Bunlar aracın çalışması için
# gerekli DEĞİL; deponun kendini anlatması için gerekli.
YAYIN_EKLERI = [
    "README.md",
    "ornek/danisman_ozeti.html",
    "ornek/gorseller/01-ogrenci.png",
    "ornek/gorseller/02-yonetici.png",
    "ornek/gorseller/03-transkript.png",
    "ornek/gorseller/04-cakisma.png",
    "ornek/gorseller/05-koyu.png",
]

# Yayımlanan deponun kendi .gitignore'u. Ana deponunki bütün projeleri
# kapsıyor; burada yalnız bu projeye ait olanlar duruyor.
YAYIN_GITIGNORE = u"""# --- Python ---
__pycache__/
*.py[cod]
.venv/
venv/

# --- Kimlik bilgisi: ASLA depoya girmemeli ---
.env

# --- Öğrenci verisi: ASLA depoya girmemeli ---
# cikti/     : pano + her öğrencinin ham OBİS sayfası
# chrome-*   : OBİS oturum çerezleri (kopyalayan sizin adınıza girebilir)
# ornek_*    : testlerin GERÇEK veriden ürettiği fixture'lar
cikti/
chrome-profili/
testler/ornek_pano.html
testler/ornek_transkript.html
bolum_onayi.json
veri/bolum.taslak.json

# --- Kendi kurulumunuz ---
# Araci acip kendi belgelerinizi verdiginizde buraya yaziliyor: kendi
# bolumunuzun belgeleri ve cozulmus halleri. Depoya girmemeli.
veri-yerel/

# --- Bölüm belgeleri (büyük ikili dosyalar) ---
# Çözülmüş hâlleri veri/*.json olarak depoda duruyor; belgelerin
# kendisi bölümün malıdır, yayımlamak size kalmış.
veri/*.docx
veri/*.xlsx
veri/mufredat/
*.pdf

# --- Derleme çıktısı ---
DanismanOzeti.exe
build/
dist/
*.spec
"""

# Yayımlanan deponun requirements'i. Ana depodaki dosya altı projeyi
# birden kapsıyor (pandas, numpy, pywin32...); bu proje o kadarına
# ihtiyaç duymuyor.
YAYIN_REQUIREMENTS = u"""selenium
beautifulsoup4
python-dotenv
openpyxl
"""

# ASLA kopyalanmayacaklar - kod değil, karar.
YASAK = ["cikti", ".env", "chrome-profili", "__pycache__",
         "testler/ornek_pano.html", "testler/ornek_transkript.html",
         # Bölüm teyidi kurulumun kendisine aittir. Kopyalanırsa karşı
         # taraf "bu sizin bölümünüz mü?" sorusunu HİÇ görmez ve başka
         # bir bölümün planıyla çalıştığını fark etmez.
         "bolum_onayi.json",
         # Danismanin kendi kurulumu: kendi bolumunun belgeleri ve
         # cozulmus hâlleri. Kopyalanirsa karsi taraf BASKA bir bolumun
         # planiyla calisir ve bunu fark etmez.
         "veri-yerel"]

OKUBENI = u"""# Ders Kayıt Kontrol — kurulum

Bu klasör, danışman özeti üreten salt-okunur bir araçtır. **Hiçbir
öğrenciye ders eklemez, çıkarmaz, onaylamaz veya reddetmez.** Yalnız
OBİS'ten okur ve tek dosyalık bir HTML pano üretir. Tek yazma işlemi
OBİS'in öğrenci kilidini açmaktır.

## 1. Gerekenler

Bu KAYNAK KOD kopyasıdır; Python gerekir. (Python istemiyorsanız
tek dosyalık `DanismanOzeti.exe` sürümünü isteyin - onda Python
gerekmez.)

* Python 3.9+  (https://www.python.org/downloads/ - kurulumda
  "Add Python to PATH" kutusunu işaretleyin)
* Google Chrome
* İnternet (OBİS + ilk çalıştırmada chromedriver indirilir)
* Kütüphaneler:

      pip install selenium beautifulsoup4 python-dotenv openpyxl

## 2. Giriş bilgileriniz

`.env.example` dosyasını `.env` adıyla kopyalayın ve KENDİ OBİS
bilgilerinizi yazın:

    OBIS_KULLANICI=sicil_numaraniz
    OBIS_SIFRE=sifreniz

`.env` dosyasını kimseyle paylaşmayın.

## 3. Çalıştırma

    python baslat.py

Giriş bilgilerinizi sorar, tarar ve `cikti/danisman_ozeti.html`
dosyasını üretip açar. Şifre ekrana yazılmaz, hiçbir yere kaydedilmez.

Bir öğrencinin kaydını elle düzelttiyseniz yalnız onu tazeleyin
(diğerleri diskten korunur, pano eksilmez):

    python ders_kayit.py --ogrenci 230000003

Kural değiştirirseniz OBİS'e tekrar girmeye gerek yok:

    python panoyu_yenile.py

## 4. BAŞKA BİR BÖLÜMDE kullanıyorsanız — önce bunu okuyun

Bu kopya **bir bölüme göre yapılandırılmıştır**. Açılış ekranında ve
pano başlığında hangi bölüm olduğu yazar. Orada KENDİ bölümünüzü
görmüyorsanız sayılar sizin planınıza göre değil onunkine göre
hesaplanır — önce kurulum yapın:

    python kurulum.py --belgeler    bizden ne isteniyor
    python kurulum.py --denetle     elde ne var, ne eksik
    python kurulum.py               sihirbaz

Sihirbaz size iki belge soracak:

1. **Son 4-5 yılın "Okutulacak Dersler" belgesi** (bölüm başkanlığından),
   `veri/mufredat/2022.docx`, `veri/mufredat/2023.docx` ... biçiminde.
   Dosya adındaki yıl, o belgenin geçerli olduğu GİRİŞ YILIDIR.
   Bunlardan yarıyıl planı, TOS listesi, dönem kompozisyonu, AKTS'si
   değişen dersler ve müfredata sonradan eklenen dersler ÇIKARILIR.
   Tek yıl verirseniz araç yine çalışır ama AKTS kaybı ve kohort açığı
   hesaplanamaz — karşılaştıracak yıl yoktur.

2. **Bu yarıyılın ders programı** (`veri/ders_programi.xlsx`). Yoksa
   yalnız çakışma denetimi kapanır.

Geri kalanı birkaç sorudur: fakülte/bölüm adı ve program yılı; açığın
hangi yarıyıldan kapatıldığı; sabit saati olmayan dersler; laboratuvar
ve uygulama dersleri.

Kod düzenlemeniz GEREKMEZ. Bölüme özgü her şey `veri/bolum.json`
dosyasındadır; `python bolum.py --denetle` tutarlılığını sınar.

Belgeler değiştiğinde:

* `veri/mufredat.docx` yenilendi → `python mufredat.py`
* `veri/mufredat/` arşivi değişti → `python mufredat_arsivi.py --json`
* `veri/ders_programi.xlsx` yenilendi → `python ders_programi.py`

`veri/akts_referans.json` — giriş yılına göre AKTS fotoğrafı. Bir
kohorttan hiç dersten kalmamış bir öğrencinin OBİS ders kayıt sayfasından
çıkarılır. Arşiviniz varsa buna gerek yok; kohortun kendi transkript
kayıtları varsa zaten onlar kullanılır.

## 5. Doğru çalıştığını görmek

Önce OBİS'e dokunmadan hızlı sınama:

    python baslat.py --tani

Sonra testler:

    cd testler
    python test_kurallar.py
    python test_mufredat.py
    python test_kohort.py
    python test_pano.py

Ayrıntılı anlatım: `KULLANIM.md`
"""


def _sizinti_denetimi(klasor):
    """Yayımlanacak ağacı kişisel veri ve sır açısından tarar.

    Depo herkese açık olacaksa bu son kapıdır: listeler elle
    tutuluyor ve bir dosya yanlışlıkla listeye girebilir.
    """
    import re

    desenler = [
        # Sınır (\b) KULLANILMIYOR: "_" bir sözcük karakteri
        # olduğu için `ders_sayfasi_<numara>.html` içindeki numara
        # sınırlı desene HİÇ takılmıyordu. Aynı tuzak test
        # korumasında da vardı ve orada koruma baştan beri ölüydü.
        ("gerçek biçimli öğrenci no",
         re.compile(r"(?<!\d)\d{2}2709\d{3}(?!\d)")),
        # Yalniz TIRNAK ICINDE yazili deger araniyor: `sifre = x`
        # bir degisken atamasidir, sir degil. Once genel bir desen
        # kullanildi ve ders_kayit.py'yi sir sandi.
        ("gömülü şifre",
         re.compile("(?i)(sifre|password|passwd|secret|token"
                    "|api[_-]?key)[ \\t]*[=:][ \\t]*"
                    "[\"']([^\"'\\n]{3,})[\"']")),
        ("TC kimlik", re.compile(r"\b[1-9]\d{10}\b")),
    ]
    bulgu, bakilan = [], 0
    for dizin, altlar, dosyalar in os.walk(klasor):
        altlar[:] = [a for a in altlar if a != "__pycache__"]
        for d in dosyalar:
            yol = os.path.join(dizin, d)
            bagil = os.path.relpath(yol, klasor)
            if d in ("cikti", ".env") or bagil.startswith("cikti"):
                bulgu.append("[HATA] yasak dosya kopyalanmış: " + bagil)
                continue
            if not d.endswith((".py", ".md", ".js", ".json", ".html",
                               ".txt", ".example", ".gitignore")):
                continue
            try:
                icerik = io.open(yol, encoding="utf-8").read()
            except (OSError, UnicodeDecodeError):
                continue
            bakilan += 1
            for ad, desen in desenler:
                for m in desen.findall(icerik):
                    bulgu.append("[HATA] %s: %s (%s)"
                                 % (ad, bagil,
                                    (m if isinstance(m, str)
                                     else m[0])[:24]))
    for ad in (".env", "chrome-profili", "cikti", "bolum_onayi.json",
               "veri-yerel"):
        if os.path.exists(os.path.join(klasor, ad)):
            bulgu.append("[HATA] yasak: " + ad)
    if not bulgu:
        return ["%d metin dosyası tarandı, bulgu yok." % bakilan,
                "Öğrenci verisi, şifre ve oturum bilgisi YOK."]
    return sorted(set(bulgu))


def main():
    yayin = "--yayin" in sys.argv
    argvler = [a for a in sys.argv[1:] if not a.startswith("--")]
    hedef = (argvler[0] if argvler else
             os.path.join(os.path.expanduser("~"), "Desktop",
                          "DersKayitKontrol-yayin" if yayin
                          else "DersKayitKontrol_paylasim"))
    hedef = os.path.abspath(hedef)
    if os.path.abspath(BURASI) == hedef:
        print("Hedef klasör projenin kendisi olamaz.")
        return 1

    print("Hedef: " + hedef)
    print("")
    kopyalanan, eksik = [], []

    def kopyala(bagil, kaynak_kok=BURASI):
        kaynak = os.path.join(kaynak_kok, bagil.replace("/", os.sep))
        if not os.path.exists(kaynak):
            eksik.append(bagil)
            return
        varis = os.path.join(hedef, os.path.basename(bagil)
                             if kaynak_kok == DEPO
                             else bagil.replace("/", os.sep))
        klasor = os.path.dirname(varis)
        if klasor and not os.path.isdir(klasor):
            os.makedirs(klasor)
        shutil.copy2(kaynak, varis)
        kopyalanan.append((bagil, os.path.getsize(kaynak)))

    if not os.path.isdir(hedef):
        os.makedirs(hedef)
    listeler = (KOD + VERI + TESTLER
                + [d for d in ISTEGE_BAGLI_VERI
                   if os.path.exists(os.path.join(BURASI, d))])
    if yayin:
        listeler = [d for d in listeler if d not in YAYIN_DISI]
    for ad in listeler:
        kopyala(ad)
    for ad in DEPO_DOSYALARI:
        kopyala(ad, DEPO)

    if yayin:
        # GitHub'a konacak ağaç: kendi .gitignore'u, kendi
        # requirements'i, README ve örnek görseller.
        for ad in YAYIN_EKLERI:
            kopyala(ad)
        for ad, icerik in ((".gitignore", YAYIN_GITIGNORE),
                           ("requirements.txt", YAYIN_REQUIREMENTS)):
            yol = os.path.join(hedef, ad)
            with open(yol, "w", encoding="utf-8") as f:
                f.write(icerik)
            kopyalanan.append((ad + " (üretildi)", os.path.getsize(yol)))
    else:
        okubeni = os.path.join(hedef, "OKUBENI.md")
        with open(okubeni, "w", encoding="utf-8") as f:
            f.write(OKUBENI)
        kopyalanan.append(("OKUBENI.md (üretildi)",
                           os.path.getsize(okubeni)))

    for ad, boyut in kopyalanan:
        print("  + %-42s %7.1f KB" % (ad, boyut / 1024.0))
    if eksik:
        print("")
        for ad in eksik:
            print("  ! bulunamadı, atlandı: " + ad)

    print("")
    if yayin:
        print("Yayına konmayan bölüm belgeleri (çözülmüş hâlleri gitti):")
        for ad in YAYIN_DISI:
            print("  - " + ad)
        print("")
    print("Kopyalanmayanlar (öğrenci verisi / kimlik bilgisi):")
    for ad in YASAK:
        # .env depo kökünde, geri kalanı proje klasöründe duruyor.
        for kok in (BURASI, DEPO):
            yol = os.path.join(kok, ad.replace("/", os.sep))
            if os.path.exists(yol):
                print("  - " + ad + ("  (depo kökü)" if kok == DEPO else ""))
                break
    print("")
    if yayin:
        sizinti = _sizinti_denetimi(hedef)
        print("")
        print("SIZINTI DENETIMI")
        for satir in sizinti:
            print("  " + satir)
        print("")
        print("%d dosya. Yayımlamak icin:" % len(kopyalanan))
        print("    cd %s" % hedef)
        print("    git init && git add -A && git commit -m \"Ilk surum\"")
        print("    git remote add origin <github-adresi>")
        print("    git push -u origin main")
        return 0

    print("%d dosya kopyalandı. Klasörü zipleyip verebilirsiniz."
          % len(kopyalanan))
    print("Karşı taraf kendi .env dosyasını oluşturmalı (.env.example).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
