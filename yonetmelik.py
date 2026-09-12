# -*- coding: utf-8 -*-
"""Selçuk Üniversitesi Ön Lisans ve Lisans Eğitim-Öğretim ve Sınav Yönetmeliği.

Kaynak: RG 7/5/2023-32183
Değişiklikler: RG 16/7/2023-32250, RG 24/7/2025-32965

Her sabitin ve fonksiyonun yanında dayandığı madde yazılıdır. Bu dosya
yalnızca yönetmelikten çıkan kuralları içerir; bölüme özgü olan her şey
(yarıyıl planı, TOS listesi, dönem kompozisyonu, sonradan eklenen dersler)
veri/bolum.json'dan gelir — bkz. bolum.py. Selenium/OBİS bağımlılığı
yoktur, saf hesaplama yapar.

DİKKAT: Bu modül karar VERMEZ, durum TESPİT EDER. Amaç danışmana özet
çıkarmaktır; ders ekleme/çıkarma/onaylama yapılmaz.
"""
import difflib
import re

import bolum

# =========================================================================
#  MADDE 13/2 - Mutlak değerlendirme sistemi not tablosu
# =========================================================================
# (alt puan, üst puan, başarı notu, AKTS notu, açıklama)
NOT_TABLOSU = [
    (88, 100, "AA", 4.00, "A", "Mükemmel"),
    (80, 87, "BA", 3.50, "B", "Çok İyi"),
    (73, 79, "BB", 3.00, "C", "İyi"),
    (66, 72, "CB", 2.50, "D", "Orta"),
    (60, 65, "CC", 2.00, "E", "Yeterli"),
    (50, 59, "DC", 1.50, "-", "Şartlı Geçer"),
    (0, 49, "FF", 0.00, "FX", "Derste Başarısız"),
    (0, 0, "F", 0.00, "F", "Devamsız Başarısız"),
]
NOT_KATSAYILARI = {h: k for _, _, h, k, _, _ in NOT_TABLOSU}

# MADDE 13/3 - harf notlarının anlamları
GECER_NOTLAR = {"AA", "BA", "BB", "CB", "CC"}      # 13/3-a
SARTLI_NOTLAR = {"DC"}                              # 13/3-b (YANO'ya bağlı)
KALIR_NOTLAR = {"FF", "F"}                          # 13/3-c ve 13/3-ç
KREDISIZ_GECER = {"G"}                              # 13/3-d
KREDISIZ_KALIR = {"K"}                              # 13/3-e
MUAF_NOTLAR = {"M"}                                 # 13/3-f (derecelendirme dışı)
SONUCSUZ_NOTLAR = {"", "-", "--", "---"}            # henüz not girilmemiş

# Yönetmelikte tanımlı TÜM harfler. Bunun dışında bir harf görürsek
# sessizce sınıflandırmıyoruz, danışmana bildiriyoruz.
TANIMLI_NOTLAR = (GECER_NOTLAR | SARTLI_NOTLAR | KALIR_NOTLAR |
                  KREDISIZ_GECER | KREDISIZ_KALIR | MUAF_NOTLAR)

# MADDE 15/1 - DC alan öğrencinin başarılı sayılabilmesi için ilgili
# yarıyılda YANO'sunun 2,50 olması gerekir. Aksi hâlde dersi tekrar eder.
DC_GECER_YANO_ESIGI = 2.50

# =========================================================================
#  MADDE 9/1-c - Yarıyıl AKTS üst sınırı
# =========================================================================
# GANO < 1,50  -> alttan dersler dâhil, açılan AKTS kadar (30)
# GANO >= 1,50 -> alttan dersler dâhil, %50 fazlası (45)
# Son sınıf öğrencilerine kredi sınırlaması UYGULANMAZ.
GANO_ESIGI = 1.50
YARIYIL_ACILAN_AKTS = 30
AKTS_LIMITI_DUSUK_GANO = 30
AKTS_LIMITI_NORMAL = 45

# MADDE 9/1-ç - Üst yarıyıldan ders alma
UST_YARIYIL_GANO_ESIGI = 3.00
UST_YARIYIL_ORANI = 0.20        # bulunduğu yarıyıl AKTS'sinin %20'si

# MADDE 9/1-d - Not yükseltme: "BB'den daha düşük not aldığı ders/dersler"
# BB'nin kendisi dâhil DEĞİL. Son alınan not geçerli olur.
# DD bagil sistemden geliyor ve GECER sayiliyor (ESKI_SISTEM_GECER);
# BB'den dusuk oldugu icin MADDE 9/1-d kapsamindadir. Kumede olmadigi
# icin DD ile gecmis dersi not yukseltmek uzere secen ogrenciye
# "VERME - zaten gecmis" deniyordu.
NOT_YUKSELTILEBILIR = {"CB", "CC", "DC", "DD"}

# MADDE 10/1 - Devam zorunluluğu
DEVAM_TEORIK_ORANI = 0.70       # teorik derslerin %30'undan fazlasına devamsızlık
DEVAM_UYGULAMA_ORANI = 0.80     # uygulamaların %20'sinden fazlasına devamsızlık

# MADDE 8/4 - Program başına asgari toplam AKTS
MEZUNIYET_AKTS = {2: 120, 4: 240, 5: 300}
# MADDE 22/1 - Mezuniyet ağırlıklı not ortalaması
MEZUNIYET_AGNO = 2.00
# MADDE 23/2 - Lisanstan ön lisans diploması (ilk 4 yarıyıl)
ONLISANS_DIPLOMA_AKTS = 120

# MADDE 16/1 - Azami öğrenim süreleri (yıl)
AZAMI_SURE = {2: 4, 4: 7, 5: 8}
HAZIRLIK_AZAMI_SURE = 2

# MADDE 11/1-ç - Üç ders sınavı (RG 24/7/2025-32965 ile "üç" oldu)
UC_DERS_SINAVI_AZAMI_DERS = 3
UC_DERS_SINAVI_GECER_NOT = "CC"

# MADDE 3/p - Son sınıf: dört yıllık lisansta 7. yarıyıldan en az 1 ders
# almaya hak kazandığı sınıf.
SON_SINIF_YARIYILI = {2: 3, 4: 7, 5: 9}


# =========================================================================
#  Not değerlendirme
# =========================================================================
def harf_durumu(harf, yano=None):
    """Bir harf notunun sonucunu döndürür.

    MADDE 13/3 ve MADDE 15. DC şartlıdır: YANO bilinmiyorsa 'sartli'
    döner ve karar danışmana bırakılır.

    Dönen değerler: gecti | kaldi | sartli | sartli_gecti | sartli_kaldi |
                    muaf | kredisiz_gecti | kredisiz_kaldi | sonucsuz |
                    bilinmiyor
    """
    h = (harf or "").strip().upper()
    if h in GECER_NOTLAR:
        return "gecti"
    if h in SARTLI_NOTLAR:
        if yano is None:
            return "sartli"
        return "sartli_gecti" if yano >= DC_GECER_YANO_ESIGI else "sartli_kaldi"
    if h in KALIR_NOTLAR:
        return "kaldi"
    if h in MUAF_NOTLAR:
        return "muaf"
    if h in KREDISIZ_GECER:
        return "kredisiz_gecti"
    if h in KREDISIZ_KALIR:
        return "kredisiz_kaldi"
    if h in SONUCSUZ_NOTLAR:
        return "sonucsuz"
    return "bilinmiyor"


# =========================================================================
#  MADDE 15 - Şartlı geçer (DC) ve OBİS'in kendi değerlendirmesi
# =========================================================================
# DC "şartlı geçer"dir: tek başına harfe bakarak geçti/kaldı denemez.
# Şartın sağlanıp sağlanmadığını OBİS transkriptte ZATEN değerlendirmiş ve
# sayılmayan satırları kırmızıya boyamıştır.
#
# KURAL (danışman kararı): kırmızı DC = öğrenci KALMIŞTIR, dersi tekrar
# alacaktır. Yorum yapmıyoruz.
#
# Neden yorum yapmıyoruz: DC'nin geçerliliği eskiden dersin alındığı
# DÖNEMİN ortalamasına bağlıydı, yürürlükteki yönetmelikte GANO'ya bağlı
# (MADDE 15). Bir transkriptte iki dönemin kuralı yan yana duruyor; bu
# yüzden aynı öğrencide bazı DC'ler geçmiş, bazıları kalmış görünüyor
# (bir öğrencide GANO 2,42 iken hem kırmızı hem normal DC var). Hangi satıra
# hangi kuralın uygulandığını biz yeniden türetemeyiz - OBİS türetmiş,
# işaretini okuyoruz.
#
# Gözlemle doğrulandı (60 transkript):
#   - FF ve F satırlarının TAMAMI kırmızı,
#   - kırmızı olmayan satırlarda hiç FF/F yok,
#   - DC satırlarının bir kısmı kırmızı, bir kısmı değil.
def transkript_deneme_durumu(harf, obis_sayiyor=None):
    """Bir transkript satırının sonucu.

    obis_sayiyor:
        True  - OBİS satırı sayıyor (kırmızı değil)  -> harfe göre
        False - OBİS saymıyor (kırmızıya boyanmış)   -> başarısız
        None  - işaret okunamadı                     -> yalnızca harfe göre

    Dönen: gecti | kaldi | sartli_kaldi | muaf | kredisiz_gecti |
           kredisiz_kaldi | sonucsuz | bilinmiyor
    """
    harfe_gore = transkript_harf_durumu(harf)
    if obis_sayiyor is not False:
        return harfe_gore
    # OBİS saymıyor. Harf zaten kalır diyorsa aynen kalsın; geçer diyorsa
    # şartlı geçerdir ve şartı tutmamıştır. Sonuç FF ile aynı: kalmıştır,
    # tekrar alacaktır. Ayrı bir ad taşımasının tek sebebi danışmanın
    # panoda "DC ama sayılmadı" ile "sınavdan kaldı"yı ayırt edebilmesi.
    if harfe_gore in ("kaldi", "kredisiz_kaldi", "sonucsuz", "bilinmiyor"):
        return harfe_gore
    if (harf or "").strip().upper() in SARTLI_NOTLAR:
        return "sartli_kaldi"
    return "kaldi"


