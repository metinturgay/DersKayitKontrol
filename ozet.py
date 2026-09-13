# -*- coding: utf-8 -*-
"""Danışman özeti motoru.

Ders kayıt sayfası + transkript + yönetmelik kurallarını birleştirip
bir öğrenci için "durum / dikkat / yapılacak" özeti üretir.

Bu modül KARAR VERMEZ ve HİÇBİR ŞEY DEĞİŞTİRMEZ. Dikkatli bir danışmanın
tek tek bakacağı her şeyi toplayıp önüne koyar; onay/ret/ekleme/çıkarma
kararı danışmanındır.
"""
import bolum
import mufredat as mf
import yonetmelik as ym


def ym_mufredat_akts(mufredat, ders_no):
    """Müfredat belgesindeki AKTS; yoksa None."""
    return mf.akts(mufredat, ders_no, None)

# Uyarı önem seviyeleri
YAPILACAK = "yapilacak"   # danışman müdahale etmeli
DIKKAT = "dikkat"         # kontrol etmeli
BILGI = "bilgi"           # kayda geçsin

ONEM_SIRASI = {YAPILACAK: 0, DIKKAT: 1, BILGI: 2}

# yonetmelik.danisman_uyarilari() önem adlarını buraya çeviriyoruz
_ONEM_ESLESMESI = {"yuksek": YAPILACAK, "orta": DIKKAT, "bilgi": BILGI}

# Laboratuvar / uygulama dersleri: FF notu devamsızlıktan mı uygulamadan
# mı belli olmadığı için devam muafiyeti bu derslerde teyit ister
# (MADDE 10/5); devamsızlık hakkı da %30 değil %20'dir (MADDE 10/1).
# HANGİ dersler böyle olduğu BÖLÜM KARARIDIR - bir zamanlar Matematik'in
# iki fizik laboratuvarı doğrudan buraya yazılıydı.
LABORATUVAR_ADLARI = tuple(bolum.program_ayarlari()["uygulamali_dersler"])

# ders_kaydini_coz()'un sekme adları. Bölüm sekmesi programın kendi
# müfredatı; diğeri Üniversite genelindeki yaygın seçmeli havuzu.
BOLUM_SEKMESI = "Bölüm Dersleri"


def _uyari(onem, baslik, aciklama, kaynak="", ders_no=None, ders_adi=None):
    return {"onem": onem, "baslik": baslik, "aciklama": aciklama,
            "kaynak": kaynak, "ders_no": ders_no, "ders_adi": ders_adi}


def _laboratuvar_mi(ders_adi):
    return ym.ders_adi_anahtari(ders_adi) in LABORATUVAR_ADLARI


def _devam_gerekli_mi(ders, eslesme_dizini):
    """Bu derse DEVAM etmek zorunda mı? (MADDE 10/2)

    Danışman kuralı: öğrenci dersi daha önce aldıysa - KODU FARKLI OLSA
    BİLE - ve F dışında bir notla kaldıysa, derse devam etmiştir; tekrarda
    yeniden devam aranmaz. Devamsızlıktan kalma (F/DZ) bunun dışında.

    Dönen: (devam_gerekli, gerekce)
    """
    kod = ders.get("ders_no")
    # 1) OBİS'in kendi işareti: DVLT = devamlı tekrar (devam sağlanmış)
    if (ders.get("dvlt") or "").strip():
        return False, "OBİS DVLT (devamlı tekrar) işaretli"
    # 2) Transkript: eski kodla bile olsa daha önce alınmış mı?
    kayit = eslesme_dizini.get(kod)
    eski = (kayit or {}).get("eslesme")
    if eski is not None and (kayit or {}).get("tip") in ("kod", "ad"):
        harf = eski.get("harf")
        if ym.devam_saglanmis_mi(harf):
            ayni = kayit.get("tip") == "kod"
            return False, ("%s yılında %s notu almış%s - devam şartını "
                           "sağlamış" % (eski.get("yil"), harf,
                                         "" if ayni else
                                         " (eski kod %s)" % eski.get("ders_kodu")))
        return True, "%s notu devamsızlıktan - devam zorunlu" % harf
    # 3) OBİS DVST = devamsız tekrar
    if (ders.get("dvst") or "").strip():
        return True, "OBİS DVST (devamsız tekrar) işaretli"
    return True, "ilk kez alınıyor"


def _oneriler(birakilacak, ilgili_kodlar, bolum_dersleri, dizin, harita,
              ders_dizini, es_dizin, ad_dizini, korunacak=None):
    """Bırakılacak dersin yerine ne konabilir?

    Aday: AYNI TÜRDEN (seçmeli yerine seçmeli, TOS yerine TOS), aynı
    dönemden, kontenjanı açık, eklenebilir, henüz seçilmemiş ders.

    Çakışma değerlendirmesi devam zorunluluğunu hesaba katar: adayın,
    devam zorunluluğu OLMAYAN bir dersle çakışması engel değildir -
    öğrenci o derse zaten girmek zorunda değil (MADDE 10/2). Yalnızca
    devam zorunluluğu olan derslerle çakışma engeldir.

    korunacak: bu çiftte tutulacak dersin kodu. Onunla çakışan aday
    takası anlamsız kılar (aynı saat sorunu sürer), hiç önerilmez.

    Karar danışmanın; bu yalnızca listedir. Hiçbir aday tamamen temiz
    değilse en az engelleyen birkaçı yine gösterilir ki danışman
    manzarayı görsün - sessizce boş liste dönmek işe yaramaz.
    """
    kod_b = birakilacak.get("ders_no")
    b_donem = ym.donem_numarasi(birakilacak.get("donem"))
    tos_mu = kod_b in ym.TOS_DERSLERI
    if not tos_mu and not ym.secmeli_mi(birakilacak):
        return []          # zorunlu dersin yerine başka ders konmaz

    # Öğrencinin geri kalan dersleri; bunlardan yalnızca DEVAM ZORUNLU
    # olanlar bir adayı engeller.
    engelleyen = [k for k in set(ilgili_kodlar)
                  if k != kod_b and k in harita
                  and _devam_gerekli_mi(ders_dizini.get(k, {}), es_dizin)[0]]

    adaylar = []
    for d in bolum_dersleri:
        kod = d.get("ders_no")
        if kod == kod_b or d.get("secili"):
            continue
        if d.get("doldu") or not d.get("eklenebilir"):
            continue
        if ym.donem_numarasi(d.get("donem")) != b_donem:
            continue
        if tos_mu:
            if kod not in ym.TOS_DERSLERI:
                continue
        elif not ym.secmeli_mi(d) or kod in ym.TOS_DERSLERI:
            continue
        if kod not in harita:
            # Programda saati yok: çakışma bilinemez, yine de aday.
            adaylar.append({"ders_no": kod, "ders_adi": d.get("ders_adi"),
                            "akts": d.get("akts"), "catisma": [],
                            "saat_bilinmiyor": True})
            continue
        ad = harita[kod]["program_adi"]
        catisan_kod = [k for k in engelleyen
                       if dizin.get(ad, {}).get(harita[k]["program_adi"])]
        # Korunacak dersle çakışan aday bu çakışmayı ÇÖZMEZ; önermiyoruz.
        if korunacak and korunacak in catisan_kod:
            continue
        catisan = [ad_dizini.get(k) or k for k in catisan_kod]
        adaylar.append({"ders_no": kod, "ders_adi": d.get("ders_adi"),
                        "akts": d.get("akts"), "catisma": catisan,
                        "saat_bilinmiyor": False})

    # Önce hiç engellenmeyenler, sonra AKTS'si bırakılana en yakın olan
    # (AKTS dengesi bozulmasın), sonra ada göre.
    hedef_akts = birakilacak.get("akts") or 0
    adaylar.sort(key=lambda x: (len(x["catisma"]), x["saat_bilinmiyor"],
                                abs((x["akts"] or 0) - hedef_akts),
                                x["ders_adi"] or ""))
    return adaylar[:5]


