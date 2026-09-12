# -*- coding: utf-8 -*-
"""Bölüm profili — yönetmelikten GELMEYEN her şey.

Neden ayrı bir dosya
--------------------
`yonetmelik.py` Selçuk Üniversitesi'nin tamamı için aynıdır: not tablosu,
AKTS limiti, azami süre, devam koşulu. Hiçbir bölüm bunları değiştiremez.

Ama araç çalışsın diye bilmesi gereken bir şeyler daha var ve bunların
hiçbiri yönetmelikte yazmaz:

    yarıyıl AKTS planı, TOS ders listesi, dönem kompozisyonu,
    müfredata sonradan eklenmiş dersler, ders programının sayfa düzeni.

Bunlar BÖLÜM KARARIDIR. Matematik için ölçülüp koda yazılmışlardı; başka
bir bölümün danışmanı aracı açtığında o değerler onun bölümü için YANLIŞ
olur ve araç bunu fark etmez — sessizce yanlış AKTS hesaplar. `yollar.py`
ile aynı ders: sessiz yanlış, gürültülü hatadan beterdir.

Bu yüzden hepsi `veri/bolum.json` dosyasına taşındı. Dosya yoksa modül
açılmaz ve ne yapılacağını söyler; uydurma varsayılana düşmez.

    python bolum.py              profili özetler
    python bolum.py --denetle    tutarlılığını sınar
"""
import io
import json

import yollar

PROFIL_ADI = "bolum.json"
SURUM = 1

_profil = None


class ProfilYok(SystemExit):
    """Profil bulunamadı ya da okunamadı."""


def yol():
    return yollar.veri(PROFIL_ADI)


def yukle(zorla=False):
    """veri/bolum.json — bir kez okunur, sonra bellekten verilir."""
    global _profil
    if _profil is not None and not zorla:
        return _profil
    p = yol()
    if not p.exists():
        raise ProfilYok(
            "Bölüm profili yok: %s\n"
            "Kurulum sihirbazını çalıştırın:  python kurulum.py" % p)
    try:
        veri = json.load(io.open(str(p), encoding="utf-8"))
    except ValueError as e:
        raise ProfilYok("Bölüm profili bozuk (%s): %s" % (p, e))
    sorunlar = denetle(veri)
    agir = [s for s in sorunlar if s[0] == "HATA"]
    if agir:
        raise ProfilYok(
            "Bölüm profili kullanılamaz (%s):\n%s"
            % (p, "\n".join("  " + m for _, m in agir)))
    _profil = veri
    return veri


# =========================================================================
#  Erişimciler — çağıran taraf JSON'un şeklini bilmek zorunda değil
# =========================================================================
def _b(*anahtarlar):
    d = yukle()
    for a in anahtarlar:
        d = (d or {}).get(a)
    return d


def ad():
    return _b("bolum", "ad") or "?"


def tanim():
    """'Selçuk Üniversitesi Fen Fakültesi Matematik Bölümü'"""
    b = yukle().get("bolum") or {}
    parcalar = [b.get("universite"), b.get("fakulte"),
                (b.get("ad") or "") + " Bölümü" if b.get("ad") else None]
    return " ".join(p for p in parcalar if p)


def program_yili():
    """Kaç yıllık program: 2 ön lisans, 4 lisans, 5 (diş/vet vb.)."""
    return int(_b("bolum", "program_yili") or 4)


def donem_plani():
    """{yarıyıl: AKTS} — anahtarlar int."""
    ham = _b("plan", "donem_akts") or {}
    return {int(k): v for k, v in ham.items()}


def tos_dersleri():
    return dict(_b("tos", "dersler") or {})


def tos_akts():
    return _b("tos", "akts")


def tos_azami_adet():
    return _b("tos", "azami_adet")


def sonradan_eklenen_dersler():
    """{ders kodu: geçerli olduğu EN ERKEN giriş yılı}"""
    ham = _b("kohort", "sonradan_eklenen_dersler") or {}
    return {k: int(v) for k, v in ham.items()}


def acik_kapatma_yariyili():
    return _b("kohort", "acik_kapatma_yariyili")


def donem_kompozisyonu():
    """Belge yokken kullanılan yedek kompozisyon. Anahtarlar int."""
    ham = _b("donem_kompozisyonu") or {}
    return {int(k): {"zorunlu_kodlar": tuple(v.get("zorunlu_kodlar") or ()),
                     "tos_adedi": v.get("tos_adedi") or 0}
            for k, v in ham.items()}


def program_ayarlari():
    """Ders programı xlsx'inin sayfa düzeni ve istisna dersleri."""
    p = dict(_b("program") or {})
    p.setdefault("sayfa_adi", "I. Öğretim")
    p.setdefault("gunler", ["PAZARTESİ", "SALI", "ÇARŞAMBA",
                            "PERŞEMBE", "CUMA"])
    p.setdefault("saat_sutunlari", {})
    p.setdefault("asenkron_dersler", [])
    p.setdefault("esnek_dersler", [])
    p.setdefault("uygulamali_dersler", [])
    p.setdefault("tos_blok_adi", "TOS")
    return p


def kaynaklar():
    """Danışmandan istenen belgeler: {anahtar: {...}}"""
    return dict(yukle().get("kaynaklar") or {})


