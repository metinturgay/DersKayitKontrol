# -*- coding: utf-8 -*-
"""Danışman özetini tek adımda üretir — exe'nin giriş noktası.

Danışmandan yalnız OBİS giriş bilgilerini ister, tüm öğrencileri tarar
ve `cikti/danisman_ozeti.html` dosyasını üretip açar.

    python baslat.py              # ya da: DanismanOzeti.exe

SALT OKUNUR: hiçbir öğrenciye ders eklemez, çıkarmaz, onaylamaz veya
reddetmez. OBİS'e yazdığı tek şey, bir sonraki öğrenciyi görebilmek
için öğrenci kilidini bırakmaktır.
"""
import datetime
import io
import json
import sys
import traceback
import webbrowser

import yollar


def konsolu_utf8_yap():
    """Windows konsolunda Türkçe harfleri düzeltir.

    Varsayılan kod sayfası (cp857/cp1254) UTF-8 metni bozuyor:
    "DANIŞMAN ÖZETİ" ekrana "DANI?MAN ?ZET?" diye düşüyor. Exe'yi çift
    tıklayan danışmanın gördüğü ilk şey bu olmamalı.
    """
    if sys.platform != "win32":
        return
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleOutputCP(65001)
        ctypes.windll.kernel32.SetConsoleCP(65001)
    except Exception:                                      # noqa: BLE001
        pass
    for akis in ("stdout", "stderr"):
        nesne = getattr(sys, akis, None)
        yeniden = getattr(nesne, "reconfigure", None)
        if yeniden is not None:
            try:
                yeniden(encoding="utf-8", errors="replace")
            except Exception:                              # noqa: BLE001
                pass


# Panonun hangi gorunumleri tasidigi. Exe'nin icine bakilamiyor, bu
# yuzden --tani bunu bildiriyor: "bende yeni sekme var mi?"
PANO_SEKMELERI = [
    (u"Yönetici Özeti", "yonetici-dugme"),
    (u"Çakışma Tablosu", "cakisma-dugme"),
    (u"Dersler", "dersler-dugme"),
    (u"Çözülmeli Çakışma", "cozulmeli-dugme"),
    (u"Ders Alanlar", "secim-dugme"),
    (u"AKTS Değişimi", "akts-dugme"),
    (u"Transkript sekmesi", "transkriptGovde"),
    (u"Türkçe arama", "_kucult"),
    (u"Koyu tema", "prefers-color-scheme"),
    # Kohort acigi: 2023 girislinin planinda olmayan dersler yuzunden
    # ulasilamayan AKTS. Panoda bu ibare gecmiyorsa exe bu duzeltmeden
    # ONCEKI surumdur ve mezuniyet AKTS'sini FAZLA gosterir.
    (u"Kohort açığı", u"Plana ulaşılamayan AKTS"),
    (u"İlerleme çubuğu", "ilerlemeCubugu"),
    (u"Yarıyıl şeridi", "yariyilSeridi"),
    (u"Özeti kopyala", "kopyalanacakMetin"),
    (u"Dağılım grafiği", "dagilimlar"),
    (u"Yazdırma biçemi", "@media print"),
    # Pano hangi BÖLÜMÜN kurallarıyla üretildiğini yazmalı: exe bölüme
    # özgüdür, yanlış bölümün exe'si her sayıyı sessizce yanlış hesaplar.
    (u"Bölüm adı", "__BOLUM__"),
]

BASLIK = u"""
======================================================================
  DANIŞMAN ÖZETİ  -  ders kayıt kontrolü
  __BOLUM__
======================================================================
  Bu araç SALT OKUNURDUR. Hiçbir öğrenciye ders eklemez, çıkarmaz,
  onaylamaz ya da reddetmez. Yalnız okur ve bir rapor sayfası üretir.

  Yapacakları:
    1. OBİS'e sizin bilgilerinizle girer
    2. Danışmanı olduğunuz öğrencileri tek tek açar, okur, kilidi bırakır
    3. cikti/danisman_ozeti.html dosyasını üretir ve açar

  Tarama öğrenci sayısına göre birkaç dakika sürebilir.
  Chrome penceresini kapatmayın.
======================================================================
"""