# Başarısız sayılan sonuçlar (mezuniyete ve alttan derse esas).
BASARISIZ_SONUCLAR = ("kaldi", "kredisiz_kaldi", "sartli_kaldi")


def deneme_sonucu(deneme):
    """Bir transkript satırının çözülmüş sonucu.

    transkripti_coz() satırı OBİS'in işaretiyle birlikte zaten
    değerlendirmiştir; onu kullanıyoruz. Eski/elle üretilmiş kayıtlarda
    alan yoksa harfe düşülür.
    """
    if isinstance(deneme, dict) and deneme.get("sonuc"):
        return deneme["sonuc"]
    return transkript_harf_durumu((deneme or {}).get("harf"))


def basarili_sayilir_mi(durum):
    """Ders yükünden düşen (tekrar alınması gerekmeyen) durumlar."""
    return durum in ("gecti", "sartli_gecti", "muaf", "kredisiz_gecti")


def tekrar_gerekir_mi(durum):
    """Dersin tekrar alınması gereken durumlar."""
    return durum in ("kaldi", "sartli_kaldi", "kredisiz_kaldi")


def not_yukseltilebilir_mi(harf):
    """MADDE 9/1-d: BB'den daha düşük notlar not yükseltmek için tekrar alınabilir."""
    return (harf or "").strip().upper() in NOT_YUKSELTILEBILIR


# =========================================================================
#  GEÇMİŞ TRANSKRİPT NOTLARI - yönetmelik geriye dönük UYGULANMAZ
# =========================================================================
# Önceki yıllarda bağıl değerlendirme sistemi uygulanmıştı. O dönemlerin
# harf notları bugünkü mutlak sistemin puan aralıklarına ve DC/YANO şartına
# birebir karşılık gelmez. Bu yüzden transkript okurken:
#   - harfi OLDUĞU GİBİ alıyoruz,
#   - DC'yi YANO'ya bakarak yeniden değerlendirmiyoruz (MADDE 15'i geçmişe
#     uygulamıyoruz); OBİS o kararı zaten vermiş, dersi tekrar ettirmişse
#     eski denemeyi kırmızıya boyamış durumda,
#   - bağıl sistemden kalan DD/FD harflerini de tanıyoruz.
# Yönetmelik kuralları YALNIZCA bu dönemki ders seçimine uygulanır.
ESKI_SISTEM_GECER = {"DD"}      # bağıl sistemde şartlı geçer
ESKI_SISTEM_KALIR = {"FD"}      # bağıl sistemde başarısız
ESKI_SISTEM_NOTLARI = ESKI_SISTEM_GECER | ESKI_SISTEM_KALIR

TRANSKRIPT_GECER = GECER_NOTLAR | SARTLI_NOTLAR | ESKI_SISTEM_GECER
TRANSKRIPT_KALIR = KALIR_NOTLAR | ESKI_SISTEM_KALIR


def devam_saglanmis_mi(harf):
    """MADDE 10/1-2: Öğrenci bu denemede devam şartını sağlamış mı?

    Devamsızlık F notunu doğurur (13/3-ç: devamsızlık veya uygulamalardan
    başarısızlık nedeniyle final/bütünlemeye girme hakkı yok). Dolayısıyla
    F dışındaki her harf, öğrencinin derse devam ettiğini gösterir.

    Bu bilgi tekrar alınan derslerde önemli: devam şartı bir kez sağlanmışsa
    yeniden aranmaz (MADDE 10/2).
    """
    h = (harf or "").strip().upper()
    if not h or h in SONUCSUZ_NOTLAR:
        return None                 # bilinmiyor
    return h not in ("F", "DZ")     # DZ: eski sistemde devamsız


def devamsizlik_hakki(saat_sayisi, uygulama=False):
    """MADDE 10/1-2: Bu derste kaç saat devamsızlık yapılabilir?

    Teorik derslerin en az %70'ine, uygulamaların en az %80'ine devam
    zorunlu. Kalanı öğrencinin devamsızlık hakkıdır.

    Haftalık saat üzerinden oran döner (dönem boyunca aynı orandır).
    """
    oran = (1 - DEVAM_UYGULAMA_ORANI) if uygulama else (1 - DEVAM_TEORIK_ORANI)
    return (saat_sayisi or 0) * oran


def cakisma_devamsizliga_sigar_mi(a_saat, b_saat, ortak_saat,
                                  a_uygulama=False, b_uygulama=False):
    """İki dersin çakışması devamsızlık hakkının içinde kalıyor mu?

    Öğrenci çakışan her saatte derslerden BİRİNE girer, diğerine giremez.
    Kaçırdığı saatler devamsızlık hakkından düşer. Çakışan `ortak_saat`
    saatin x kadarını A dersinden, kalanını B dersinden kaçırırsa:

        x <= A hakkı  ve  (ortak - x) <= B hakkı

    Böyle bir x varsa çakışma iki dersin devamsızlık hakkına SIĞAR:

        ortak_saat <= A hakkı + B hakkı

    Ayrıca "birini tam takip etme" durumu ayrıca raporlanır: öğrenci A'ya
    hiç girmezse tüm kayıp B'den değil A'dan gider; tek derse yığmak
    mümkünse danışman bunu bilmeli.

    DİKKAT: sığması, harcanması gerektiği anlamına gelmez. Hakkın tamamı
    programa harcanırsa hastalık/mazeret için pay kalmaz. Bu yüzden karar
    danışmanındır; biz yalnızca sığıp sığmadığını söylüyoruz.
    """
    a_hak = devamsizlik_hakki(a_saat, a_uygulama)
    b_hak = devamsizlik_hakki(b_saat, b_uygulama)
    ortak = ortak_saat or 0
    sigar = ortak <= a_hak + b_hak + 1e-9
    # Tek tarafa yığmak: A'ya hiç girmemek (kayıp tamamen A'dan) ya da
    # B'ye hiç girmemek.
    yalniz_a = ortak <= a_hak + 1e-9      # A'dan kaçır, B'ye tam devam
    yalniz_b = ortak <= b_hak + 1e-9      # B'den kaçır, A'ya tam devam
    return {
        "sigar": sigar,
        "tek_derse_yigilabilir": yalniz_a or yalniz_b,
        "a_hak": round(a_hak, 2), "b_hak": round(b_hak, 2),
        "ortak_saat": ortak,
        "a_saat": a_saat, "b_saat": b_saat,
        # Tümü tek dersten karşılanırsa o dersin devamsızlık oranı
        "a_oran": round(ortak / a_saat, 2) if a_saat else None,
        "b_oran": round(ortak / b_saat, 2) if b_saat else None,
        "kalan_pay": round(a_hak + b_hak - ortak, 2),
    }


# OBİS'in ders kayıt sayfasındaki devam sütunları
#   DVLT = devamlı tekrar   -> devam şartı sağlanmış, tekrar devam gerekmez
#   DVST = devamsız tekrar  -> devam şartı sağlanmamış, devam zorunlu
DEVAM_SUTUNLARI = {"dvlt": "devamlı tekrar", "dvst": "devamsız tekrar"}


def transkript_harf_durumu(harf):
    """Transkriptteki harfi YALNIZCA harfe bakarak sınıflandırır.

    harf_durumu()'nun aksine YANO'ya bakmaz, yönetmeliği geriye dönük
    uygulamaz. Geçmiş dönemler bağıl sistemle değerlendirilmiş olabilir.

    Dönen: gecti | kaldi | muaf | kredisiz_gecti | kredisiz_kaldi |
           sonucsuz | bilinmiyor
    """
    h = (harf or "").strip().upper()
    if h in TRANSKRIPT_GECER:
        return "gecti"
    if h in TRANSKRIPT_KALIR:
        return "kaldi"
    if h in MUAF_NOTLAR:
        return "muaf"
    if h in KREDISIZ_GECER:
        return "kredisiz_gecti"
    if h in KREDISIZ_KALIR:
        return "kredisiz_kaldi"
    if h in SONUCSUZ_NOTLAR:
        return "sonucsuz"
    return "bilinmiyor"


# =========================================================================
#  Kredi sınırları
# =========================================================================
def azami_akts(gano, son_sinif=False, acilan_akts=YARIYIL_ACILAN_AKTS):
    """MADDE 9/1-c: Bir yarıyılda alınabilecek azami AKTS.

    Alttan alınan derslerin kredileri bu sınıra DÂHİLDİR.
    Son sınıf öğrencisine sınırlama uygulanmaz (None döner).
    """
    if son_sinif:
        return None
    if gano is None:
        return None
    if gano < GANO_ESIGI:
        return acilan_akts
    return int(round(acilan_akts * 1.5))


def ust_yariyil_akts_hakki(gano, tum_dersler_basarili,
                           yariyil_akts=YARIYIL_ACILAN_AKTS):
    """MADDE 9/1-ç: Üst yarıyıldan alınabilecek azami AKTS.

    Şartlar: danışmanın olumlu görüşü + o güne kadar aldığı TÜM derslerden
    başarılı olmak + GANO >= 3,00. Lisansta en erken 2. yarıyıl sonunda.
    Hakkı yoksa 0 döner.
    """
    if not tum_dersler_basarili:
        return 0
    if gano is None or gano < UST_YARIYIL_GANO_ESIGI:
        return 0
    return int(yariyil_akts * UST_YARIYIL_ORANI)


def ust_yariyil_degerlendir(gano, kalinan_ders_sayisi, gecen_yariyil_sayisi,
                            yariyil_akts=YARIYIL_ACILAN_AKTS):
    """MADDE 9/1-ç şartlarını tek tek denetler ve gerekçe döndürür.

    Bu, son sınıf olmayan öğrencinin üst dönemden ders alıp alamayacağını
    belirler. Sınırsız AKTS AÇMAZ; yalnızca %20'lik ek hak verir.
    """
    tum_basarili = (kalinan_ders_sayisi or 0) == 0
    eksikler = []
    if gecen_yariyil_sayisi is not None and gecen_yariyil_sayisi < 2:
        eksikler.append("lisansta en erken 2. yarıyıl sonunda alınabilir")
    if not tum_basarili:
        eksikler.append("%d dersten başarısız (tüm derslerden başarılı olmalı)"
                        % kalinan_ders_sayisi)
    if gano is None:
        eksikler.append("GANO bilinmiyor")
    elif gano < UST_YARIYIL_GANO_ESIGI:
        eksikler.append("GANO %.2f < %.2f" % (gano, UST_YARIYIL_GANO_ESIGI))

    # Formul TEK YERDE dursun: ust_yariyil_akts_hakki() ile ayni hesap
    # iki ayri yerde yazilirsa biri degisip digeri kalabilir.
    hak = 0 if eksikler else ust_yariyil_akts_hakki(
        gano, tum_basarili, yariyil_akts)
    return {
        "hak_akts": hak,
        "uygun": not eksikler,
        "eksikler": eksikler,
        "sebep": ("Üst dönemden en fazla %d AKTS alabilir (danışman olumlu "
                  "görüş verirse)." % hak) if hak else
                 ("Üst dönemden ders alamaz: " + "; ".join(eksikler) + "."),
    }