def _cakismalari_denetle(program, bolum_dersleri, secili, alttan_acik,
                         uyarilar, eslesmeler=None, hedef_donem=None):
    """Ders programı çakışmalarını bulur (MADDE 9/1-b).

    İki tür çakışma raporlanıyor:
      1. Öğrencinin SEÇTİĞİ iki ders aynı saatte  -> biri bırakılmalı
      2. ALTTAN dersi ile seçtiği bir ders aynı saatte -> yönetmelik
         alttan dersi öncelikli sayıyor, seçilen bırakılmalı

    Her çift ayrıca DEVAM ZORUNLULUĞU açısından değerlendiriliyor: bir
    tarafta devam zorunluluğu yoksa öğrenci o derse girmeyebilir, çakışma
    engel değildir (bildirilir ama "değiştirilmesi zorunlu değil").

    Programda karşılığı bulunamayan ders sessizce atlanmaz; sayısı
    raporlanır ki eksik kontrol yaptığımızı danışman bilsin.
    """
    import ders_programi as dprog

    harita = dprog.program_eslestir(bolum_dersleri, program)
    dizin = dprog.cakisma_dizini(program)
    ad_dizini = {d.get("ders_no"): d.get("ders_adi") for d in bolum_dersleri}

    secili_kodlar = [d.get("ders_no") for d in (secili or [])]
    alttan_kodlar = [a["ders"].get("ders_no") for a in (alttan_acik or [])]
    # Ders kaydı ve transkript eşleşmesi: devam zorunluluğu buradan çıkıyor.
    ders_dizini = {d.get("ders_no"): d for d in bolum_dersleri}
    for a in (alttan_acik or []):
        ders_dizini.setdefault(a["ders"].get("ders_no"), a["ders"])
    es_dizin = {e["ders"].get("ders_no"): e for e in (eslesmeler or [])}
    esles = {k: harita[k]["program_adi"] for k in
             set(secili_kodlar) | set(alttan_kodlar) if k in harita}

    def _ad(kod):
        return ad_dizini.get(kod) or kod

    # İlgilendiğimiz dersler: seçtikleri + alması gereken alttan dersler.
    # Bir ders ikisinde birden olabilir (alttan dersi seçmişse); çiftleri
    # bir kez raporlamak için küme üzerinden gidiyoruz.
    alttan_kume = set(alttan_kodlar)
    ilgili = sorted(set(secili_kodlar) | alttan_kume)
    bulunanlar = []

    for i, a in enumerate(ilgili):
        for b in ilgili[i + 1:]:
            if a not in esles or b not in esles:
                continue
            saatler = dizin.get(esles[a], {}).get(esles[b])
            if not saatler:
                continue

            a_alt, b_alt = a in alttan_kume, b in alttan_kume
            if a_alt and not b_alt:
                tip, oncelikli, birakilacak = "alttan", a, b
            elif b_alt and not a_alt:
                tip, oncelikli, birakilacak = "alttan", b, a
            elif a_alt and b_alt:
                tip, oncelikli, birakilacak = "iki_alttan", a, b
            else:
                tip, oncelikli, birakilacak = "secili", a, b

            # --- Devam zorunluluğu (MADDE 10/2) ------------------------
            # Bir tarafta devam zorunluluğu yoksa öğrenci o derse
            # girmeyebilir; çakışma fiilen engel değildir.
            a_dev, a_neden = _devam_gerekli_mi(ders_dizini.get(oncelikli, {}),
                                               es_dizin)
            b_dev, b_neden = _devam_gerekli_mi(ders_dizini.get(birakilacak, {}),
                                               es_dizin)

            # --- MADDE 10/1: devamsızlık hakkı ------------------------
            # İki derste de devam zorunlu olsa bile, çakışan saatler
            # devamsızlık hakkının (teorikte %30) içinde kalıyorsa
            # öğrenci ikisini birden alabilir: çakışan saatlerde birine
            # girer, kaçırdığı saatler haktan düşer.
            hak = None
            if a_dev and b_dev:
                pa = harita.get(oncelikli, {}).get("program_adi")
                pb = harita.get(birakilacak, {}).get("program_adi")
                sa = ((program.get("dersler") or {}).get(pa) or {})
                sb = ((program.get("dersler") or {}).get(pb) or {})
                if sa.get("saat_sayisi") and sb.get("saat_sayisi"):
                    hak = ym.cakisma_devamsizliga_sigar_mi(
                        sa["saat_sayisi"], sb["saat_sayisi"], len(saatler),
                        a_uygulama=_laboratuvar_mi(_ad(oncelikli)),
                        b_uygulama=_laboratuvar_mi(_ad(birakilacak)))
            hak_ici = bool(hak and hak["sigar"])
            zorunlu = a_dev and b_dev and not hak_ici

            kayit = {
                "tip": tip, "a": oncelikli, "a_ad": _ad(oncelikli),
                "b": birakilacak, "b_ad": _ad(birakilacak),
                "saatler": saatler,
                "b_secili": birakilacak in secili_kodlar,
                "a_devam": a_dev, "a_devam_neden": a_neden,
                "b_devam": b_dev, "b_devam_neden": b_neden,
                "cozulmeli": zorunlu,
                "hak_ici": hak_ici, "devamsizlik": hak,
                "oneriler": [], "a_oneriler": [],
                "a_zorunlu_ders": False, "b_zorunlu_ders": False,
            }
            if zorunlu or hak_ici:
                # Kural gereği bırakılması gereken taraf için öneri.
                # hak_ici olanlarda da öneriyoruz: çakışmasız bir
                # alternatif varsa devamsızlık hakkını harcamaya gerek yok.
                kayit["oneriler"] = _oneriler(
                    ders_dizini.get(birakilacak, {}), ilgili,
                    bolum_dersleri, dizin, harita, ders_dizini, es_dizin,
                    ad_dizini, korunacak=oncelikli)
                # İki ders de öğrencinin serbest seçimiyse danışman
                # hangisini bırakacağına kendi karar verir; öteki taraf
                # için de öneri veriyoruz.
                if tip == "secili":
                    kayit["a_oneriler"] = _oneriler(
                        ders_dizini.get(oncelikli, {}), ilgili,
                        bolum_dersleri, dizin, harita, ders_dizini,
                        es_dizin, ad_dizini, korunacak=birakilacak)
                kayit["b_zorunlu_ders"] = not (
                    ym.secmeli_mi(ders_dizini.get(birakilacak, {}))
                    or birakilacak in ym.TOS_DERSLERI)
                kayit["a_zorunlu_ders"] = not (
                    ym.secmeli_mi(ders_dizini.get(oncelikli, {}))
                    or oncelikli in ym.TOS_DERSLERI)
            bulunanlar.append(kayit)

    zorunlular = [c for c in bulunanlar if c["cozulmeli"]]
    hak_icinde = [c for c in bulunanlar if c.get("hak_ici")]
    serbestler = [c for c in bulunanlar
                  if not c["cozulmeli"] and not c.get("hak_ici")]

    if zorunlular:
        ilk = zorunlular[:3]
        ornek = "; ".join("%s ↔ %s" % (c["a_ad"], c["b_ad"]) for c in ilk)
        if len(zorunlular) > 3:
            ornek += " ve %d çift daha" % (len(zorunlular) - 3)
        alttan_sayisi = sum(1 for c in zorunlular if c["tip"] == "alttan")
        onerili = sum(1 for c in zorunlular if c["oneriler"])
        uyarilar.append(_uyari(
            YAPILACAK,
            "ÇAKIŞMA - DEĞİŞTİRİLMELİ (%d çift)" % len(zorunlular),
            "%s. Her iki derste de devam zorunluluğu var, ikisine birden "
            "girilemez. %s%sAyrıntı ve öneriler aşağıdaki çakışma "
            "tablosunda."
            % (ornek,
               ("Bunların %d tanesinde alttan ders var; yönetmelik alttan "
                "dersi öncelikli sayıyor, diğeri bırakılmalı. "
                % alttan_sayisi) if alttan_sayisi else "",
               ("%d tanesi için yerine konabilecek ders önerildi. "
                % onerili) if onerili else ""),
            "MADDE 9/1-b"))

    if hak_icinde:
        ornek = "; ".join("%s ↔ %s" % (c["a_ad"], c["b_ad"])
                          for c in hak_icinde[:3])
        if len(hak_icinde) > 3:
            ornek += " ve %d çift daha" % (len(hak_icinde) - 3)
        temiz = sum(1 for c in hak_icinde
                    if any(not x["catisma"]
                           for x in (c["oneriler"] or []) +
                           (c.get("a_oneriler") or [])))
        uyarilar.append(_uyari(
            DIKKAT,
            "Çakışma devamsızlık hakkına sığıyor (%d çift)" % len(hak_icinde),
            "%s. Çakışan saatler devamsızlık hakkının (teorikte %%30) "
            "içinde kalıyor; öğrenci ikisini birden alabilir. ANCAK hakkın "
            "büyük kısmı programa harcanmış olur, hastalık/mazeret için pay "
            "kalmaz. %sKarar sizin." % (
                ornek,
                ("%d tanesinde çakışmasız alternatif var, hak harcamadan "
                 "çözülebilir. " % temiz) if temiz else ""),
            "MADDE 10/1"))

    if serbestler:
        ornek = "; ".join("%s ↔ %s" % (c["a_ad"], c["b_ad"])
                          for c in serbestler[:3])
        if len(serbestler) > 3:
            ornek += " ve %d çift daha" % (len(serbestler) - 3)
        uyarilar.append(_uyari(
            DIKKAT,
            "Çakışma var ama devam zorunluluğu yok (%d çift)"
            % len(serbestler),
            "%s. En az bir tarafta devam şartı daha önce sağlanmış "
            "(MADDE 10/2), öğrenci o derse girmek zorunda değil. "
            "DEĞİŞTİRİLMESİ ZORUNLU DEĞİL - bilginize. Sınav saatleri "
            "çakışırsa ayrıca bakılmalı." % ornek,
            "MADDE 10/2"))

    eslesmeyen = [k for k in set(secili_kodlar) if k not in harita]
    if eslesmeyen:
        uyarilar.append(_uyari(
            DIKKAT, "Programda bulunamayan ders",
            "Şu seçili derslerin ders programında karşılığı bulunamadı, "
            "çakışma kontrolü yapılamadı: %s"
            % ", ".join("%s %s" % (k, _ad(k)) for k in sorted(eslesmeyen))))

    return {"cakismalar": bulunanlar,
            "cakisma_cozulmeli": len(zorunlular),
            "cakisma_hak_ici": len(hak_icinde),
            "cakisma_serbest": len(serbestler),
            "program_eslesmeyen": eslesmeyen}


