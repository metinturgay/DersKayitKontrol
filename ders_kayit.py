# -*- coding: utf-8 -*-
"""
Ders Kayıt Kontrol — 1. Aşama: giriş ve erişim testi

OBİS'e giriş yapar ve Ders Onay sayfasına erişilip erişilemediğini doğrular.
Giriş bilgileri depo kökündeki .env dosyasından okunur. Güvenlik kodunu
(captcha) makine çözemediği için o alanı tarayıcıda sizin doldurmanız gerekir;
script sicil no ile şifreyi kendi yazar, imleci güvenlik kodu alanına bırakır
ve girişin tamamlanmasını bekler.

Çalıştırma:
    python ders_kayit.py
"""

import csv
import datetime
import getpass
import os
import re
import sys
import time

from bs4 import BeautifulSoup
from dotenv import load_dotenv, find_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By

import akts_degisimi
import ders_programi
import mufredat as mufredat_modulu
import ozet
import rapor
import yollar
import yonetmelik
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    ElementNotInteractableException,
    NoSuchElementException,
    WebDriverException,
)


VARSAYILAN_OBIS = "https://obis2.selcuk.edu.tr"
GIRIS_BEKLEME_SURESI = 300  # güvenlik kodu için tanınan süre (saniye)

# Kalıcı Chrome profili. Oturum çerezi diskte kaldığı için sonraki
# çalıştırmalarda güvenlik kodunu tekrar girmek gerekmeyebilir.
# DİKKAT: bu klasör oturum bilgisi taşır, .gitignore ile hariç tutulmuştur.
PROFIL_KLASORU = yollar.profil()

# Öğrenci verisi içeren çıktılar buraya yazılır. .gitignore ile hariç tutulmuştur.
# Exe'de cikti exe'nin YANINA yazilir; gecici klasore yazarsak
# program kapaninca silinir.
CIKTI_KLASORU = yollar.cikti()

# --- Giriş formu alanları (obis2 form yapısı) -----------------------------
# Not: sicil ve şifre alanlarının id'si yok, name üzerinden bulunuyor.
SICIL_ALANI = (By.CSS_SELECTOR, 'form input[name="id"]')
SIFRE_ALANI = (By.CSS_SELECTOR, 'form input[name="pass"]')
CAPTCHA_ALANI = (By.ID, "TxtCaptcha")
GIRIS_BUTONU = (By.CSS_SELECTOR, 'form button[type="submit"]')
HATA_KUTUSU = (By.CSS_SELECTOR, ".alert-danger")

# "Destek ve Yardım" popup'ı. Sayfa yüklendikten 800 ms sonra açılıyor ve
# data-backdrop="static" olduğu için arkasındaki formu tamamen bloke ediyor.
# Açılıp açılmayacağına şu localStorage/sessionStorage anahtarlarına bakarak
# karar veriyor:
DESTEK_MODAL_ID = "destekBilgiModal"
DESTEK_LOCAL_ANAHTAR = "obis_destek_tekrar_gosterme"
DESTEK_SESSION_ANAHTAR = "obis_destek_popup_gosterildi"


# =========================================================================
#  Ayarlar
# =========================================================================
def ayarlari_oku(sorabilir=True):
    """Giriş bilgilerini ve OBİS adresini bulur.

    Sıra: .env dosyası -> ortam değişkeni -> kullanıcıya sor.

    Exe olarak dağıtıldığında .env yoktur; danışmandan sicil ve şifre
    istenir. Şifre ekrana yazılmaz (getpass) ve HİÇBİR YERE KAYDEDİLMEZ -
    yalnız o çalışma boyunca bellekte durur.
    """
    env = yollar.env_dosyasi()
    if env:
        load_dotenv(str(env))
    else:
        load_dotenv(find_dotenv())

    kullanici = os.getenv("OBIS_KULLANICI")
    sifre = os.getenv("OBIS_SIFRE")

    # Girdi gerçekten bir konsola bağlı değilse (pythonw, servis) hiç
    # sormayalım. DİKKAT: bu koruma her şeyi yakalamaz - ölçüldü, Git
    # Bash'te "< /dev/null" ile çalıştırıldığında isatty() yine True
    # dönüyor. Asıl güvence aşağıdaki EOFError yakalaması: girdi
    # bittiğinde "Vazgeçildi." deyip temiz çıkıyoruz, asılı kalmıyoruz.
    konsol_var = bool(sys.stdin) and sys.stdin.isatty()
    if (not kullanici or not sifre) and sorabilir and konsol_var:
        print("")
        print("OBİS giriş bilgileri")
        print("-" * 52)
        print("Şifre ekrana yazılmaz ve hiçbir yere kaydedilmez.")
        print("")
        try:
            if not kullanici:
                kullanici = input("Sicil / kullanıcı adı : ").strip()
            if not sifre:
                sifre = getpass.getpass("Şifre                 : ").strip()
        except (EOFError, KeyboardInterrupt):
            raise SystemExit("\nVazgeçildi.")

    if not kullanici or not sifre:
        raise SystemExit(
            "Giriş bilgisi yok.\n"
            "Ya çalıştırırken sorulduğunda girin, ya da yanına bir .env "
            "dosyası koyun (örnek için .env.example)."
        )

    taban = (os.getenv("OBIS_BASE_URL") or VARSAYILAN_OBIS).rstrip("/")
    return kullanici, sifre, taban


# =========================================================================
#  Tarayıcı
# =========================================================================
def sessizlestir(secenekler):
    r"""Chrome'un kendi günlük satırlarını konsoldan çıkarır.

    Tarama sırasında her öğrencide şunlar stderr'e düşüyordu:

        ERROR:chrome\updater\ipc\update_service_dialer_win.cc:75
              Failed to open named pipe server process ...
              Erişim engellendi. (0x5)
        ERROR:google_apis\gcm\engine\registration_request.cc:291
              Registration response error message: DEPRECATED_ENDPOINT

    İkisi de Chrome'un kendi arka plan işleri: birincisi otomatik
    güncelleyiciye bağlanmaya çalışıyor (servis yetkisi olmadığı için
    reddediliyor), ikincisi push bildirim kaydı. OBİS taramasıyla
    ilgileri yok, satırların arasında tarama sorunsuz tamamlanıyor.
    Ama danışman ekranda kırmızı ERROR görünce iş bozuldu sanıyor.

    Dört önlem:
      enable-logging elenir -> chromedriver Chrome'a günlüğü konsola
        bas demez; asıl gürültü kaynağı budur.
      log-level=3           -> yalnızca FATAL kalır, ERROR/WARNING susar.
      background-networking -> GCM kaydı, güncelleme yoklaması ve
        benzeri arka plan istekleri hiç başlamaz.
      component-update      -> bileşen güncelleyici devre dışı.

    chromedriver'ın KENDİ çıktısı için bir şey yapmaya gerek yok:
    selenium Service'i log_output verilmediğinde zaten DEVNULL'a
    bağlıyor. Gürültünün tamamı Chrome'un kendisinden geliyor, o da
    chromedriver ona --enable-logging geçtiği için konsola yazıyordu -
    yukarıdaki excludeSwitches tam olarak bunu kesiyor.

    Kendi hata mesajlarımızı etkilemez: onlar Python tarafından
    basılıyor, Chrome gerçekten açılamazsa selenium yine istisna atıyor.
    """
    secenekler.add_experimental_option("excludeSwitches", ["enable-logging"])
    secenekler.add_argument("--log-level=3")
    secenekler.add_argument("--disable-background-networking")
    secenekler.add_argument("--disable-component-update")
    return secenekler


