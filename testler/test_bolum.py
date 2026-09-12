# -*- coding: utf-8 -*-
"""Bölüm profili testleri.

Neyi koruyor
------------
Bölüme özgü her sayı (yarıyıl planı, TOS listesi, dönem kompozisyonu,
sonradan eklenen dersler, ders programının sayfa düzeni) artık
veri/bolum.json'dan geliyor. İki şeyin doğru olması gerekiyor:

  1. PROFİL GERÇEKTEN OKUNUYOR. Bir sabit koda geri kaçarsa hiçbir şey
     patlamaz, program yine Matematik'in değerleriyle çalışır ve başka
     bölümün danışmanı SESSİZCE yanlış AKTS görür. Bunu ölçmek için
     uydurma bir profille ayrı bir süreç açıp yonetmelik'in sabitlerinin
     GERÇEKTEN DEĞİŞTİĞİNİ görüyoruz.

  2. BOZUK PROFİL AÇILMIYOR. Mezun edilemeyecek bir plan, tanımsız
     program yılı, planda olmayan bir yarıyıl — hepsi açılışta
     yakalanmalı, hesaba girmemeli.
"""
import io
import json
import os
import subprocess
import sys
import tempfile

BURASI = os.path.dirname(os.path.abspath(__file__))
KOK = os.path.dirname(BURASI)
sys.path.insert(0, KOK)
sys.path.insert(0, BURASI)

import bolum                                              # noqa: E402
import ders_programi as dp                                # noqa: E402
import yonetmelik as ym                                   # noqa: E402

OK = []


def kontrol(ad, beklenen, gelen):
    tamam = beklenen == gelen
    print(("  [OK]  " if tamam else "  [HATA] ") + ad +
          ("" if tamam else "\n          beklenen=%r\n          gelen   =%r"
           % (beklenen, gelen)))
    OK.append(tamam)


# --------------------------------------------------------------------
#  Uydurma profille ayrı süreç: sabitler GERÇEKTEN profilden mi geliyor?
# --------------------------------------------------------------------
BETIK = u'''# -*- coding: utf-8 -*-
import json, sys
from pathlib import Path
sys.path.insert(0, %(kok)r)
import yollar
_veri = Path(%(veri)r)
yollar.veri = lambda *p: _veri.joinpath(*p)
import bolum, yonetmelik as ym, ders_programi as dp
print(json.dumps({
    "plan": {str(k): v for k, v in ym.VARSAYILAN_DONEM_PLANI.items()},
    "plan_toplami": ym.plan_toplami(),
    "tos_akts": ym.TOS_AKTS,
    "tos_adet": ym.TOS_AZAMI_ADET,
    "tos_kodlari": sorted(ym.TOS_DERSLERI),
    "sonradan": {k: v for k, v in ym.SONRADAN_EKLENEN_DERSLER.items()},
    "kapatma": ym.ACIK_KAPATMA_YARIYILI,
    "program_yili": ym.PROGRAM_YILI,
    "kompozisyon": sorted(ym.DONEM_KOMPOZISYONU),
    "gunler": list(dp.GUNLER),
    "sayfa": dp.SAYFA_ADI,
    "asenkron": sorted(dp.ASENKRON_DERSLER),
    "uygulamali": list(__import__("ozet").LABORATUVAR_ADLARI),
    "esik": ym.akts_kaybi_esigi(),
    "kohort_disi_2022": sorted(ym.kohort_disi_kodlar(2022)),
}, ensure_ascii=False))
'''


def _ayri_surecte(profil):
    """Verilen profille modülleri yükleyip sabitleri geri döndürür."""
    klasor = tempfile.mkdtemp(prefix="dkk_profil_")
    veri = os.path.join(klasor, "veri")
    os.makedirs(veri)
    with io.open(os.path.join(veri, "bolum.json"), "w",
                 encoding="utf-8") as f:
        f.write(json.dumps(profil, ensure_ascii=False))
    betik = os.path.join(klasor, "sor.py")
    with io.open(betik, "w", encoding="utf-8") as f:
        f.write(BETIK % {"kok": KOK, "veri": veri})
    ortam = dict(os.environ, PYTHONIOENCODING="utf-8")
    c = subprocess.run([sys.executable, betik], capture_output=True,
                       text=True, encoding="utf-8", errors="replace",
                       env=ortam)
    return c.returncode, c.stdout, c.stderr


