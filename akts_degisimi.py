# -*- coding: utf-8 -*-
"""Müfredatın AKTS'sini değiştirdiği dersleri KOHORT KOHORT çıkarır.

Neden gerekli
-------------
Bölüm müfredatı güncelledi. Bir öğrenci kaldığı ya da hiç almadığı dersi
yeni dönemde alırken GÜNCEL AKTS geçerli olur; geçtiği dersler ise
geçtiği andaki AKTS ile sayılır (danışman kararı). Bu iki değer farklıysa
öğrenci mezuniyet AKTS'sinden kaybeder.

Neden KOHORT başına
-------------------
Bir dersin "eski" değeri diye tek bir sayı YOKTUR; öğrencinin giriş
yılına bağlıdır. Ölçüldü (2026-09):

  ders                       2023 girişli    2024 girişli / güncel
  Fizik I / II                     5                4
  İngilizce I / II                 3                2
  Cebir I / II                     6                5
  Diferensiyel Geometri I / II     6                5
  Sayılar Teorisi I / II           4                3

Yani 2023 girişli için 1-4. yarıyıl 124 AKTS, 2024 girişli için 120.
Hiç dersten kalmamış 2024 girişli bir öğrencinin genel kredisi tam 120
çıkıyor ve bu müfredat belgesiyle birebir tutuyor: 2024 kohortu için
"ilk hâl" ile "son hâl" aynı, dolayısıyla AKTS kaybı yok.

2023 tabanını 2024 girişli bir öğrenciye uygularsak hiç yaşamadığı bir
kayıp uydurmuş oluruz. Bu yüzden taban her kohort için ayrı kurulur:

  1. ESKİ değer - sırayla:
       (a) o kohortun kendi transkriptlerindeki EN ESKİ kayıt (ölçülmüş),
       (b) veri/akts_referans.json içindeki kohort fotoğrafı (ölçülmüş),
       (c) o kohort girdiğinde yürürlükte olan MÜFREDAT BELGESİ
           (veri/mufredat/<yıl>.docx arşivi; bkz. mufredat_arsivi.py),
       (d) hiçbiri yoksa güncel değer, yani "değişmemiş" sayılır -
           uydurma kayıp üretmeyiz.
     Ölçülmüş kaynaklar belgesel olanın önünde: bir öğrencinin
     transkriptindeki AKTS, belgenin ne yazdığından daha güçlü kanıttır.
     (c) Matematik'te hiç çalışmıyor (tek yıllık belge var); yeni bir
     bölüm için ise AKTS kaybı tespitinin tek kaynağı odur.
  2. GÜNCEL değer - müfredat belgesi (veri/mufredat.docx). AKTS için tek
     doğru kaynak.

Ders kimliği kod üzerinden kurulamaz: müfredat bazı derslerin KODUNU da
değiştirmiş (2709508 CEBİR I -> 2709545). Bu yüzden önce kod, tutmazsa ad
eşleştirmesi kullanılır - ad eşleştirmesinde ders seviyesi (I/II) kesin
ayırıcıdır, bkz. yonetmelik.ad_benzerligi().
"""
import io
import json
import os

import yollar
import yonetmelik as ym

REFERANS_YOLU = str(yollar.veri("akts_referans.json"))

# NOT: Bir zamanlar "taban öğrenci" (hiç kalmamış bir öğrencinin
# transkripti) elle kodluydu. Ölçüldü: her
# ders için EN ESKİ KAYDI almak aynı sonucu veriyor ama hiçbir öğrenci
# numarasına bağlı değil ve başka danışmanlarda da çalışıyor.
#
# Otomatik taban seçimi ayrıca TEHLİKELİ: "hiç kalmamış, en çok ders
# almış" ölçütü 2025 girişli bir öğrenciyi seçince "eski değer" aslında
# yeni değer oluyor ve Lineer Cebir 5 -> 6 ARTMIŞ görünüyordu.
TABAN_OGRENCI = None