def tarayici_baslat():
    """Chrome'u kalıcı profille açar."""
    secenekler = webdriver.ChromeOptions()
    secenekler.add_argument("--user-data-dir=" + str(PROFIL_KLASORU))
    sessizlestir(secenekler)
    # Script normal biterse pencere açık kalsın (hata ayıklayıcı altında
    # çalıştırırken bu garanti değildir, süreç ağacı komple sonlandırılabilir).
    secenekler.add_experimental_option("detach", True)

    try:
        driver = webdriver.Chrome(options=secenekler)
    except WebDriverException as hata:
        # Profil klasörü başka bir Chrome tarafından tutuluyorsa Chrome
        # ya "already in use" der ya da hiç açılmayıp
        # "DevToolsActivePort file doesn't exist" ile çöker. İkincisi
        # sebebi hiç anlatmadığı için ikisini de aynı mesaja bağlıyoruz.
        metin = str(hata)
        kilit_imleri = ("user data directory is already in use",
                        "DevToolsActivePort file doesn't exist",
                        "Chrome failed to start")
        if any(im in metin for im in kilit_imleri):
            raise SystemExit(
                "Chrome açılamadı: profil klasörü büyük ihtimalle önceki\n"
                "çalıştırmadan kalan bir Chrome penceresi tarafından "
                "kullanılıyor.\n"
                "O pencereyi kapatıp tekrar deneyin (kendi Chrome'unuzu "
                "kapatmanıza gerek yok;\nbu script ayrı bir profil "
                "kullanıyor).\n"
                "Profil klasörü: " + str(PROFIL_KLASORU)
            )
        raise

    driver.maximize_window()
    return driver


def popupu_devre_disi_birak(driver):
    """'Destek ve Yardım' popup'ının hiç açılmamasını sağlar.

    Popup gecikmeli açıldığı için "açılırsa kapat" yaklaşımı yarış durumuna
    giriyor. Bunun yerine popup'ın baktığı bayrakları yazıp sayfayı yeniliyoruz;
    böylece bir daha hiç açılmıyor.
    """
    try:
        driver.execute_script(
            "try {"
            "  localStorage.setItem(arguments[0], 'true');"
            "  sessionStorage.setItem(arguments[1], 'true');"
            "} catch (e) {}",
            DESTEK_LOCAL_ANAHTAR,
            DESTEK_SESSION_ANAHTAR,
        )
        driver.refresh()
        WebDriverWait(driver, 20).until(EC.presence_of_element_located(SIFRE_ALANI))
    except WebDriverException:
        pass

    # Emniyet kemeri: bayraklar bir şekilde yazılamadıysa (tarayıcı depolamayı
    # engelliyorsa) popup yine de açılabilir. Kısa süre gözetleyip kapatalım.
    popupu_kapat(driver)


def popupu_kapat(driver, bekleme=2.0):
    """Açıksa popup'ı kapatır, arkada kalan karartma perdesini temizler."""
    bitis = time.time() + bekleme
    kapatildi = False

    while time.time() < bitis:
        try:
            acik = driver.execute_script(
                "var m = document.getElementById(arguments[0]);"
                "return !!(m && m.classList.contains('in'));",
                DESTEK_MODAL_ID,
            )
        except WebDriverException:
            break

        if acik:
            try:
                driver.execute_script(
                    "if (window.jQuery) { jQuery('#' + arguments[0]).modal('hide'); }",
                    DESTEK_MODAL_ID,
                )
            except WebDriverException:
                pass
            kapatildi = True
            time.sleep(0.5)
            break

        time.sleep(0.2)

    # Bootstrap perdeyi kendi temizler ama takılı kalırsa forma tıklanamaz.
    try:
        driver.execute_script(
            "document.querySelectorAll('.modal-backdrop').forEach(function (e) {"
            "  e.parentNode.removeChild(e);"
            "});"
            "document.body.classList.remove('modal-open');"
        )
    except WebDriverException:
        pass

    return kapatildi


def alani_doldur(driver, secici, deger, ad):
    """Alanı doldurur; popup engellerse kapatıp bir kez daha dener."""
    for deneme in (1, 2):
        try:
            alan = driver.find_element(*secici)
            alan.clear()
            alan.send_keys(deger)
            return
        except ElementNotInteractableException:
            if deneme == 1:
                print("  ! " + ad + " alanına yazılamadı, popup kapatılıp tekrar denenecek.")
                popupu_kapat(driver)
                time.sleep(0.5)
            else:
                raise


# =========================================================================
#  Giriş
# =========================================================================
def giris_formu_var_mi(driver):
    """Sayfada hâlâ giriş formu duruyor mu (yani giriş yapılmamış mı)?"""
    try:
        return len(driver.find_elements(*SIFRE_ALANI)) > 0
    except WebDriverException:
        return True  # sayfa yükleniyor olabilir, girdi sayma


def hata_mesaji(driver):
    """Giriş formundaki kırmızı uyarı kutusunun metnini döndürür."""
    try:
        for kutu in driver.find_elements(*HATA_KUTUSU):
            if not kutu.is_displayed():
                continue
            satirlar = [s.strip() for s in kutu.text.splitlines()]
            satirlar = [s for s in satirlar if s and s not in ("×", "Error!")]
            if satirlar:
                return " ".join(satirlar)
    except WebDriverException:
        pass
    return None


def giris_yap(driver, taban, kullanici, sifre):
    """Sicil no ve şifreyi doldurur, güvenlik kodunu kullanıcıdan bekler."""
    adres = taban + "/Home/PerIndex"
    print("Giriş sayfası açılıyor: " + adres)
    driver.get(adres)

    WebDriverWait(driver, 20).until(EC.presence_of_element_located(SIFRE_ALANI))
    popupu_devre_disi_birak(driver)

    alani_doldur(driver, SICIL_ALANI, kullanici, "Sicil no")
    alani_doldur(driver, SIFRE_ALANI, sifre, "Şifre")

    # İmleci güvenlik kodu alanına bırak ki kullanıcı doğrudan yazabilsin
    try:
        driver.find_element(*CAPTCHA_ALANI).click()
    except (NoSuchElementException, ElementNotInteractableException):
        print("  ! Güvenlik kodu alanına odaklanılamadı, elle tıklayın.")

    print("")
    print("=" * 66)
    print("  Sicil no ve şifre dolduruldu.")
    print("  Tarayıcıda GÜVENLİK KODUNU yazıp GİRİŞ'e basın.")
    print("  Giriş tamamlanınca script kendiliğinden devam edecek.")
    print("=" * 66)
    print("")

    return _girisi_bekle(driver)


def _girisi_bekle(driver, saniye=GIRIS_BEKLEME_SURESI):
    """Giriş formu kaybolana kadar bekler. Hata mesajı çıkarsa yazdırır."""
    bitis = time.time() + saniye
    son_hata = None

    while time.time() < bitis:
        if not giris_formu_var_mi(driver):
            # Sayfa geçişi sırasında yanılmamak için bir kez daha doğrula
            time.sleep(1.5)
            if not giris_formu_var_mi(driver):
                return True

        hata = hata_mesaji(driver)
        if hata and hata != son_hata:
            print("  ! OBİS uyarısı: " + hata)
            son_hata = hata

        time.sleep(0.5)

    return False


# =========================================================================
#  Ders Onay sayfası
# =========================================================================
def ders_onay_sayfasina_git(driver, taban, sessiz=False):
    """Ders Onay sayfasını açar ve gerçekten açılıp açılmadığını doğrular."""
    adres = taban + "/DersOnay/Index"
    if not sessiz:
        print("Ders Onay sayfasına gidiliyor: " + adres)
    driver.get(adres)
    time.sleep(1)

    if giris_formu_var_mi(driver):
        return False, "Giriş sayfasına geri düşüldü, oturum açılmamış."

    govde = driver.find_element(By.TAG_NAME, "body").text
    if "404 Page Not Found" in govde or "We looked everywhere" in govde:
        return False, "Sunucu hata sayfası döndü (oturum düşmüş olabilir)."

    return True, "Sayfa açıldı."


def ogrenci_listesini_oku(driver):
    """Ders Onayı sayfasındaki danışman öğrenci tablosunu okur.

    Tablo sütunları: #, Öğrenci No, Adı Soyadı, Seçtiği Ders Sayısı,
    Onay Durumu, (Dersleri Düzenle bağlantısı).
    """
    ogrenciler = []

    satirlar = driver.find_elements(By.CSS_SELECTOR, "#dynamic-table tbody tr")
    for satir in satirlar:
        hucreler = satir.find_elements(By.TAG_NAME, "td")
        if len(hucreler) < 5:
            continue

        ders_sayisi_metni = hucreler[3].text.strip()
        baglanti = None
        for a in satir.find_elements(By.TAG_NAME, "a"):
            adres = a.get_attribute("href") or ""
            if "ogrenciDersOnay" in adres:
                baglanti = adres
                break

        ogrenciler.append({
            "sira": hucreler[0].text.strip(),
            "no": hucreler[1].text.strip(),
            "ad": hucreler[2].text.strip(),
            "ders_sayisi": int(ders_sayisi_metni) if ders_sayisi_metni.isdigit() else 0,
            "durum": hucreler[4].text.strip(),
            "baglanti": baglanti,
        })

    return ogrenciler