# =========================================================================
#  Öğrencinin sınıfı ve hedef dönemi
# =========================================================================
# İşletilen tanım (danışman kararı):
#   Öğrenci EN SON hangi dönemden ders aldıysa (geçmiş/kalmış fark etmez)
#   sınıfı odur; yeni dönemde bir üst dönemin derslerini alır.
#     hiç 3. dönemden ders almamış -> 1. sınıf -> bu dönem 3. dönem dersleri
#     hiç 5. dönemden ders almamış -> 2. sınıf -> bu dönem 5. dönem dersleri
#     5. dönemden ders almış        -> 3. sınıf -> bu dönem 7. dönem dersleri
#
# Güz yarıyılında tek numaralı (1,3,5,7), baharda çift numaralı dönemler
# açılır; hesap açılan dönemlerin paritesine göre yapılır.
GUZ_DONEMLERI = (1, 3, 5, 7)
BAHAR_DONEMLERI = (2, 4, 6, 8)


# =========================================================================
#  BÖLÜM PARAMETRELERİ - yönetmelikten gelmez, danışmandan alınır
# =========================================================================
# Buradan aşağısı BÖLÜM KARARIDIR ve bölümden bölüme değişir. Bir zamanlar
# Matematik'in değerleri doğrudan bu dosyaya yazılıydı; başka bir bölümün
# danışmanı aracı açtığında o sayılar sessizce yanlış sonuç üretiyordu.
# Artık hepsi veri/bolum.json'dan geliyor (bkz. bolum.py). Adlar aynı
# kaldı; değişen yalnızca değerin NEREDEN geldiği.
#
# Ders planı örneği (Matematik): 1-6. dönemler 30'ar AKTS; 7. ve 8.
# dönemler TOS ve (*) işaretli derslerle 32'şer. Toplam 244 AKTS,
# yönetmelik asgarisi 240 (MADDE 8/4).
PROGRAM_YILI = bolum.program_yili()
VARSAYILAN_DONEM_PLANI = bolum.donem_plani()


# --- Müfredatın SONRADAN eklediği dersler --------------------------------
# 2024 güncellemesi bazı derslerin AKTS'sini DÜŞÜRÜP düşen payı YENİ
# derslere taşıdı; yarıyıl toplamı yine 30 tutuyor:
#
#   1. yarıyıl  Fizik I 5->4, İngilizce I 3->2   -> Fizik Laboratuvarı I (2)
#   5. yarıyıl  Cebir I 6->5, Dif. Geo I 6->5,
#               Sayılar Teorisi I 4->3            -> Uygulamalı Matematik I (3)
#   (6. yarıyılda aynı üçlünün II'leri -> Uygulamalı Matematik II)
#
# Bu YENİ dersler daha önce girmiş öğrencilerin planında yok; bölüm kararı
# geriye dönük aldırmamak. Sonuç: eski ders kümesini tamamlayan öğrenci
# yarıyılı plandan DÜŞÜK kapatıyor ve bu açık yarıyılın kendi içinde
# kapanmıyor. Açığı ACIK_KAPATMA_YARIYILI seçmeli havuzundan FAZLADAN
# ders alarak kapatıyorlar.
#
# Değer = dersin geçerli olduğu EN ERKEN giriş yılı. Bu yıldan önce giren
# öğrenci dersi almaz.
SONRADAN_EKLENEN_DERSLER = bolum.sonradan_eklenen_dersler()

# Açık hangi yarıyılın seçmeli havuzundan kapatılıyor (bölüm kararı).
# 5. yarıyıl seçmelileri güzde açık ve ALT yarıyıl oldukları için üst
# sınıftaki öğrenci de alabiliyor (MADDE 9/1-a).
ACIK_KAPATMA_YARIYILI = bolum.acik_kapatma_yariyili()


def kohort_disi_mi(ders_kodu, giris_yili):
    """Bu ders, bu giriş yılındaki öğrencinin planında var mı?

    giris_yili bilinmiyorsa (None) hiçbir ders elenmez - uydurma muafiyet
    üretmeyiz.
    """
    ilk = SONRADAN_EKLENEN_DERSLER.get(ders_kodu)
    if ilk is None or giris_yili is None:
        return False
    return giris_yili < ilk


def kohort_disi_kodlar(giris_yili):
    """Bu kohortun almayacağı ders kodları."""
    return {k for k in SONRADAN_EKLENEN_DERSLER
            if kohort_disi_mi(k, giris_yili)}


# --- TOS dersleri ---------------------------------------------------------
# Tüm bölümlere açık ortak seçmeliler. Ders adının sonunda (*) ile
# işaretleniyorlar ve katalogda BÖLÜM sekmesinde, çeşitli dönem
# başlıklarının altında dağınık duruyorlar.
# Bir öğrenci bir dönemde EN FAZLA 1 TOS dersi alabilir.
# Hepsi 4 AKTS.
# DİKKAT: Bu derslerin bir kısmı başka fakültelere ait olduğu için
# katalogda hiç görünmeyebilir (örn. 2615580 Edebiyat Fakültesi).
# Bu yüzden koda liste olarak yazıldılar; yalnızca (*) işaretine
# güvenmiyoruz.
# İki kaynağın BİRLEŞİMİ:
#   (a) bu dönem açılan TOS dersleri (danışmandan) — çoğu başka
#       bölümlerin dersi, bu yüzden müfredat belgesinde yer almıyor,
#   (b) Matematik bölümünün kendi TOS dersleri (müfredat belgesi).
# Bir kaynakta olmayan diğerinde olabiliyor; ikisini de tanımalıyız.
# mufredat_denetle.py bu listeyi belgeyle karşılaştırıp farkı raporlar.
TOS_DERSLERI = bolum.tos_dersleri()
TOS_AZAMI_ADET = bolum.tos_azami_adet()     # dönem başına
TOS_AKTS = bolum.tos_akts()

# --- Dönem kompozisyonu ---------------------------------------------------
# 7. dönem 32 AKTS = 1 zorunlu (4) + 1 TOS (4) + 6 bölüm içi seçmeli (24)
# Bu sözlük yalnızca ELDEKİ BELGE YOKKEN kullanılan yedektir; asıl yapı
# donem_yapisi() ile müfredat belgesinden türetilir (bkz. aşağısı).
DONEM_KOMPOZISYONU = bolum.donem_kompozisyonu()


def donem_yapisi(donem, mufredat=None, giris_yili=None):
    """Bir yarıyılın kompozisyonu: zorunlu kodlar, TOS ve seçmeli adedi.

    Müfredat belgesi verilirse yapı BELGEDEN türetilir; böylece sistem
    yalnızca 7. dönem için değil, sekiz yarıyılın tamamı için çalışır.
    3. sınıf danışmanı (hedef 5. dönem) çalıştırdığında da zorunlu ders
    denetimi işler.

    giris_yili verilirse o kohortun planında OLMAYAN dersler (müfredata
    sonradan eklenenler, bkz. SONRADAN_EKLENEN_DERSLER) zorunlulardan
    çıkarılır. Yarıyılın AKTS toplamı değişmediği için açık seçmeli
    kotasına yansır: 5. yarıyılda 2023 girişli için zorunlu 26 yerine
    23 AKTS, seçmeli 1 yerine 2 ders olur.

    Belge yoksa elle kodlanmış DONEM_KOMPOZISYONU'na düşülür.
    """
    if not mufredat:
        return DONEM_KOMPOZISYONU.get(donem)
    dersler = mufredat.get("dersler") or {}
    y = (mufredat.get("yariyillar") or {}).get(donem)
    if not y:
        return DONEM_KOMPOZISYONU.get(donem)

    zorunlu, tos, secmeli, kohort_disi = [], [], [], []
    for kod, d in dersler.items():
        if d.get("yariyil") != donem:
            continue
        if kohort_disi_mi(kod, giris_yili):
            kohort_disi.append(kod)
            continue
        tip = d.get("tip")
        if tip == "Zorunlu":
            zorunlu.append(kod)
        elif tip == "TOS":
            tos.append(kod)
        else:
            secmeli.append(kod)

    toplam = y.get("toplam_akts") or plan_toplami_donem(donem)
    zorunlu_akts = sum(dersler[k].get("akts") or 0 for k in zorunlu)
    tos_adedi = TOS_AZAMI_ADET if tos else 0
    kalan = (toplam or 0) - zorunlu_akts - tos_adedi * TOS_AKTS
    # Bölüm içi seçmelilerin tipik AKTS'si (çoğunlukla hepsi aynı)
    secmeli_aktsler = [dersler[k].get("akts") or 0 for k in secmeli]
    tipik = max(set(secmeli_aktsler), key=secmeli_aktsler.count) \
        if secmeli_aktsler else 0
    secmeli_adedi = int(round(kalan / tipik)) if tipik and kalan > 0 else 0

    return {
        "zorunlu_kodlar": tuple(sorted(zorunlu)),
        "tos_adedi": tos_adedi,
        "secmeli_adedi": secmeli_adedi,
        "secmeli_akts": tipik,
        "toplam_akts": toplam,
        "kohort_disi": tuple(sorted(kohort_disi)),
        "kaynak": "müfredat belgesi",
    }


def plan_toplami_donem(donem):
    return VARSAYILAN_DONEM_PLANI.get(donem, YARIYIL_ACILAN_AKTS)