def referanslari_yukle(yol=REFERANS_YOLU):
    """Kohort AKTS fotoğrafları: {giris_yili(int): {ders_kodu: akts}}.

    Transkripti olmayan bir kohort için (örn. danışmanın listesinde 2024
    girişli var ama o dersi henüz alan olmamış) eski değeri buradan
    okuyoruz. Dosya yoksa boş sözlük döner - sistem yine çalışır.
    """
    if not os.path.exists(yol):
        return {}
    try:
        ham = json.load(io.open(yol, encoding="utf-8"))
    except ValueError:
        return {}
    cikti = {}
    for yil, bilgi in (ham.get("kohortlar") or {}).items():
        try:
            anahtar = int(yil)
        except (TypeError, ValueError):
            continue
        cikti[anahtar] = {k: v for k, v in (bilgi.get("dersler") or {}).items()
                          if v is not None}
    return cikti


def arsiv_referanslari(yol=None):
    """Müfredat arşivinden kohort AKTS tabanları: {yıl(int): {kod: akts}}.

    veri/mufredat_arsivi.json'dan okunur (docx'lere dokunulmaz; exe'ye
    de yalnız bu dosya gömülür). Arşiv yoksa boş döner ve hiçbir şey
    değişmez.
    """
    import mufredat_arsivi

    veri = mufredat_arsivi.yukle(yol)
    cikti = {}
    for yil, dersler in ((veri or {}).get("kohort_akts") or {}).items():
        try:
            anahtar = int(yil)
        except (TypeError, ValueError):
            continue
        cikti[anahtar] = {k: v for k, v in (dersler or {}).items()
                          if v is not None}
    return cikti


def _arsiv_degeri(arsiv, kohort, *kodlar):
    """Kohortun giriş yılında yürürlükte olan belgedeki AKTS.

    Tam o yılın belgesi yoksa ONDAN ÖNCEKİ en yakın yıl kullanılır -
    öğrenci girdiğinde yürürlükte olan belge odur. Öncesi de yoksa
    None döner; tahmin yürütmüyoruz.
    """
    uygun = [y for y in arsiv if y <= kohort]
    if not uygun:
        return None, None
    yil = max(uygun)
    for kod in kodlar:
        if kod and arsiv[yil].get(kod) is not None:
            return arsiv[yil][kod], yil
    return None, None


def _belgede_bul(kod, ad, belge):
    """Transkript dersinin müfredat belgesindeki karşılığı."""
    if kod in belge:
        return kod, belge[kod], "kod"
    en_iyi, oran = None, 0.0
    for bkod, bilgi in belge.items():
        o = ym.ad_benzerligi(ad, bilgi["ders_adi"])
        if o > oran:
            en_iyi, oran = (bkod, bilgi), o
    if en_iyi and oran >= ym.BENZERLIK_ESIGI:
        return en_iyi[0], en_iyi[1], "ad"
    return None, None, None