# =========================================================================
#  Denetim — profil kendi içinde tutarlı mı?
# =========================================================================
def denetle(veri=None):
    """[(seviye, mesaj)] döndürür. seviye: HATA (açılmaz) | UYARI."""
    if veri is None:
        veri = yukle()
    s = []

    def hata(m):
        s.append(("HATA", m))

    def uyari(m):
        s.append(("UYARI", m))

    if veri.get("surum") != SURUM:
        uyari("Profil sürümü %r, bu araç %d bekliyor."
              % (veri.get("surum"), SURUM))

    b = veri.get("bolum") or {}
    if not b.get("ad"):
        hata("bolum.ad boş — panoda bölüm adı yazamayız.")
    py = b.get("program_yili")
    if py not in (2, 4, 5):
        hata("bolum.program_yili %r; 2, 4 veya 5 olmalı (MADDE 8/4)." % py)

    plan = (veri.get("plan") or {}).get("donem_akts") or {}
    beklenen = 2 * (py or 4)
    try:
        yariyillar = sorted(int(k) for k in plan)
    except (TypeError, ValueError):
        hata("plan.donem_akts anahtarları yarıyıl numarası olmalı.")
        yariyillar = []
    if yariyillar and yariyillar != list(range(1, beklenen + 1)):
        hata("plan.donem_akts %d yarıyıl içermeli (1..%d), gelen: %s"
             % (beklenen, beklenen, yariyillar or "-"))
    for k, v in plan.items():
        if not isinstance(v, int) or v <= 0:
            hata("plan.donem_akts[%s] = %r; pozitif tam sayı olmalı."
                 % (k, v))
    toplam = sum(v for v in plan.values() if isinstance(v, int))
    asgari = {2: 120, 4: 240, 5: 300}.get(py)
    if asgari and toplam and toplam < asgari:
        hata("Plan toplamı %d AKTS, yönetmelik asgarisi %d (MADDE 8/4). "
             "Bu planla mezun olunamaz." % (toplam, asgari))

    tos = veri.get("tos") or {}
    if tos.get("dersler") and not tos.get("akts"):
        hata("tos.dersler dolu ama tos.akts boş — kota hesaplanamaz.")
    if tos.get("azami_adet") is None:
        uyari("tos.azami_adet boş; dönem başına TOS sınırı denetlenmez.")

    kohort = veri.get("kohort") or {}
    for kod, yil in (kohort.get("sonradan_eklenen_dersler") or {}).items():
        try:
            int(yil)
        except (TypeError, ValueError):
            hata("kohort.sonradan_eklenen_dersler[%s] = %r; giriş yılı "
                 "olmalı (örn. 2024)." % (kod, yil))
    ay = kohort.get("acik_kapatma_yariyili")
    if kohort.get("sonradan_eklenen_dersler") and not ay:
        uyari("Sonradan eklenen ders var ama kohort.acik_kapatma_yariyili "
              "boş; açığın nereden kapatılacağını söyleyemeyiz.")
    if ay is not None and yariyillar and ay not in yariyillar:
        hata("kohort.acik_kapatma_yariyili %r planda olmayan bir yarıyıl."
             % ay)

    for d, yapi in (veri.get("donem_kompozisyonu") or {}).items():
        if not isinstance(yapi, dict):
            hata("donem_kompozisyonu[%s] sözlük olmalı." % d)
            continue
        if yariyillar and int(d) not in yariyillar:
            uyari("donem_kompozisyonu[%s] planda olmayan bir yarıyıl." % d)

    pr = veri.get("program") or {}
    if pr and pr.get("saat_sutunlari"):
        for sutun in pr["saat_sutunlari"]:
            if not (isinstance(sutun, str) and sutun.isalpha()):
                hata("program.saat_sutunlari anahtarı Excel sütun harfi "
                     "olmalı (C, D, ...): %r" % sutun)
    return s


def ozet_yaz():
    v = yukle()
    print(tanim())
    print("  profil          %s (sürüm %s)" % (yol(), v.get("surum")))
    print("  program         %d yıl, %d yarıyıl"
          % (program_yili(), 2 * program_yili()))
    plan = donem_plani()
    print("  plan            %s = %d AKTS"
          % (" + ".join(str(plan[y]) for y in sorted(plan)), sum(plan.values())))
    print("  TOS             %d ders tanımlı, %s AKTS, dönem başına en çok %s"
          % (len(tos_dersleri()), tos_akts(), tos_azami_adet()))
    se = sonradan_eklenen_dersler()
    print("  sonradan eklenen %d ders%s"
          % (len(se), (" (açık %d. yarıyıldan kapatılıyor)"
                       % acik_kapatma_yariyili()) if se else ""))
    for kod, yil in sorted(se.items()):
        print("       %s  %d ve sonrası" % (kod, yil))
    pr = program_ayarlari()
    print("  ders programı   sayfa %r, %d saat sütunu, %d asenkron, "
          "%d esnek ders"
          % (pr["sayfa_adi"], len(pr["saat_sutunlari"]),
             len(pr["asenkron_dersler"]), len(pr["esnek_dersler"])))


if __name__ == "__main__":
    import sys

    if "--denetle" in sys.argv:
        try:
            ham = json.load(io.open(str(yol()), encoding="utf-8"))
        except Exception as e:          # noqa: BLE001 - kullanıcıya göster
            print("Profil okunamadı: %s" % e)
            raise SystemExit(1)
        sorunlar = denetle(ham)
        for seviye, mesaj in sorunlar:
            print("  [%s] %s" % (seviye, mesaj))
        if not sorunlar:
            print("  Profil tutarlı.")
        raise SystemExit(1 if any(s == "HATA" for s, _ in sorunlar) else 0)
    ozet_yaz()