def tos_mu(ders):
    """TOS dersi mi? Önce koda, sonra ad sonundaki (*) işaretine bakar."""
    if (ders.get("ders_no") or "") in TOS_DERSLERI:
        return True
    return (ders.get("ders_adi") or "").strip().endswith("*")


def plan_toplami(donem_plani=None):
    """Ders planının toplam AKTS'si (Matematik için 244)."""
    return sum((donem_plani or VARSAYILAN_DONEM_PLANI).values())


def akts_kaybi_esigi(donem_plani=None, program_yili=PROGRAM_YILI):
    """Kaç AKTS kayıptan sonra mezuniyet riske girer?

    Plan 244, yönetmelik asgarisi 240 ise 4 AKTS'ye kadar kayıp sorun
    değil; 5. AKTS kaybında toplam 239'a düşer ve MADDE 8/4 sağlanmaz.
    Eşik sabit değil, plandan türetiliyor.
    """
    asgari = MEZUNIYET_AKTS.get(program_yili)
    if asgari is None:
        return None
    return plan_toplami(donem_plani) - asgari + 1


def ogrenci_donem_durumu(alinan_donemler, acilan_donemler=GUZ_DONEMLERI):
    """Öğrencinin sınıfını ve bu dönem alacağı hedef dönemi belirler.

    alinan_donemler: transkriptte geçen dönem numaraları (geçmiş/kalmış farketmez)
    acilan_donemler: bu yarıyıl açılan dönemler, örn. (1,3,5,7)
    """
    acilan = sorted(acilan_donemler)
    parite = acilan[0] % 2
    ayni_parite = sorted({d for d in (alinan_donemler or [])
                          if d is not None and d % 2 == parite})

    if not ayni_parite:
        # Hiç ders almamış: en alt dönemden başlar.
        return {
            "en_yuksek_alinan": None, "sinif": 1,
            "hedef_donem": acilan[0], "alinan_donemler": [],
            "ilk_kez": True,
        }

    en_yuksek = ayni_parite[-1]
    hedef = min(en_yuksek + 2, acilan[-1])
    return {
        "en_yuksek_alinan": en_yuksek,
        "sinif": (en_yuksek + 1) // 2 if parite else en_yuksek // 2,
        "hedef_donem": hedef,
        "alinan_donemler": ayni_parite,
        "ilk_kez": False,
    }


def ust_donem_mi(ders_donemi, hedef_donem):
    """Bu ders öğrencinin hedef döneminin ÜSTÜNDE mi? (MADDE 9/1-ç kapsamı)"""
    if ders_donemi is None or hedef_donem is None:
        return False
    return ders_donemi > hedef_donem


def donem_gecilen_akts(gecilen_dersler, donem):
    """Transkriptte belirli bir döneme ait geçilen AKTS toplamı."""
    return sum(d.get("akts") or 0 for d in gecilen_dersler
               if d.get("donem") == donem)


def alt_donem_yuku(gecilen_dersler, hedef_donem,
                   acilan_donemler=GUZ_DONEMLERI, donem_plani=None,
                   kalinan_dersler=None):
    """Hedef dönemin ALTINDAKİ dönemlerden tamamlanmamış AKTS yükü.

    MADDE 9/1-a: alt sınıflardan hiç almadığı/kaldığı dersler önceliklidir;
    son sınıf hesabına girmeden önce bu yük bütçeden düşülmelidir.

    Bir dönemin eksiği = plandaki AKTS - o dönemden geçilen AKTS.
    Bu tek formül hem kalınan zorunlu dersleri hem doldurulmamış seçmeli
    kotasını birlikte yakalar; zorunlu/seçmeli ayrımı gerekmez.

    DİKKAT: Müfredat bir dersin AKTS'sini düşürdüyse öğrenci dersi
    geçmiş olsa bile o dönem plandan birkaç AKTS eksik görünür. Bu bir
    "alttan ders" değil, AKTS kaybıdır; akts_kaybi() ile ayrıca
    raporlanıyor. Eksik, kalınan dersi olmayan dönemlerde sıfırlanır.
    """
    plan = donem_plani or VARSAYILAN_DONEM_PLANI
    # Kalınan dersi olmayan dönemde plandan sapma varsa bu bir yük değil,
    # AKTS kaybıdır (ders geçilmiş ama AKTS'si düşürülmüş).
    kalinan_donemler = {d.get("donem") for d in (kalinan_dersler or [])}
    # AMA: hiç GİRİLMEMİŞ bir dönemin de kalınan dersi yoktur. O dönem
    # aynı kapıdan geçip yükten siliniyordu: 5. yarıyıldan tek ders bile
    # almamış öğrencinin 30 AKTS'lik yükü "AKTS kaybı" sayılıp 0'a
    # düşüyor, danışman panoda 6 AKTS yük görüyordu (gerçeği 36).
    # Sıfırlama yalnızca o dönemde EN AZ BİR ders geçilmişse geçerli.
    gecilen_donemler = {d.get("donem") for d in (gecilen_dersler or [])}

    toplam, ayrinti = 0, []
    for donem in sorted(acilan_donemler):
        if hedef_donem is not None and donem >= hedef_donem:
            continue
        donem_plan = plan.get(donem, YARIYIL_ACILAN_AKTS)
        gecilen = donem_gecilen_akts(gecilen_dersler, donem)
        fark = max(0, donem_plan - gecilen)

        if (kalinan_dersler is not None
                and donem not in kalinan_donemler
                and donem in gecilen_donemler):
            eksik, tip = 0, "akts_kaybi" if fark else "tam"
        else:
            eksik, tip = fark, "alttan" if fark else "tam"

        ayrinti.append({"donem": donem, "plan": donem_plan,
                        "gecilen": gecilen, "fark": fark,
                        "eksik": eksik, "tip": tip})
        toplam += eksik
    return toplam, ayrinti


def yariyil_acigi(yariyil, gecilen_dersler, secili_kodlar, mufredat,
                  donem_plani=None, giris_yili=None, katalog_dersleri=None):
    """Bu yarıyıl plandaki AKTS'ye ULAŞABİLİR mi? Ulaşamıyorsa ne kadar?

    Neden gerekli
    -------------
    Mezuniyet projeksiyonu her yarıyılın PLAN değerinin kazanılacağını
    varsayar. İki durumda bu varsayım tutmaz:

    1. Müfredat bir dersin AKTS'sini düşürüp payı YENİ bir derse taşıdı,
       ama o yeni ders bu kohortun planında yok (SONRADAN_EKLENEN_DERSLER).
       5. yarıyıl: Cebir 6->5, Dif.Geo 6->5, Sayılar 4->3 ve düşen 3 AKTS
       Uygulamalı Matematik I'e taşındı. 2023 girişli o dersi almadığı
       için yarıyıl 27'de kalıyor.

    2. Ders AKTS'si ARTMIŞ ama öğrenci düşük değerken geçmiş. Lineer
       Cebir I/II 6 -> 5 -> 6 oldu; 5 iken geçen öğrenci 1 AKTS eksik
       taşıyor ve dersi tekrar alamayacağı için bu açık kapanmıyor.

    İkisinde de dersten KALMIŞ olmak gerekmiyor; bu yüzden ne alttan yük
    ne de akts_kaybi() hesabına giriyorlardı.

    Hesap
    -----
        eksik       = plan - geçilen - bu dönem seçilen
        zorunlu_ile = o yarıyılda hâlâ alabileceği (kohorta ait)
                      zorunluların GÜNCEL AKTS toplamı
        havuz_ile   = yarıyılın seçmeli + TOS kotasından kalan
        kalıcı      = eksik - zorunlu_ile - havuz_ile      (0'dan küçük olamaz)

    zorunlu_ile KATALOGDAN BAĞIMSIZ: bahar dersi güz katalogunda
    görünmez ama öğrenci onu baharda alacak. Katalog yalnızca "bu dönem
    hangisini seçebilir" sorusunu (adaylar) yanıtlar.

    kalıcı, yarıyılın kendi içinde hiçbir şekilde kapanmayan açıktır;
    ACIK_KAPATMA_YARIYILI seçmeli havuzundan FAZLADAN ders gerektirir.

    Döner: None (açık yok) ya da sözlük.
    """
    plan = (donem_plani or VARSAYILAN_DONEM_PLANI).get(yariyil)
    belge = (mufredat or {}).get("dersler") or {}
    if not plan or not belge:
        return None

    yapi = donem_yapisi(yariyil, mufredat) or {}
    # Kota STANDART kompozisyondan alınır (kohort düzeltmesi YAPILMADAN):
    # kohorta göre şişirilmiş kota zaten çözümün kendisi, açığı ölçerken
    # kullanırsak açık sıfır çıkar ve danışmana hiçbir şey söylemeyiz.
    havuz_kotasi = ((yapi.get("secmeli_adedi") or 0)
                    * (yapi.get("secmeli_akts") or 0)
                    + (yapi.get("tos_adedi") or 0) * TOS_AKTS)

    # --- geçilenler: belge karşılıklarıyla ----------------------------
    gecilen_belge, gecilen, gecilen_havuz = set(), 0, 0
    dusuk_gecilen = []
    for d in gecilen_dersler or []:
        if d.get("donem") != yariyil:
            continue
        akts = d.get("akts") or 0
        gecilen += akts
        kod = belge_karsiligi(d.get("ders_kodu"), d.get("ders_adi") or "",
                              belge)
        if kod:
            gecilen_belge.add(kod)
        bilgi = belge.get(kod) or {}
        zorunlu_mu = (bilgi.get("yariyil") == yariyil
                      and (bilgi.get("tip") or "").startswith("Zorunlu"))
        if not zorunlu_mu:
            gecilen_havuz += akts
        # Dersin AKTS'si SONRADAN ARTMIŞ ve öğrenci düşük değerken
        # geçmiş: Lineer Cebir I/II 6 -> 5 -> 6 oldu, 5 iken geçen
        # öğrenci 1 AKTS eksik taşıyor. Dersi tekrar alamayacağı için
        # bu açık kapanmıyor; kaybedilen AKTS'nin ters yönü olduğu için
        # akts_kaybi() da görmüyordu.
        guncel = bilgi.get("akts")
        if guncel is not None and akts and guncel > akts:
            dusuk_gecilen.append({
                "ders_no": kod, "ders_adi": bilgi.get("ders_adi"),
                "gecilen_akts": akts, "guncel_akts": guncel,
                "fark": guncel - akts})

    # --- bu dönem seçilenler ------------------------------------------
    secili_kodlar = set(secili_kodlar or ())
    secilen, secilen_havuz = 0, 0
    for kod in secili_kodlar:
        bilgi = belge.get(kod)
        if not bilgi or bilgi.get("yariyil") != yariyil:
            continue
        akts = bilgi.get("akts") or 0
        secilen += akts
        if not (bilgi.get("tip") or "").startswith("Zorunlu"):
            secilen_havuz += akts

    eksik = max(0, plan - gecilen - secilen)

    # --- hâlâ alınabilecek zorunlular ---------------------------------
    katalog = {d.get("ders_no"): d for d in (katalog_dersleri or [])}
    zorunlu_ile, adaylar, kohort_disi = 0, [], []
    for kod, bilgi in sorted(belge.items()):
        if bilgi.get("yariyil") != yariyil:
            continue
        if not (bilgi.get("tip") or "").startswith("Zorunlu"):
            continue
        if kod in gecilen_belge or kod in secili_kodlar:
            continue
        kayit = {"ders_no": kod, "ders_adi": bilgi.get("ders_adi"),
                 "akts": bilgi.get("akts") or 0}
        if kohort_disi_mi(kod, giris_yili):
            kohort_disi.append(kayit)      # planında yok, açığı bu yaratıyor
            continue
        zorunlu_ile += kayit["akts"]
        ders = katalog.get(kod)
        if ders is not None:               # bu dönem katalogda açık
            adaylar.append(dict(kayit, doldu=bool(ders.get("doldu"))))

    havuz_ile = max(0, havuz_kotasi - gecilen_havuz - secilen_havuz)

    # Bu yarıyıldan en fazla kaç AKTS gelebilir? Plandan AZ olabileceği
    # gibi FAZLA da olabilir: öğrenci kotanın üstünde seçmeli alırsa
    # (açığı kapatmak için tam da bunu yapması isteniyor) ya da eski
    # yüksek AKTS'li dersleri geçmişse yarıyıl 30'u aşar.
    ulasilabilir = gecilen + secilen + zorunlu_ile + havuz_ile
    kalici = max(0, plan - ulasilabilir)
    fazla = max(0, ulasilabilir - plan)
    if not kalici and not fazla:
        return None                        # yarıyıl tam planında

    return {"yariyil": yariyil, "plan": plan, "gecilen": gecilen,
            "secilen": secilen, "sonra": gecilen + secilen, "eksik": eksik,
            "zorunlu_ile": zorunlu_ile, "havuz_ile": havuz_ile,
            "havuz_kotasi": havuz_kotasi, "ulasilabilir": ulasilabilir,
            "kalici": kalici, "fazla": fazla,
            "adaylar": adaylar, "kohort_disi": kohort_disi,
            "dusuk_gecilen": dusuk_gecilen}