SAHTE = {
    "surum": 1,
    "bolum": {"universite": "Selçuk Üniversitesi",
              "fakulte": "Mühendislik Fakültesi",
              "ad": "Sınama", "program_yili": 4},
    "plan": {"donem_akts": {"1": 31, "2": 31, "3": 31, "4": 31,
                            "5": 31, "6": 31, "7": 31, "8": 31}},
    "tos": {"akts": 5, "azami_adet": 2,
            "dersler": {"9999001": "SINAMA TOS I",
                        "9999002": "SINAMA TOS II"}},
    "kohort": {"sonradan_eklenen_dersler": {"9999501": 2025},
               "acik_kapatma_yariyili": 3},
    "donem_kompozisyonu": {"4": {"zorunlu_kodlar": ["9999401"],
                                 "tos_adedi": 2}},
    "program": {"sayfa_adi": "II. Öğretim",
                "gunler": ["PAZARTESİ", "SALI", "ÇARŞAMBA"],
                "saat_sutunlari": {"C": "09:00-09:45"},
                "tos_blok_adi": "ORTAK",
                "asenkron_dersler": ["SINAMA ASENKRON 1"],
                "esnek_dersler": [],
                "uygulamali_dersler": ["SINAMA LABORATUVARI 1"]},
}


def _profil_okunuyor_mu():
    print("")
    print("  === Profil gerçekten okunuyor mu? ===")
    kod, cikti, hata = _ayri_surecte(SAHTE)
    if kod != 0:
        print("  [HATA] uydurma profille süreç açılmadı:\n%s" % hata[-900:])
        OK.append(False)
        return
    g = json.loads(cikti)
    kontrol("yarıyıl planı profilden geliyor",
            {str(y): 31 for y in range(1, 9)}, g["plan"])
    kontrol("plan toplamı profilden türüyor", 248, g["plan_toplami"])
    kontrol("TOS AKTS'si profilden", 5, g["tos_akts"])
    kontrol("dönem başına TOS sınırı profilden", 2, g["tos_adet"])
    kontrol("TOS ders listesi profilden",
            ["9999001", "9999002"], g["tos_kodlari"])
    kontrol("sonradan eklenenler profilden",
            {"9999501": 2025}, g["sonradan"])
    kontrol("açık kapatma yarıyılı profilden", 3, g["kapatma"])
    kontrol("dönem kompozisyonu profilden", [4], g["kompozisyon"])
    kontrol("ders programı günleri profilden",
            ["PAZARTESİ", "SALI", "ÇARŞAMBA"], g["gunler"])
    kontrol("ders programı sayfası profilden", "II. Öğretim", g["sayfa"])
    kontrol("asenkron dersler profilden",
            ["SINAMA ASENKRON 1"], g["asenkron"])
    kontrol("uygulamalı dersler profilden",
            ["SINAMA LABORATUVARI 1"], g["uygulamali"])
    # Türetilmiş davranış da değişmeli. Eşik = plan - asgari + 1, yani
    # "kayıp bu sayıya ULAŞIRSA mezuniyet riske girer": plan 248, asgari
    # 240 -> 8 AKTS'ye kadar pay var, 9'uncuda 239'a düşer.
    kontrol("AKTS kaybı eşiği yeni plandan türüyor", 9, g["esik"])
    kontrol("kohort filtresi yeni derse uygulanıyor",
            ["9999501"], g["kohort_disi_2022"])
    # ...ve Matematik'in değerleri hiç sızmamalı
    kontrol("Matematik TOS kodu sızmıyor", False,
            any(k.startswith("2709") for k in g["tos_kodlari"]))
    kontrol("Matematik'in laboratuvarı sızmıyor", False,
            any("FIZIK" in a for a in g["uygulamali"]))


