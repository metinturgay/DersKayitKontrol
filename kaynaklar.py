# -*- coding: utf-8 -*-
"""Danışmandan belgeleri alır, doğrular ve yerel kurulumu kurar.

Akış (baslat.py bunu sicil/şifreden ÖNCE çağırır):

  1. Elde ne var? Bölüm ve kullanılan belgeler YOLLARIYLA gösterilir.
  2. "Bu belgelerle devam edilsin mi?"  -> evet ise hiçbir şey değişmez.
  3. Hayır ise: Okutulacak Dersler belgeleri tek tek istenir (istenildiği
     kadar; "tamam" yazınca biter), sonra ders programı istenir.
  4. Her belge ALINIR ALINMAZ çözümlenir ve NE OKUNDUĞU yazılır. Belge
     anlaşılmazsa kabul EDİLMEZ.
  5. Her belgenin GİRİŞ YILI teyit ettirilir - asla sessizce tahmin
     edilmez, çünkü yanlış yıl sessizce yanlış AKTS demektir.
  6. Belgeler veri-yerel/ altına kopyalanır, çözülmüş hâlleri üretilir,
     profil yazılır ve EN SON damga atılır.

Damga en sonda: yarım kalmış bir kurulum (Ctrl+C, bozuk belge, dolu
disk) devreye giremesin diye. Bkz. yollar.yerel_hazir_mi().
"""
import datetime
import io
import json
import os
import shutil
import sys
from pathlib import Path

import yollar

BELGE_UZANTISI = ".docx"
PROGRAM_UZANTISI = (".xlsx", ".xlsm")
BITIR = ("tamam", "bitti", "son", "q")

# Peş peşe kaç anlamsız cevaptan sonra vazgeçilir. Sonsuz döngüye karşı:
# sor() Ctrl+C/EOF'ta None döndürür, ama kullanıcı ısrarla boş ENTER'a
# basarsa ya da otomatik bir çağrı akışa düşerse de çıkış olmalı.
# Ölçüldü (mutasyon denemesi): belge_dongusu "en az bir belge" isterken
# cevaplar tükendi ve döngü SONSUZA kadar döndü.
VAZGECME_ESIGI = 5


# =========================================================================
#  Girdi yardımcıları
# =========================================================================
def yol_temizle(metin):
    """Kullanıcının yapıştırdığı yolu kullanılabilir hâle getirir.

    Dosyayı pencereye sürükleyip bırakmak yolu tırnak içinde veriyor;
    kopyala-yapıştır da baş/son boşluk bırakabiliyor. Bunlar
    temizlenmezse "dosya bulunamadı" denip kullanıcı haklı olarak
    şaşırıyor.
    """
    y = (metin or "").strip()
    for tirnak in ('"', "'"):
        if len(y) >= 2 and y[0] == tirnak and y[-1] == tirnak:
            y = y[1:-1]
    return y.strip()


def etkilesim_var():
    """Bu oturumda soru sorulabilir mi?

    Script'ten ya da zamanlanmış görevden çağrılan exe input() üzerinde
    ASILI KALMAMALI. stdin bir terminale bağlı değilse soru sormuyoruz.
    """
    try:
        return bool(sys.stdin) and sys.stdin.isatty()
    except (AttributeError, ValueError):
        return False


# =========================================================================
#  Elde ne var?
# =========================================================================
def mevcut_kaynaklar():
    """Şu an KULLANILAN belgeler: [(etiket, yol, açıklama)]"""
    import mufredat_arsivi as ma

    satirlar = []
    arsiv = ma.belgeleri_bul()
    for yil, yol in arsiv:
        satirlar.append(("%d girişliler" % yil, yol, ""))
    if not arsiv:
        tek = yollar.veri("mufredat.docx")
        coz = yollar.veri("mufredat.json")
        if tek.exists():
            satirlar.append(("tüm kohortlar", str(tek), "tek belge"))
        elif coz.exists():
            satirlar.append(("tüm kohortlar", str(coz),
                             "çözülmüş hâli (belge yok)"))
    return satirlar