def ogrenci_ozeti(kayit, acilan_donemler=ym.GUZ_DONEMLERI,
                  donem_plani=None, program_yili=4, icinde_bulunulan_yil=None,
                  program=None, mufredat=None):
    """Bir öğrencinin tüm kurallara göre danışman özetini üretir.

    kayit: ders_kaydini_coz() çıktısı, içinde kayit["transkript"] olacak.
    """
    t = kayit.get("transkript") or {}
    katalog = kayit.get("katalog") or []
    secili = kayit.get("secili_dersler") or []
    uyarilar = []

    ozet = {
        "no": kayit.get("no"),
        "ad": kayit.get("ad"),
        "onay_durumu": kayit.get("durum"),
        "gano": kayit.get("genel_ort"),
        "secilen_akts": kayit.get("toplam_akts"),
        "secilen_ders_sayisi": kayit.get("ders_sayisi"),
        "obis_maks_akts": kayit.get("maks_akts"),
        "transkript_hatasi": t.get("hata"),
        "uyarilar": uyarilar,
    }

    if t.get("hata"):
        uyarilar.append(_uyari(
            YAPILACAK, "Transkript okunamadı",
            "Öğrencinin not durumu alınamadığı için kuralların çoğu "
            "uygulanamadı. Sayfayı elle kontrol edin.",
            ders_no=None))
        ozet["durum_rengi"] = YAPILACAK
        return ozet

    # ---------------------------------------------------------------
    #  1. Sınıf ve hedef dönem
    # ---------------------------------------------------------------
    alinan_donemler = sorted({d.get("donem") for d in t.get("denemeler") or []
                              if d.get("donem")})
    donem_durumu = ym.ogrenci_donem_durumu(alinan_donemler, acilan_donemler)
    ozet["donem_durumu"] = donem_durumu
    ozet["alinan_donemler"] = alinan_donemler

    # ---------------------------------------------------------------
    #  2. Katalog eşleştirmesi (eski kod / yeni kod)
    # ---------------------------------------------------------------
    # KAPSAM: Kurallar yalnızca BÖLÜM derslerine uygulanır. Sayfadaki
    # ikinci sekme (Yabancı Dilde Yaygın Seçmeli, MADDE 9/1-ı) Üniversite
    # genelindeki havuzdur; başka fakültelerin dersleri oradadır ve
    # bölümün müfredatıyla ilgisi yoktur. Onlar yalnızca seçilmişse
    # bilgi notu olarak raporlanır.
    # Sekme bilgisi yoksa bölüm dersi sayıyoruz: kuralların sessizce
    # devre dışı kalması, fazladan uyarı üretmekten daha tehlikeli.
    # AKTS için TEK DOĞRU KAYNAK müfredat belgesi (danışman kuralı:
    # kalınan/eksik ders yeni dönemde alınınca belgedeki AKTS geçerli).
    # OBİS katalogu farklı diyorsa belgeyi kullanıp danışmanı uyarıyoruz.
    katalog = [dict(d) for d in katalog]
    akts_farklari = []
    if mufredat:
        for d in katalog:
            belge = ym_mufredat_akts(mufredat, d.get("ders_no"))
            if belge is None or d.get("akts") == belge:
                continue
            akts_farklari.append((d.get("ders_no"), d.get("ders_adi"),
                                  d.get("akts"), belge))
            d["akts"] = belge
    ozet["akts_farklari"] = akts_farklari
    for kod, ad, obis, belge in akts_farklari:
        uyarilar.append(_uyari(
            DIKKAT, "OBİS ile müfredat AKTS'si farklı",
            "OBİS %s AKTS diyor, müfredat belgesi %s AKTS. Belge esas "
            "alındı." % (obis, belge), "Müfredat belgesi", kod, ad))

    bolum_dersleri = [d for d in katalog
                      if (d.get("sekme") or BOLUM_SEKMESI) == BOLUM_SEKMESI]
    yaygin_dersler = [d for d in katalog
                      if (d.get("sekme") or BOLUM_SEKMESI) != BOLUM_SEKMESI]

    eslesmeler = ym.katalog_eslestir(bolum_dersleri, t.get("son_durum") or {})
    ozet["eslesmeler"] = eslesmeler
    ozet["yaygin_secmeli_sayisi"] = len(yaygin_dersler)

    secilen_yaygin = [d for d in yaygin_dersler if d.get("secili")]
    ozet["secilen_yaygin"] = secilen_yaygin
    # BÖLÜM KURALI: öğrenciler ortak/yaygın seçmeli havuzundan ders
    # SEÇMEMELİ. Yönetmelik izin veriyor (MADDE 9/1-ı) ama bölümün
    # tercihi bu yönde; hatayla seçilmişse çıkarılması gerekiyor.
    for d in secilen_yaygin:
        uyarilar.append(_uyari(
            YAPILACAK, "ORTAK HAVUZDAN DERS SEÇİLMİŞ - ÇIKARILMALI",
            "%s (%s) ortak seçmeli havuzundan seçilmiş. Öğrencilerimiz bu "
            "havuzdan ders almamalı; bu ders çıkarılıp yerine bölüm dersi "
            "seçilmeli."
            % (d.get("ders_adi"), d.get("birim") or "başka birim"),
            "Bölüm kuralı", d.get("ders_no"), d.get("ders_adi")))

    for ham in ym.danisman_uyarilari(eslesmeler, t):
        onem = _ONEM_ESLESMESI.get(ham["onem"], BILGI)
        # Laboratuvar dersinde devam muafiyeti teyit ister
        aciklama = ham["aciklama"]
        if (ham["baslik"].startswith("DEVAM MUAFİYETİ")
                and _laboratuvar_mi(ham.get("ders_adi"))):
            aciklama += (" DİKKAT: Bu laboratuvarlı bir ders. FF notu "
                         "uygulamadan başarısızlıktan geliyorsa devam "
                         "zorunluluğu sürer (MADDE 10/5), teyit edin.")
        uyarilar.append(_uyari(onem, ham["baslik"], aciklama, ham["kaynak"],
                               ham["ders_no"], ham["ders_adi"]))

    # ---------------------------------------------------------------
    #  3. Alt dönem yükü + son sınıf + AKTS limiti
    # ---------------------------------------------------------------
    alt_yuk, alt_ayrinti = ym.alt_donem_yuku(
        t.get("gecilen") or [], donem_durumu["hedef_donem"],
        acilan_donemler, donem_plani, t.get("kalinan") or [])
    ozet["alt_donem_yuku"] = alt_yuk
    ozet["alt_donem_ayrinti"] = alt_ayrinti

    son_yariyil = ym.SON_SINIF_YARIYILI.get(program_yili)
    # Son sınıf kararı BÖLÜM dersleri üzerinden verilir; yabancı dilde
    # yaygın seçmeli havuzunun (başka fakültelerin dersleri) o sekmede de
    # "7. Dönem Dersleri" başlığı var ama programın son yarıyılı değil.
    # Zaten seçilmiş dersler eklenebilir görünmez, onları da saymalıyız.
    # eslesmeler zaten yalnızca bölüm derslerinden kuruldu.
    son_donem_dersleri = [
        e["ders"] for e in eslesmeler
        if ym.donem_numarasi(e["ders"].get("donem")) == son_yariyil
        and (e["ders"].get("secili")
             or (e["ders"].get("eklenebilir") and not e["ders"].get("doldu")))]

    son_sinif = ym.son_sinif_degerlendir(
        ozet["gano"], donem_durumu, alt_yuk, son_donem_dersleri, program_yili)
    ozet["son_sinif"] = son_sinif

    limit = ym.yariyil_akts_limiti(ozet["gano"], son_sinif["son_sinif"])
    ozet["akts_limiti"] = limit

    secilen = ozet["secilen_akts"] or 0
    if limit is not None and secilen > limit:
        uyarilar.append(_uyari(
            YAPILACAK, "AKTS LİMİTİ AŞILMIŞ",
            "Seçilen %d AKTS, limit %d AKTS. %d AKTS fazla."
            % (secilen, limit, secilen - limit), "MADDE 9/1-c"))
    elif (limit is None and not son_sinif["son_sinif"]
          and ozet["gano"] is None):
        # limit=None IKI ayri sey demek: "son sınıf, sınır yok" ve
        # "GANO okunamadı, hesaplanamadı". İkincisinde MADDE 9/1-c
        # denetimi sessizce hiç çalışmıyordu - 60 AKTS seçen 1. yarıyıl
        # öğrencisi için tek uyarı çıkmazdı. Son sınıf olmadığı hâlde
        # limit yoksa sebep GANO'dur; danışman bunu bilmeli.
        uyarilar.append(_uyari(
            DIKKAT, "AKTS LİMİTİ HESAPLANAMADI",
            "Öğrencinin GANO'su okunamadı; MADDE 9/1-c yarıyıl AKTS üst "
            "sınırı (GANO 1,50 altı 30, üstü 45) bu öğrenci için "
            "DENETLENEMEDİ. Seçilen %d AKTS elle kontrol edilmeli."
            % secilen, "MADDE 9/1-c"))

    # Son sınıf değilse üst dönemden ders alabilir mi?
    if son_sinif.get("ust_donem_durumu"):
        ust = ym.ust_yariyil_degerlendir(
            ozet["gano"], len(t.get("kalinan") or []), len(alinan_donemler))
        ozet["ust_donem"] = ust
        ust_secilenler = [
            e["ders"] for e in eslesmeler
            if e["ders"].get("secili")
            and ym.ust_donem_mi(ym.donem_numarasi(e["ders"].get("donem")),
                                donem_durumu["hedef_donem"])]
        ust_akts = sum(d.get("akts") or 0 for d in ust_secilenler)
        ozet["ust_donem_secilen_akts"] = ust_akts
        if ust_akts > ust["hak_akts"]:
            uyarilar.append(_uyari(
                YAPILACAK, "ÜST DÖNEM HAKKI AŞILMIŞ",
                "Üst dönemden %d AKTS seçilmiş ama hakkı %d AKTS. %s"
                % (ust_akts, ust["hak_akts"], ust["sebep"]), "MADDE 9/1-ç"))

    # ---------------------------------------------------------------
    #  4. Alttan dersler alınmış mı? (MADDE 9/1-a önceliği)
    # ---------------------------------------------------------------
    secili_kodlar = {d.get("ders_no") for d in secili}
    # Alttan dersin bu dönem açılan karşılığı (kod ya da ad üzerinden)
    alttan_acik, alttan_secilmemis = [], []
    for kayit_e in eslesmeler:
        eski = kayit_e.get("eslesme")
        if eski is None or kayit_e.get("tip") not in ("kod", "ad"):
            continue
        if not ym.tekrar_gerekir_mi(ym.deneme_sonucu(eski)):
            continue
        ders = kayit_e["ders"]
        alttan_acik.append({"ders": ders, "transkript": eski})
        if ders.get("ders_no") not in secili_kodlar:
            alttan_secilmemis.append({"ders": ders, "transkript": eski})

    ozet["alttan_acik"] = alttan_acik
    ozet["alttan_secilmemis"] = alttan_secilmemis

    for a in alttan_secilmemis:
        ders, eski = a["ders"], a["transkript"]
        if ders.get("doldu"):
            uyarilar.append(_uyari(
                YAPILACAK, "Alttan ders SEÇİLMEMİŞ - kontenjan dolu",
                "%s yılında %s almış. Ders bu dönem açık ama kontenjanı dolu."
                % (eski["yil"], eski["harf"]), "MADDE 9/1-a",
                ders.get("ders_no"), ders.get("ders_adi")))
        else:
            uyarilar.append(_uyari(
                YAPILACAK, "Alttan ders SEÇİLMEMİŞ",
                "%s yılında %s almış, bu dönem açık ve seçilmemiş. "
                "Öncelikli alınması gerekir."
                % (eski["yil"], eski["harf"]), "MADDE 9/1-a",
                ders.get("ders_no"), ders.get("ders_adi")))

    # Kalınan seçmeli ders: aynı dönemden başka seçmeli de alınabilir
    for a in alttan_acik:
        ders = a["ders"]
        if not ym.secmeli_mi(ders):
            continue
        donem = ym.donem_numarasi(ders.get("donem"))
        # Seçmeli grubu bölümün o dönemki seçmelileridir; yaygın seçmeli
        # havuzu ayrı bir şey (MADDE 9/1-a vs 9/1-ı).
        alternatifler = ym.secmeli_alternatifleri(
            donem, bolum_dersleri, haric_kodlar=[ders.get("ders_no")])
        if alternatifler:
            uyarilar.append(_uyari(
                BILGI, "Seçmeli - aynı dersi almak zorunda değil",
                "Bu bir seçmeli ders. %d. dönemin seçmeli grubundan başka "
                "bir ders de alabilir (%d alternatif açık)."
                % (donem or 0, len(alternatifler)), "MADDE 9/1-a",
                ders.get("ders_no"), ders.get("ders_adi")))

    # ---------------------------------------------------------------
    #  5. AKTS kaybı (mezuniyet riski)
    # ---------------------------------------------------------------
    kayip = ym.akts_kaybi(t, eslesmeler, donem_plani, program_yili)
    ozet["akts_kaybi"] = kayip

    # Kohort açığı: sekiz yarıyılın hangisinde plana ULAŞILAMIYOR?
    # Projeksiyondan ÖNCE hesaplanıyor, çünkü doğru düşüm bu.
    giris_yili = ym.giris_yili(ozet.get("no"))
    ozet["giris_yili"] = giris_yili
    acik = None
    if mufredat:
        secili_kodlar = {d.get("ders_no") for d in secili}
        acik = ym.kohort_acigi(t.get("gecilen") or [], secili_kodlar,
                               mufredat, donem_plani, giris_yili,
                               bolum_dersleri)
    ozet["kohort_acigi"] = acik

    projeksiyon = ym.mezuniyet_projeksiyonu(
        t, eslesmeler, donem_durumu, donem_plani, acilan_donemler,
        # NET: kalıcı açıktan, fazladan alınan AKTS düşülmüş hâli.
        program_yili, kalici_acik=(acik["net"] if acik else None))
    ozet["projeksiyon"] = projeksiyon

    # Müfredat belgesi varsa mezuniyet AKTS'sini TEK yer anlatır: aşağıdaki
    # 5a-2 (kohort açığı). Buradaki iki eski uyarı akts_kaybi() sayısını
    # kullanıyor; o hesap müfredatın düşen payı YENİ bir derse taşımış
    # olmasını göremediği için farklı bir rakam veriyor. İkisini birden
    # yazmak danışmana aynı öğrenci için İKİ FARKLI mezuniyet AKTS'si
    # göstermek olurdu. Belge yoksa (yedek yol) eskiler devrede kalır.
    if acik is None:
        if projeksiyon["yeterli"] is False:
            uyarilar.append(_uyari(
                YAPILACAK, "MEZUNİYET AKTS'Sİ YETMİYOR",
                "Planı eksiksiz tamamlasa bile %d AKTS ile mezun olur; "
                "asgari %d AKTS, %d AKTS eksik kalıyor. Sebep: müfredat "
                "AKTS düşüşlerinden toplam %d AKTS kayıp. Bu öğrenciye "
                "fazladan ders yazılması gerekiyor."
                % (projeksiyon["projeksiyon"], projeksiyon["asgari"],
                   -projeksiyon["fark"], projeksiyon["akts_kaybi"]),
                "MADDE 8/4"))
        # NOT: kayip["riskli"] ile yukarıdaki uyarı aynı öğrencileri
        # yakalıyor (ikisi de plan - kayıp < 240 demek). Tek uyarı bırakıp
        # ayrıntıyı oraya taşıdık; tekrar eden uyarı paneli şişiriyordu.
        if kayip["toplam_kayip"] and not kayip["riskli"]:
            uyarilar.append(_uyari(
                BILGI, "AKTS kaybı var ama sınırın altında",
                "Toplam %d AKTS kayıp; %d ile mezun olur (asgari %d, "
                "eşik %d)."
                % (kayip["toplam_kayip"], kayip["beklenen_mezuniyet_akts"],
                   kayip["mezuniyet_asgarisi"], kayip["esik"]), "MADDE 8/4"))

    # ---------------------------------------------------------------
    #  4b. Ders programı çakışmaları (MADDE 9/1-b)
    # ---------------------------------------------------------------
    if program:
        ozet.update(_cakismalari_denetle(
            program, bolum_dersleri, secili, alttan_acik, uyarilar,
            eslesmeler=eslesmeler,
            hedef_donem=donem_durumu["hedef_donem"]))

    # ---------------------------------------------------------------
    #  5a-2. Kohort açığı: hangi yarıyıl plana ULAŞAMIYOR?
    # ---------------------------------------------------------------
    # İki sebep, tek sonuç:
    #   (a) Müfredat bir dersin AKTS'sini düşürüp payı YENİ bir derse
    #       taşıdı, ama o ders bu kohortun planında yok
    #       (Uygulamalı Matematik I/II, Fizik Laboratuvarı I/II).
    #   (b) AKTS'si ARTAN bir dersi öğrenci düşük değerken geçmiş
    #       (Lineer Cebir I/II 6 -> 5 -> 6).
    # İkisinde de dersten KALMIŞ olmak gerekmiyor, bu yüzden ne alttan
    # yük ne de akts_kaybi() hesabına giriyorlardı.
    #
    # Yarıyıl yarıyıl AYRI uyarı yazmıyoruz: danışmanın vereceği karar
    # tek ("fazladan kaç seçmeli yazayım?"), dört ayrı satır o kararı
    # bölerdi. Ayrıntı tek uyarının içinde duruyor.
    if acik and (acik["toplam"] or acik["fazla"]):
        asgari = ym.MEZUNIYET_AKTS.get(program_yili)
        mez = acik["mezuniyet_akts"]

        parcalar = []
        for k in acik["kalemler"]:
            sebepler = ["%s planında yok" % d["ders_adi"]
                        for d in k["kohort_disi"]]
            sebepler += ["%s %s AKTS ile geçilmiş, müfredat %s"
                         % (d["ders_adi"], d["gecilen_akts"],
                            d["guncel_akts"])
                         for d in k["dusuk_gecilen"]]
            parcalar.append("%d. yarıyıl %d AKTS%s"
                            % (k["yariyil"], k["kalici"],
                               (" (" + "; ".join(sebepler) + ")")
                               if sebepler else ""))

        # Açığı kapatacak seçmeli havuzu (bölüm kararı: 5. yarıyıl).
        havuz_yy = ym.ACIK_KAPATMA_YARIYILI
        alternatifler = ym.secmeli_alternatifleri(
            havuz_yy, bolum_dersleri,
            haric_kodlar={d.get("ders_no") for d in secili})
        ders_akts = next((d.get("akts") for d in alternatifler
                          if d.get("akts")), ym.TOS_AKTS)

        yetmiyor = asgari is not None and mez < asgari
        if yetmiyor:
            gereken = asgari - mez
            adet = -(-gereken // ders_akts)          # yukarı yuvarla
            nasil = ("Kapatmak için %d. yarıyıl seçmeli havuzundan %d ders "
                     "FAZLADAN alınmalı (%d AKTS). Bu dönem açık: %s."
                     % (havuz_yy, adet, adet * ders_akts,
                        ", ".join("%s (%s AKTS)" % (d.get("ders_adi"),
                                                    d.get("akts"))
                                  for d in alternatifler[:6])
                        or "havuzda açık ders yok, bölüme sorulmalı"))
            uyarilar.append(_uyari(
                YAPILACAK,
                "MEZUNİYET AKTS'Sİ %d EKSİK - FAZLADAN SEÇMELİ GEREKİYOR"
                % gereken,
                "Planı eksiksiz yürütse bile %d AKTS ile mezun olur; "
                "asgari %d. Plandaki AKTS'ye ULAŞILAMAYAN yarıyıllar: %s. "
                "Dersten kalmış olmak gerekmiyor - bu dersler ya %s "
                "girişlinin planında hiç yok, ya da AKTS'si sonradan "
                "artmış ve düşük değerken geçilmiş. %s"
                % (mez, asgari, "; ".join(parcalar),
                   giris_yili if giris_yili else "bu", nasil),
                "MADDE 8/4"))
        else:
            # Fazladan alınan AKTS varsa onu da söylüyoruz: danışman
            # "ben zaten fazladan ders yazdım" dediğinde sayının bunu
            # gördüğünden emin olmalı.
            fazla_notu = ("" if not acik["fazla"] else
                          " Kotanın üstünde alınan %d AKTS düşüldü."
                          % acik["fazla"])
            uyarilar.append(_uyari(
                BILGI, ("Plandan %d AKTS eksik ama asgariyi geçiyor"
                        % acik["net"]) if acik["net"] > 0 else
                       "Plan açığı fazladan alınan derslerle kapanmış",
                "Plana ulaşılamayan yarıyıllar: %s. Net %d AKTS eksikle "
                "%d AKTS'ye ulaşır; asgari %d olduğu için mezuniyet riske "
                "girmiyor, fazladan ders GEREKMİYOR.%s"
                % ("; ".join(parcalar) or "yok", acik["net"], mez, asgari,
                   fazla_notu),
                "MADDE 8/4"))

    # ---------------------------------------------------------------
    #  5b. Hedef dönemin kotası dolmuş mu? (kontenjan planı için)
    # ---------------------------------------------------------------
    hedef = donem_durumu["hedef_donem"]
    plan = donem_plani or ym.VARSAYILAN_DONEM_PLANI
    hedef_plan_akts = plan.get(hedef, ym.YARIYIL_ACILAN_AKTS)

    hedef_secmeliler = [d for d in bolum_dersleri
                        if ym.donem_numarasi(d.get("donem")) == hedef
                        and ym.secmeli_mi(d)]
    secilen_hedef_akts = sum(
        d.get("akts") or 0 for d in bolum_dersleri
        if d.get("secili") and ym.donem_numarasi(d.get("donem")) == hedef)

    # Seçmelilerin tipik AKTS'si (Matematik 7. dönemde hepsi 4)
    aktsler = [d.get("akts") for d in hedef_secmeliler if d.get("akts")]
    tipik_akts = max(set(aktsler), key=aktsler.count) if aktsler else 0

    # Dönemin ders kompozisyonunu denetle: zorunlu + TOS + bölüm içi
    # seçmeli ayrı ayrı. Sadece AKTS toplamına bakmak yetmiyor.
    # son_durum DENENMIS tum dersleri tutuyor (kalinanlar dahil);
    # kompozisyon denetimi bu kumeyi "gecilmis" kabul ediyor. Kalinan
    # ders gecmis sayilinca (a) "ZORUNLU DERS SECILMEMIS" uyarisi hic
    # cikmiyor, (b) zorunlunun AKTS'si kotadan dustugu icin ogrenciye
    # fazladan seçmeli yazdiriliyordu. Yalniz GECILEN kodlari veriyoruz.
    gecilen_kodlar = {d.get("ders_kodu")
                      for d in (t.get("gecilen") or [])
                      if d.get("ders_kodu")}
    komp = ym.donem_kompozisyonu_denetle(
        hedef, secili, bolum_dersleri, gecilen_kodlar, donem_plani,
        mufredat=mufredat, giris_yili=giris_yili)
    ozet["kompozisyon"] = komp

    ozet["donem_ihtiyaci"] = {
        "donem": hedef,
        "plan_akts": hedef_plan_akts,
        "secilen_akts": komp["secilen_akts"],
        "ihtiyac_akts": komp["eksik_akts"],
        # Kontenjan planı yalnızca BÖLÜM İÇİ seçmeliye bakar; TOS ve
        # zorunlu derslerde bizim açacağımız kontenjan yok.
        "ihtiyac_ders": komp["secmeli_eksik"],
        "tipik_akts": tipik_akts,
        "acik_secmeli": [d for d in hedef_secmeliler if not d.get("doldu")],
        "dolu_secmeli": [d for d in hedef_secmeliler if d.get("doldu")],
    }

    if not komp["yapi_bilinmiyor"]:
        # AKTS kapasitesi: sınırı olan öğrenciye sığmayacak dersi
        # "seçilmemiş" diye yazmak uygulanamaz bir tavsiye olur. Alttan
        # dersler zaten önceliklidir (MADDE 9/1-a); bütçe onlara gitmişse
        # hedef dönemin zorunluları ileri kalır - bunu ders ders değil,
        # tek bir özet notla söylüyoruz.
        limit = ozet.get("akts_limiti")
        secili_akts = komp["secilen_akts"] or 0
        kalan_kapasite = None if limit is None else max(0, limit - secili_akts)
        sigmayan = []
        for z in komp["zorunlu_eksik"]:
            z_akts = z.get("akts") or 0
            if kalan_kapasite is not None and z_akts > kalan_kapasite:
                sigmayan.append(z)
                continue
            uyarilar.append(_uyari(
                YAPILACAK, "ZORUNLU ders seçilmemiş",
                "%d. dönemin zorunlu dersi seçilmemiş.%s"
                % (hedef, " Kontenjanı dolu." if z["doldu"] else ""),
                "Bölüm planı", z["ders_no"], z["ders_adi"]))
        if sigmayan:
            uyarilar.append(_uyari(
                DIKKAT, "%d. dönemin zorunluları ileri kalıyor" % hedef,
                "AKTS sınırı %s, seçilen %s - kalan %s AKTS. Şu zorunlu "
                "dersler bu dönem sığmıyor: %s. Alttan dersler öncelikli "
                "olduğu için normal; mezuniyet takvimi bundan etkilenir."
                % (limit, secili_akts, kalan_kapasite,
                   ", ".join((z.get("ders_adi") or z["ders_no"])[:28]
                             for z in sigmayan)),
                "MADDE 9/1-a"))

        if komp["tos_fazla"]:
            uyarilar.append(_uyari(
                YAPILACAK, "BİRDEN FAZLA TOS dersi seçilmiş",
                "Dönemde en fazla %d TOS dersi alınabilir, %d seçilmiş: %s. "
                "Fazlası çıkarılmalı."
                % (komp["tos_azami"], len(komp["tos_secilen"]),
                   ", ".join(d["ders_adi"] or d["ders_no"]
                             for d in komp["tos_secilen"])), "Bölüm planı"))
        elif komp["tos_eksik"]:
            uyarilar.append(_uyari(
                YAPILACAK, "TOS dersi seçilmemiş",
                "%d. dönemde 1 TOS dersi (4 AKTS) alınmalı, seçilmemiş."
                % hedef, "Bölüm planı"))

        if komp["secmeli_eksik"]:
            # Zorunlu derslerde olduğu gibi: bütçesi alttan derslerle
            # dolmuş öğrenciye "bir seçmeli daha al" demek uygulanamaz.
            en_ucuz = min(
                [(d.get("akts") or 0) for d in bolum_dersleri
                 if ym.secmeli_mi(d) and not d.get("secili")
                 and d.get("eklenebilir") and not d.get("doldu")
                 and ym.donem_numarasi(d.get("donem")) == hedef] or [0])
            sigar = (kalan_kapasite is None or not en_ucuz
                     or en_ucuz <= kalan_kapasite)
            uyarilar.append(_uyari(
                YAPILACAK if sigar else DIKKAT,
                "%d. DÖNEM EKSİK - %d seçmeli ders gerekiyor"
                % (hedef, komp["secmeli_eksik"]),
                "Bölüm içi seçmeliden %d ders gerekiyor, %d seçilmiş. "
                "Toplam %d AKTS seçilmiş, %d AKTS olmalı (%d AKTS eksik).%s"
                % (komp["secmeli_gereken"], len(komp["secmeli_secilen"]),
                   komp["secilen_akts"], komp["toplam_akts"],
                   komp["eksik_akts"],
                   "" if sigar else
                   " AKTS sınırı (%s) dolduğu için bu dönem eklenemez; "
                   "alttan dersler öncelikli, seçmeli ileri kalıyor."
                   % ozet.get("akts_limiti")),
                "Bölüm planı"))

        if komp["diger"]:
            uyarilar.append(_uyari(
                DIKKAT, "Dönem planına girmeyen ders seçilmiş",
                "Şu dersler %d. dönemin zorunlu/TOS/seçmeli kovalarına "
                "girmiyor: %s. Alttan ders değilse gözden geçirin."
                % (hedef, ", ".join("%s %s" % (d["ders_no"],
                                               (d["ders_adi"] or "")[:28])
                                    for d in komp["diger"])), "Bölüm planı"))

    # Dönem kotası boşluğu - "yapı biliniyor mu" kapısının DIŞINDA.
    # DONEM_KOMPOZISYONU yalnızca 7. dönemi tanıyor; 1-6. dönemlerde
    # secmeli_eksik hesaplanamadığı için eksik_akts>0 olsa bile hiçbir
    # uyarı çıkmıyordu (bir öğrenci 5. dönemde 24/30 seçmişti, alabileceği
    # 20 açık ders vardı, pano onu "temiz" gösteriyordu). Vakayı ADSIZ
    # yazıyoruz: 60 kişilik bir bölümde ad + dönem + AKTS o kişiyi
    # tanınır kılar ve bu dosya yayımlanıyor.
    # Boş bırakılan her AKTS mezuniyeti
    # geciktirir. Ders SEÇMİYORUZ, yalnızca boşluğu bildiriyoruz.
    if komp["eksik_akts"] > 0 and not komp["secmeli_eksik"] \
            and not komp["zorunlu_eksik"] and not komp["tos_eksik"]:
        adaylar = [d for d in bolum_dersleri
                   if not d.get("secili") and d.get("eklenebilir")
                   and not d.get("doldu")
                   and (ym.donem_numarasi(d.get("donem")) or 99) <= hedef]
        if adaylar:
            en_kucuk = min((d.get("akts") or 0) for d in adaylar)
            uyarilar.append(_uyari(
                YAPILACAK, "%d. DÖNEM KOTASI DOLMAMIŞ" % hedef,
                "%d AKTS seçilmiş, %d AKTS olmalı - %d AKTS boşta. "
                "Alınabilecek %d açık ders var (en küçüğü %d AKTS). "
                "Boş bırakılan AKTS mezuniyeti geciktirir."
                % (komp["secilen_akts"], komp["toplam_akts"],
                   komp["eksik_akts"], len(adaylar), en_kucuk),
                "Bölüm planı"))

    # ---------------------------------------------------------------
    #  6. Azami süre
    # ---------------------------------------------------------------
    if icinde_bulunulan_yil:
        sure = ym.azami_sure_durumu(ozet["no"], icinde_bulunulan_yil,
                                    program_yili)
        ozet["azami_sure"] = sure
        if sure and sure["asildi"]:
            uyarilar.append(_uyari(
                YAPILACAK, "AZAMİ SÜRE AŞILMIŞ",
                "%d girişli, %d yıl geçmiş, azami süre %d yıl."
                % (sure["giris_yili"], sure["gecen_yil"], sure["azami_yil"]),
                "MADDE 16/1"))
        elif sure and sure["kalan_yil"] <= 1:
            uyarilar.append(_uyari(
                DIKKAT, "Azami süre doluyor",
                "%d girişli, azami süreye %d yıl kaldı."
                % (sure["giris_yili"], sure["kalan_yil"]), "MADDE 16/1"))

    # ---------------------------------------------------------------
    #  7. Mezuniyet yakınlığı / üç ders sınavı
    # ---------------------------------------------------------------
    kalan_ders = len(t.get("kalinan") or [])
    if 0 < kalan_ders <= ym.UC_DERS_SINAVI_AZAMI_DERS:
        uyarilar.append(_uyari(
            BILGI, "Üç ders sınavı hakkı olabilir",
            "Alttan %d dersi var. Mezuniyetine bu dersler engelse dilekçeyle "
            "üç ders sınavına girebilir (en az CC yeterli)." % kalan_ders,
            "MADDE 11/1-ç"))

    # ---------------------------------------------------------------
    #  8. Ders seçilmemiş / onay durumu
    # ---------------------------------------------------------------
    if not secili:
        uyarilar.append(_uyari(
            YAPILACAK, "Hiç ders seçilmemiş",
            "Öğrenci bu dönem hiç ders seçmemiş.", "MADDE 6/1"))

    # ---------------------------------------------------------------
    #  9. Tanınmayan not harfleri
    # ---------------------------------------------------------------
    if t.get("bilinmeyen_notlar"):
        uyarilar.append(_uyari(
            DIKKAT, "Tanınmayan not harfi",
            "Transkriptte sınıflandıramadığım harfler var: %s. "
            "Geçti/kaldı sayılmadılar."
            % ", ".join("%s (%d)" % (h, n)
                        for h, n in t["bilinmeyen_notlar"].items())))

    # ---------------------------------------------------------------
    #  10. OBİS toplamıyla tutarlılık
    # ---------------------------------------------------------------
    if t.get("akts_dogrulama") is False:
        uyarilar.append(_uyari(
            DIKKAT, "Transkript toplamı tutmuyor",
            "Aldığı AKTS'yi %s hesapladım, OBİS %s diyor. Transkriptten "
            "satır kaçırmış olabilirim - bu öğrencinin sayılarına güvenmeyin."
            % (t.get("alinan_akts"), (t.get("ozet") or {}).get("toplam_akts"))))
    if t.get("gano_dogrulama") is False:
        uyarilar.append(_uyari(
            DIKKAT, "GANO tutmuyor",
            "Transkriptten hesapladığım ortalama OBİS'in yazdığıyla "
            "uyuşmuyor. Harf ya da AKTS okuması şüpheli."))

    uyarilar.sort(key=lambda u: (ONEM_SIRASI.get(u["onem"], 9),
                                 u["ders_no"] or ""))

    sayim = {YAPILACAK: 0, DIKKAT: 0, BILGI: 0}
    for u in uyarilar:
        sayim[u["onem"]] = sayim.get(u["onem"], 0) + 1
    ozet["sayim"] = sayim
    ozet["durum_rengi"] = (YAPILACAK if sayim[YAPILACAK] else
                           DIKKAT if sayim[DIKKAT] else BILGI)
    return ozet


# =========================================================================
#  Yönetici özeti: kontenjan planı
# =========================================================================
def kontenjan_planlari(ozetler):
    """Kohortta bulunan HER hedef dönem için ayrı kontenjan planı.

    Danışmanın öğrencileri tek bir sınıfta olmayabilir; 3. sınıf
    danışmanında hedef 5, 4. sınıfta 7 olur, karışık da olabilir.
    Sabit bir döneme bağlamak yerine veride ne varsa onu üretiyoruz.
    """
    donemler = sorted({(o.get("donem_ihtiyaci") or {}).get("donem")
                       for o in ozetler
                       if (o.get("donem_ihtiyaci") or {}).get("donem")})
    planlar = []
    for d in donemler:
        p = kontenjan_plani(ozetler, hedef_donem=d)
        # İhtiyacı olan öğrenci yoksa yönetici özetine koymaya gerek yok.
        if p["ogrenci_sayisi"] or p["toplam_kontenjan"]:
            planlar.append(p)
    return {"planlar": planlar,
            "donemler": [p["hedef_donem"] for p in planlar]}


def kontenjan_plani(ozetler, hedef_donem=None):
    """Hedef dönemde her seçmeli dersten kaç İLAVE kontenjan açılmalı?

    Sorun: öğrencilerin bir kısmı hedef dönemin AKTS kotasını dolduramıyor
    çünkü seçmeli derslerin kontenjanı dolmuş. Bu fonksiyon toplam ihtiyacı
    çıkarıp mevcut derslere olabildiğince EŞİT dağıtıyor.

    Varsayımlar (danışman doğrulamalı):
      - "Eksik dersi olan öğrenci" = hedef döneminin plandaki AKTS'sini
        seçtiği derslerle dolduramamış öğrenci.
      - İhtiyaç, tipik seçmeli AKTS'sine bölünüp ders adedine çevriliyor.
      - Kontenjan tüm seçmelilere eşit dağıtılıyor; artıklar kontenjanı
        DOLU olan derslere öncelikle veriliyor (talep oradan geliyor).
    """
    ihtiyac_sahipleri, dersler = [], {}
    toplam_ders_ihtiyaci = 0

    for o in ozetler:
        di = o.get("donem_ihtiyaci")
        if not di:
            continue
        if hedef_donem is not None and di["donem"] != hedef_donem:
            continue
        for d in di["acik_secmeli"] + di["dolu_secmeli"]:
            dersler.setdefault(d["ders_no"], {
                "ders_no": d["ders_no"], "ders_adi": d.get("ders_adi"),
                "akts": d.get("akts"), "doldu": bool(d.get("doldu")),
                "donem": di["donem"],
            })
        if di["ihtiyac_ders"] > 0:
            toplam_ders_ihtiyaci += di["ihtiyac_ders"]
            ihtiyac_sahipleri.append({
                "no": o.get("no"), "ad": o.get("ad"),
                "plan_akts": di["plan_akts"],
                "secilen_akts": di["secilen_akts"],
                "ihtiyac_akts": di["ihtiyac_akts"],
                "ihtiyac_ders": di["ihtiyac_ders"],
            })

    liste = sorted(dersler.values(),
                   key=lambda d: (not d["doldu"], d["ders_no"]))
    if not liste or not toplam_ders_ihtiyaci:
        # İhtiyaç yoksa da her ders "ilave_kontenjan" alanını taşımalı;
        # bazı derslerde alanın hiç olmaması panoda sessizce '—' üretiyor,
        # Python tarafında ise KeyError'a düşüyordu.
        for ders in liste:
            ders["ilave_kontenjan"] = 0
        return {
            "hedef_donem": hedef_donem,
            "ogrenci_sayisi": len(ihtiyac_sahipleri),
            "toplam_kontenjan": 0, "ders_basina": 0, "artik": 0,
            "dersler": liste, "ogrenciler": ihtiyac_sahipleri,
        }

    # Eşit dağıtım: taban herkese, artık dolu derslere önce.
    taban, artik = divmod(toplam_ders_ihtiyaci, len(liste))
    for sira, ders in enumerate(liste):
        ders["ilave_kontenjan"] = taban + (1 if sira < artik else 0)

    return {
        "hedef_donem": hedef_donem,
        "ogrenci_sayisi": len(ihtiyac_sahipleri),
        "toplam_kontenjan": toplam_ders_ihtiyaci,
        "ders_basina": taban,
        "artik": artik,
        "dersler": liste,
        "ogrenciler": sorted(ihtiyac_sahipleri,
                             key=lambda x: -x["ihtiyac_ders"]),
    }