def kohort_acigi(gecilen_dersler, secili_kodlar, mufredat, donem_plani=None,
                 giris_yili=None, katalog_dersleri=None,
                 yariyillar=range(1, 9)):
    """Sekiz yarıyılın tamamında KAPANMAYAN toplam AKTS açığı.

    Her yarıyıl için yariyil_acigi() çağrılır ve "kalıcı" paylar
    toplanır. Sonuç, öğrencinin planı eksiksiz yürütse bile mezuniyette
    ULAŞAMAYACAĞI AKTS'dir:

        gerçek mezuniyet AKTS'si = plan toplamı - toplam kalıcı açık

    Öğrencinin henüz girmediği yarıyıllar da hesaba katılır: 2023
    girişlinin 6. yarıyılı da Uygulamalı Matematik II yüzünden eksik
    kapanacak, bunu bugünden bilmek gerekiyor.

    Doğrulama (2026-09, 60 öğrenci): kohort kuralı KAPALIYKEN toplam
    kalıcı açık 60 öğrencinin hepsinde 0 çıkıyor - yani hesap kendi
    başına kayıp uydurmuyor, açığın tamamı kohort farkından geliyor.
    """
    kalemler, toplam, fazla_toplam = [], 0, 0
    for yy in yariyillar:
        a = yariyil_acigi(yy, gecilen_dersler, secili_kodlar, mufredat,
                          donem_plani, giris_yili, katalog_dersleri)
        if not a:
            continue
        if a["kalici"]:
            kalemler.append(a)
            toplam += a["kalici"]
        fazla_toplam += a["fazla"]

    # Mezuniyet AKTS'si bir TOPLAMDIR; yarıyıl sınırı yoktur. 5.
    # yarıyıldan fazladan alınan ders 1. yarıyılın açığını da kapatır.
    # Eskiden yalnız "kalıcı" paylar toplanıp plandan düşülüyordu; fazla
    # hiç sayılmadığı için danışman panonun dediğini yapıp fazladan ders
    # yazdırdığında sayı KIPIRDAMIYORDU (ölçüldü: 230000004'e dört ek
    # seçmeli yazıldı, mezuniyet 239'da çakılı kaldı). Uyarı böylece
    # kapatılamaz, dolayısıyla eyleme dönüştürülemez oluyordu.
    plan = plan_toplami(donem_plani)
    net = toplam - fazla_toplam
    return {"toplam": toplam, "fazla": fazla_toplam, "net": net,
            "kalemler": kalemler, "plan_toplami": plan,
            "mezuniyet_akts": plan - net}


def akts_kaybi(transkript, eslesmeler=None, donem_plani=None,
               program_yili=PROGRAM_YILI):
    """Müfredat AKTS düşürdüğü için kaybedilen / kaybedilecek AKTS.

    Bir ders, öğrenci onu ilk aldığındakinden DÜŞÜK AKTS ile tekrar
    alındığında plandaki toplam aşağı kayar. İki kaynak var:

      gerceklesmis - öğrenci dersi düşük AKTS ile tekrar alıp geçmiş.
                     (örnek: FİZİK II 5 -> 4, kayıp 1)
      beklenen     - hâlâ alttan olan ders, katalogda daha düşük AKTS.
                     Tekrar aldığında kayıp gerçekleşecek.

    Kayıp eşiği plandan türetilir: plan 244, asgari 240 ise 5 AKTS ve
    üzeri kayıp mezuniyeti riske sokar.
    """
    gerceklesmis, beklenen = [], []

    # --- Geçmiş denemeler arasındaki düşüş -----------------------------
    for tekrar in (transkript.get("tekrar_edilen") or []):
        aktsler = [a for a in (tekrar.get("aktsler") or []) if a]
        if not aktsler:
            continue
        guncel = tekrar["guncel"].get("akts") or 0
        fark = max(aktsler) - guncel
        if fark > 0:
            gerceklesmis.append({
                "ders_kodu": tekrar["ders_kodu"],
                "ders_adi": tekrar["ders_adi"],
                "eski_akts": max(aktsler), "yeni_akts": guncel, "kayip": fark,
            })

    # --- Hâlâ alttan olan derslerin katalogdaki AKTS'si düşmüşse -------
    for kayit in (eslesmeler or []):
        eski = kayit.get("eslesme")
        if eski is None or kayit.get("tip") not in ("kod", "ad"):
            continue
        if not tekrar_gerekir_mi(deneme_sonucu(eski)):
            continue
        eski_akts = eski.get("akts") or 0
        yeni_akts = kayit["ders"].get("akts") or 0
        if eski_akts and yeni_akts and yeni_akts < eski_akts:
            beklenen.append({
                "ders_kodu": kayit["ders"].get("ders_no"),
                "ders_adi": kayit["ders"].get("ders_adi"),
                "eski_akts": eski_akts, "yeni_akts": yeni_akts,
                "kayip": eski_akts - yeni_akts,
            })

    toplam = (sum(k["kayip"] for k in gerceklesmis) +
              sum(k["kayip"] for k in beklenen))
    plan = plan_toplami(donem_plani)
    esik = akts_kaybi_esigi(donem_plani, program_yili)
    asgari = MEZUNIYET_AKTS.get(program_yili)

    return {
        "gerceklesmis": gerceklesmis,
        "beklenen": beklenen,
        "toplam_kayip": toplam,
        "plan_toplami": plan,
        "beklenen_mezuniyet_akts": plan - toplam,
        "esik": esik,
        "mezuniyet_asgarisi": asgari,
        "riskli": esik is not None and toplam >= esik,
    }