def mevcut_program():
    """Şu an kullanılan ders programı: (yol, açıklama) ya da None."""
    for ad in ("ders_programi.xlsx", "ders_programi.xlsm"):
        p = yollar.veri(ad)
        if p.exists():
            return str(p), ""
    c = yollar.veri("cakismalar.json")
    if c.exists():
        return str(c), "çözülmüş hâli (xlsx yok)"
    return None


def ozet_yaz(yaz=print):
    """Bölüm ve kullanılan belgeleri YOLLARIYLA yazar."""
    import bolum

    yaz("")
    yaz("  BÖLÜM     : %s" % bolum.tanim())
    yaz("  Profil    : %s  (%s)" % (bolum.yol(), bolum.kaynak()))
    yaz("")
    yaz("  Okutulacak Dersler belgeleri:")
    kaynaklar = mevcut_kaynaklar()
    if not kaynaklar:
        yaz("      YOK")
    for etiket, yol, ek in kaynaklar:
        yaz("      %-18s %s%s"
            % (etiket, yol, ("   [%s]" % ek) if ek else ""))
    yaz("")
    p = mevcut_program()
    yaz("  Ders programı:")
    if p:
        yaz("      %s%s" % (p[0], ("   [%s]" % p[1]) if p[1] else ""))
    else:
        yaz("      YOK  (çakışma denetimi kapalı)")


# =========================================================================
#  Belge doğrulama
# =========================================================================
def belge_dogrula(yol):
    """docx'i ÇÖZÜMLEYEREK doğrular. (tamam, özet, veri) döndürür.

    Belge alınır alınmaz çözümlenir: şablon farkı burada yakalanır.
    Bu adım olmadan başka bir fakültenin farklı şablonlu belgesi
    sessizce boş bir müfredata dönüşüyordu.
    """
    import mufredat

    if not os.path.isfile(yol):
        return False, "Bulunamadı: %s" % yol, None
    if not yol.lower().endswith(BELGE_UZANTISI):
        return False, ("Word belgesi (%s) bekleniyor, bu değil: %s"
                       % (BELGE_UZANTISI, os.path.basename(yol))), None
    try:
        veri = mufredat.oku(yol)
    except mufredat.BelgeAnlasilmadi as e:
        return False, str(e), None
    except Exception as e:                # noqa: BLE001 - kullanıcıya göster
        return False, "Belge okunamadı (%s): %s" % (type(e).__name__, e), None

    y = veri["yariyillar"]
    toplam = sum((b.get("toplam_akts") or 0) for b in y.values())
    ozet = ("%d ders · %d yarıyıl · yarıyıl toplamları %s = %d AKTS"
            % (len(veri["dersler"]), len(y),
               " + ".join(str(y[k].get("toplam_akts") or "?")
                          for k in sorted(y)), toplam))
    return True, ozet, veri


def program_dogrula(yol):
    """xlsx'i ÇÖZÜMLEYEREK doğrular. (tamam, özet, None)"""
    import ders_programi as dp

    if not os.path.isfile(yol):
        return False, "Bulunamadı: %s" % yol, None
    if not yol.lower().endswith(PROGRAM_UZANTISI):
        return False, ("Excel dosyası (%s) bekleniyor, bu değil: %s"
                       % ("/".join(PROGRAM_UZANTISI),
                          os.path.basename(yol))), None
    try:
        yerlesim, ayrinti = dp.programi_oku(yol)
    except dp.ProgramAnlasilmadi as e:
        return False, str(e), None
    except Exception as e:                # noqa: BLE001
        return False, "Program okunamadı (%s): %s" % (type(e).__name__, e), None

    cakismalar = dp.cakismalari_bul(yerlesim)
    return True, ("%d ders · %d çakışan ders çifti"
                  % (len(yerlesim), len(cakismalar))), None


# =========================================================================
#  Soru döngüleri
# =========================================================================
def _iptal_mi(cevap):
    """sor() vazgeçme bildirdi mi? (Ctrl+C / EOF)"""
    return cevap is None