def _bozuk_profil_acilmiyor_mu():
    print("")
    print("  === Bozuk profil açılmıyor ===")

    def boz(**degisiklik):
        p = json.loads(json.dumps(SAHTE))
        for yol, deger in degisiklik.items():
            d = p
            parcalar = yol.split("__")
            for a in parcalar[:-1]:
                d = d[a]
            if deger is None:
                d.pop(parcalar[-1], None)
            else:
                d[parcalar[-1]] = deger
        return p

    durumlar = [
        ("program yılı tanımsız", boz(bolum__program_yili=3)),
        ("plan 240'ın altında",
         boz(plan__donem_akts={str(y): 25 for y in range(1, 9)})),
        ("plan eksik yarıyıl",
         boz(plan__donem_akts={str(y): 30 for y in range(1, 8)})),
        ("bölüm adı boş", boz(bolum__ad="")),
        ("TOS var ama AKTS yok", boz(tos__akts=None)),
        ("açık kapatma yarıyılı planda yok",
         boz(kohort__acik_kapatma_yariyili=99)),
        ("saat sütunu harf değil",
         boz(program__saat_sutunlari={"3": "09:00-09:45"})),
    ]
    for ad, p in durumlar:
        agir = [m for s, m in bolum.denetle(p) if s == "HATA"]
        kontrol("%s -> HATA" % ad, True, bool(agir))

    # Ve gerçekten AÇILMIYOR: bozuk profille süreç sıfırdan farklı biter
    kod, _, hata = _ayri_surecte(boz(bolum__program_yili=3))
    kontrol("bozuk profille modül yüklenmiyor", True, kod != 0)
    kontrol("hata mesajı sebebi söylüyor", True,
            "program_yili" in hata)

    # Profil hiç yoksa ne yapılacağını söylemeli
    klasor = tempfile.mkdtemp(prefix="dkk_profilsiz_")
    os.makedirs(os.path.join(klasor, "veri"))
    betik = os.path.join(klasor, "sor.py")
    with io.open(betik, "w", encoding="utf-8") as f:
        f.write(BETIK % {"kok": KOK,
                         "veri": os.path.join(klasor, "veri")})
    c = subprocess.run([sys.executable, betik], capture_output=True,
                       text=True, encoding="utf-8", errors="replace",
                       env=dict(os.environ, PYTHONIOENCODING="utf-8"))
    kontrol("profil yoksa açılmıyor", True, c.returncode != 0)
    kontrol("profil yoksa çözümü söylüyor", True,
            "kurulum.py" in (c.stdout + c.stderr))


def _yerlesik_profil_kontrolu():
    print("")
    print("  === Yerleşik profil (Matematik) ===")
    kontrol("veri/bolum.json var", True, bolum.yol().exists())
    kontrol("profil tutarlı", [], bolum.denetle())
    kontrol("bölüm adı yazılı", True, bool(bolum.ad()))
    kontrol("plan toplamı yönetmelik asgarisinin üstünde", True,
            sum(bolum.donem_plani().values())
            >= ym.MEZUNIYET_AKTS[bolum.program_yili()])

    # yonetmelik ve ders_programi profille AYNI değeri taşımalı;
    # ayrışırlarsa biri koda geri kaçmış demektir.
    kontrol("yonetmelik planı = profil", bolum.donem_plani(),
            ym.VARSAYILAN_DONEM_PLANI)
    kontrol("yonetmelik TOS'u = profil", bolum.tos_dersleri(),
            ym.TOS_DERSLERI)
    kontrol("yonetmelik TOS AKTS = profil", bolum.tos_akts(), ym.TOS_AKTS)
    kontrol("yonetmelik TOS adedi = profil", bolum.tos_azami_adet(),
            ym.TOS_AZAMI_ADET)
    kontrol("yonetmelik sonradan eklenenleri = profil",
            bolum.sonradan_eklenen_dersler(), ym.SONRADAN_EKLENEN_DERSLER)
    kontrol("yonetmelik kapatma yarıyılı = profil",
            bolum.acik_kapatma_yariyili(), ym.ACIK_KAPATMA_YARIYILI)
    kontrol("yonetmelik kompozisyonu = profil", bolum.donem_kompozisyonu(),
            ym.DONEM_KOMPOZISYONU)
    kontrol("yonetmelik program yılı = profil", bolum.program_yili(),
            ym.PROGRAM_YILI)

    pr = bolum.program_ayarlari()
    kontrol("program günleri = profil", tuple(pr["gunler"]), dp.GUNLER)
    kontrol("program saatleri = profil", pr["saat_sutunlari"],
            dp.SAAT_SUTUNLARI)
    kontrol("asenkron dersler = profil", set(pr["asenkron_dersler"]),
            dp.ASENKRON_DERSLER)
    kontrol("esnek dersler = profil", set(pr["esnek_dersler"]),
            dp.ESNEK_DERSLER)
    import ozet
    kontrol("uygulamalı dersler = profil",
            tuple(pr["uygulamali_dersler"]), ozet.LABORATUVAR_ADLARI)
    kontrol("TOS blok adı = profil", pr["tos_blok_adi"], dp.TOS_BLOK_ADI)