def liste_ozeti(ogrenciler):
    """Okunan listeyi konsola özetler."""
    print("")
    print("--- Danışman öğrenci listesi ---")
    print("  Toplam öğrenci : " + str(len(ogrenciler)))

    durumlar = {}
    for o in ogrenciler:
        durumlar[o["durum"]] = durumlar.get(o["durum"], 0) + 1
    for durum, adet in sorted(durumlar.items(), key=lambda x: -x[1]):
        print("  " + durum + " : " + str(adet))

    kayitli = [o for o in ogrenciler if o["ders_sayisi"] > 0]
    if kayitli:
        toplam = sum(o["ders_sayisi"] for o in kayitli)
        en_az = min(kayitli, key=lambda o: o["ders_sayisi"])
        en_cok = max(kayitli, key=lambda o: o["ders_sayisi"])
        print("  Ders seçmiş öğrenci : " + str(len(kayitli)))
        print("  Ortalama ders sayısı: " + str(round(toplam / len(kayitli), 1)))
        print("  En az  : " + en_az["no"] + " -> " + str(en_az["ders_sayisi"]) + " ders")
        print("  En çok : " + en_cok["no"] + " -> " + str(en_cok["ders_sayisi"]) + " ders")


def listeyi_kaydet(ogrenciler):
    """Listeyi CSV olarak çıktı klasörüne yazar (öğrenci verisi, git'e girmez)."""
    CIKTI_KLASORU.mkdir(parents=True, exist_ok=True)
    yol = CIKTI_KLASORU / "danisman_ogrenci_listesi.csv"

    with open(yol, "w", encoding="utf-8-sig", newline="") as dosya:
        yazici = csv.writer(dosya, delimiter=";")
        yazici.writerow(["Sıra", "Öğrenci No", "Adı Soyadı", "Ders Sayısı", "Onay Durumu"])
        for o in ogrenciler:
            yazici.writerow([o["sira"], o["no"], o["ad"], o["ders_sayisi"], o["durum"]])

    print("  Liste kaydedildi: " + str(yol))
    return yol


# =========================================================================
#  Öğrencinin ders kayıt sayfası
# =========================================================================
def _sayiya_cevir(metin):
    """'2,8' -> 2.8 ; '16 (ilk: 16 ...)' -> 16.0 ; boşsa None."""
    if not metin:
        return None
    eslesme = re.search(r"-?\d+(?:[.,]\d+)?", metin)
    if not eslesme:
        return None
    return float(eslesme.group().replace(",", "."))


def ogrenci_sayfasini_ac(driver, taban, ogrno):
    """Öğrencinin ders kayıt sayfasını açar.

    DİKKAT: OBİS bu sayfa açılınca öğrenciyi kilitler. Başka bir öğrenciye
    geçmeden önce kilidi_kaldir() çağrılmalıdır.
    """
    driver.get(taban + "/DersOnay/ogrenciDersOnay?ogrno=" + str(ogrno))
    time.sleep(1)

    if giris_formu_var_mi(driver):
        raise SystemExit("Oturum düştü, öğrenci sayfası açılamadı: " + str(ogrno))

    return driver.page_source


def kilidi_kaldir(driver):
    """Açık öğrencinin kilidini kaldırır, sonraki öğrenciye geçilebilsin diye."""
    try:
        buton = driver.find_element(
            By.CSS_SELECTOR, "form[action='/DersOnay/KilidiKaldir'] button[type='submit']"
        )
        driver.execute_script("arguments[0].click();", buton)
        time.sleep(1)
        return True
    except (NoSuchElementException, WebDriverException):
        return False


# Üst bilgi tablosundaki etiketlerin iç adlarımıza karşılığı
UST_BILGI_ESLESMESI = {
    "Öğrenci No": "no",
    "Adı": "ad",
    "Genel Ort": "genel_ort",
    "Genel Krd": "genel_kredi",
    "Son Dönem Ort": "son_donem_ort",
    "Son Dönem Krd": "son_donem_kredi",
    "Seçilen Ders Sayısı": "ders_sayisi",
    "Seçilen Toplam AKTS": "toplam_akts",
    "Maks. Kredi": "maks_akts",
}


def ders_kaydini_coz(sayfa_kaynagi):
    """Ders kayıt sayfasını yapısal bir sözlüğe çevirir."""
    corba = BeautifulSoup(sayfa_kaynagi, "html.parser")
    kayit = {"katalog": [], "secili_dersler": []}

    # --- Üst bilgi tablosu (ortalama, kredi, AKTS, maks. kredi) ---
    ham = {}
    ust = corba.select_one("div.row.table-responsive table")
    if ust:
        for satir in ust.select("tr"):
            hucreler = [td.get_text(" ", strip=True) for td in satir.select("td")]
            for i in range(0, len(hucreler) - 1, 2):
                etiket = hucreler[i].replace(":", "").strip()
                ham[etiket] = hucreler[i + 1]

    for etiket, ad in UST_BILGI_ESLESMESI.items():
        deger = ham.get(etiket)
        kayit[ad] = deger if ad in ("no", "ad") else _sayiya_cevir(deger)

    # "16 (ilk: 16 - tekrar: 0)" ayrıntısı
    toplam_metni = ham.get("Seçilen Toplam AKTS", "")
    ilk = re.search(r"ilk\s*:\s*(\d+)", toplam_metni)
    tekrar = re.search(r"tekrar\s*:\s*(\d+)", toplam_metni)
    kayit["ilk_akts"] = int(ilk.group(1)) if ilk else None
    kayit["tekrar_akts"] = int(tekrar.group(1)) if tekrar else None

    # --- Onay durumu ---
    basliklar = [h.get_text(strip=True) for h in corba.select("div.col-sm-4.text-center h1")]
    kayit["durum"] = basliklar[0] if basliklar else None

    # --- Ders kataloğu (iki sekme: bölüm dersleri + yabancı dilde seçmeli) ---
    for sekme_id, sekme_adi in (("home4", "Bölüm Dersleri"),
                                ("dropdown14", "Yabancı Dilde Seçmeli")):
        tablo = corba.select_one("#" + sekme_id + " table")
        if not tablo:
            continue

        donem_adi = None
        for bolum in tablo.find_all(["thead", "tbody"], recursive=False):
            if bolum.name == "thead":
                sutunlar = [th.get_text(strip=True) for th in bolum.select("th")]
                donem_adi = sutunlar[1] if len(sutunlar) > 1 else None
                continue

            for satir in bolum.select("tr"):
                hucreler = satir.select("td")
                if len(hucreler) < 7:
                    continue

                ekle = satir.select_one("a[href*=dersiEkle]")
                cikar = satir.select_one("a[href*=dersiCikar]")
                stil = satir.get("style") or ""
                secim_metni = hucreler[6].get_text(" ", strip=True)

                ders_tipi = None
                if ekle:
                    tip = re.search(r"derstipi=(\d+)", ekle.get("href", ""))
                    ders_tipi = int(tip.group(1)) if tip else None

                # Yaygın seçmeli sekmesinde ders adının altına <br> ile
                # dersi veren birim yazılıyor:
                #     "AUFSATZ I <br>EDEBİYAT FAKÜLTESİ"
                # İkisini ayırıyoruz; birim adı ders adına karışırsa hem
                # eşleştirme hem ekran bozuluyor.
                parcalar = [p.strip() for p in
                            hucreler[1].stripped_strings]
                ders_adi = parcalar[0] if parcalar else ""
                birim = " ".join(parcalar[1:]) if len(parcalar) > 1 else None

                kayit["katalog"].append({
                    "sekme": sekme_adi,
                    "donem": donem_adi,
                    "ders_no": hucreler[0].get_text(strip=True),
                    "ders_adi": ders_adi,
                    "birim": birim,
                    "akts": int(_sayiya_cevir(hucreler[2].get_text()) or 0),
                    "ilk_bayrak": bool(hucreler[3].select_one("i.fa-flag")),
                    "dvlt": hucreler[4].get_text(strip=True),
                    "dvst": hucreler[5].get_text(strip=True),
                    "doldu": "Doldu" in secim_metni,
                    "secili": cikar is not None,
                    "eklenebilir": ekle is not None,
                    "ders_tipi": ders_tipi,
                    "ekle_adresi": ekle.get("href") if ekle else None,
                    "cikar_adresi": cikar.get("href") if cikar else None,
                    "yesil_yazi": "5cb85c" in stil,       # anlamını henüz bilmiyoruz
                    "sari_zemin": "FFFFCC" in stil,       # seçili olanlar sarı
                })

    # --- Sağdaki "kaydedilecek dersler" paneli ---
    kaydet_formu = corba.select_one("form[action='/DersOnay/ogrDersleriKaydet']")
    if kaydet_formu:
        for satir in kaydet_formu.select("tbody tr"):
            hucreler = satir.select("td")
            if len(hucreler) < 3:
                continue
            gizli = satir.select_one("input[name^='dersler']")
            kayit["secili_dersler"].append({
                "ders_no": hucreler[0].get_text(strip=True),
                "ders_adi": hucreler[1].get_text(" ", strip=True).split("\n")[0].strip(),
                "aciklama": hucreler[2].get_text(" ", strip=True),
                "form_degeri": gizli.get("value") if gizli else None,
            })

    return kayit