def yil_sor(yol, sor):
    """Belgenin GİRİŞ YILI. Dosya adından çıkarsa teyit ettirilir.

    Asla sessizce tahmin edilmez: yıl, kohort hesabının tabanıdır ve
    yanlış yıl sessizce yanlış AKTS demektir.
    """
    import mufredat_arsivi as ma

    oneri = ma.yil_coz(yol)
    ad = os.path.basename(yol)
    kotu = 0
    while True:
        if oneri:
            istem = ('  "%s"' + chr(10)
                     + "     -> bu belge %d GİRİŞLİLER için mi? [e/h] ")
            c = sor(istem % (ad, oneri))
            if _iptal_mi(c):
                return None
            if c.strip().lower().startswith("e"):
                return oneri
            oneri = None
            continue
        c = sor("     Bu belge hangi yıl girişliler için geçerli? "
                "(örn. 2024) ")
        if _iptal_mi(c):
            return None
        c = c.strip()
        if c.isdigit() and 1990 <= int(c) <= 2100:
            return int(c)
        kotu += 1
        if kotu >= VAZGECME_ESIGI:
            print("     Vazgeçildi.")
            return None
        print("     Dört haneli bir giriş yılı yazın (örn. 2024).")


def belge_dongusu(sor):
    """Okutulacak Dersler belgelerini tek tek toplar.

    Kullanıcı istediği kadar belge verebilir; "tamam" yazınca biter.
    Her belge anında çözümlenir ve NE OKUNDUĞU yazılır.
    """
    print("")
    print("  OKUTULACAK DERSLER BELGELERİ")
    print("  " + "-" * 66)
    print("  Her belge BİR ÖĞRETİM YILINA aittir. Son 4-5 yılın belgesini")
    print("  verirseniz AKTS değişimleri ve müfredata sonradan eklenen")
    print("  dersler kendiliğinden çıkar. EN AZ BİR belge gerekli.")
    print("")
    print("  Dosyayı bu pencereye sürükleyip bırakabilirsiniz.")
    print("  Bitirmek için 'tamam' yazın.")
    print("")

    secilenler = {}          # yıl -> yol
    bos = 0
    while True:
        istem = ("  [%d belge] Yeni belgenin yolu (bitirmek için 'tamam'): "
                 % len(secilenler))
        ham = sor(istem)
        if _iptal_mi(ham):
            return None
        y = yol_temizle(ham)
        # Sonsuz döngüye karşı çıkış: peş peşe anlamsız cevap gelirse
        # vazgeç. Belge vermeden 'tamam' demek kabul edilmiyor ama bu,
        # cevabı tükenen bir çağrıyı döngüde asılı bırakmamalı.
        if not y or y.lower() in BITIR:
            bos += 1
            if bos >= VAZGECME_ESIGI and not secilenler:
                print("     Vazgeçildi; belge alınmadı.")
                return None
        else:
            bos = 0
        if y.lower() in BITIR:
            if secilenler:
                return secilenler
            print("     En az bir belge gerekli; bu olmadan araç çalışamaz.")
            continue
        if not y:
            continue

        if os.path.isdir(y):
            import glob
            adaylar = sorted(glob.glob(os.path.join(y, "*" + BELGE_UZANTISI)))
            if not adaylar:
                print("     Bu klasörde .docx yok: %s" % y)
                continue
            print("     Klasörde %d belge var:" % len(adaylar))
            for a in adaylar:
                print("       %s" % os.path.basename(a))
            print("     Hepsini tek tek verin ya da klasör yerine dosya "
                  "yolu yazın.")
            continue

        tamam, ozet, _veri = belge_dogrula(y)
        if not tamam:
            print("")
            print("     KABUL EDİLMEDİ")
            for satir in str(ozet).splitlines():
                print("       " + satir)
            print("")
            continue

        yil = yil_sor(y, sor)
        if yil is None:
            return None
        if yil in secilenler:
            print("     %d için zaten bir belge vardı, bu onun yerine "
                  "geçiyor." % yil)
        secilenler[yil] = y
        print("     ✓ %d  %s" % (yil, ozet))
        print("")