def mezuniyet_projeksiyonu(transkript, eslesmeler, donem_durumu,
                           donem_plani=None, acilan_donemler=GUZ_DONEMLERI,
                           program_yili=PROGRAM_YILI,
                           kalici_acik=None):
    """Öğrenci mezun olduğunda kaç AKTS'ye ulaşacak?

    Üç adımda ilerliyor, her adım ayrı raporlanıyor ki danışman
    aritmetiği görebilsin:

      1. basarili_akts  - transkriptte şu an geçilmiş toplam
      2. alttan_yeni    - alttan derslerin KATALOGDAKİ (yeni) AKTS'leri;
                          dersi tekrar alınca bu kadar eklenecek
      3. kalan_donemler - henüz hiç girilmemiş dönemlerin plandaki AKTS'si
                          (Matematik'te 7. ve 8. dönem 32'şer)

    Toplam = 1 + 2 + 3, yönetmelik asgarisiyle (240) karşılaştırılıyor.
    """
    plan = donem_plani or VARSAYILAN_DONEM_PLANI
    asgari = MEZUNIYET_AKTS.get(program_yili)
    basarili = transkript.get("gecilen_akts") or 0

    # --- 2. Alttan derslerin YENİ AKTS'leri --------------------------
    alttan = []
    for kayit in (eslesmeler or []):
        eski = kayit.get("eslesme")
        if eski is None or kayit.get("tip") not in ("kod", "ad"):
            continue
        if not tekrar_gerekir_mi(deneme_sonucu(eski)):
            continue
        alttan.append({
            "ders_no": kayit["ders"].get("ders_no"),
            "ders_adi": kayit["ders"].get("ders_adi"),
            "eski_akts": eski.get("akts") or 0,
            "yeni_akts": kayit["ders"].get("akts") or 0,
        })
    alttan_yeni = sum(d["yeni_akts"] for d in alttan)
    alttan_eski = sum(d["eski_akts"] for d in alttan)

    # --- 3. Dönemleri ikiye ayır -------------------------------------
    # Girilmiş dönem: transkriptte o döneme ait en az bir ders var.
    # Girilmemiş dönem: hiç dokunulmamış, tamamı önünde duruyor.
    girilen = set(donem_durumu.get("alinan_donemler") or [])
    girilen |= {d.get("donem") for d in (transkript.get("denemeler") or [])
                if d.get("donem")}
    girilen = {d for d in girilen if d in plan}

    kalan_donemler = sorted(d for d in plan if d not in girilen)
    kalan_akts = sum(plan[d] for d in kalan_donemler)

    # Girilmiş dönemlerin plandaki toplamından geçileni düşünce, o
    # dönemlerden HÂLÂ BORÇLU olduğu AKTS çıkar. Bu yalnızca kalınan
    # dersleri değil, hiç alınmamış zorunluları ve doldurulmamış seçmeli
    # kotasını da kapsar. (Eski sürüm sadece bu dönem açık olan alttan
    # dersleri sayıyordu; çift dönemlerdeki borç görünmüyordu ve eksiği
    # olan her öğrenci "mezun olamaz" çıkıyordu.)
    girilen_plan = sum(plan[d] for d in girilen)
    alt_yukumluluk = max(0, girilen_plan - basarili)

    # Mezuniyette elde edeceği toplam. Tanım gereği:
    #   başarılı + alt yükümlülük + kalan dönemler = plan toplamı
    # Müfredat AKTS düşürdüyse o kadarı eksilir.
    kayip = akts_kaybi(transkript, eslesmeler, plan, program_yili)

    # Hangi düşümü kullanıyoruz?
    #   kalici_acik (kohort_acigi) - müfredat belgesi varsa TEK ve DOĞRU
    #     kaynak. Yarıyıl yarıyıl "bu öğrenci buradan en fazla kaç AKTS
    #     alabilir" hesabı; AKTS düşüşünü de artışını da, kohortun
    #     almayacağı dersi de aynı aritmetikte topluyor.
    #   akts_kaybi - belge yoksa kullanılan daha kaba yedek. Yalnız
    #     tekrar edilen ve kalınan dersleri sayar; müfredatın düşen payı
    #     YENİ bir derse taşımış olmasını göremez, bu yüzden karamsardır.
    # İKİSİNİ BİRDEN düşmüyoruz: aynı AKTS'yi iki kez eksiltirdi.
    dusum = kayip["toplam_kayip"] if kalici_acik is None else kalici_acik
    toplam = basarili + alt_yukumluluk + kalan_akts - dusum

    return {
        "basarili_akts": basarili,
        "alttan": alttan,
        "alttan_yeni_akts": alttan_yeni,
        "alttan_eski_akts": alttan_eski,
        "girilen_donemler": sorted(girilen),
        "girilen_plan_akts": girilen_plan,
        "alt_yukumluluk": alt_yukumluluk,
        "kalan_donemler": kalan_donemler,
        "kalan_donem_akts": kalan_akts,
        "akts_kaybi": kayip["toplam_kayip"],
        "kalici_acik": kalici_acik,
        "dusum": dusum,
        "dusum_kaynagi": ("müfredat belgesi (yarıyıl açığı)"
                          if kalici_acik is not None else "AKTS kaybı"),
        "projeksiyon": toplam,
        "asgari": asgari,
        "fark": (toplam - asgari) if asgari else None,
        "yeterli": (toplam >= asgari) if asgari else None,
        "plan_toplami": plan_toplami(plan),
    }


def son_sinif_degerlendir(gano, donem_durumu, alt_yuk_akts,
                          son_donem_dersleri,
                          program_yili=PROGRAM_YILI):
    """Son sınıf mı, AKTS sınırı kalkar mı? MADDE 3/p + MADDE 9/1-c.

    İKİ KAPI var:

    KAPI 1 - Hedef dönem son yarıyıla ulaşmış olmalı.
      Öğrenci 5. dönemden İLK KEZ ders alıyorsa (hedef=5), 7. dönem
      dersleri onun için ÜST DÖNEM dersidir. MADDE 9/1-ç kapsamına girer,
      kendi sınırı vardır (%20) ve sınırsız AKTS AÇTIRMAZ.

    KAPI 2 - Bütçe.
      GANO'ya göre açılan 30/45 AKTS'den alt dönemlerin tamamlanmamış
      yükü düşüldükten sonra, son yarıyıldan en az 1 ders sığmalı.

    Her iki kapı da geçilirse son sınıf sayılır ve AKTS sınırı kalkar.
    """
    son_yariyil = SON_SINIF_YARIYILI.get(program_yili)
    taban_limit = azami_akts(gano, son_sinif=False)
    hedef = (donem_durumu or {}).get("hedef_donem")

    sonuc = {
        "son_sinif": False,
        "son_yariyil": son_yariyil,
        "hedef_donem": hedef,
        "taban_limit": taban_limit,
        "alt_yuk_akts": alt_yuk_akts or 0,
        "kalan_kapasite": None,
        "en_ucuz_ders": None,
        "ust_donem_durumu": False,
        "sebep": "",
    }

    # --- KAPI 1 --------------------------------------------------------
    if hedef is None or son_yariyil is None:
        sonuc["sebep"] = "Hedef dönem belirlenemedi."
        return sonuc
    if hedef < son_yariyil:
        sonuc["ust_donem_durumu"] = True
        sonuc["sebep"] = (
            "Öğrenci bu dönem %d. dönem derslerini alıyor. %d. dönem dersleri "
            "onun için ÜST DÖNEM dersi (MADDE 9/1-ç); AKTS'si yetse bile "
            "sınırsız AKTS açılmaz." % (hedef, son_yariyil))
        return sonuc

    # --- KAPI 2 --------------------------------------------------------
    if taban_limit is None:
        sonuc["sebep"] = "GANO bilinmiyor, taban limit hesaplanamadı."
        return sonuc

    kalan = taban_limit - (alt_yuk_akts or 0)
    sonuc["kalan_kapasite"] = kalan

    uygun = [d for d in (son_donem_dersleri or []) if d.get("akts")]
    if not uygun:
        sonuc["sebep"] = ("%d. dönemde öğrencinin alabileceği ders yok."
                          % son_yariyil)
        return sonuc

    en_ucuz = min(uygun, key=lambda d: d["akts"])
    sonuc["en_ucuz_ders"] = en_ucuz

    if kalan >= en_ucuz["akts"]:
        sonuc["son_sinif"] = True
        sonuc["sebep"] = (
            "%d AKTS bütçenin %d'si alt dönemlerin eksiğine gidiyor; kalan "
            "%d AKTS'ye %d. dönemden '%s' (%d AKTS) sığıyor."
            % (taban_limit, alt_yuk_akts or 0, kalan, son_yariyil,
               en_ucuz["ders_adi"], en_ucuz["akts"]))
    else:
        sonuc["sebep"] = (
            "%d AKTS bütçeden alt dönem eksiğine %d gidince kalan %d AKTS, "
            "%d. dönemin en düşük AKTS'li dersine (%d) yetmiyor."
            % (taban_limit, alt_yuk_akts or 0, kalan, son_yariyil,
               en_ucuz["akts"]))
    return sonuc


def yariyil_akts_limiti(gano, son_sinif):
    """MADDE 9/1-c: Nihai AKTS sınırı. Son sınıfta sınır yoktur (None)."""
    if son_sinif:
        return None
    return azami_akts(gano, son_sinif=False)


# =========================================================================
#  MADDE 16 - Azami süre takibi
# =========================================================================
def giris_yili(ogrno):
    """Öğrenci numarasının ilk iki hanesinden giriş yılını çıkarır.

    Örn: 23xxxxxxx -> 2023. Numara biçimi değişirse None döner.
    """
    sayi = re.sub(r"\D", "", str(ogrno or ""))
    if len(sayi) < 2:
        return None
    yy = int(sayi[:2])
    return 2000 + yy if yy <= 79 else 1900 + yy


def azami_sure_durumu(ogrno, icinde_bulunulan_yil,
                      program_yili=PROGRAM_YILI,
                      hazirlik_yili=0):
    """MADDE 16/1: Azami sürenin neresinde olduğunu döndürür."""
    baslangic = giris_yili(ogrno)
    if baslangic is None or icinde_bulunulan_yil is None:
        return None
    azami = AZAMI_SURE.get(program_yili)
    if azami is None:
        return None
    gecen = icinde_bulunulan_yil - baslangic
    return {
        "giris_yili": baslangic,
        "gecen_yil": gecen,
        "azami_yil": azami + hazirlik_yili,
        "kalan_yil": (azami + hazirlik_yili) - gecen,
        # gecen = TAMAMLANMIS yil sayisi. 2019 girisli, 2026 guzunde
        # 8. ogretim yilina basliyor; azami 7 yil ise MADDE 16/1
        # asilmistir. ">" ile kalan_yil 0 iken "asilmadi" deniyordu -
        # kendi icinde celiskili ve danismani bir yil geciktiriyordu.
        "asildi": gecen >= (azami + hazirlik_yili),
    }


# =========================================================================
#  Ders adı eşleştirme (müfredat değişikliği / eski kod - yeni kod)
# =========================================================================
# MADDE 9/1-f: Programdan kaldırılan ve yerine yeni ders konulmayan dersten
# başarısız olan öğrencinin sorumluluğu kalkar. Yerine yeni ders KONULMUŞSA
# (kod değişmiş, ders aynı) öğrenci o dersi tekrar almamalı.
# OBİS kod eşleşmesine baktığı için bunu bizim yakalamamız gerekiyor.

# --- Ders adı eşleştirme -------------------------------------------------
# Gövdesi eslestirme.py'ye taşındı (kurulum sihirbazı profil yokken de
# kullanabilsin diye). Adlar burada duruyor; `ym.ad_benzerligi` gibi
# mevcut kullanımlar değişmedi.
from eslestirme import (_TURKCE_ESLER, _TEMIZLENECEK, _ROMEN,  # noqa: F401
                        _YAZIM_ESLERI, _sadelestir,
                        ders_adi_anahtari, ders_seviyesi,
                        ad_benzerligi, BENZERLIK_ESIGI)