def hesapla(transkriptler, mufredat, katalog=None, taban_no=TABAN_OGRENCI,
            referanslar=None):
    """AKTS değişim tablosunu KOHORT KOHORT üretir.

    transkriptler: {ogrenci_no: transkripti_coz() sonucu}
    mufredat     : mufredat.yukle() sonucu
    katalog      : {ders_no: katalog dersi} - bu dönem AÇIK olanlar
    referanslar  : {giris_yili: {ders_kodu: akts}} - transkripti olmayan
                   kohortlar için AKTS fotoğrafı; None ise dosyadan okunur

    Dönen sözlükte her ders satırı, öğrencinin giriş yılına göre ayrı
    "eski" değer taşır: satir["kohortlar"][2023]["eski_akts"] gibi.
    Üst düzey eski_akts/fark alanları EN ESKİ kohortu gösterir; tek
    kohortlu bir danışman listesinde ikisi aynı şeydir.
    """
    if not mufredat:
        return {"dersler": [], "yariyillar": {}, "taban": None,
                "kohortlar": [], "uyarilar": [
                    "Müfredat belgesi yüklenmedi (veri/mufredat.json yok)."]}

    belge = mufredat["dersler"]
    uyarilar = []
    if referanslar is None:
        referanslar = referanslari_yukle()
    arsiv_ref = arsiv_referanslari()

    # --- transkriptlerden ders geçmişi -----------------------------------
    # kod -> {"ad", "donem", "ogrenciler", "kalanlar",
    #         "kohort": {giris_yili: {"yillar", "ogrenciler", "kalanlar"}}}
    gecmis = {}
    kohort_ogrencileri = {}
    for no, t in sorted(transkriptler.items()):
        if not t:
            continue
        kohort = ym.giris_yili(no)
        kohort_ogrencileri.setdefault(kohort, set()).add(no)
        kalan_kodlar = {d["ders_kodu"] for d in (t.get("kalinan") or [])}
        for d in t.get("denemeler") or []:
            kayit = gecmis.setdefault(d["ders_kodu"], {
                "ad": d["ders_adi"], "donem": d.get("donem"),
                "ogrenciler": set(), "kalanlar": set(), "kohort": {}})
            kk = kayit["kohort"].setdefault(kohort, {
                "yillar": {}, "ogrenciler": set(), "kalanlar": set()})
            kk["yillar"].setdefault(d["yil"], set()).add(d["akts"])
            kk["ogrenciler"].add(no)
            kayit["ogrenciler"].add(no)
            if d["ders_kodu"] in kalan_kodlar:
                kk["kalanlar"].add(no)
                kayit["kalanlar"].add(no)
            if kayit["donem"] is None:
                kayit["donem"] = d.get("donem")

    # Listede transkripti olmayan kohort da olabilir (öğrenci yeni girmiş
    # ve hiç ders almamış). Onları da tabloda görmek istiyoruz.
    tum_kohortlar = sorted(k for k in kohort_ogrencileri if k is not None)

    taban = transkriptler.get(taban_no) if taban_no else None
    taban_akts = {}
    if taban:
        for d in taban.get("denemeler") or []:
            taban_akts[d["ders_kodu"]] = d["akts"]
        if taban.get("kalinan"):
            uyarilar.append(
                "Taban öğrenci (%s) kalmış dersi olduğu için temiz bir "
                "kohort fotoğrafı değil." % taban_no)
    elif taban_no:
        uyarilar.append(
            "Verilen taban öğrenci (%s) listede yok; eski AKTS değerleri "
            "her kohortun kendi en eski kaydından alındı." % taban_no)
    for k in tum_kohortlar:
        if k in referanslar or any(k in g["kohort"] for g in gecmis.values()):
            continue
        # Arşivde o kohorta ait (ya da ondan önceki) bir belge varsa
        # taban ORADAN geliyor; uyarı yazmak yanlış olur.
        if [y for y in arsiv_ref if y <= k]:
            continue
        uyarilar.append(
            "%s girişli öğrenciler için ne transkript kaydı, ne referans "
            "fotoğrafı, ne de o yıla ait müfredat belgesi var; o kohort "
            "için AKTS değişmemiş kabul edildi." % k)

    # --- karşılaştırma ---------------------------------------------------
    satirlar = []
    for kod, k in sorted(gecmis.items()):
        yeni_kod, bilgi, yontem = _belgede_bul(kod, k["ad"], belge)
        if bilgi is None:
            uyarilar.append(
                "%s %s: müfredat belgesinde karşılığı bulunamadı."
                % (kod, k["ad"]))
            continue
        guncel = bilgi["akts"]
        if guncel is None:
            continue

        # --- her kohort için AYRI eski değer --------------------------
        # Bir dersin "eski" AKTS'si diye tek bir sayı yok; öğrencinin
        # giriş yılına bağlı. Sıra: kohortun kendi kaydı -> kohortun
        # referans fotoğrafı -> "değişmemiş" (uydurma kayıp üretmeyiz).
        kohortlar = {}
        for kohort in tum_kohortlar:
            kh = k["kohort"].get(kohort)
            kyillar = {yy: sorted(a) for yy, a in
                       sorted(((kh or {}).get("yillar") or {}).items())
                       if yy is not None}
            ref = referanslar.get(kohort) or {}
            ref_deger = ref.get(yeni_kod)
            if ref_deger is None:
                ref_deger = ref.get(kod)
            if kod in taban_akts and kohort == ym.giris_yili(taban_no):
                eski_deg, kaynak = taban_akts[kod], "taban öğrenci"
            elif kyillar:
                ilk = sorted(kyillar)[0]
                eski_deg = kyillar[ilk][0]
                kaynak = "%s girişlilerin en eski kaydı (%s)" % (kohort, ilk)
            elif ref_deger is not None:
                eski_deg = ref_deger
                kaynak = "%s referans fotoğrafı" % kohort
            else:
                # Belgesel kaynak: o kohort girdiğinde yürürlükte olan
                # müfredat. Ölçülmüş kayıtların ARDINDA duruyor - bir
                # öğrencinin transkriptindeki değer, belgenin ne yazdığından
                # daha güçlü kanıttır. Matematik'te arşiv olmadığı için bu
                # dal hiç çalışmıyor; yeni bir bölümde ise AKTS kaybı
                # tespitinin tek kaynağı bu.
                ars_deger, ars_yil = _arsiv_degeri(arsiv_ref, kohort,
                                                   yeni_kod, kod)
                if ars_deger is not None:
                    eski_deg = ars_deger
                    kaynak = "%s müfredat belgesi" % ars_yil
                else:
                    eski_deg, kaynak = guncel, "veri yok - değişmemiş sayıldı"
            kohortlar[kohort] = {
                "eski_akts": eski_deg,
                "eski_kaynak": kaynak,
                "fark": guncel - eski_deg,
                "yillar": kyillar,
                "ogrenci_sayisi": len((kh or {}).get("ogrenciler") or ()),
                "kalan_sayisi": len((kh or {}).get("kalanlar") or ()),
                "kalanlar": sorted((kh or {}).get("kalanlar") or ()),
            }

        # Üst düzey alanlar, o dersi gerçekten almış EN ESKİ kohortu
        # temsil eder; tek kohortlu danışman listesinde tek seçenek.
        veri_olan = [c for c in sorted(kohortlar)
                     if kohortlar[c]["ogrenci_sayisi"]]
        ana = veri_olan[0] if veri_olan else None
        anak = kohortlar.get(ana) or {}
        eski = anak.get("eski_akts", guncel)
        eski_kaynak = anak.get("eski_kaynak", "veri yok")
        yillar = anak.get("yillar") or {}

        yariyil = bilgi.get("yariyil") or k["donem"]
        # AYNI kodun AKTS'si yıllar içinde oynamış mı? Kod değişikliğinden
        # farklı bir şey: ders yerinde dururken değeri değişmiş demektir.
        tum_degerler = set()
        for a in yillar.values():
            tum_degerler |= set(a)
        # Kohortlar arası fark da oynaklıktır: 2023 girişli 6, 2024 5.
        tum_degerler |= {c["eski_akts"] for c in kohortlar.values()
                         if c["ogrenci_sayisi"]}
        oynak = len(tum_degerler) > 1
        son_yil = max(yillar) if yillar else None
        son_akts = yillar[son_yil] if son_yil else []
        # Değer oynamış ama belge başlangıçtaki değere DÖNMÜŞ mü?
        # Lineer Cebir I/II böyle: 6 -> 5 -> 6. Bu bir çelişki değil,
        # müfredatın geri aldığı bir değişiklik. Yine de gösteriyoruz:
        # arada DÜŞÜK değerle geçen öğrenciler o farkı kaybetmiş oluyor.
        ilk_deger = yillar[sorted(yillar)[0]][0] if yillar else None
        geri_alinmis = oynak and ilk_deger is not None and guncel == ilk_deger
        # Çelişki: değer oynamış, belge ilk değere de dönmemiş VE en son
        # işlenen kayıt belgeyle tutmuyor. Burada gerçekten teyit gerekir.
        celiski = (oynak and not geri_alinmis
                   and bool(son_akts) and guncel not in son_akts)
        acik = (katalog or {}).get(yeni_kod) or (katalog or {}).get(kod)
        satirlar.append({
            "acik_kod": acik.get("ders_no") if acik else None,
            "acik_akts": acik.get("akts") if acik else None,
            "bu_donem_acik": acik is not None,
            "celiski": celiski,
            "oynak": oynak,
            "geri_alinmis": geri_alinmis,
            "son_yil": son_yil,
            "son_akts": son_akts,
            "eski_kod": kod,
            "yeni_kod": yeni_kod,
            "kod_degisti": yeni_kod != kod,
            "ders_adi": bilgi["ders_adi"] or k["ad"],
            "transkript_adi": k["ad"],
            "yariyil": yariyil,
            "eski_akts": eski,
            "eski_kaynak": eski_kaynak,
            "guncel_akts": guncel,
            "fark": guncel - eski,
            "ana_kohort": ana,
            "kohortlar": kohortlar,
            # Kohortlar aynı fikirde mi? Değilse danışmanın öğrencileri
            # aynı dersi farklı AKTS ile taşıyor demektir.
            "kohort_farki": len({c["eski_akts"] for c in kohortlar.values()
                                 if c["ogrenci_sayisi"]}) > 1,
            "yillar": yillar,
            "ogrenci_sayisi": len(k["ogrenciler"]),
            "kalan_sayisi": len(k["kalanlar"]),
            "kalanlar": sorted(k["kalanlar"]),
            "eslesme": yontem,
        })

    # --- belgede olup hiçbir transkriptte geçmeyen dersler ---------------
    gorulen_yeni = {s["yeni_kod"] for s in satirlar}
    kapsam_disi = {}
    for bkod, bilgi in belge.items():
        if bkod in gorulen_yeni:
            continue
        y = bilgi.get("yariyil")
        kapsam_disi.setdefault(y, []).append(
            {"kod": bkod, "ders_adi": bilgi["ders_adi"],
             "akts": bilgi["akts"], "tip": bilgi.get("tip")})

    yariyillar = {}
    for s in satirlar:
        yariyillar.setdefault(s["yariyil"], []).append(s)
    for y in yariyillar:
        yariyillar[y].sort(key=lambda s: (-abs(s["fark"]), s["ders_adi"]))

    degisen = [s for s in satirlar if s["fark"]]

    # --- kohort özeti ----------------------------------------------------
    # Danışmanın listesinde hangi giriş yılları var, her biri için kaç
    # ders değişmiş, hangi öğrenciler etkileniyor.
    kohort_ozeti = []
    for kohort in tum_kohortlar:
        kd = [s for s in satirlar
              if (s["kohortlar"].get(kohort) or {}).get("fark")
              and s["kohortlar"][kohort]["ogrenci_sayisi"]]
        etkilenen = set()
        for s in kd:
            etkilenen |= set(s["kohortlar"][kohort]["kalanlar"])
        kohort_ozeti.append({
            "giris_yili": kohort,
            "ogrenci_sayisi": len(kohort_ogrencileri.get(kohort) or ()),
            "degisen": len(kd),
            "dusen": len([s for s in kd
                          if s["kohortlar"][kohort]["fark"] < 0]),
            "artan": len([s for s in kd
                          if s["kohortlar"][kohort]["fark"] > 0]),
            "kaynak": ("referans fotoğrafı"
                       if kohort in referanslar
                       and not any(s["kohortlar"][kohort]["yillar"]
                                   for s in satirlar)
                       else "transkript kayıtları"),
            "kalan_ogrenci_sayisi": len(etkilenen),
        })

    return {
        "dersler": satirlar,
        "degisen": degisen,
        "yariyillar": yariyillar,
        "kapsam_disi": kapsam_disi,
        "taban": taban_no if taban else None,
        "taban_ad": (taban or {}).get("ozet", {}).get("ad"),
        "kohortlar": kohort_ozeti,
        "kohort_yillari": tum_kohortlar,
        "referans_kohortlari": sorted(referanslar),
        "uyarilar": uyarilar,
        "ozet": {
            "karsilastirilan": len(satirlar),
            "degisen": len(degisen),
            "dusen": len([s for s in degisen if s["fark"] < 0]),
            "artan": len([s for s in degisen if s["fark"] > 0]),
            "kod_degisen": len([s for s in satirlar if s["kod_degisti"]]),
            "kohort_sayisi": len(tum_kohortlar),
            "kohort_farkli_ders": len([s for s in satirlar
                                       if s["kohort_farki"]]),
        },
    }