def program_sor(sor):
    """Ders programı xlsx'ini ister. Boş bırakılabilir."""
    print("")
    print("  DERS PROGRAMI")
    print("  " + "-" * 66)
    print("  Bu yarıyılın ders programı (xlsx). Çakışma denetimi buna")
    print("  dayanır (MADDE 9/1-b). Vermezseniz yalnız o denetim kapanır,")
    print("  geri kalan her şey çalışır.")
    print("")
    kotu = 0
    while True:
        ham = sor("  Ders programının yolu (atlamak için boş bırakın): ")
        if _iptal_mi(ham):
            return None
        y = yol_temizle(ham)
        if not y:
            print("     Atlandı - ÇAKIŞMA DENETİMİ KAPALI olacak.")
            return ""
        tamam, ozet, _ = program_dogrula(y)
        if not tamam:
            print("")
            print("     KABUL EDİLMEDİ")
            for satir in str(ozet).splitlines():
                print("       " + satir)
            print("")
            kotu += 1
            if kotu >= VAZGECME_ESIGI:
                print("     Vazgeçildi; ders programı alınmadı.")
                return ""
            continue
        print("     ✓ %s" % ozet)
        return y


# =========================================================================
#  Kurulum
# =========================================================================
# NEDEN YENİDEN BAŞLATMA GEREKİYOR
# --------------------------------
# yonetmelik.py, ders_programi.py ve ozet.py bölüm profilini IMPORT
# ANINDA okuyup modül sabitlerine bağlıyor (yarıyıl planı, TOS listesi,
# saat sütunları, asenkron ders listesi...). Kurulum ile tarama aynı
# çalışmada olursa profil yenilense bile bu sabitler ESKİ değerde kalır
# ve program hiç hata vermeden ÖNCEKİ bölümün planıyla hesaplar.
#
# Bu yüzden kurulum yalnızca BELGELERİ ve PROFİLİ yazar; çözülmüş
# hâller (mufredat.json, cakismalar.json) yeniden başlatmadan SONRA,
# doğru profille üretilir.
TURETILEN = ("mufredat.json", "cakismalar.json", "mufredat_arsivi.json")


def kur(belgeler, program_yolu, cevaplar, yaz=print):
    """Belgeleri yerel kuruluma kurar ve profili yazar.

    Damga EN SON atılır: yarım kalmış bir kurulum devreye giremesin.
    Döner: (tamam, mesaj)
    """
    import bolum
    import kurulum

    yerel = yollar.yerel_veri_kok()
    yaz("")
    yaz("  Kuruluyor: %s" % yerel)

    # Yazma izni ÖNCE sınanır: exe salt okunur bir klasörde duruyorsa
    # bunu kurulumun ortasında değil başında öğrenmeliyiz.
    try:
        yerel.mkdir(parents=True, exist_ok=True)
        deneme = yerel / ".yazma_denemesi"
        deneme.write_text("x", encoding="utf-8")
        deneme.unlink()
    except OSError as e:
        return False, ("Bu klasöre yazılamıyor: %s\n  %s\n"
                       "  Programı Masaüstü gibi yazma izniniz olan bir "
                       "klasöre taşıyın." % (yerel, e))

    # 1. Belgeleri kopyala
    # veri_yaz() DOSYA yolu için parent'ı açar; burada hedef bir KLASÖR,
    # onu ayrıca oluşturmak gerekiyor.
    arsiv = yollar.veri_yaz("mufredat")
    arsiv.mkdir(parents=True, exist_ok=True)
    for eski in sorted(arsiv.glob("*.docx")):
        eski.unlink()
    for yil, kaynak in sorted(belgeler.items()):
        hedef = arsiv / ("%d.docx" % yil)
        shutil.copy2(kaynak, hedef)
        yaz("    + %s" % hedef.name)
    hedef = None
    if program_yolu:
        hedef = yollar.veri_yaz("ders_programi" +
                                os.path.splitext(program_yolu)[1].lower())
        shutil.copy2(program_yolu, hedef)
        yaz("    + %s" % hedef.name)

    # 2. Profili üret (belgelerden türetilebilen + insandan alınanlar)
    eski_arsiv, eski_program = kurulum.ARSIV, kurulum.PROGRAM_XLSX
    try:
        kurulum.ARSIV = arsiv
        if program_yolu:
            kurulum.PROGRAM_XLSX = Path(program_yolu)
        profil, bilgi = kurulum.taslak(cevaplar, klasor=arsiv)
    finally:
        kurulum.ARSIV, kurulum.PROGRAM_XLSX = eski_arsiv, eski_program

    agir = [m for s, m in bolum.denetle(profil) if s == "HATA"]
    if agir:
        return False, ("Üretilen profil kullanılamaz:\n  %s"
                       % "\n  ".join(agir))

    kurulum.yaz(profil, yollar.veri_yaz(bolum.PROFIL_ADI))
    yaz("    + %s" % bolum.PROFIL_ADI)

    # 3. Çözülmüş hâller yeniden başlatmadan SONRA üretilecek; eskileri
    #    kalırsa yeni belgelerle ESKİ çözümleme karışır.
    for ad in TURETILEN:
        p = yerel / ad
        if p.exists():
            p.unlink()

    # 4. Damga EN SON
    yollar.damga_yaz({
        "tarih": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "bolum": (profil.get("bolum") or {}).get("ad") or "",
        "belgeler": {str(y): os.path.basename(k)
                     for y, k in sorted(belgeler.items())},
        "ders_programi": os.path.basename(program_yolu) if program_yolu
                         else None,
        # Yerel kurulumun SAHİP OLDUĞU her ad. Arşiv KLASÖRÜ ve ders
        # programı dosyası da burada olmalı: listede olmayan bir ad
        # gömülü köke düşer ve kurulum "yarım" kalır - ölçüldü, arşiv
        # klasörü listede olmadığı için belgeler bulunamıyor ve
        # türetilenler hiç üretilmiyordu.
        "dosyalar": ([bolum.PROFIL_ADI, "mufredat"] + list(TURETILEN)
                     + ([os.path.basename(str(hedef))]
                        if program_yolu else [])),
    })
    return True, "Kurulum tamam."