# =========================================================================
#  MADDE 9/1-a - Seçmeli ders grupları
# =========================================================================
# "Daha önce aldığı bir seçmeli dersin tekrarında, aynı dersi almak zorunda
#  değildir; bunun yerine aynı seçmeli gruptan başka bir dersi/dersleri
#  alabilir."
# İşletilen tanım (danışman kararı): bir dönemin TÜM seçmeli dersleri tek
# bir grup sayılır. Yani öğrenci o dönemin seçmelisinden kaldıysa, aynı
# dönemin başka herhangi bir seçmelisini alabilir.
#
# Seçmeli tespiti ders adındaki "(SEÇ)" işaretinden ve satırın yeşil
# renginden yapılıyor; ders tipi kodlarına GÜVENİLMİYOR (kullanıcı notu:
# OBİS'teki ders tipleri tutarsız).
_SECMELI_IMI = re.compile(r"\(\s*SEC", re.IGNORECASE)


def belge_karsiligi(ders_kodu, ders_adi, belge):
    """Transkript/katalog dersinin müfredat belgesindeki kodu.

    ÖNCE kod, tutmazsa ad benzerliği. İkisi de tek başına yetmiyor:

      - Müfredat bazı derslerin KODUNU değiştirdi
        (2709508 CEBİR I -> 2709545, 2709155 LİNEER CEBİR I -> 2709171),
      - belge ad kısaltıyor: "Atatürk İlk. ve İnk. Tarihi I" ile
        transkriptteki "ATATÜRK İLKELERİ VE İNKILAP TARİHİ 1"
        benzerliği 0,857 - BENZERLIK_ESIGI'nin (0,88) altında.

    İkisi birlikte 60 öğrencinin geçtiği derslerin TAMAMINI eşliyor
    (ölçüldü 2026-09); eşleşmeyen tek kayıt kalmıyor.

    Eşleşme bulunamazsa None döner.
    """
    if ders_kodu and ders_kodu in belge:
        return ders_kodu
    en_iyi, oran = None, 0.0
    for kod, bilgi in (belge or {}).items():
        o = ad_benzerligi(ders_adi, bilgi.get("ders_adi") or "")
        if o > oran:
            en_iyi, oran = kod, o
    return en_iyi if oran >= BENZERLIK_ESIGI else None


def secmeli_mi(ders):
    """Katalog satırı BÖLÜM İÇİ seçmeli ders mi?

    İki bağımsız gösterge: ders adında '(SEÇ' ibaresi, satırın yeşil
    renkte olması. İkisi çelişirse 'seçmeli' tarafına düşüyoruz ki
    danışmanın önüne çıksın.

    TOS dersleri (* işaretli ortak seçmeliler) buraya DAHİL DEĞİL; ayrı
    bir kotaları var (dönemde en fazla 1) ve bölüm içi seçmeli yerine
    geçmezler.
    """
    if tos_mu(ders):
        return False
    ad = _sadelestir(ders.get("ders_adi", ""))
    return bool(_SECMELI_IMI.search(ad)) or bool(ders.get("yesil_yazi"))


def donem_numarasi(donem_adi):
    """'5. Dönem Dersleri' -> 5"""
    esleme = re.match(r"\s*(\d+)", str(donem_adi or ""))
    return int(esleme.group(1)) if esleme else None


def secmeli_gruplari(katalog):
    """{dönem no: [seçmeli dersler]} — MADDE 9/1-a grupları."""
    gruplar = {}
    for ders in katalog:
        if not secmeli_mi(ders):
            continue
        donem = donem_numarasi(ders.get("donem"))
        if donem is None:
            continue
        gruplar.setdefault(donem, []).append(ders)
    return gruplar