def kaydi_yazdir(kayit):
    """Bir öğrencinin ders kayıt durumunu okunabilir biçimde basar."""
    print("")
    print("=" * 70)
    print("  " + str(kayit.get("no")) + " - " + str(kayit.get("ad")))
    print("  Durum: " + str(kayit.get("durum")))
    print("=" * 70)
    print("  Genel ortalama : " + str(kayit.get("genel_ort")) +
          "   | Genel kredi     : " + str(kayit.get("genel_kredi")))
    print("  Son dönem ort. : " + str(kayit.get("son_donem_ort")) +
          "   | Son dönem kredi : " + str(kayit.get("son_donem_kredi")))
    print("  Seçilen ders   : " + str(kayit.get("ders_sayisi")) +
          "     | Seçilen AKTS    : " + str(kayit.get("toplam_akts")) +
          "  (ilk: " + str(kayit.get("ilk_akts")) +
          ", tekrar: " + str(kayit.get("tekrar_akts")) + ")")
    print("  Maks. AKTS     : " + str(kayit.get("maks_akts")))

    bos = kayit.get("maks_akts")
    alinan = kayit.get("toplam_akts")
    if bos is not None and alinan is not None:
        print("  Kalan kapasite : " + str(bos - alinan) + " AKTS")

    print("")
    print("  --- Seçili dersler (" + str(len(kayit["secili_dersler"])) + ") ---")
    for d in kayit["secili_dersler"]:
        print("    " + d["ders_no"] + "  " + d["ders_adi"][:42].ljust(42) + "  " + d["aciklama"])

    print("")
    print("  --- Katalog özeti ---")
    gruplar = {}
    for d in kayit["katalog"]:
        anahtar = (d["sekme"], d["donem"])
        g = gruplar.setdefault(anahtar, {"toplam": 0, "acik": 0, "doldu": 0, "secili": 0})
        g["toplam"] += 1
        g["acik"] += 1 if d["eklenebilir"] else 0
        g["doldu"] += 1 if d["doldu"] else 0
        g["secili"] += 1 if d["secili"] else 0

    for (sekme, donem), g in gruplar.items():
        print("    %-22s %-22s toplam:%3d  eklenebilir:%3d  doldu:%3d  secili:%2d"
              % (sekme, str(donem), g["toplam"], g["acik"], g["doldu"], g["secili"]))

    acik = [d for d in kayit["katalog"] if d["eklenebilir"] and not d["secili"]]
    bolum = [d for d in acik if d["sekme"] == "Bölüm Dersleri"]
    diger = len(acik) - len(bolum)

    print("")
    print("  --- Eklenebilir bölüm dersleri (" + str(len(bolum)) + ") ---")
    for d in bolum:
        print("    %-8s %-46s AKTS:%2d  %-18s tip:%s"
              % (d["ders_no"], d["ders_adi"][:46], d["akts"], str(d["donem"]), str(d["ders_tipi"])))
    if diger:
        print("    (+ yabancı dilde seçmeli havuzunda " + str(diger) + " ders daha)")

    dolu = [d for d in kayit["katalog"]
            if d["doldu"] and not d["secili"] and d["sekme"] == "Bölüm Dersleri"]
    if dolu:
        print("")
        print("  --- Kontenjanı dolu bölüm dersleri (" + str(len(dolu)) + ") ---")
        for d in dolu:
            print("    %-8s %-46s AKTS:%2d  %s"
                  % (d["ders_no"], d["ders_adi"][:46], d["akts"], str(d["donem"])))


# =========================================================================
#  Transkript (Öğrenci Not Durumu)
# =========================================================================
# Sayfadaki "Öğrenci Not Durumu" butonu şu AJAX çağrısını yapıyor:
#     POST /Personel/OgrenciNot   (gövde: id=<ogrno>)
# Dönen HTML parçası #dersKayitOgrDetay içine basılıyor.
TRANSKRIPT_ADRESI = "/Personel/OgrenciNot"

# Not harfleri artık yonetmelik.py'den geliyor (MADDE 13/2-3). Eski
# scriptlerden devralınan DD/FD/DZ/U/GR/S harfleri yönetmelikte YOK; onlar
# kaldırıldı. Tanımadığımız bir harf çıkarsa rapor ediliyor, sessizce
# "geçti" ya da "kaldı" sayılmıyor.
GECER_NOTLAR = yonetmelik.GECER_NOTLAR
KALIR_NOTLAR = yonetmelik.KALIR_NOTLAR
SONUCSUZ_NOTLAR = yonetmelik.SONUCSUZ_NOTLAR

# Transkript tablosunun gerçek sütun düzeni (/Personel/OgrenciNot çıktısından
# birebir doğrulandı):
#   0 Ders Kodu | 1 Yıl | 2 Ders Adı | 3 AKTS |
#   4 Ara Sınav 1 | 5 Ara Sınav 2 | 6 Genel Sınav | 7 Bütünleme | 8 Harf
VARSAYILAN_SUTUNLAR = {
    "kod": 0, "yil": 1, "ad": 2, "akts": 3,
    "vize1": 4, "vize2": 5, "final": 6, "but": 7, "harf": 8,
}
ZORUNLU_SUTUNLAR = ("kod", "yil", "ad", "akts", "harf")

# OBİS, bir dersin ARTIK SAYILMAYAN (sonradan tekrar alınmış) denemesini
# satırı kırmızıya boyayarak işaretliyor:
#     <tr style="color:red;font-weight:bolder">
# Güncel durumu belirlerken bu işareti esas alıyoruz; yıl yalnızca yedek ölçüt.
GECERSIZ_SATIR_IMI = "color:red"

# Transkript başındaki özet kutusunun etiketleri (Türkçe karakterler
# sadeleştirilmiş hâlleriyle eşleştiriliyor).
BILGI_ETIKETLERI = {
    "OGRENCI NO": "no",
    "ADI SOYADI": "ad_soyad",
    "AKADEMIK ORTALAMA": "gno",
    "TOPLAM AKTS": "toplam_akts",
    "SON DONEM ORTALAMASI": "son_donem_ort",
    "SON DONEM AKTS TOPLAMI": "son_donem_akts",
}

_TURKCE_ESLER = {
    "ç": "c", "Ç": "C", "ğ": "g", "Ğ": "G", "ı": "i", "İ": "i",
    "ö": "o", "Ö": "O", "ş": "s", "Ş": "S", "ü": "u", "Ü": "U",
}