def turetilenleri_hazirla(yaz=print):
    """Eksik çözülmüş dosyaları üretir (yeniden başlatmadan sonra).

    Bu adım kurulumdan AYRI çalışır, çünkü artık modüller DOĞRU profille
    yüklenmiştir. Kurulumla aynı çalışmada üretilseydi eski bölümün
    saat sütunları ve asenkron ders listesi kullanılırdı.
    """
    import ders_programi
    import mufredat
    import mufredat_arsivi

    if not yollar.yerel_hazir_mi():
        return True
    yerel = yollar.yerel_veri_kok()
    arsiv = yollar.veri("mufredat")
    belgeler = mufredat_arsivi.belgeleri_bul(arsiv)

    if not (yerel / "mufredat.json").exists():
        if not belgeler:
            yaz("  UYARI: yerel kurulumda müfredat belgesi bulunamadı: %s"
                % arsiv)
            return False
        en_yeni = belgeler[-1][1]
        yaz("  Müfredat çözülüyor: %s" % os.path.basename(en_yeni))
        yol, veri = mufredat.kaydet(en_yeni)
        yaz("    %d ders, %d yarıyıl" % (len(veri["dersler"]),
                                         len(veri["yariyillar"])))

    if not (yerel / "mufredat_arsivi.json").exists() and len(belgeler) >= 1:
        yol, veri, _ = mufredat_arsivi.kaydet(arsiv)
        yaz("    arşiv: %d yıl, %d AKTS değişimi, %d sonradan eklenen ders"
            % (len(veri.get("yillar") or ()),
               len(veri.get("akts_degisenler") or ()),
               len(veri.get("sonradan_eklenen_dersler") or {})))

    if not (yerel / "cakismalar.json").exists():
        xlsx = None
        for ad in ("ders_programi.xlsx", "ders_programi.xlsm"):
            p = yerel / ad
            if p.exists():
                xlsx = p
                break
        if xlsx:
            yaz("  Ders programı çözülüyor: %s" % xlsx.name)
            yol, veri = ders_programi.kaydet(str(xlsx))
            yaz("    %d ders, %d çakışan çift"
                % (len(veri["dersler"]), len(veri["cakismalar"])))
    return True