def donem_kompozisyonu_denetle(hedef_donem, secili_dersler, katalog,
                               gecilen_kodlar=(), donem_plani=None,
                               mufredat=None, giris_yili=None):
    """Hedef dönemin ders kompozisyonu doğru mu, eksik ne var?

    7. dönem 32 AKTS üç parçadan oluşuyor:
        zorunlu         1 ders  (MATEMATİK UYGULAMALARI I)    4 AKTS
        TOS             1 ders  (* işaretli ortak seçmeli)     4 AKTS
        bölüm içi seçm. 6 ders  ((SEÇ) işaretli)              24 AKTS

    Öğrencinin seçimini bu üç kovaya ayırıp her birinde eksik/fazla
    olanı çıkarır. AKTS toplamına bakmak yetmiyor: 32 AKTS'yi yanlış
    dağılımla da doldurabilir (örn. 8 bölüm seçmeli, hiç TOS yok).
    """
    plan = donem_plani or VARSAYILAN_DONEM_PLANI
    toplam_akts = plan.get(hedef_donem, YARIYIL_ACILAN_AKTS)
    # giris_yili verilirse kohortun almayacağı dersler zorunlu
    # listesinden düşer ve açık, seçmeli kotasına yansır (5. dönemde
    # 2023 girişli için 1 değil 2 seçmeli).
    yapi = donem_yapisi(hedef_donem, mufredat, giris_yili)

    katalog_dizini = {d.get("ders_no"): d for d in (katalog or [])}
    gecilen = set(gecilen_kodlar or ())

    # Seçilenleri kovalara ayır. Katalogda olmayan ders de olabilir
    # (başka fakültenin TOS dersi), o yüzden secili_dersler esas.
    zorunlu_secilen, tos_secilen, secmeli_secilen, diger = [], [], [], []
    secilen_akts = 0
    for s in (secili_dersler or []):
        kod = s.get("ders_no")
        ders = katalog_dizini.get(kod) or dict(s)
        akts = ders.get("akts")
        if akts is None:
            akts = TOS_AKTS if tos_mu(ders) else 0
        secilen_akts += akts
        kayit = {"ders_no": kod, "ders_adi": ders.get("ders_adi")
                 or s.get("ders_adi"), "akts": akts}

        if yapi and kod in yapi["zorunlu_kodlar"]:
            zorunlu_secilen.append(kayit)
        elif tos_mu(ders):
            tos_secilen.append(kayit)
        elif secmeli_mi(ders) and donem_numarasi(ders.get("donem")) == hedef_donem:
            secmeli_secilen.append(kayit)
        else:
            diger.append(kayit)

    sonuc = {
        "donem": hedef_donem, "toplam_akts": toplam_akts,
        "secilen_akts": secilen_akts, "eksik_akts": max(0, toplam_akts - secilen_akts),
        "zorunlu_eksik": [], "zorunlu_secilen": zorunlu_secilen,
        "tos_secilen": tos_secilen, "tos_azami": TOS_AZAMI_ADET,
        "tos_eksik": 0, "tos_fazla": 0,
        "secmeli_secilen": secmeli_secilen,
        "secmeli_gereken": None, "secmeli_eksik": 0,
        "diger": diger, "yapi_bilinmiyor": yapi is None,
    }
    if yapi is None:
        return sonuc

    # --- zorunlu ---
    for kod in yapi["zorunlu_kodlar"]:
        if kod in gecilen:
            continue                      # daha önce geçmiş, gerekmiyor
        if not any(z["ders_no"] == kod for z in zorunlu_secilen):
            ders = katalog_dizini.get(kod, {})
            sonuc["zorunlu_eksik"].append({
                "ders_no": kod,
                "ders_adi": ders.get("ders_adi") or "(katalogda yok)",
                "akts": ders.get("akts") or 0,
                "doldu": bool(ders.get("doldu")),
            })

    # --- TOS ---
    sonuc["tos_eksik"] = max(0, yapi["tos_adedi"] - len(tos_secilen))
    sonuc["tos_fazla"] = max(0, len(tos_secilen) - TOS_AZAMI_ADET)

    # --- bölüm içi seçmeli ---
    # Adet ve tipik AKTS'yi donem_yapisi() zaten belgeden turetiyor;
    # burada YENIDEN hesaplamak iki kaynak demekti ve ikincisi bolen
    # olarak TOS_AKTS kullaniyordu. Bolum ici secmeliler bugun 4 AKTS
    # oldugu icin sonuclar cakisiyordu; mufredat bir yariyilin
    # secmelisini baska bir degere cekerse ikisi ayrisirdi.
    birim = yapi.get("secmeli_akts") or TOS_AKTS
    zorunlu_akts = sum((katalog_dizini.get(k, {}).get("akts") or 0)
                       for k in yapi["zorunlu_kodlar"] if k not in gecilen)
    secmeli_akts = toplam_akts - zorunlu_akts - yapi["tos_adedi"] * TOS_AKTS
    sonuc["secmeli_gereken"] = max(0, -(-secmeli_akts // birim))
    sonuc["secmeli_eksik"] = max(0, sonuc["secmeli_gereken"]
                                 - len(secmeli_secilen))
    return sonuc


def secmeli_alternatifleri(donem, katalog, haric_kodlar=()):
    """Bir dönemin seçmeli grubundan alınabilir alternatifler.

    Kalınan seçmeli dersin yerine önerilebilecek dersler. Kontenjanı dolu
    olanlar ve haric_kodlar elenir. Karar danışmanın; bu sadece listedir.
    """
    haric = set(haric_kodlar)
    return [d for d in secmeli_gruplari(katalog).get(donem, [])
            if d.get("ders_no") not in haric and not d.get("doldu")]


# =========================================================================
#  Katalog <-> transkript eşleştirmesi
# =========================================================================
def _transkript_ad_dizini(son_durum):
    """{ders adı anahtarı: [deneme, ...]} dizini kurar."""
    dizin = {}
    for deneme in son_durum.values():
        dizin.setdefault(ders_adi_anahtari(deneme["ders_adi"]), []).append(deneme)
    return dizin


def katalog_eslestir(katalog, son_durum):
    """Kayıt sayfasındaki her dersi transkriptteki karşılığıyla eşler.

    Eşleşme tipleri:
      kod    - ders kodu birebir aynı (en güvenilir)
      ad     - kod farklı ama ders adı birebir aynı (müfredat kod değişikliği)
      benzer - ad çok yakın; DANIŞMAN DOĞRULAMALI, otomatik karar verilmez
      None   - transkriptte karşılığı yok, gerçekten hiç alınmamış

    MADDE 9/1-f gereği yerine yeni ders konulan derslerin sorumluluğu devam
    eder; OBİS bunu kod üzerinden gördüğü için kod değişince dersi "hiç
    alınmamış" gösteriyor. 'ad' ve 'benzer' eşleşmeleri bu boşluğu kapatır.
    """
    ad_dizini = _transkript_ad_dizini(son_durum)
    sonuclar = []

    for ders in katalog:
        kod = ders.get("ders_no")
        kayit = {
            "ders": ders, "eslesme": None, "tip": None,
            "benzerlik": None, "aday": None,
        }

        if kod in son_durum:
            kayit["eslesme"] = son_durum[kod]
            kayit["tip"] = "kod"
            sonuclar.append(kayit)
            continue

        anahtar = ders_adi_anahtari(ders.get("ders_adi", ""))
        if anahtar and anahtar in ad_dizini:
            # Aynı adla birden çok eski kod varsa en yenisini alıyoruz.
            adaylar = sorted(ad_dizini[anahtar], key=lambda d: (d.get("yil") or 0))
            kayit["eslesme"] = adaylar[-1]
            kayit["tip"] = "ad"
            kayit["benzerlik"] = 1.0
            sonuclar.append(kayit)
            continue

        en_iyi, en_iyi_oran = None, 0.0
        for baska_anahtar, denemeler in ad_dizini.items():
            oran = difflib.SequenceMatcher(None, anahtar, baska_anahtar).ratio()
            if oran > en_iyi_oran:
                en_iyi_oran, en_iyi = oran, denemeler[-1]
        if en_iyi is not None and en_iyi_oran >= BENZERLIK_ESIGI:
            kayit["aday"] = en_iyi
            kayit["tip"] = "benzer"
            kayit["benzerlik"] = round(en_iyi_oran, 3)

        sonuclar.append(kayit)

    return sonuclar


# =========================================================================
#  Danışman uyarıları
# =========================================================================
# Önem sırası: yuksek = danışman mutlaka baksın, orta = kontrol etsin,
# bilgi = sadece kayda geçsin.
def danisman_uyarilari(eslesmeler, transkript, yano=None):
    """Katalog-transkript eşleşmelerinden danışman uyarıları üretir.

    Karar VERMEZ; "şu dersi verme", "şuna dikkat et" diye işaretler.
    """
    uyarilar = []
    kod_degisenler = []

    def ekle(onem, baslik, ders, aciklama, kaynak=""):
        uyarilar.append({
            "onem": onem, "baslik": baslik, "aciklama": aciklama,
            "ders_no": ders.get("ders_no"), "ders_adi": ders.get("ders_adi"),
            "akts": ders.get("akts"), "kaynak": kaynak,
        })

    for kayit in eslesmeler:
        ders = kayit["ders"]
        eski = kayit["eslesme"]
        secili = ders.get("secili")

        # --- Kod değişmiş, öğrenci eski koduyla GEÇMİŞ -> VERME -------------
        if eski is not None and kayit["tip"] in ("kod", "ad"):
            # Geçmiş notlar için yönetmeliği geriye dönük uygulamıyoruz;
            # transkriptteki harf ne diyorsa o (bağıl sistem dönemi olabilir).
            # Tek istisna DC: şartlı geçerin tutup tutmadığına OBİS'in kendi
            # işareti karar verir, o karar deneme["sonuc"]a işlenmiştir.
            durum = deneme_sonucu(eski)
            ayni_kod = kayit["tip"] == "kod"

            if basarili_sayilir_mi(durum):
                if not ayni_kod:
                    # Müfredat kod değiştirdiği için OBİS bu dersi "hiç
                    # alınmamış" gösteriyor. Öğrenci SEÇMEDİYSE bu bir
                    # eylem değil; seçtiyse dersi çıkarmak gerekiyor.
                    # Seçilmemişleri tek tek uyarı yapmak paneli boğuyordu
                    # (59 öğrencinin 59'unda toplam 189 uyarı), onlar
                    # aşağıda tek bir özet notta toplanıyor.
                    if secili:
                        ekle("yuksek", "ÇIKAR - eski koduyla geçmiş", ders,
                             "%s kodlu '%s' dersinden %s ile geçmiş (%s). "
                             "Aynı ders, kodu değişmiş; seçilmiş olması "
                             "hatalı." %
                             (eski["ders_kodu"], eski["ders_adi"],
                              eski["harf"], eski["yil"]), "MADDE 9/1-f")
                    else:
                        kod_degisenler.append((ders, eski))
                elif secili and not not_yukseltilebilir_mi(eski["harf"]):
                    ekle("yuksek", "VERME - zaten geçmiş", ders,
                         "%s notu var (%s); %s not yükseltmeye de uygun değil."
                         % (eski["harf"], eski["yil"], eski["harf"]),
                         "MADDE 9/1-d")
                elif secili:
                    ekle("bilgi", "Not yükseltme", ders,
                         "%s notunu yükseltmek için tekrar alıyor; "
                         "son alınan not geçerli olacak."
                         % eski["harf"], "MADDE 9/1-d")

            elif tekrar_gerekir_mi(durum):
                # Seçilmişse öğrenci doğrusunu yapmış, eylem gerekmiyor.
                # Seçilmemişse zaten "Alttan ders SEÇİLMEMİŞ" uyarısı var.
                ekle("bilgi", "ALTTAN ders", ders,
                     "%s yılında %s almış, tekrar alması gerekiyor."
                     % (eski["yil"], eski["harf"]), "MADDE 9/1-a")

                # MADDE 10/2: tekrarlanan derste devam şartı daha önce
                # yerine getirilmişse yeniden devam aranmaz. Kod değiştiği
                # için OBİS bunu göremiyor, dersi 'ilk kez alınıyor' sayıp
                # devam zorunlu gösterecek.
                if not ayni_kod and devam_saglanmis_mi(eski["harf"]):
                    ekle("orta", "DEVAM MUAFİYETİ - OBİS görmeyecek", ders,
                         "Eski kodla (%s) devam şartını sağlamış (%s notu, "
                         "devamsızlık yok). Yeni kodda OBİS bunu göremeyip "
                         "devamı zorunlu gösterecek; öğrencinin devam "
                         "zorunluluğu YOK." % (eski["ders_kodu"], eski["harf"]),
                         "MADDE 10/2")

            # --- AKTS değişmiş mi? ------------------------------------------
            eski_akts = eski.get("akts")
            yeni_akts = ders.get("akts")
            if (eski_akts and yeni_akts and eski_akts != yeni_akts):
                # Kalınan dersin AKTS'si değiştiyse öğrenci dersi yeni AKTS
                # ile tekrar alacak; mezuniyet toplamı ve yarıyıl yükü
                # etkilenir. Danışman ekstra dikkat etmeli.
                if tekrar_gerekir_mi(durum):
                    ekle("orta", "AKTS DEĞİŞMİŞ - alttan ders", ders,
                         "Kaldığı dersi %s AKTS olarak almıştı, tekrar "
                         "alacağı ders %s AKTS. Fark: %+d AKTS."
                         % (eski_akts, yeni_akts, yeni_akts - eski_akts),
                         "MADDE 8/3")
                else:
                    # Geçilmiş ders: mezuniyette geçtiği AKTS sayılır,
                    # yeni müfredattaki değer değil.
                    ekle("bilgi", "AKTS değişmiş (geçilmiş ders)", ders,
                         "%s AKTS ile geçmiş, yeni müfredatta %s AKTS. "
                         "Mezuniyet toplamında geçtiği %s AKTS sayılır."
                         % (eski_akts, yeni_akts, eski_akts), "MADDE 8/3")

        # --- Ad benzer ama emin değiliz -> danışman baksın ------------------
        elif kayit["tip"] == "benzer":
            aday = kayit["aday"]
            ekle("orta", "Aynı ders olabilir - DOĞRULA", ders,
                 "Transkriptte %s '%s' (%s, %s AKTS, %%%d benzer). "
                 "Aynı dersse verilmemeli." %
                 (aday["ders_kodu"], aday["ders_adi"], aday["harf"],
                  aday["akts"], round(kayit["benzerlik"] * 100)),
                 "MADDE 9/1-f")

    # --- Öğrencinin kendi denemeleri arasında AKTS değişmiş mi? ------------
    for tekrar in transkript.get("tekrar_edilen", []):
        aktsler = []
        for deneme in transkript["denemeler"]:
            if deneme["ders_kodu"] == tekrar["ders_kodu"]:
                aktsler.append(deneme["akts"])
        if len(set(aktsler)) > 1:
            uyarilar.append({
                "onem": "orta", "baslik": "AKTS değişmiş (geçmiş denemeler)",
                "aciklama": "Aynı ders farklı AKTS'lerle alınmış: %s. "
                            "Toplam AKTS hesabı etkilenir." %
                            " -> ".join(str(a) for a in aktsler),
                "ders_no": tekrar["ders_kodu"], "ders_adi": tekrar["ders_adi"],
                "akts": tekrar["guncel"]["akts"], "kaynak": "MADDE 14/2",
            })

    # Kodu değişmiş ama seçilmemiş dersler: tek özet not.
    if kod_degisenler:
        ornek = ", ".join("%s→%s %s" % (e["ders_kodu"], d.get("ders_no"),
                                        (d.get("ders_adi") or "")[:24])
                          for d, e in kod_degisenler[:4])
        if len(kod_degisenler) > 4:
            ornek += " ve %d ders daha" % (len(kod_degisenler) - 4)
        uyarilar.append({
            "onem": "bilgi", "baslik": "Müfredat kod değişikliği",
            "aciklama": "OBİS %d dersi 'hiç alınmamış' gösteriyor ama "
                        "öğrenci bunları eski koduyla geçmiş: %s. "
                        "Eklenmemeli." % (len(kod_degisenler), ornek),
            "ders_no": None, "ders_adi": None, "kaynak": "MADDE 9/1-f",
        })

    sira = {"yuksek": 0, "orta": 1, "bilgi": 2}
    uyarilar.sort(key=lambda u: (sira.get(u["onem"], 9), u["ders_no"] or ""))
    return uyarilar