def _sadelestir(metin):
    """Türkçe karakterleri sadeleştirip büyütür: 'Ders Adı' -> 'DERS ADI'.

    Python'da 'i'.upper() 'I' verdiği için Türkçe metinlerde doğrudan upper()
    ile karşılaştırma güvenilir değil; bu yüzden harfleri önce eşliyoruz.
    """
    duz = "".join(_TURKCE_ESLER.get(h, h) for h in (metin or ""))
    return re.sub(r"[^A-Z0-9]+", " ", duz.upper()).strip()


def _metin(dugum):
    return dugum.get_text(" ", strip=True) if dugum is not None else ""


def _ondalik(metin):
    """'2,8' -> 2.8"""
    esleme = re.search(r"-?\d+(?:[.,]\d+)?", metin or "")
    if not esleme:
        return None
    try:
        return float(esleme.group(0).replace(",", "."))
    except ValueError:
        return None


def _tamsayi(metin):
    esleme = re.search(r"\d+", metin or "")
    return int(esleme.group(0)) if esleme else None


def transkript_getir(driver, ogrno):
    """Transkript HTML parçasını sayfanın kendi oturumuyla çeker.

    'Öğrenci Not Durumu' butonu sayfada şu çağrıyı yapıyor:
        POST /Personel/OgrenciNot   (gövde: id=<ogrno>)
    Dönen parça #dersKayitOgrDetay içine basılıyor. Modalı açıp beklemek
    yerine aynı uç noktayı doğrudan çağırıyoruz.
    """
    driver.set_script_timeout(40)
    return driver.execute_async_script(
        "var ogrno = arguments[0];"
        "var bitir = arguments[arguments.length - 1];"
        "fetch(arguments[1], {"
        "  method: 'POST',"
        "  headers: {'Content-Type': 'application/x-www-form-urlencoded'},"
        "  body: 'id=' + encodeURIComponent(ogrno),"
        "  credentials: 'same-origin'"
        "}).then(function (c) { return c.text(); })"
        " .then(function (m) { bitir(m); })"
        " .catch(function (h) { bitir('__HATA__' + h); });",
        str(ogrno), TRANSKRIPT_ADRESI,
    )


def _ozet_bilgisi(corba):
    """Transkript başındaki öğrenci özet kutusunu okur (2 hücreli satırlar)."""
    bilgi = {}
    for satir in corba.find_all("tr"):
        hucreler = satir.find_all("td", recursive=False)
        if len(hucreler) != 2:
            continue
        anahtar = BILGI_ETIKETLERI.get(_sadelestir(_metin(hucreler[0])))
        if not anahtar:
            continue
        deger = _metin(hucreler[1])
        if anahtar in ("no", "ad_soyad"):
            bilgi[anahtar] = deger
        elif anahtar in ("gno", "son_donem_ort"):
            bilgi[anahtar] = _ondalik(deger)
        else:
            bilgi[anahtar] = _tamsayi(deger)
    return bilgi


def _sutun_haritasi(tablo):
    """Sütun konumlarını başlıklardan bulur, bulamazsa bilinen düzene düşer."""
    basliklar = [_metin(th) for th in tablo.find_all("th")]
    harita = {}
    for sira, baslik in enumerate(basliklar):
        b = _sadelestir(baslik)
        if b in ("DERS KODU", "DERS NO", "KOD"):
            harita.setdefault("kod", sira)
        elif b == "YIL":
            harita.setdefault("yil", sira)
        elif b in ("DERS ADI", "DERSIN ADI"):
            harita.setdefault("ad", sira)
        elif b == "AKTS":
            harita.setdefault("akts", sira)
        elif b in ("HARF", "HARF NOTU", "NOT"):
            harita.setdefault("harf", sira)
        elif b.startswith("ARA SINAV"):
            harita.setdefault("vize2" if "vize1" in harita else "vize1", sira)
        elif b in ("GENEL SINAV", "FINAL"):
            harita.setdefault("final", sira)
        elif b in ("BUTUNLEME", "BUT"):
            harita.setdefault("but", sira)

    if set(ZORUNLU_SUTUNLAR) - set(harita):
        return dict(VARSAYILAN_SUTUNLAR), basliklar, "varsayilan"
    for ad, sira in VARSAYILAN_SUTUNLAR.items():
        harita.setdefault(ad, sira)
    return harita, basliklar, "baslik"


def _tablo_donemi(tablo):
    """Tablonun üstündeki '3. DÖNEM NOTLARI' başlığından dönemi çıkarır."""
    baslik = tablo.find_previous(class_="table-header")
    if baslik is None:
        return None, ""
    metin = _metin(baslik)
    esleme = re.match(r"(\d+)\s+DONEM", _sadelestir(metin))
    return (int(esleme.group(1)) if esleme else None), metin


def _satir_gecersiz_mi(satir, hucreler):
    """OBİS'in kırmızıya boyadığı (artık sayılmayan) deneme mi?"""
    stiller = [satir.get("style") or ""]
    stiller += [h.get("style") or "" for h in hucreler]
    return GECERSIZ_SATIR_IMI in "".join(stiller).replace(" ", "").lower()