# Bölüm teyidi bir kez sorulur ve buraya yazılır. Çıktı klasörüne
# DEĞİL exe'nin yanına: cikti/ silinebilir bir çalışma klasörü, teyit
# ise kurulumun kendisine ait.
ONAY_DOSYASI = "bolum_onayi.json"


def onay_yolu():
    return yollar.yazilan_kok() / ONAY_DOSYASI


def bolum_teyidi(nerede):
    """İlk çalıştırmada 'bu sizin bölümünüz mü?' diye sorar.

    Neden gerekli
    -------------
    Araç bölüme özgü bir profille çalışır (veri/bolum.json). Bir
    kopyayı ya da exe'yi alan danışmanın elinde BAŞKA bir bölümün
    profili olabilir; program yine çalışır, pano yine dolar ve
    sayıların hepsi o bölümün planına göre hesaplanır. Başlıkta bölüm
    adını yazmak görünürlük sağlar ama kimse başlığı okumaz.

    Bir kez sorulur; cevap exe'nin yanına yazılır. Profil değişirse
    (başka bir bölüm için yeniden yapılandırılırsa) yeniden sorulur.

    Cevap alınamazsa (stdin yok, otomatik çalıştırma) SORU ATLANIR ama
    teyit YAZILMAZ: bir dahaki elle çalıştırmada yine sorar. Otomasyonu
    kilitlememek için böyle.
    """
    yol = onay_yolu()
    try:
        kayit = json.loads(io.open(str(yol), encoding="utf-8").read())
        if kayit.get("bolum") == nerede:
            return True
    except Exception:                     # noqa: BLE001 - dosya yok/bozuk
        pass

    print("")
    print("-" * 70)
    print("  Bu araç şu bölüm için yapılandırılmış:")
    print("")
    print("      %s" % nerede)
    print("")
    print("  Bütün AKTS hesapları, mezuniyet projeksiyonu ve ders")
    print("  kompozisyonu denetimi BU BÖLÜMÜN planına göre yapılır.")
    print("  Başka bir bölümün danışmanıysanız sonuçlar YANLIŞ olur.")
    print("-" * 70)
    try:
        cevap = input("  Bu sizin bölümünüz mü? [e/h] ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print("")
        print("  (cevap alınamadı - bir dahaki çalıştırmada tekrar sorulacak)")
        return True

    if cevap.startswith("e"):
        try:
            io.open(str(yol), "w", encoding="utf-8").write(
                json.dumps({"bolum": nerede,
                            "onay_tarihi": datetime.datetime.now()
                            .strftime("%Y-%m-%d %H:%M")},
                           ensure_ascii=False, indent=1))
            print("  Tamam. Bu soru bir daha sorulmayacak (%s)."
                  % yol.name)
        except OSError as e:
            print("  (teyit kaydedilemedi: %s - her açılışta sorulacak)" % e)
        return True

    print("")
    print("  Durduruldu. Kendi bölümünüz için kurulum yapmalısınız:")
    print("")
    print("      python kurulum.py --belgeler   hangi belgeler gerekli")
    print("      python kurulum.py              kurulum sihirbazı")
    print("")
    print("  Bu bir exe ise kaynak kod sürümünü isteyin: exe, müfredatı")
    print("  ve bölüm profilini İÇİNE gömdüğü için kendi bölümünüz")
    print("  için yeniden derlenmesi gerekir.")
    return False


def bekle(mesaj=u"Kapatmak için ENTER'a basın... "):
    """Exe çift tıklanınca pencere hemen kapanmasın."""
    try:
        input(mesaj)
    except (EOFError, KeyboardInterrupt):
        pass


def tani():
    """OBİS'e hiç girmeden: veri yerinde mi, yazma izni var mı?

    Exe'yi alan kişi bunu çalıştırıp her şeyin yerli yerinde olduğunu
    OBİS'e dokunmadan görebilir.
    """
    import akts_degisimi
    import bolum
    import ders_programi
    import mufredat
    import rapor
    import yonetmelik

    print("Yollar")
    for anahtar, deger in yollar.bilgi().items():
        print("  %-12s %s" % (anahtar, deger))

    print("")
    print("Bölüm profili")
    # Araç artık Matematik'e gömülü değil; hangi bölüm için yapılandığı
    # ilk bakılacak şey. Yanlış profille çalışan bir exe her sayıyı
    # yanlış hesaplar ve bunu hiçbir yerde söylemez.
    try:
        print("  %s" % bolum.tanim())
        plan = bolum.donem_plani()
        print("  plan          : %d yarıyıl, %d AKTS (asgari %s)"
              % (len(plan), sum(plan.values()),
                 yonetmelik.MEZUNIYET_AKTS.get(bolum.program_yili())))
        print("  TOS           : %d ders, %s AKTS"
              % (len(bolum.tos_dersleri()), bolum.tos_akts()))
        se = bolum.sonradan_eklenen_dersler()
        print("  sonradan eklenen: %d ders%s"
              % (len(se), (" (açık %s. yarıyıldan kapatılıyor)"
                           % bolum.acik_kapatma_yariyili()) if se else ""))
        for seviye, mesaj in bolum.denetle():
            print("  [%s] %s" % (seviye, mesaj))
        o = onay_yolu()
        if o.exists():
            try:
                k = json.loads(io.open(str(o), encoding="utf-8").read())
                print("  teyit        : %s tarihinde onaylandı"
                      % k.get("onay_tarihi", "?"))
            except Exception:             # noqa: BLE001
                print("  teyit        : kayıt okunamadı")
        else:
            print("  teyit        : HENÜZ SORULMADI "
                  "(ilk çalıştırmada sorulacak)")
    except SystemExit as e:
        print("  PROFİL OKUNAMADI: %s" % e)

    print("")
    print("Gömülü veri")
    belge = (mufredat.yukle() or {}).get("dersler") or {}
    program = ders_programi.yukle()
    referans = akts_degisimi.referanslari_yukle()
    print("  müfredat      : %d ders" % len(belge))
    print("  ders programı : %s" % ("yüklendi" if program else "YOK"))
    print("  AKTS referansı: %s" % (sorted(referans) or "YOK"))

    print("")
    print("Gömülü pano")
    for ad, imza in PANO_SEKMELERI:
        print("  %-22s %s" % (ad, "var" if imza in rapor.SAYFA else "YOK"))

    print("")
    print("Yazma denemesi")
    try:
        klasor = yollar.cikti()
        klasor.mkdir(parents=True, exist_ok=True)
        deneme = klasor / "_yazma_denemesi.tmp"
        deneme.write_text("ok", encoding="utf-8")
        deneme.unlink()
        print("  %s  -> yazılabiliyor" % klasor)
    except OSError as hata:
        print("  YAZILAMIYOR: %s" % hata)
        print("  Exe'yi yazma izniniz olan bir klasöre taşıyın "
              "(örn. Masaüstü).")
        return 1

    tarayici_sorunu = tarayiciyi_dene()

    eksik = (not belge) or (not program) or tarayici_sorunu
    print("")
    print("SONUÇ: " + ("EKSİK VAR - yukarıya bakın" if eksik
                       else "her şey yerinde, tarama yapılabilir"))
    return 1 if eksik else 0


def chrome_yolu():
    """Chrome'un kurulu olduğu yer (yalnız bilgi amaçlı)."""
    import os
    adaylar = []
    for anahtar in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        kok = os.environ.get(anahtar)
        if kok:
            adaylar.append(os.path.join(
                kok, "Google", "Chrome", "Application", "chrome.exe"))
    for aday in adaylar:
        if os.path.exists(aday):
            return aday
    return None


def tarayiciyi_dene():
    """Chrome gerçekten açılıyor mu? Açıp hemen kapatır.

    Taramanın can alıcı noktası bu: selenium, chromedriver'ı kendisi
    indiriyor (selenium-manager) ve bunun için ilk çalıştırmada
    internet gerekiyor. OBİS'e hiç girmeden burada anlaşılsın.

    Kendi Chrome pencerelerinize dokunmaz: ayrı ve GEÇİCİ bir profil
    klasörü kullanır.
    """
    import shutil
    import tempfile

    print("")
    print("Tarayıcı")
    yol = chrome_yolu()
    print("  Chrome        : %s" % (yol or "bilinen yerlerde bulunamadı"))

    gecici = tempfile.mkdtemp(prefix="dkk_tani_")
    try:
        from selenium import webdriver
        from selenium.common.exceptions import WebDriverException
    except ImportError as hata:                            # noqa: BLE001
        print("  selenium      : YÜKLENEMEDİ (%s)" % hata)
        return True

    secenekler = webdriver.ChromeOptions()
    secenekler.add_argument("--user-data-dir=" + gecici)
    secenekler.add_argument("--headless=new")
    secenekler.add_argument("--no-first-run")
    # Tanı çıktısı da Chrome'un ERROR satırlarıyla dolmasın.
    import ders_kayit as dk
    dk.sessizlestir(secenekler)
    try:
        surucu = webdriver.Chrome(options=secenekler)
    except WebDriverException as hata:
        metin = str(hata).strip().splitlines()[0][:150]
        print("  chromedriver  : BAŞLATILAMADI")
        print("                  %s" % metin)
        print("  -> Chrome kurulu mu? İlk çalıştırmada chromedriver")
        print("     indirildiği için internet bağlantısı gerekir.")
        shutil.rmtree(gecici, ignore_errors=True)
        return True
    except Exception as hata:                              # noqa: BLE001
        print("  chromedriver  : BEKLENMEYEN HATA - %s" % str(hata)[:120])
        shutil.rmtree(gecici, ignore_errors=True)
        return True

    try:
        surucu.get("about:blank")
        surum = (surucu.capabilities or {}).get("browserVersion", "?")
        print("  chromedriver  : çalışıyor (Chrome %s)" % surum)
    finally:
        try:
            surucu.quit()
        except Exception:                                  # noqa: BLE001
            pass
        shutil.rmtree(gecici, ignore_errors=True)
    return False


def tek_ogrenci_sor():
    """Önceki tarama varsa: tümü mü, tek öğrenci mi?

    Bir öğrencinin kaydını elle düzeltip son durumu görmek isteyen
    danışman 60 kişiyi yeniden taramak zorunda kalmasın. Soruyu
    yalnız ÖNCEKİ TARAMA VARSA soruyoruz; ilk çalıştırmada kısmi
    tazelemenin anlamı yok, fazladan soru da olmasın.

    Döner: aranacak numara/ad, ya da tümünü taramak için "".
    """
    try:
        onceki = sorted(yollar.cikti().glob("ders_sayfasi_*.html"))
    except OSError:
        onceki = []
    if not onceki:
        return ""
    if not (sys.stdin and sys.stdin.isatty()):
        return ""

    print("")
    print("Önceki tarama bulundu (%d öğrenci)." % len(onceki))
    print("Bir öğrencinin kaydını değiştirdiyseniz yalnız onu")
    print("tazeleyebilirsiniz - diğerleri diskten korunur.")
    print("")
    try:
        cevap = input("Tek öğrenci için numara/ad yazın, "
                      "TÜMÜ için boş bırakın: ").strip()
    except (EOFError, KeyboardInterrupt):
        return ""
    return cevap


def _saat(zaman):
    return datetime.datetime.fromtimestamp(zaman).strftime("%d.%m.%Y %H:%M")


def pano_tazeligi(pano):
    """Pano, en yeni ham sayfadan SONRA mı üretilmiş?

    Dosyanın var olması bir şey söylemiyor: önceki taramadan kalan eski
    bir pano da oradadır. Tarama ham sayfayı yenileyip panoyu
    yenileyemediyse danışman değişikliğini göremez ama ekranda başarı
    mesajı görür - sessiz ve tehlikeli.

    Döner: (durum, pano_zamani, ham_zamani)
      durum "yok" / "taze" / "eski"
    """
    if not pano.exists():
        return "yok", None, None
    p = pano.stat().st_mtime
    hamlar = list(yollar.cikti().glob("ders_sayfasi_*.html"))
    if not hamlar:
        return "taze", p, None
    h = max(x.stat().st_mtime for x in hamlar)
    # 2 saniyelik pay: pano ham sayfalardan hemen sonra yazılıyor,
    # dosya sistemi zaman çözünürlüğü yüzünden eşitlik kayabiliyor.
    return ("taze" if p + 2 >= h else "eski"), p, h


def main():
    konsolu_utf8_yap()
    if "--tani" in sys.argv:
        return tani()
    # Hangi BÖLÜM için yapılandırıldığını en başta yazıyoruz. Exe bölüme
    # özgüdür: müfredat, ders programı ve bölüm profili içine gömülüdür.
    # Matematik için derlenmiş bir exe Fizik danışmanının elinde her
    # sayıyı yanlış hesaplar ve bunu hiçbir yerde söylemezdi.
    try:
        import bolum
        nerede = bolum.tanim()
    except SystemExit as hata:
        print(str(hata))
        bekle()
        return 1
    print(BASLIK.replace("__BOLUM__", nerede))

    if "--belgeler" in sys.argv:
        import kurulum
        print(kurulum.BELGE_LISTESI)
        bekle()
        return 0

    # İlk çalıştırmada bölümü teyit ettir. Tek soru, tek sefer.
    if not bolum_teyidi(nerede):
        bekle()
        return 1

    # ders_kayit selenium'u da yüklüyor; hata olursa kullanıcı görsün diye
    # başlığın ardından, try içinde alıyoruz.
    import ders_kayit as dk

    try:
        kullanici, sifre, taban = dk.ayarlari_oku()
    except SystemExit as hata:
        print(str(hata))
        bekle()
        return 1

    # ders_kayit.main() argümanlara bakıyor; exe çift tıklanınca argüman
    # gelmiyor, o yüzden tam taramayı burada açıkça istiyoruz.
    if "--ogrenci" not in " ".join(sys.argv):
        kim = tek_ogrenci_sor()
        if kim:
            sys.argv += ["--ogrenci", kim]
    for bayrak in ("--tumu", "--pano", "--html"):
        if bayrak not in sys.argv:
            sys.argv.append(bayrak)

    print("")
    print("Giriş bilgileri alındı, OBİS açılıyor...")
    sonuc = dk.main(hazir_giris=(kullanici, sifre, taban))

    pano = yollar.cikti("danisman_ozeti.html")
    durum, p_zaman, h_zaman = pano_tazeligi(pano)
    print("")
    print("=" * 70)
    if sonuc:
        print("TARAMA TAMAMLANMADI (çıkış kodu %d)." % sonuc)
        print("")

    if durum == "yok":
        print("Pano üretilemedi. Yukarıdaki mesajlara bakın.")
    elif durum == "eski":
        # Eski panoyu AÇMIYORUZ: açmak, hatayı görünmez kılan şeyin ta
        # kendisiydi - danışman sayfayı görüp işin bittiğini sanıyordu.
        print("DİKKAT: PANO GÜNCELLENMEDİ.")
        print("   pano         : " + _saat(p_zaman))
        print("   ham sayfalar : " + _saat(h_zaman) + "  (daha yeni)")
        print("")
        print("   Öğrenci OBİS'ten okundu ama pano yeniden üretilemedi;")
        print("   ekrandaki sayfa bu değişikliği İÇERMİYOR.")
        print("   Açmıyorum. Yukarıdaki hata mesajlarına bakın.")
        if not sonuc:
            sonuc = 1
    else:
        print("Pano hazır:")
        print("   " + str(pano))
        try:
            webbrowser.open(pano.as_uri())
        except Exception:                                  # noqa: BLE001
            print("   (tarayıcıda açılamadı, dosyaya çift tıklayın)")
    print("=" * 70)
    bekle()
    return sonuc


if __name__ == "__main__":
    try:
        kod = main()
    except SystemExit:
        raise
    except BaseException:                                  # noqa: BLE001
        # Exe'de beklenmeyen hata sessizce pencereyi kapatmasın.
        print("")
        print("BEKLENMEYEN HATA - aşağıdaki metni geliştiriciye iletin:")
        print("-" * 70)
        traceback.print_exc()
        print("-" * 70)
        bekle()
        kod = 1
    raise SystemExit(kod)