def _teyit_kontrolu():
    """Bölüm teyidi bir kez soruluyor ve KOPYALANMIYOR mu?

    Teyit kopyalanırsa karşı taraf soruyu hiç görmez: başka bir bölümün
    planıyla çalıştığını fark etmeden pano üretir. Depoya girerse aynı
    şey herkes için olur.
    """
    print("")
    print("  === Bölüm teyidi ===")
    import baslat
    import paylas

    kaynak = io.open(os.path.join(KOK, "baslat.py"),
                     encoding="utf-8").read()
    kontrol("teyit ana akışta soruluyor", True,
            "kaynak_teyidi(sor)" in kaynak)
    kontrol("teyit üç sonuç veriyor", True,
            all(x in kaynak for x in ('== "dur"', '== "kur"')))

    # SIRA: teyit ve belge akışı SİCİL/ŞİFREDEN ÖNCE olmalı. Yanlış
    # bölümün belgeleriyle OBİS'e girmenin anlamı yok; üstelik
    # kullanıcıdan şifresini istemeden önce neyle çalışacağımızı
    # göstermek doğrusu.
    govde = kaynak.split("def main(")[1]
    yerler = {ad: govde.find(ad) for ad in
              ("kaynak_teyidi(sor)", "belge_akisi(sor)",
               "ayarlari_oku()", "tek_ogrenci_sor()")}
    kontrol("teyit, giriş bilgilerinden ÖNCE", True,
            0 <= yerler["kaynak_teyidi(sor)"] < yerler["ayarlari_oku()"])
    kontrol("belge akışı, giriş bilgilerinden ÖNCE", True,
            0 <= yerler["belge_akisi(sor)"] < yerler["ayarlari_oku()"])
    kontrol("giriş bilgileri, öğrenci sorusundan önce", True,
            yerler["ayarlari_oku()"] < yerler["tek_ogrenci_sor()"])

    # Kurulumdan sonra YENİDEN BAŞLATMA: modül sabitleri import anında
    # donuyor; aynı çalışmada taramak eski bölümün planıyla hesaplamak
    # demek olurdu.
    kontrol("kurulumdan sonra yeniden başlatılıyor", True,
            "_yeniden_baslat()" in kaynak)
    kontrol("teyit kurulum yolunu gösteriyor", True,
            "kurulum.py" in kaynak)
    kontrol("teyit yazılan köke yazılıyor", True,
            "yollar.yazilan_kok() / ONAY_DOSYASI" in kaynak)
    kontrol("teyit paylaşımda YASAK", True,
            baslat.ONAY_DOSYASI in paylas.YASAK)
    kontrol("teyit paylaşım listelerinde DEĞİL", [],
            [d for d in (paylas.KOD + paylas.VERI + paylas.TESTLER)
             if baslat.ONAY_DOSYASI in d])

    # .gitignore kapsıyor mu? (depoya girerse herkes onaylanmış başlar)
    gi = os.path.join(os.path.dirname(KOK), ".gitignore")
    if os.path.exists(gi):
        kontrol("teyit .gitignore'da", True,
                baslat.ONAY_DOSYASI in io.open(gi, encoding="utf-8").read())


def _kaynak_kontrolu():
    """Bölüme özgü sayılar koda geri sızmasın."""
    import re

    print("")
    print("  === Bölüm sabiti koda geri sızmadı mı? ===")
    nerede = {
        "yonetmelik.py": ("VARSAYILAN_DONEM_PLANI", "TOS_DERSLERI",
                          "TOS_AKTS", "TOS_AZAMI_ADET",
                          "SONRADAN_EKLENEN_DERSLER",
                          "ACIK_KAPATMA_YARIYILI", "DONEM_KOMPOZISYONU",
                          "PROGRAM_YILI"),
        "ozet.py": ("LABORATUVAR_ADLARI",),
        "ders_programi.py": ("SAAT_SUTUNLARI", "GUNLER", "TOS_BLOK_ADI",
                             "ASENKRON_DERSLER", "ESNEK_DERSLER"),
    }
    for dosya, adlar in sorted(nerede.items()):
        kaynak = io.open(os.path.join(KOK, dosya), encoding="utf-8").read()
        # Yorum satırları örnek verebilir; yalnız KOD satırlarına bakıyoruz.
        kod_satirlari = [s for s in kaynak.splitlines()
                         if s.strip() and not s.lstrip().startswith("#")]
        for ad in adlar:
            atama = [s for s in kod_satirlari
                     if re.match(r"^%s\s*=" % ad, s)]
            kontrol("%s: %s tek yerde atanıyor" % (dosya, ad), 1,
                    len(atama))
            kontrol("  değeri profilden geliyor", True,
                    bool(atama) and ("bolum." in atama[0]
                                     or "_P[" in atama[0]))


def main():
    _yerlesik_profil_kontrolu()
    _profil_okunuyor_mu()
    _bozuk_profil_acilmiyor_mu()
    _teyit_kontrolu()
    _kaynak_kontrolu()
    print("")
    print("  %d/%d kontrol geçti." % (sum(OK), len(OK)))
    return 0 if all(OK) else 1


if __name__ == "__main__":
    sys.exit(main())