def transkripti_coz(parca_html):
    """Transkript parçasını ders denemelerine ve güncel duruma çevirir."""
    sonuc = {
        "ozet": {}, "denemeler": [], "son_durum": {}, "gecilen": [],
        "kalinan": [], "sonucsuz": [], "dc_dersler": [], "muaf": [],
        "eski_sistem_dersleri": [], "tekrar_edilen": [],
        "sartli_kalinan": [],
        "basarisiz_denemeler": [],
        "bilinmeyen_notlar": {}, "tablo_bilgisi": [], "uyarilar": [],
    }

    if not parca_html or str(parca_html).startswith("__HATA__"):
        sonuc["hata"] = parca_html or "boş yanıt"
        return sonuc

    corba = BeautifulSoup(parca_html, "html.parser")
    sonuc["ozet"] = _ozet_bilgisi(corba)

    sayac = 0
    for sira, tablo in enumerate(corba.find_all("table")):
        harita, basliklar, yontem = _sutun_haritasi(tablo)
        gereken = max(harita[ad] for ad in ZORUNLU_SUTUNLAR) + 1
        donem, donem_basligi = _tablo_donemi(tablo)
        okunan = 0

        for satir in tablo.find_all("tr"):
            hucreler = satir.find_all("td", recursive=False)
            if len(hucreler) < gereken:
                continue

            kod = _metin(hucreler[harita["kod"]])
            if not re.fullmatch(r"\d{5,9}", kod):
                continue  # ders satırı değil (özet kutusu, ara başlık vb.)

            harf = _sadelestir(_metin(hucreler[harita["harf"]]))
            deneme = {
                "ders_kodu": kod,
                "ders_adi": _metin(hucreler[harita["ad"]]),
                "yil": _tamsayi(_metin(hucreler[harita["yil"]])),
                "akts": _tamsayi(_metin(hucreler[harita["akts"]])) or 0,
                "harf": harf,
                "donem": donem,
                "gecersiz": _satir_gecersiz_mi(satir, hucreler),
                "tablo": sira,
                "sira": sayac,
            }
            for ad in ("vize1", "vize2", "final", "but"):
                yer = harita.get(ad)
                if yer is not None and yer < len(hucreler):
                    deneme[ad] = _metin(hucreler[yer])

            # Geçmişe dönük yönetmelik UYGULANMIYOR: eski dönemler bağıl
            # sistemle değerlendirilmiş olabilir, harf bugünkü eşiklere
            # karşılık gelmeyebilir. Harfi okuyoruz - ve DC'nin (şartlı
            # geçer) tutup tutmadığına OBİS'in kendi işareti karar veriyor.
            # Sonuç satır bazında değil, aşağıda ders bazında belirleniyor;
            # burası yalnızca ilk hâli.
            deneme["sonuc"] = yonetmelik.transkript_harf_durumu(harf)
            deneme["eski_sistem"] = harf in yonetmelik.ESKI_SISTEM_NOTLARI
            if deneme["sonuc"] == "bilinmiyor":
                sonuc["bilinmeyen_notlar"][harf] = \
                    sonuc["bilinmeyen_notlar"].get(harf, 0) + 1

            sonuc["denemeler"].append(deneme)
            sayac += 1
            okunan += 1

        if okunan:
            sonuc["tablo_bilgisi"].append({
                "tablo": sira, "donem": donem, "baslik": donem_basligi,
                "satir": okunan, "yontem": yontem, "basliklar": basliklar,
            })

    # --- Aynı ders birden çok kez alınmış olabilir --------------------------
    # Güncel durumu OBİS'in kırmızıya boyamadığı (yani saydığı) deneme belirler;
    # işaret yoksa en son yıla düşülür.
    gruplar = {}
    for deneme in sonuc["denemeler"]:
        gruplar.setdefault(deneme["ders_kodu"], []).append(deneme)

    # OBİS'in kırmızı işareti bu transkriptte kullanılıyor mu? Hiç kırmızı
    # satır yoksa (hiç kalmamış öğrenci) işaret yok demektir, harfe düşülür.
    isaret_var = any(d["gecersiz"] for d in sonuc["denemeler"])
    sonuc["obis_isareti"] = isaret_var

    for kod, denemeler in gruplar.items():
        gecerliler = [d for d in denemeler if not d["gecersiz"]]
        adaylar = sorted(gecerliler or denemeler,
                         key=lambda d: (d["yil"] or 0, d["sira"]))
        secilen = adaylar[-1]
        # Satırın sonucu: işaret varsa OBİS'in kararı esas.
        for d in denemeler:
            d["sonuc"] = yonetmelik.transkript_deneme_durumu(
                d["harf"], (not d["gecersiz"]) if isaret_var else None)
        sonuc["son_durum"][kod] = secilen

        if len(denemeler) > 1:
            sonuc["tekrar_edilen"].append({
                "ders_kodu": kod, "ders_adi": secilen["ders_adi"],
                "deneme_sayisi": len(denemeler),
                "yillar": [d["yil"] for d in denemeler],
                "harfler": [d["harf"] for d in denemeler],
                "aktsler": [d["akts"] for d in denemeler],
                "guncel": secilen,
            })
        if len(gecerliler) > 1:
            sonuc["uyarilar"].append(
                kod + ": " + str(len(gecerliler)) +
                " deneme de geçerli görünüyor, en son yıl esas alındı.")
        if not gecerliler:
            sonuc["uyarilar"].append(
                kod + ": tüm denemeler geçersiz işaretli, en son yıl alındı.")

    for deneme in sonuc["son_durum"].values():
        durum = deneme["sonuc"]
        if durum in ("gecti", "muaf", "kredisiz_gecti"):
            sonuc["gecilen"].append(deneme)
            if durum == "muaf":
                sonuc["muaf"].append(deneme)
        elif durum in yonetmelik.BASARISIZ_SONUCLAR:
            sonuc["kalinan"].append(deneme)
            if durum == "sartli_kaldi":
                sonuc.setdefault("sartli_kalinan", []).append(deneme)
        elif durum == "sonucsuz":
            sonuc["sonucsuz"].append(deneme)

        # DC şartlı geçerdir; sayılıp sayılmadığına OBİS'in satır işareti
        # karar verir. Sayılanları da danışman görsün diye listeliyoruz.
        # Bağıl sistemden gelen harfler de işaretleniyor.
        if deneme["harf"] == "DC":
            sonuc["dc_dersler"].append(deneme)
        if deneme.get("eski_sistem"):
            sonuc["eski_sistem_dersleri"].append(deneme)

    # Geçmişteki başarısızlıklar (sonradan geçilmiş olsa bile).
    sonuc["basarisiz_denemeler"] = sorted(
        (d for d in sonuc["denemeler"]
         if yonetmelik.tekrar_gerekir_mi(d["sonuc"])),
        key=lambda d: (-(d["yil"] or 0), d["ders_kodu"]))

    sonuc["kalinan"].sort(key=lambda d: (-(d["yil"] or 0), d["ders_kodu"]))
    sonuc["gecilen"].sort(key=lambda d: (d["donem"] or 0, d["ders_kodu"]))
    sonuc["tekrar_edilen"].sort(key=lambda k: k["ders_kodu"])

    sonuc["gecilen_akts"] = sum(d["akts"] for d in sonuc["gecilen"])
    sonuc["kalinan_akts"] = sum(d["akts"] for d in sonuc["kalinan"])
    sonuc["son_kalma_yili"] = max(
        (d["yil"] for d in sonuc["kalinan"] if d["yil"] is not None),
        default=None)
    sonuc["son_basarisizlik_yili"] = max(
        (d["yil"] for d in sonuc["basarisiz_denemeler"] if d["yil"] is not None),
        default=None)
    sonuc["son_donem_no"] = max(
        (b["donem"] for b in sonuc["tablo_bilgisi"] if b["donem"]), default=None)

    # Kendini denetleme.
    #
    # OBİS'in "Toplam AKTS" alanı ALINAN AKTS'dir: her ders kodu için SON
    # denemenin AKTS'si, geçti/kaldı ayrımı yapılmadan. 60 transkriptte
    # birebir doğrulandı. GEÇİLEN AKTS ile karşılaştırmak yanlıştı - iki
    # farklı büyüklük olduğu için bir kez bile kalmış her öğrencide
    # "tutmuyor" diyordu (60 öğrencinin 55'i). Aynı büyüklükle
    # karşılaştırınca gerçek bir bütünlük kontrolü oluyor: tutmuyorsa
    # transkriptten satır kaçırmışız demektir.
    sonuc["alinan_akts"] = sum(d["akts"] for d in sonuc["son_durum"].values())
    obis_akts = sonuc["ozet"].get("toplam_akts")
    if obis_akts is not None:
        sonuc["akts_dogrulama"] = (obis_akts == sonuc["alinan_akts"])
        if not sonuc["akts_dogrulama"]:
            sonuc["uyarilar"].append(
                "Alınan AKTS " + str(sonuc["alinan_akts"]) +
                " hesaplandı ama OBİS 'Toplam AKTS: " + str(obis_akts) +
                "' diyor - transkriptten satır kaçırmış olabiliriz.")

    # GANO da bağımsız bir hakem: son denemeler üzerinden DC=1,50 ile
    # hesaplanan ortalama OBİS'in yazdığıyla tutmalı (60/60 doğrulandı).
    obis_gano = sonuc["ozet"].get("gno")
    if obis_gano is not None and sonuc["alinan_akts"]:
        puan = sum(d["akts"] * yonetmelik.NOT_KATSAYILARI.get(d["harf"], 0.0)
                   for d in sonuc["son_durum"].values())
        hesap = round(puan / sonuc["alinan_akts"], 2)
        sonuc["gano_dogrulama"] = abs(hesap - float(obis_gano)) <= 0.005
        if not sonuc["gano_dogrulama"]:
            sonuc["uyarilar"].append(
                "GANO " + str(hesap) + " hesaplandı ama OBİS " +
                str(obis_gano) + " diyor - harf ya da AKTS okuması şüpheli.")
    return sonuc


def transkripti_yazdir(t):
    """Transkript özetini basar."""
    print("")
    print("  --- Transkript ---")

    if t.get("hata"):
        print("    ! Alınamadı: " + str(t["hata"])[:120])
        return

    ozet = t.get("ozet") or {}
    if ozet:
        print("    OBİS özeti       : GNO %s | toplam %s AKTS | "
              "son dönem ort %s / %s AKTS"
              % (ozet.get("gno"), ozet.get("toplam_akts"),
                 ozet.get("son_donem_ort"), ozet.get("son_donem_akts")))

    donemler = [str(b["donem"]) for b in t["tablo_bilgisi"] if b["donem"]]
    print("    Okunan dönem     : " + (", ".join(donemler) or "-") +
          "  (" + str(len(t["tablo_bilgisi"])) + " tablo)")
    for bilgi in t["tablo_bilgisi"]:
        if bilgi["yontem"] != "baslik":
            print("      ! tablo %d başlıktan okunamadı, varsayılan sütun düzeni"
                  % bilgi["tablo"])

    print("    Toplam deneme    : " + str(len(t["denemeler"])) +
          "  |  Farklı ders: " + str(len(t["son_durum"])))
    dogrulama = t.get("akts_dogrulama")
    isaret = ""
    if dogrulama is True:
        isaret = "   (OBİS toplamıyla uyuşuyor)"
    elif dogrulama is False:
        isaret = "   (! OBİS toplamıyla uyuşmuyor)"
    print("    Geçilen          : " + str(len(t["gecilen"])) +
          " ders, " + str(t["gecilen_akts"]) + " AKTS" + isaret)
    print("    Alttan (güncel)  : " + str(len(t["kalinan"])) +
          " ders, " + str(t["kalinan_akts"]) + " AKTS")
    if t["dc_dersler"]:
        print("    DC ile geçilen   : " + str(len(t["dc_dersler"])) +
              " ders, " + str(sum(d["akts"] for d in t["dc_dersler"])) + " AKTS")
    if t["eski_sistem_dersleri"]:
        print("    Bağıl sistem notu: " + str(len(t["eski_sistem_dersleri"])) +
              " ders (DD/FD)")
    if t["muaf"]:
        print("    Muaf (M)         : " + str(len(t["muaf"])) + " ders")
    if t["sonucsuz"]:
        print("    Sonuçlanmamış    : " + str(len(t["sonucsuz"])) + " ders")
    print("    Son kalma yılı   : " + str(t["son_kalma_yili"]) +
          "   (geçmişteki son başarısızlık: " +
          str(t["son_basarisizlik_yili"]) + ")")

    if t["kalinan"]:
        print("")
        print("    Güncel alttan dersler (en yeniden eskiye):")
        for d in t["kalinan"]:
            print("      %-8s %-40s AKTS:%2d  yıl:%s  not:%s"
                  % (d["ders_kodu"], d["ders_adi"][:40], d["akts"],
                     str(d["yil"]), d["harf"]))

    if t["sonucsuz"]:
        print("")
        print("    Sonuçlanmamış dersler:")
        for d in t["sonucsuz"]:
            print("      %-8s %-40s AKTS:%2d  yıl:%s"
                  % (d["ders_kodu"], d["ders_adi"][:40], d["akts"],
                     str(d["yil"])))

    if t["dc_dersler"]:
        print("")
        print("    DC ile geçilen dersler (transkriptteki harf esas alındı;")
        print("    geçmiş dönemler bağıl sistemle değerlendirilmiş olabilir):")
        for d in t["dc_dersler"]:
            print("      %-8s %-40s AKTS:%2d  yıl:%s"
                  % (d["ders_kodu"], d["ders_adi"][:40], d["akts"],
                     str(d["yil"])))

    if t["tekrar_edilen"]:
        print("")
        print("    Birden çok kez alınan dersler:")
        for k in t["tekrar_edilen"]:
            gecmis = " -> ".join("%s:%s" % (y, h)
                                 for y, h in zip(k["yillar"], k["harfler"]))
            print("      %-8s %-30s %s  (güncel: %s)"
                  % (k["ders_kodu"], k["ders_adi"][:30], gecmis,
                     k["guncel"]["harf"]))

    if t["basarisiz_denemeler"]:
        print("")
        print("    Başarısızlık geçmişi (sonradan geçilmiş olsa da):")
        for d in t["basarisiz_denemeler"]:
            durum = "sonradan geçilmiş" if d["gecersiz"] else "hâlâ alttan"
            print("      %-8s %-30s yıl:%s  not:%-3s  (%s)"
                  % (d["ders_kodu"], d["ders_adi"][:30], str(d["yil"]),
                     d["harf"], durum))

    if t["bilinmeyen_notlar"]:
        print("")
        print("    ! Tanımadığım not harfleri (geçti/kaldı sayılmadı):")
        for harf, adet in sorted(t["bilinmeyen_notlar"].items(),
                                 key=lambda x: -x[1]):
            print("      '" + harf + "' -> " + str(adet) + " kez")

    if t["uyarilar"]:
        print("")
        print("    ! Uyarılar:")
        for uyari in t["uyarilar"]:
            print("      - " + uyari)


def ogrenciyi_incele(driver, taban, ogrenci, html_kaydet=False):
    """Bir öğrencinin ders kaydını okur ve kilidi mutlaka geri bırakır.

    Bu aşamada SADECE OKUMA yapılır: ders eklenmez, çıkarılmaz, kaydedilmez,
    onaylanmaz, reddedilmez.
    """
    print("")
    print("Açılıyor: " + ogrenci["no"] + " - " + ogrenci["ad"])

    try:
        sayfa = ogrenci_sayfasini_ac(driver, taban, ogrenci["no"])

        kayit = ders_kaydini_coz(sayfa)
        # Bu ogrenciyi OBIS'ten TAM SU AN okuduk. Kismi tazelemede
        # (--ogrenci) satirlar farkli zamanlardan gelecegi icin pano
        # her ogrencinin okunma anini gostermek zorunda.
        kayit["son_tarama"] = datetime.datetime.now().strftime(
            "%d.%m.%Y %H:%M")

        # Transkript, ders kayıt sayfası açıkken aynı oturumla çekilir.
        try:
            transkript_html = transkript_getir(driver, ogrenci["no"])
        except WebDriverException as hata:
            transkript_html = "__HATA__" + str(hata)
        kayit["transkript"] = transkripti_coz(transkript_html)

        if html_kaydet:
            CIKTI_KLASORU.mkdir(parents=True, exist_ok=True)
            yol = CIKTI_KLASORU / ("ders_sayfasi_" + ogrenci["no"] + ".html")
            yol.write_text(sayfa, encoding="utf-8")
            print("  Ders sayfası kaydedildi : " + str(yol))

            yol_t = CIKTI_KLASORU / ("transkript_" + ogrenci["no"] + ".html")
            yol_t.write_text(transkript_html or "", encoding="utf-8")
            print("  Transkript kaydedildi   : " + str(yol_t))

        return kayit

    finally:
        # Kilit bırakılmazsa ne script ne de siz başka öğrenci açabilirsiniz.
        if kilidi_kaldir(driver):
            print("  Kilit bırakıldı.")
        else:
            print("  ! Kilit bırakılamadı, sayfayı elle kontrol edin.")


# =========================================================================
#  Ana akış
# =========================================================================
def acik_tut(driver):
    """Script'i canlı tutar; süreç yaşadığı sürece tarayıcı da yaşar."""
    print("")
    print("Tarayıcı açık. Sonraki aşamada bu oturumu kullanacağız.")
    try:
        input("Bitirmek için ENTER'a basın... ")
    except (EOFError, KeyboardInterrupt):
        print("")


def _arama_anahtari(metin):
    """Türkçe arama için sadeleştirme.

    "I" ve "İ" küçültülünce farklı harflere düşüyor ("ı" / "i"); dört
    i türevini de tek biçime katlıyoruz ki danışman nasıl yazarsa
    yazsın bulsun. (Panodaki _kucult() ile aynı mantık.)
    """
    metin = str(metin or "")
    for harf in "İIıi":
        metin = metin.replace(harf, "i")
    return metin.lower().strip()


def ogrenci_sec(ogrenciler, arama):
    """Listeden TEK öğrenci seçer; numara ya da ad parçasıyla.

    Döner: (secilen, mesaj). Seçilemezse secilen None olur ve mesaj
    nedenini anlatır - hiç eşleşmedi mi, birden fazla mı eşleşti.
    """
    anahtar = _arama_anahtari(arama)
    if not anahtar:
        return None, "Aranacak numara ya da ad verilmedi."

    tam = [o for o in ogrenciler if _arama_anahtari(o.get("no")) == anahtar]
    if len(tam) == 1:
        return tam[0], ""

    eslesen = [o for o in ogrenciler
               if anahtar in _arama_anahtari(o.get("no"))
               or anahtar in _arama_anahtari(o.get("ad"))]
    if not eslesen:
        return None, ("'%s' listenizde bulunamadı. Danışmanı olduğunuz "
                      "%d öğrenci var." % (arama, len(ogrenciler)))
    if len(eslesen) > 1:
        satirlar = "\n".join("    %s  %s" % (o.get("no"), o.get("ad"))
                              for o in eslesen[:12])
        if len(eslesen) > 12:
            satirlar += "\n    ... (%d tane daha)" % (len(eslesen) - 12)
        return None, ("'%s' birden fazla öğrenciyle eşleşti; daha "
                      "belirgin yazın:\n%s" % (arama, satirlar))
    return eslesen[0], ""


def _bayrak_degeri(bayrak):
    """--ogrenci 230000003  ya da  --ogrenci=230000003"""
    for i, parca in enumerate(sys.argv):
        if parca == bayrak:
            return sys.argv[i + 1] if i + 1 < len(sys.argv) else ""
        if parca.startswith(bayrak + "="):
            return parca.split("=", 1)[1]
    return None


def main(hazir_giris=None):
    """hazir_giris: (kullanici, sifre, taban) - baslat.py zaten sormussa
    ikinci kez sormayalim."""
    kullanici, sifre, taban = hazir_giris or ayarlari_oku()
    print("OBİS adresi : " + taban)
    print("Sicil no    : " + kullanici)
    print("Profil      : " + str(PROFIL_KLASORU))
    print("")

    driver = tarayici_baslat()

    # Kalıcı profil sayesinde önceki oturum hâlâ geçerli olabilir; öyleyse
    # güvenlik kodu adımını hiç yaşamayalım.
    if ders_onay_sayfasina_git(driver, taban, sessiz=True)[0]:
        print("Önceki oturum hâlâ geçerli, giriş adımı atlandı.")
    else:
        if not giris_yap(driver, taban, kullanici, sifre):
            print("")
            print("BAŞARISIZ: " + str(GIRIS_BEKLEME_SURESI) + " saniye içinde giriş tamamlanmadı.")
            acik_tut(driver)
            return 1

        print("Giriş başarılı.")
        print("")

        tamam, mesaj = ders_onay_sayfasina_git(driver, taban)
        if not tamam:
            print("")
            print("BAŞARISIZ: " + mesaj)
            acik_tut(driver)
            return 1

    ogrenciler = ogrenci_listesini_oku(driver)
    if not ogrenciler:
        print("")
        print("BAŞARISIZ: Öğrenci tablosu okunamadı (#dynamic-table boş).")
        acik_tut(driver)
        return 1

    liste_ozeti(ogrenciler)
    listeyi_kaydet(ogrenciler)

    hedefler = [o for o in ogrenciler if o["baglanti"]]
    if not hedefler:
        print("")
        print("Ders seçmiş öğrenci yok, incelenecek kayıt bulunamadı.")
        acik_tut(driver)
        return 0

    # --ogrenci: yalnız bir öğrenciyi tazele. Bir öğrencinin kaydını
    # elle değiştirdikten sonra 60 kişiyi yeniden taramaya gerek yok;
    # onun iki ham dosyası yenilenir, pano diskten yeniden kurulur.
    tek_arama = _bayrak_degeri("--ogrenci")
    tek_ogrenci = None
    if tek_arama is not None:
        tek_ogrenci, mesaj = ogrenci_sec(ogrenciler, tek_arama)
        if tek_ogrenci is None:
            print("")
            print(mesaj)
            driver.quit()
            return 1
        if not tek_ogrenci.get("baglanti"):
            print("")
            print("%s - %s ders kaydı yapmamış, incelenecek bir şey yok."
                  % (tek_ogrenci.get("no"), tek_ogrenci.get("ad")))
            driver.quit()
            return 1
        hedefler = [tek_ogrenci]
        print("")
        print("TEK ÖĞRENCİ: %s - %s"
              % (tek_ogrenci.get("no"), tek_ogrenci.get("ad")))
    elif "--tumu" not in sys.argv:
        hedefler = hedefler[:1]
        print("")
        print("Tek öğrenci inceleniyor. Tümü için: python ders_kayit.py --tumu")

    # Tek öğrenci tazelenirken ham sayfa MUTLAKA diske yazılmalı; pano
    # ondan sonra diskteki bütün öğrencilerden yeniden kuruluyor.
    html_kaydet = ("--html" in sys.argv) or (tek_ogrenci is not None)
    pano_modu = "--pano" in sys.argv
    toplananlar = []

    for sira, ogrenci in enumerate(hedefler, 1):
        if pano_modu:
            print("[%d/%d] %s - %s"
                  % (sira, len(hedefler), ogrenci["no"], ogrenci["ad"]))
        try:
            kayit = ogrenciyi_incele(driver, taban, ogrenci,
                                     html_kaydet=html_kaydet)
        except WebDriverException as hata:
            # Bir öğrencide takılırsak diğerlerini de kaybetmeyelim.
            print("  ! Okunamadı: " + str(hata)[:120])
            continue

        if pano_modu:
            toplananlar.append(
                (kayit, ozet.ogrenci_ozeti(
                    kayit, icinde_bulunulan_yil=datetime.date.today().year,
                    program=ders_programi.yukle(),
                    mufredat=mufredat_modulu.yukle())))
        else:
            kaydi_yazdir(kayit)
            if kayit.get("transkript"):
                transkripti_yazdir(kayit["transkript"])

    if tek_ogrenci is not None:
        # Panoyu YALNIZ bu öğrenciden kurarsak diğerlerini kaybederiz.
        # cikti/ altındaki bütün ham sayfalardan yeniden üretiyoruz;
        # tazelenen tek dosya bu öğrencininki oluyor.
        driver.quit()
        print("Tarayıcı kapatıldı (oturum profilde saklı).")
        print("")
        import panoyu_yenile          # döngüsel içe aktarmayı önlemek
        return panoyu_yenile.main()   # için burada, modül başında değil

    if pano_modu and toplananlar:
        # Hedef dönem sabit değil; kohortta hangi dönemler varsa hepsi.
        kontenjan = ozet.kontenjan_planlari([o for _, o in toplananlar])

        # Katalog öğrenciden öğrenciye değişiyor (OBİS herkese kendi
        # alabileceklerini gösteriyor); ders listesi için birleşim alınır.
        katalog = {}
        for kayit_x, _ in toplananlar:
            for d in kayit_x.get("katalog") or []:
                if d.get("sekme") == "Bölüm Dersleri":
                    katalog.setdefault(d["ders_no"], d)

        mfr = mufredat_modulu.yukle()
        degisim = akts_degisimi.hesapla(
            {(k.get("no") or ""): k.get("transkript")
             for k, _ in toplananlar}, mfr, katalog)

        yol = rapor.pano_yaz(toplananlar, CIKTI_KLASORU / "danisman_ozeti.html",
                             danisman=kullanici, kontenjan=kontenjan,
                             program=ders_programi.yukle(),
                             katalog=sorted(katalog.values(),
                                            key=lambda d: d["ders_no"]),
                             akts_degisim=degisim)
        print("")
        print("Pano hazır: " + str(yol))
        _pano_ozeti(toplananlar)

    print("")
    print("HAZIR: " + str(len(hedefler)) + " öğrenci incelendi (salt okuma).")

    if pano_modu:
        # Pano modunda tarayıcıya artık ihtiyaç yok. Açık bırakırsak
        # kalıcı profil klasörü kilitli kalıyor ve bir sonraki çalıştırma
        # "DevToolsActivePort file doesn't exist" ile patlıyor.
        # Oturum çerezleri profil klasöründe diskte durduğu için
        # kapatmakla giriş kaybolmuyor.
        driver.quit()
        print("Tarayıcı kapatıldı (oturum profilde saklı).")
    else:
        acik_tut(driver)
    return 0


def _pano_ozeti(toplananlar):
    """Panoyu açmadan önce terminalde kısa bir genel görünüm."""
    yapilacak = [o for _, o in toplananlar if o["sayim"].get("yapilacak")]
    dikkat = [o for _, o in toplananlar
              if not o["sayim"].get("yapilacak") and o["sayim"].get("dikkat")]
    print("  Müdahale gereken : " + str(len(yapilacak)))
    print("  Kontrol edilecek : " + str(len(dikkat)))
    print("  Temiz            : "
          + str(len(toplananlar) - len(yapilacak) - len(dikkat)))
    for o in sorted(yapilacak,
                    key=lambda x: -x["sayim"].get("yapilacak", 0))[:10]:
        print("    ! %-10s %-28s %d yapılacak"
              % (o["no"], (o["ad"] or "")[:28], o["sayim"]["yapilacak"]))


if __name__ == "__main__":
    raise SystemExit(main())
