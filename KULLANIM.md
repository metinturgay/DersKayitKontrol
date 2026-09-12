# Ders Kayıt Kontrol — Kullanım

> Kısa tanıtım, ekran görüntüleri ve **ilk kurulum** için önce
> [README.md](README.md) dosyasına bakın. Burası ayrıntılı el kitabıdır.

Danışman öğrencilerinin ders kayıtlarını OBİS'ten okuyup, yönetmelik ve
bölüm kurallarına göre bir **danışman özeti panosu** üretir.

> **Bu araç hiçbir şeyi değiştirmez.** Ders eklemez, çıkarmaz, kaydetmez,
> onaylamaz, reddetmez. Yalnızca okur ve raporlar. Onay/ret kararı size
> aittir. Tek yazma işlemi, açtığı öğrencinin **kilidini geri bırakmaktır**
> — OBİS bir öğrencinin sayfası açıldığında onu kilitliyor, script her
> öğrenciden sonra bu kilidi kaldırıyor.

---

## Hangi durumda ne çalıştırmalıyım?

| Durum | Komut |
|---|---|
| **Dönem başı, ilk kez çalıştırıyorum** | `python ders_kayit.py --tumu --pano --html` |
| Öğrenciler ders seçimi yaptı, **güncel veri istiyorum** | `python ders_kayit.py --tumu --pano --html` |
| **Kural değişti**, veri aynı — panoyu yenile | `python panoyu_yenile.py` |
| Tek öğrenciyle **hızlı deneme** yapacağım | `python ders_kayit.py --pano` |
| Panoya değil, **terminale** bakmak istiyorum | `python ders_kayit.py --tumu` |
| Kod değiştirdim, **bozdum mu** diye bakacağım | `cd testler` → aşağıdaki testler |

En sık kullanacağınız ikisi:

```bash
python ders_kayit.py --tumu --pano --html
```

```bash
python panoyu_yenile.py
```

### Tek öğrenciyi değiştirdim, sadece onu görmek istiyorum

```bash
python ders_kayit.py --ogrenci 230000003
```

Ayrıntısı aşağıda: [Tek öğrenciyi tazeleme](#tek-öğrenciyi-tazeleme).

### Tek komut yeterli mi?

**Evet — normal kullanımda `python ders_kayit.py --tumu --pano --html`
tek başına yeterli.** OBİS'e girer, 60 öğrenciyi okur, çakışma tablosunu,
AKTS değişimini, kontenjan planını ve öğrenci sayfalarını üretir.

Şu **üç durumda** önce başka bir komut çalıştırmanız gerekir, çünkü bu
üç dosya OBİS'ten değil sizin verdiğiniz belgelerden üretiliyor:

| Ne değiştiyse | Önce bunu çalıştırın |
|---|---|
| **Ders programı** (`veri/*.xlsx`) yenilendi | `python ders_programi.py` |
| **Okutulacak dersler belgesi** (`veri/*.docx`) yenilendi | `python mufredat.py` |
| Yalnızca **kural/metin** değişti, veri aynı | `python panoyu_yenile.py` (tarama gerekmez) |

Bu üçü değişmediyse tek komut yeter. `veri/cakismalar.json` ve
`veri/mufredat.json` diskte durduğu sürece her taramada yeniden okunur.

---

## Başka bir bölümde kullanmak

Bu araç Matematik bölümü için yazıldı ama içindeki kuralların neredeyse
tamamı **Selçuk Üniversitesi'nin tümü için aynı**: not tablosu, AKTS
limiti, azami süre, devam koşulu, mezuniyet asgarisi. Hepsi
`yonetmelik.py` içinde ve hiçbir bölüm bunları değiştiremez.

Bölümden bölüme değişen şeyler bir avuç:

    yarıyıl AKTS planı · TOS ders listesi · dönem kompozisyonu ·
    müfredata sonradan eklenmiş dersler · ders programının sayfa düzeni

Bunların hepsi `veri/bolum.json` dosyasındadır (**bölüm profili**). Bir
zamanlar Matematik'in değerleri doğrudan koda yazılıydı; başka bir
bölümün danışmanı aracı açtığında o sayılar sessizce yanlış sonuç
üretiyordu. Artık profil yoksa program **açılmaz** ve ne yapılacağını
söyler — uydurma varsayılana düşmez.

### Danışmandan ne isteniyor?

```bash
python kurulum.py --belgeler
```

Kısaca:

| # | Belge | Ne çözüyor | Zorunlu mu |
|---|---|---|---|
| 1 | Son 4-5 yılın **"Okutulacak Dersler"** belgesi (docx), `veri/mufredat/<yıl>.docx` | yarıyıl planı, zorunlu/seçmeli/TOS ayrımı, **AKTS'si değişen dersler**, **müfredata sonradan eklenmiş dersler** | **Evet** (en az 2 yıl) |
| 2 | Bu yarıyılın **ders programı** (xlsx), `veri/ders_programi.xlsx` | çakışma denetimi (MADDE 9/1-b) | Hayır |
| 3 | **Birkaç soru**: fakülte/bölüm adı ve program yılı; açığın hangi yarıyıldan kapatıldığı; sabit saati olmayan dersler; laboratuvar/uygulama dersleri | profilin insandan gelmesi gereken kısmı — belgede yazmayan bölüm kararları | Evet |

Dosya adındaki yıl, o belgenin geçerli olduğu **giriş yılıdır**;
`2024-2025 Okutulacak Dersler.docx` de olur, baştaki yıl okunur.

**Neden 4-5 yıl?** Çünkü bu, danışmandan *daha fazla* değil *daha az*
şey istemek demek. Matematik'te iki bilgi elle koda yazılmıştı ve
ikisi de transkriptler tek tek karşılaştırılarak ölçülmüştü:

* hangi ders hangi girişten itibaren geçerli (müfredata sonradan
  eklenenler — eski kohort onları almayacak),
* her dersin hangi kohortta kaç AKTS olduğu.

Başka bir danışmandan aynı arkeolojiyi beklemek gerçekçi değil. Oysa
ikisi de zaten yazılı: bölümün her yıl yayımladığı belgede. Belgeler
yan yana konunca

* bir yılda **ortaya çıkan** ders → sonradan eklenen ders,
* yıldan yıla **AKTS'si değişen** ders → kohort AKTS tabanı,
* bir yılda **kaybolan** ders → kaldırılmış ders

kendiliğinden çıkıyor.

**Tek yıl verirseniz** araç yine çalışır; yarıyıl planı, TOS listesi ve
dönem kompozisyonu tek belgeden de çıkar. Ama **AKTS kaybı ve kohort
açığı hesaplanamaz** — karşılaştıracak ikinci yıl yoktur. Bu bir
eksiklik değil, elde veri yok demektir; araç bunu uydurmaz.

> **Uydurma üretmeme kuralı.** Bir ders arşivin *en eski* yılında zaten
> varsa, ondan önce var mıydı bilinmez. Böyle bir dersi "sonradan
> eklendi" saymak, hiç yaşanmamış bir AKTS açığı uydurmak olurdu. Bu
> yüzden yalnızca en eski yıldan **sonra** ortaya çıkan dersler sayılır.

### İlk çalıştırmada bölüm teyidi

`python baslat.py` (ve exe) ilk açılışta **hangi bölüm için
yapılandırıldığını gösterip teyit ister**:

```
  Bu araç şu bölüm için yapılandırılmış:

      Selçuk Üniversitesi Fen Fakültesi Matematik Bölümü

  Bütün AKTS hesapları ... BU BÖLÜMÜN planına göre yapılır.
  Başka bir bölümün danışmanıysanız sonuçlar YANLIŞ olur.

  Bu sizin bölümünüz mü? [e/h]
```

*Neden var:* araç bir kopya ya da exe olarak elden ele geçebiliyor ve
içinde **başka bir bölümün** profili gelebiliyor. Program yine çalışır,
pano yine dolar ve sayıların hepsi o bölümün planına göre hesaplanır.
Pano başlığına bölüm adını yazmak görünürlük sağlar ama kimse başlığı
okumaz; bir kez sormak gerekir.

*"h"* derseniz tarama başlamaz ve kurulum yolu gösterilir. *"e"*
derseniz cevap `bolum_onayi.json` dosyasına yazılır ve bir daha
sorulmaz. Profil değişirse yeniden sorulur.

Bu dosya `.gitignore` içindedir ve `paylas.py` onu **kopyalamaz** —
kopyayı alan kişi soruyu kendisi görmeli.

`DanismanOzeti.exe --belgeler` da hangi belgelerin gerektiğini yazar.

### Kurulum

```bash
python kurulum.py --belgeler   # danışmandan ne isteneceği
python kurulum.py --denetle    # elde ne var, ne eksik
python kurulum.py              # sihirbaz: türetir, kalanı sorar
python kurulum.py --otomatik   # soru sormadan taslak üretir
python bolum.py --denetle      # profil kendi içinde tutarlı mı
```

`--otomatik` **asla** çalışan bir profilin üstüne yazmaz;
`veri/bolum.taslak.json` bırakır. Taslakta insanın vermesi gereken
alanlar (program yılı, açık kapatma yarıyılı) boştur ve öyle bir dosya
profil olarak **kullanılamaz** — yarım bir profille sessizce çalışmaktansa
açılmamak yeğdir.

Sihirbaz ders programı xlsx'ini de açıp sayfa adını ve saat sütunlarını
kendisi bulur. Doğrulandı: Matematik'in elle kodlanmış on saat sütunu ile
sihirbazın aynı dosyadan okuduğu düzen **birebir aynı**.

### Neyi istemiyoruz

Öğrenci listesi, transkript, not dökümü istemiyoruz. Öğrenci verisi
yalnız OBİS'ten, danışmanın kendi oturumuyla okunur ve bilgisayardan
dışarı çıkmaz.

---

## Çalıştırılabilir scriptler

### `ders_kayit.py` — OBİS'ten veri çeker

Chrome'u açar, OBİS'e girer, danışman öğrenci listesini okur, her öğrenciyi
tek tek açıp ders kaydını ve transkriptini alır, kilidi bırakır.

```bash
python ders_kayit.py [--tumu] [--pano] [--html]
```

| Bayrak | Ne yapar |
|---|---|
| _(yok)_ | Sadece **ilk** öğrenciyi işler, sonucu terminale basar. Deneme için. |
| `--tumu` | Ders seçmiş **tüm** öğrencileri işler. |
| `--pano` | HTML panoyu üretir. Yazmazsanız terminale döker. |
| `--html` | Her öğrencinin ham sayfasını `cikti/` altına kaydeder. |

**`--html` neden önemli:** Ham sayfalar diskte kalırsa, kuralları
değiştirdiğinizde OBİS'e tekrar girmeye ve öğrencileri tekrar kilitleyip
açmaya gerek kalmaz — `panoyu_yenile.py` panoyu diskten yeniden üretir.
Rutin taramalarda `--html` kullanmanızı öneririm.

**Giriş:** Kalıcı Chrome profili sayesinde önceki oturum genelde hâlâ
geçerlidir ve giriş adımı atlanır. Değilse sicil ve şifre `.env`'den
otomatik doldurulur, **güvenlik kodunu (captcha) siz yazarsınız**; script
300 saniye bekler.

**Süre:** 59 öğrenci yaklaşık 5–8 dakika. `--pano` modunda iş bitince
tarayıcı kapanır (oturum profilde saklı kalır, giriş kaybolmaz).

### `ders_programi.py` — ders programını çözer

```bash
python ders_programi.py
```

`veri/*.xlsx` (yoksa Masaüstü) içindeki ders programını okuyup birlikte
alınamayacak ders çiftlerini `veri/cakismalar.json` dosyasına yazar.
Program dosyası güncellendiğinde bir kez çalıştırın, ardından
`panoyu_yenile.py`.

### `mufredat.py` — müfredat belgesini çözer

```bash
python mufredat.py
```

`veri/mufredat.docx` (okutulacak dersler belgesi) içindeki 8 yarıyılın
ders listesini `veri/mufredat.json` dosyasına yazar.

**Bu belge AKTS için tek doğru kaynaktır.** Kalınan ya da eksik bir ders
yeni dönemde alındığında buradaki AKTS geçerli olur; OBİS katalogu farklı
söylerse belge esas alınır ve danışmana uyarı çıkar.

### `mufredat_denetle.py` — sistemi belgeye karşı doğrular

```bash
python mufredat_denetle.py
```

Dönem planını, dönem kompozisyonunu, TOS listesini, OBİS katalogundaki ve
transkriptlerdeki AKTS değerlerini belgeyle karşılaştırıp farkları
raporlar. Belge güncellendiğinde çalıştırın.

### `program_denetle.py` — program okumasını denetler

```bash
python program_denetle.py
```

Excel'den bir şey kaçırıp kaçırmadığımızı raporlar: birleşik hücreler
(dikey/yatay ayrımıyla), okunamayan hücreler, katalogda olup programda
olmayan dersler, benzerlikle eşleşmiş adlar ve derslik çakışmaları.
Program dosyası değiştiğinde çalıştırıp çıktısına bakın.

### Tek öğrenciyi tazeleme

Bir öğrencinin kaydını OBİS'te elle düzelttiniz ve son durumu görmek
istiyorsunuz. 60 kişiyi yeniden taramaya gerek yok:

```bash
python ders_kayit.py --ogrenci 230000003
```

Numara yerine ad da yazabilirsiniz (`--ogrenci "ayşe yıl"`); numaranın
bir parçası da yeter (`--ogrenci 9003`). Arama Türkçe büyük/küçük harfe
takılmaz. Birden fazla öğrenci eşleşirse hiçbirini seçmez, adayları
listeler ve durur — yanlış öğrenciyi taramaktansa sormak yeğdir.

Nasıl çalışıyor: yalnız o öğrencinin sayfası ve transkripti OBİS'ten
yeniden okunup `cikti/` altına yazılır, sonra **pano diskteki bütün
öğrencilerden yeniden kurulur**. Diğer 59 öğrencinin verisi olduğu
gibi korunur; panoda eksik kimse olmaz.

`--tumu`, `--pano`, `--html` yazmaya gerek yok, hepsi kendiliğinden
uygulanır.

**Pano hangi satırın taze olduğunu söyler.** Her öğrencinin sayfasında
"OBİS okuması: gg.aa.yyyy ss:dd" rozeti var; en son okunan dışındakiler
sarı "eski" rozetiyle işaretlenir. Başlıkta da okuma aralığı yazar:
*"okumalar 12:30 – 14:30 arası (59 öğrenci daha eski)"*. Kısmi tazeleme
yapılmamışsa bu satır hiç çıkmaz.

---

### `panoyu_yenile.py` — panoyu diskten yeniden üretir

```bash
python panoyu_yenile.py
```

`cikti/` altındaki ham sayfaları okuyup panoyu baştan kurar. **OBİS'e
bağlanmaz**, birkaç saniye sürer. Önce en az bir kez `--html` ile tarama
yapmış olmanız gerekir.

Kural değiştirdiğinizde, uyarı metinlerini düzenlediğinizde veya pano
tasarımına dokunduğunuzda bunu kullanın.

---

## Çıktılar

Hepsi `cikti/` klasöründe:

| Dosya | İçerik |
|---|---|
| `danisman_ozeti.html` | **Pano.** Çift tıklayıp tarayıcıda açın. |
| `danisman_ogrenci_listesi.csv` | Öğrenci listesi ve onay durumları |
| `ders_sayfasi_<no>.html` | Ham ders kayıt sayfası (`--html` ile) |
| `transkript_<no>.html` | Ham transkript (`--html` ile) |

`cikti/` ve `chrome-profili/` **gitignore'da** — öğrenci verisi ve oturum
bilgisi depoya girmez.

### Panoyu kullanma

Pano tek bir HTML dosyasıdır: sunucu, internet, kütüphane gerekmez. Çift
tıklayıp açabilir, e-postayla gönderebilirsiniz — ama içinde öğrenci
adları, numaraları ve notları vardır, dolayısıyla **kişisel veridir**.

- **Sol taraf:** öğrenciler numaraya göre sıralı. Arama kutusu ad ve numarada
  çalışır. `Yapılacak / Dikkat / Temiz` süzgeçleri var.
  Adın altındaki ince şerit **kazanılmış AKTS'nin plana oranıdır**;
  sağ ucundaki kırmızı pay varsa plana ulaşılamayan kısımdır.
- **Rozetler:** kırmızı = müdahale gereken uyarı sayısı, sarı = kontrol.
- **Klavye:** `↑` `↓` ya da `j` `k` öğrenciler arasında gezinir,
  `/` arama kutusuna atlar, `Esc` aramayı temizler. Altmış öğrenci
  fareyle tek tek tıklanacak bir liste değil.
- **Sağ taraf:** üstte künye (GANO, sınıf, AKTS limiti, seçilen, alttan,
  mezuniyet AKTS). Altında:
  - **Mezuniyet ilerlemesi** — mezuniyet AKTS'sinin dört parçası orantıyla:
    *başarılı* (koyu), *kalan yükümlülük*, *girilmemiş dönemler* (soluk)
    ve *plana ulaşılamayan* (kırmızı kuyruk). Çizgi yönetmelik asgarisini
    (240) gösterir; kuyruk çizginin sağında başlıyorsa öğrenci asgariyi
    tutturamıyor demektir. Yanındaki rozet farkı sayıyla söyler:
    `3 AKTS pay` ya da `6 AKTS eksik`.
  - **Yarıyıl yarıyıl** — sekiz yarıyıl tek satırda, her birinde
    `geçilen/plan`. Yeşil = plan dolmuş, sarı = girilmiş ama eksik,
    **kırmızı = yarıyılın kendi içinde kapanmayan açık** (bkz. kohort
    açığı), gri = henüz girilmemiş. Çerçeveli olan hedef yarıyıldır.
    Danışmanın ilk sorusu olan "bu öğrenci nerede tıkanmış?" tek bakışta
    cevaplanıyor.
  - **Özeti kopyala** — başlıktaki düğme öğrencinin uyarılarını düz metin
    olarak panoya kopyalar; görüşmede e-postaya ya da mesaja olduğu gibi
    yapıştırılabilir. Metnin sonunda özetin salt okuma ile üretildiği,
    hiçbir dersin eklenmediği/onaylanmadığı yazar.

  Bunların altında **iki sekme**:
  - **Danışman özeti** — AKTS limitinin nasıl belirlendiği, uyarı kartları
    (her birinde dayandığı madde), mezuniyet AKTS hesabı, dönem
    kompozisyonu, çakışmalar, seçilen ve alttan dersler, transkript özeti.
    Sekme başlığındaki sayı, müdahale + dikkat uyarılarının toplamı.
  - **Transkript** — *öğrencinin TAM transkripti.* Yarıyıl yarıyıl, OBİS'teki
    sırayla: kod, ders, AKTS, yıl, iki vize, final, bütünleme ve harf.
    Üstte GANO, toplam AKTS, son dönem ortalaması ve kayıt sayısı;
    hemen altında **toplam AKTS ve GANO'nun kendi hesabımızla tutup
    tutmadığı** (tutmuyorsa ayrıştırma kaymış demektir, oradaki her sayı
    şüphelidir). Her dönem başlığında o dönemin kayıt sayısı ve geçilen
    AKTS'si yazar.
    Arama kutusu ders adı ve kodunda arar. **Geçersiz denemeler
    varsayılan olarak gizlidir**: bir ders birden çok kez alındıysa OBİS
    eskisini geçersiz işaretler, satır transkriptte durur ama artık
    sayılmaz — hepsini birden göstermek aynı dersi üç kez listeleyip
    danışmanı yanıltıyordu. "Geçersiz denemeleri de göster" kutucuğu
    açınca soluk renkte, *"geçersiz — sonradan tekrar alınmış"* notuyla
    görünürler; "kaçıncı denemede geçti" sorusunu ancak onlar yanıtlar.
    Harf rengi harfin kendisine değil **sonuca** bakar: DC yarıyıl
    ortalamasına göre geçer ya da kalır (MADDE 15/1).
  Öğrenci değiştirince sekme özete döner; transkript araması ve
  "geçersizleri göster" tercihi korunur (aynı dersi birkaç öğrencide
  arka arkaya aramak yaygın).
- **Yazdırma:** sayfa yazdırılabilir. Yan panel ve düğmeler çıkmaz,
  kaydırmalı tablolar açılır — yoksa geniş tabloların yarısı kâğıda hiç
  gelmiyordu. Görüşmeye girmeden önce ilgili öğrencinin sayfasını açıp
  yazdırın.
- **Koyu tema:** işletim sisteminizin temasını izler; ayrı bir düğme yok.
- **Öğrencinin çakışmaları iki ayrı bölümde:**
  - **Çakışma — DEĞİŞTİRİLMELİ:** her iki derste de devam zorunluluğu var,
    ikisine birden girilemez. Her çift için hangi dersin yerine hangisinin
    konabileceği listelenir; adaylar "çakışmasız" ya da hangi dersle
    çakıştığı yazılarak gösterilir. Korunacak dersle çakışan, yani sorunu
    çözmeyen aday hiç önerilmez. Zorunlu ders ise "yerine başka ders
    konamaz" denir.
  - **Çakışma — devamsızlık hakkına sığıyor:** iki derste de devam zorunlu
    ama çakışan saatler devamsızlık hakkının içinde kalıyor (MADDE 10/1:
    teorikte %30, uygulamada %20). Öğrenci çakışan saatte birine girer,
    kaçırdığı saatler haktan düşer — **ikisi birlikte alınabilir**. Kartta
    her dersin haftalık saati, hakkı, çakışan saat ve geriye kalan pay
    yazar; kaybın tek derse yığılıp yığılamayacağı da belirtilir.
    Çakışmasız bir alternatif varsa ayrıca gösterilir.
  - **Çakışma var — devam zorunluluğu yok:** en az bir tarafta devam şartı
    daha önce sağlanmış (MADDE 10/2). Bildirilir ama **değiştirilmesi
    zorunlu değildir**. Hangi dersin neden muaf olduğu satırda yazar.
- **Sol üstteki altı düğme** öğrenci listesinden bağımsız görünümler açar:
  - **Yönetici Özeti** — hangi dersten kaç ilave kontenjan açılmalı, bu
    ihtiyaç hangi öğrencilerden geliyor.
  - **Çakışma Tablosu** — hangi ders alınırsa hangileri alınamaz. Arama
    kutusu ders adında, çakıştığı derslerde ve saatlerde arar.
  - **Dersler** — dönem dönem (1/3/5/7) ders listesi: kod, ad, AKTS, tip
    (zorunlu/seçmeli/TOS), kontenjan, program saati, kaç dersle çakıştığı.
    Arama kutusu kod, ad, saat ve tipte arar.
  - **Çözülmeli Çakışma** — *kesin düzeltilmesi gereken çakışması olan
    öğrenciler.* Yalnız **iki tarafında da devam zorunluluğu olan**
    çakışmalar buraya girer (MADDE 9/1-b); öğrenci ikisine birden
    giremeyeceği için bir ders mutlaka değişmeli. Çakışma sayısı çok
    olan öğrenci üstte. Her çift için saatler, neden zorunlu olduğu ve
    **hangi dersin yerine hangisinin konabileceği** yazar; adaylar
    "çakışmasız" ya da hangi dersle çakıştığı belirtilerek gösterilir.
    Öğrenci adına tıklayınca sayfası açılır.
    Künyede diğer iki çakışma türünün sayısı da yazar (devamsızlık
    hakkına sığan / devam zorunluluğu olmayan) — **onlar buraya
    girmez**, zorunlu değiller; ayrıntıları öğrenci sayfalarında.
    Arama kutusu hem öğrenci hem ders adında çalışır.
  - **Ders Alanlar** — *hangi dersi hangi öğrenci almış.* Dersler döneme
    göre gruplanır; her dersin kutusunda o dersi **bu dönem seçmiş**
    öğrenciler listelenir: numara, ad, sınıf, hedef dönem ve seçimin
    `ilk kez` mi `TEKRAR` mı olduğu. Başlıkta kaç öğrenci olduğu, AKTS,
    ders tipi ve kontenjanın dolu olup olmadığı yazar. Öğrenci satırına
    tıklayınca o öğrencinin sayfası açılır.
    Kutunun altında, varsa, **"bu dersi alması gerekirken seçmemiş"**
    satırı çıkar: alttan kalmış, ders bu dönem açık, ama öğrenci
    seçmemiş. Kimsenin almadığı ama birinin alması gereken ders de
    listede görünür ("kimse almamış").
    Arama kutusu ders adı ve kodunda arar; **öğrenci adı ya da numarası
    da eşleşir** — o zaman yalnız o öğrencinin dersleri kalır.
  - **AKTS Değişimi** — AKTS'si değişmiş dersler, sekiz yarıyıl için,
    **giriş yılına göre ayrı ayrı**. Eski değer önce o kohortun kendi
    transkript kayıtlarından, yoksa `veri/akts_referans.json`
    fotoğrafından gelir; hiçbiri yoksa ders değişmemiş sayılır. Güncel
    değer müfredat belgesinden. Kod değişikliği, dersin bu dönem açık
    olup olmadığı ve kaç öğrencinin o dersten kaldığı da tabloda. Aynı
    dersi farklı kohortlar farklı AKTS ile taşıyorsa satırda
    "GİRİŞ YILINA GÖRE FARKLI" diye işaretlenir. Varsayılan olarak
    yalnızca değişenler görünür; kutucukla tamamı açılır.
- **Arama kutuları Türkçe büyük/küçük harfe takılmaz.** "İSTATİSTİK",
  "Istatistik" ve "istatistik" aynı sonucu verir. Düz Türkçe küçültme
  bunu beceremiyordu: "I" dotsuz "ı"ya düşüyor, ders adındaki "İ" ise
  "i"ye; arada nokta farkı kalınca hiçbir şey bulunamıyordu. Dört i
  türevi de tek biçime katlanıyor (`_kucult`).
- **Görünüm işletim sisteminin temasına uyar.** Sistem koyu temadaysa pano
  da koyu açılır (`prefers-color-scheme`). Renklerin tamamı tek bir
  değişken kümesinden geliyor; koyu tema yalnızca o kümeyi yeniden
  tanımlıyor, bileşenlerin hiçbiri sabit renk yazmıyor. Dar ekranda
  (820 pikselin altı) sol panel üste geçer ve görünüm düğmeleri yan yana
  kaydırılabilir bir şeride dönüşür.
- Sayfa yazdırmaya uygun; yazdırırken sol liste, sekme çubuğu ve arama
  kutuları gizlenir. **Yalnızca o an açık olan sekme basılır** — ikisini
  de istiyorsanız iki kez yazdırın.

---

### Yönetici Özeti

Üstte üç dağılım: **durum** (yapılacak / dikkat / temiz), **mezuniyet
projeksiyonu** (asgarinin altında / payı 5 AKTS'nin altında / rahat) ve
birden çok kohort varsa **giriş yılı**. "Grubum genel olarak nerede?"
sorusu bu üç kutuda cevaplanır; altındaki kontenjan planı ise "hangi
dersten kaç kişilik yer açılmalı" sorusunu yanıtlar.

---

## Modüller

Aşağıdakiler çoğunlukla başka modüller tarafından kullanılır; `bolum.py`,
`mufredat_arsivi.py` ve `kurulum.py` ayrıca doğrudan çalıştırılabilir
(bkz. [Başka bir bölümde kullanmak](#başka-bir-bölümde-kullanmak)).

| Dosya | Sorumluluk |
|---|---|
| `yonetmelik.py` | Yönetmelik kuralları. Her sabitin yanında dayandığı madde yazılı. Selenium bağımlılığı yok, saf hesap. Bölüme özgü olan hiçbir şey burada değil; hepsi `bolum.py` üzerinden gelir. |
| `bolum.py` | **Bölüm profili** (`veri/bolum.json`): yarıyıl planı, TOS listesi, dönem kompozisyonu, sonradan eklenen dersler, ders programının sayfa düzeni. Profil yoksa ya da tutarsızsa modül açılmaz. |
| `mufredat_arsivi.py` | Son yılların müfredat belgelerini yan yana koyar; sonradan eklenen dersleri, AKTS değişimlerini ve kohort AKTS tabanlarını **türetir**. |
| `eslestirme.py` | Ders adı normalleştirme ve benzerlik. Yönetmelikten ayrı durur çünkü kurulum sihirbazının profil *üretmeden önce* ders adlarını eşleştirmesi gerekir. |
| `ozet.py` | Kural motoru. Ders kaydı + transkript + yönetmeliği birleştirip `yapilacak / dikkat / bilgi` uyarıları üretir. Kontenjan planı da burada. |
| `rapor.py` | HTML panoyu yazar. Veri sayfaya gömülür; sunucu, internet ya da kütüphane gerekmez. |
| `ders_programi.py` | Ders programı xlsx'ini çözer, çakışan ders çiftlerini çıkarır. Sayfa düzeni ve asenkron/esnek ders listeleri bölüm profilinden gelir. |
| `mufredat.py` | Müfredat belgesini (docx) çözer. AKTS için tek doğru kaynak. |
| `akts_degisimi.py` | AKTS'si değişmiş dersleri **giriş yılı (kohort) başına** çıkarır; panonun AKTS Değişimi sekmesini besler. Eski değeri sırayla arar: kohortun kendi transkript kaydı → referans fotoğrafı → o kohort girdiğinde yürürlükte olan müfredat belgesi → hiçbiri yoksa "değişmemiş". |
| `kurulum.py` | Yeni bir bölüm için kurulum sihirbazı. Belgelerden türetir, yalnız türetilemeyeni sorar. |
| `paylas.py` | Başka bir danışmana verilebilecek temiz bir kopya hazırlar: öğrenci verisi, şifre ve tarayıcı profili dışarıda kalır. |
| `yollar.py` | Dosya yolları. Exe içinde OKUNAN kök (gömülü veri) ile YAZILAN kökü (exe'nin yanı) ayırır; sys.frozen'ı bilen tek yer. |
| `baslat.py` | Exe'nin giriş noktası: giriş bilgisini sorar, tarar, panoyu üretip açar. |
| `exe_yap.py` | Tek dosyalık `DanismanOzeti.exe` üretir. |
| `ornek_uret.py` | Yayımlanabilir **örnek pano** üretir — tamamen uydurma öğrencilerle. `cikti/` klasörüne hiç bakmaz. |
| `ornek/gorsel_uret.py` | Örnek panonun ekran görüntülerini alır (README için). |

**Kural eklemek/değiştirmek istiyorsanız** `ozet.py` içindeki
`ogrenci_ozeti()` fonksiyonuna bakın; numaralı bölümler hâlinde yazılı.
Yönetmelikten gelen bir eşik değiştiyse `yonetmelik.py`.

---

## Testler

```bash
cd testler
python test_transkript.py     # transkript çözümleyici
python test_eslestirme.py     # eski kod / yeni kod eşleştirmesi
python test_kurallar.py       # yönetmelik kuralları
python test_program.py        # ders programı ve çakışmalar
python test_mufredat.py       # müfredat belgesi ve AKTS değerleri
python test_kohort.py         # giriş yılına göre AKTS tabanı
python test_bolum.py          # bölüm profili gerçekten okunuyor mu
python test_arsiv.py          # çok yıllı müfredat arşivi ve türetimler
python test_kurulum.py        # yeni bir bölüm sıfırdan kurulabiliyor mu
python test_pano.py           # özet motoru + pano (node varsa sayfayı çizdirir)
```

`test_bolum.py`, `test_arsiv.py` ve `test_kurulum.py` alt süreç açıp
dosya üretir; diğerlerinden yavaştırlar (birkaç dakika sürebilir).

**`test_bolum.py` neyi koruyor?** Bölüme özgü bir sayının koda geri
kaçması hiçbir şeyi patlatmaz: program yine Matematik'in değerleriyle
çalışır ve başka bölümün danışmanı **sessizce yanlış** AKTS görür. Bu
yüzden uydurma bir profille ayrı bir süreç açılıp `yonetmelik`in
sabitlerinin **gerçekten değiştiği** ölçülüyor.

**`test_arsiv.py` neyi koruyor?** Arşiv doğru türetip sonra kimse
kullanmasa yine hiçbir şey patlamaz; yeni bir bölümde AKTS kaybı sessizce
hep sıfır çıkar. Bu yüzden arşivin `akts_degisimi`'ne **bağlı** olduğu,
ayrıca ölçülmüş bir transkript kaydının belgenin **önüne geçtiği**
sınanıyor.

`test_pano.py`, sistemde `node` varsa `pano_calistir.js` ile panonun
JavaScript'ini **gerçekten çalıştırır** ve her sekmeyi çizdirir. Bunun
sebebi: `rapor.py` içindeki `SAYFA` ham olmayan bir Python dizgisi;
JavaScript'e kaçan tek bir `\'` dizisi Python tarafından çözülüp string'i
kapatıyor ve sayfa **hiçbir hata vermeden bomboş** açılıyor. Statik tırnak
denetimi her durumu yakalayamaz, sayfayı çalıştırmak yakalar. Panoyu elle
de sınayabilirsiniz:

```bash
node testler/pano_calistir.js cikti/danisman_ozeti.html
```

**Testler neyi koruyor?** Geçen test bir şey kanıtlamaz; kırılınca
kızmayan test hiçbir şey korumuyordur. Bunu ölçmek için kodu kasten
bozup testleri koşuyoruz (*mutasyon denemesi*): AKTS limitini 45'ten
60'a çekmek, mezuniyet asgarisini 240'tan 200'e indirmek, DC eşiğini
düşürmek, devam oranını değiştirmek, `fazla`yı ya da `kalıcı`yı sıfıra
sabitlemek gibi. İlk turda **on mutasyondan yedisi yakalandı, üçü
kaçtı** — ve kaçan üçü, tam da o gün düzeltilmiş ama testi yazılmamış
kusurlardı (azami süre sınırı, DD'nin not yükseltme kapsamı,
kompozisyona giden kod kümesi). Üçü için de test yazıldı.

Toplam 589 kontrol. Her biri kaç kontrolün geçtiğini basar. Kod
değiştirdikten sonra onunu da çalıştırın. `test_pano.py` ve `test_eslestirme.py`, varsa gerçek sayfayı
(`cikti/ders_sayfasi_230000003.html`) kullanır; yoksa gömülü test verisine
düşer.

---

## Başka bir danışmana verme

```bash
python paylas.py
```

Masaüstünde `DersKayitKontrol_paylasim/` klasörü oluşur; ziplenip
verilebilir. Ne kopyalandığını tek tek ekrana yazar.

**Klasörü olduğu gibi kopyalamayın.** Üç şey sızar:

| Sızan | İçeriği |
|---|---|
| `cikti/` | Öğrencilerin adı, numarası, notları, transkriptleri |
| `.env` | OBİS şifreniz |
| `chrome-profili/` | OBİS oturum çerezleriniz — kopyayı alan kişi sizin adınıza OBİS'e girebilir |

`paylas.py` üçünü de dışarıda bırakır ve kurulum anlatan bir
`OKUBENI.md` üretir. Karşı taraf kendi `.env` dosyasını
`.env.example`'dan oluşturur.

Karşı tarafta gerekenler: Python 3.9+, Google Chrome ve

```bash
pip install selenium beautifulsoup4 python-dotenv openpyxl
```

Başka bir **bölüme** veriyorsanız ayrıca `veri/mufredat.docx` ile
`veri/ders_programi.xlsx` o bölümünkiyle değiştirilmeli, sonra
`python mufredat.py` ve `python ders_programi.py` çalıştırılmalı;
`yonetmelik.py` içindeki `TOS_DERSLERI` ve `LABORATUVAR_ADLARI` da
Matematik'e özgüdür.

### GitHub'a yayımlama

```bash
python paylas.py --yayin
```

Masaüstünde `DersKayitKontrol-yayin/` klasörü oluşur: kod, testler,
çözülmüş veri dosyaları, README, örnek pano ve ekran görüntüleri —
artı bu projeye özel bir `.gitignore` ve `requirements.txt`.

Kopyalamadan sonra **sızıntı denetimi** çalışır: ağaçta gerçek biçimli
öğrenci numarası, gömülü şifre, `.env`, `cikti/` ya da tarayıcı profili
var mı diye tarar ve bulduğunu tek tek yazar. Denetim temiz değilse
yayımlamayın.

### Tek dosyalık exe

Karşı tarafta Python kurmak istemiyorsanız:

```bash
pip install pyinstaller
python exe_yap.py
```

Masaüstünde **`DanismanOzeti.exe`** oluşur (~44 MB, tek dosya).
Gönderdiğiniz kişi onu boş bir klasöre koyup çift tıklar.

> **Exe BÖLÜME ÖZGÜDÜR.** Müfredat, ders programı ve bölüm profili
> exe'nin *içine* gömülür. Matematik için derlenmiş bir exe Fizik
> danışmanının elinde çalışır ama **her sayıyı Matematik'in planına
> göre hesaplar**. Başka bir bölüme vermeden önce o bölümün belgeleriyle
> [kurulum](#başka-bir-bölümde-kullanmak) yapıp exe'yi yeniden derleyin.
>
> Bu yüzden hem açılış ekranı hem pano başlığı hangi bölüm için
> yapılandırıldığını **yazar**; `--tani` de öyle. Yanlış bölüm adı
> görüyorsanız o exe'yi kullanmayın.

#### Karşı tarafta ne gerekiyor?

**Python GEREKMİYOR.** Yorumlayıcı ve bütün kütüphaneler (selenium,
beautifulsoup4, openpyxl, python-dotenv) exe'nin içinde. Müfredat ve
ders programı da gömülü. Hiç Python kurmamış biri kullanabilir.

Gerekenler:

| Ne | Neden | Zorunlu mu |
|---|---|---|
| **Windows** | exe Windows için derleniyor | Evet |
| **Google Chrome** | OBİS'i Chrome üzerinden okuyoruz | Evet |
| **İnternet** | OBİS'e girmek + ilk çalıştırmada chromedriver'ı indirmek | Evet |
| **OBİS danışman hesabı** | kendi sicili ve şifresi | Evet |
| **Yazma izni** | `cikti/` klasörünü exe'nin yanına açıyor | Evet |
| Yönetici hakkı | — | Hayır |
| Kurulum / kayıt defteri | — | Hayır |

`chromedriver`'ı **siz indirmiyorsunuz**: selenium onu ilk çalıştırmada
kendisi indirip önbelleğe alıyor (bu yüzden ilk sefer internet şart).

Uyarılar:

* **Windows Defender / SmartScreen** imzasız exe'leri durdurabiliyor.
  "Daha fazla bilgi → Yine de çalıştır" gerekebilir; kurumsal
  bilgisayarda BT'den istisna istemek gerekebilir.
* **İlk açılış ~10 saniye** sürer: tek dosya kendini geçici bir klasöre
  açıyor.
* Exe'yi **yazma izni olan** bir yere koyun (Masaüstü, Belgeler).
  `C:\Program Files` altına koyarsa `cikti/` oluşturamaz — `--tani`
  bunu söyler.
* İndirilen dosya "engellendi" olarak gelebilir: sağ tık →
  Özellikler → "Engellemeyi kaldır".

Exe çalışınca:

1. Ne yapıp ne yapmayacağını yazar (salt okunur olduğunu söyler)
2. **Sicil ve şifre sorar** — şifre ekrana yazılmaz, hiçbir yere
   kaydedilmez, yalnız o çalışma boyunca bellekte durur
3. Tüm öğrencileri tarar
4. Yanına `cikti/` klasörü açar, `danisman_ozeti.html` üretir ve açar

Girdiği tek yazma işlemi yine öğrenci kilidini bırakmaktır.

**İkinci ve sonraki çalıştırmalarda** exe, önceki taramayı görünce
sorar:

```
Önceki tarama bulundu (60 öğrenci).
Tek öğrenci için numara/ad yazın, TÜMÜ için boş bırakın:
```

Bir öğrencinin kaydını düzelttiyseniz numarasını yazın; yalnız o
tazelenir, diğerleri diskten korunur. Enter'a basarsanız tümü taranır.
İlk çalıştırmada bu soru sorulmaz.

**Müfredat/ders programı exe'nin İÇİNE gömülüdür.** Bu bilinçli:

| `veri/` nerede | Sonuç |
|---|---|
| exe'nin içinde (gömülü) | doğru okunur |
| exe'nin yanında | **hiç okunmaz — ve hata da vermez** |

Derlenmiş programda `__file__` exe'nin yanını değil, geçici açılma
klasörünü gösteriyor. `yollar.py` bu yüzden var: okunan kök
(`sys._MEIPASS`) ile yazılan kökü (`sys.executable` yanı) ayırıyor.
Veriyi gömerek danışmanın yanlış yere dosya koyma ihtimalini tamamen
kaldırıyoruz.

Bedeli: **müfredat ya da ders programı değişince exe yeniden
derlenmeli** (`python exe_yap.py`). Yanlış yere konmuş bir belgeyle
sessizce yanlış AKTS hesaplamaktansa bu yeğdir.

**Aynı tuzak `cikti/` tarafında bir kez ısırdı (2026-09).** `panoyu_yenile`
klasörünü `yollar` yerine `__file__`'dan türetiyordu. Exe'de tek öğrenci
tazelenince şu oluyordu:

1. öğrenci OBİS'ten okundu ✔
2. ham sayfası `exe'nin yanı/cikti/` klasörüne yazıldı ✔
3. pano `_MEIPASS/cikti/` klasörüne bakıp **boş buldu**, *"ders sayfası
   yok"* deyip çıktı ✘
4. exe, diskteki **eski** panoyu bulup *"Pano hazır"* diye açtı ✘

Danışmanın gördüğü tek şey başarı mesajı ve değişikliği içermeyen bir
sayfaydı. İki düzeltme yapıldı:

- `panoyu_yenile` artık `yollar.cikti()` kullanıyor; `ders_kayit`,
  `ders_programi` ve `mufredat` içindeki **kullanılmayan** `BURASI =
  Path(__file__)` sabitleri de silindi — dururlarsa bir sonraki
  değişiklikte yine onlara uzanılır.
- Exe artık panonun **var olmasına değil TAZE olmasına** bakıyor: pano
  en yeni ham sayfadan eskiyse *"PANO GÜNCELLENMEDİ"* der, zaman
  damgalarını yazar ve **eski sayfayı açmaz**. Açmak, hatayı görünmez
  kılan şeyin ta kendisiydi.

`test_pano.py` ikisini de sürekli denetliyor: `panoyu_yenile`'nin
klasörü `yollar.cikti()` ile aynı mı, ve exe'ye giren modüllerin
hiçbirinde `__file__`'dan türetilmiş yol sabiti kalmış mı.

**OBİS'e dokunmadan sınama.** Exe'yi alan kişi her şeyin yerinde
olduğunu şöyle görebilir:

```bash
DanismanOzeti.exe --tani
```

Şunları basar: yollar, gömülü verinin okunup okunmadığı (müfredat kaç
ders, ders programı var mı, AKTS referansı hangi kohortlar), `cikti/`
klasörüne yazma izni, **Chrome'un bulunup bulunmadığı ve
chromedriver'ın gerçekten açılıp açılmadığı**. Giriş bilgisi istemez,
OBİS'e bağlanmaz; tarayıcı denemesi geçici bir profille ve görünmez
(headless) yapılır, sizin Chrome pencerelerinize dokunmaz.

Ayrıca **"Gömülü pano"** bölümünde exe'nin hangi özellikleri taşıdığını
listeler — exe'nin içine bakılamadığı için "bende yeni sürüm var mı?"
sorusunun cevabı burası. Altı sekmenin yanında Türkçe arama, koyu tema,
Transkript sekmesi ve **kohort açığı** da işaretlenir.

`Kohort açığı  YOK` görürseniz o exe **2023 girişlinin planında olmayan
dersleri hesaba katmayan eski bir sürümdür** ve mezuniyet AKTS'sini
olduğundan yüksek gösterir; yeniden derleyin.

Taramadan önce bunu bir kez çalıştırmak, "her şey yerinde, tarama
yapılabilir" satırını görmek yeterli.

Kaynak kodu paylaşmak (yukarıdaki `paylas.py`) hâlâ daha esnek: karşı
taraf kendi bölümüne uyarlayabilir, müfredat değişince yeniden
derleme gerekmez. Exe ise "hiç uğraşmak istemiyorum" diyen için.

---

## Sık karşılaşılan sorunlar

**"Chrome açılamadı: profil klasörü büyük ihtimalle önceki çalıştırmadan
kalan bir Chrome penceresi tarafından kullanılıyor"**

Önceki çalıştırmadan kalan script penceresini kapatın. Kendi Chrome'unuzu
kapatmanıza gerek yok — script ayrı bir profil kullanıyor
(`DersKayitKontrol/chrome-profili`). `--pano` modu iş bitince tarayıcıyı
kendisi kapattığı için bu genelde `--pano` olmadan çalıştırdıktan sonra olur.

**Giriş sayfası geliyor, captcha soruyor**

Normal. Sicil ve şifre otomatik dolu, imleç güvenlik kodu alanında. Kodu
yazıp girin, script devam eder. Oturum profile kaydedildiği için sonraki
çalıştırmalarda genelde sormaz.

**Bir öğrenci okunamadı**

Döngü kırılmaz, o öğrenci atlanıp diğerleri işlenmeye devam eder. Terminalde
`! Okunamadı:` satırı görürsünüz. Tek tek bakmak için:
`python ders_kayit.py --pano` ile deneyin ya da o öğrencinin sayfasını elle
açın.

**Kilit bırakılamadı uyarısı**

OBİS bir öğrencinin sayfası açıkken başka öğrenci açmanıza izin vermez.
`! Kilit bırakılamadı` görürseniz o öğrencinin sayfasını OBİS'te elle açıp
"Öğrenci Kilidini Kaldır" düğmesine basın.

**"Bölüm profili yok" ya da "Bölüm profili kullanılamaz"**

`veri/bolum.json` bulunamadı ya da içi tutarsız. Program bilerek
açılmıyor: eksik bir profille çalışmak, Matematik'in sayılarını başka bir
bölüme uygulamak demektir.

```bash
python kurulum.py --denetle
python bolum.py --denetle
```

**AKTS kaybı / kohort açığı hep sıfır çıkıyor**

Muhtemelen `veri/mufredat/` altında **tek** yıl var. Karşılaştıracak
ikinci belge olmadan hangi dersin AKTS'sinin değiştiği ve hangi dersin
sonradan eklendiği bilinemez. `python kurulum.py --denetle` çıkarım
gücünü yazar.

**"Derleme başarısız" dedi ama masaüstünde exe duruyor**

O exe **eskidir**. Derleme hedef dosyayı yazamadığında (çalışan bir exe,
açık klasör önizlemesi ya da virüs taraması dosyayı kilitler) önceki sürüm
yerinde kalır ve yeniymiş gibi görünür. `python exe_yap.py` bu durumda
eski dosyanın tarihini yazar. Dağıtmadan önce derlemeyi tekrarlayın.

**Pano başlığında yanlış bölüm adı yazıyor**

O exe ya da o kopya başka bir bölüm için yapılandırılmış. Sayılar sizin
bölümünüzün planına göre değil onunkine göre hesaplanır. Kullanmayın;
kendi belgelerinizle kurulum yapıp yeniden derleyin.

---

## Kapsam notları

- **Ders kaydı yapmamış öğrenciler panoya girmez.** Seçtikleri ders
  olmadığı için değerlendirilecek bir şey yok.
- **Ortak/yaygın seçmeli havuzu kural dışıdır.** Öğrencilerimiz o havuzdan
  ders almamalı; hatayla seçilmişse "çıkarılmalı" uyarısı çıkar.
- **Geçmiş notlara yönetmelik geriye dönük uygulanmaz.** Önceki yıllar bağıl
  sistemle değerlendirildiği için transkriptteki harf olduğu gibi okunur.
  **DD bağıl sistemden gelir, geçer sayılır — ama BB'nin altında olduğu
  için not yükseltmeye de açıktır** (MADDE 9/1-d). Bir dönem kümede
  yoktu ve DD'li dersi yükseltmek için seçen öğrenciye yanlışlıkla
  "VERME — zaten geçmiş" deniyordu.
- **Azami süre, son yılın SONUNDA değil BAŞINDA dolar** (MADDE 16/1).
  2019 girişli bir öğrenci 2026 güzünde 8. öğretim yılına başlar; dört
  yıllık programda azami süre 7 yıl olduğu için o kayıt aşılmış sayılır.
  Kalan yıl 0 ise **aşılmıştır** — "0 yıl kaldı ama aşılmadı" diye bir
  durum yoktur.
- **GANO okunamazsa AKTS limiti DENETLENEMEZ, muaf olunmaz.** MADDE
  9/1-c sınırı GANO'ya bağlı (1,50 altı 30, üstü 45). Son sınıfta sınır
  yoktur; GANO'nun okunamaması ise bambaşka bir şeydir. İkisi aynı
  değerle (None) temsil edildiği için denetim sessizce atlanıyordu.
  Artık son sınıf olmadığı hâlde limit hesaplanamıyorsa **DİKKAT: AKTS
  LİMİTİ HESAPLANAMADI** uyarısı çıkar ve elle bakılması istenir.
- **DC (şartlı geçer) kararını OBİS verir, biz vermeyiz** (MADDE 15). OBİS
  transkriptte saymadığı satırları kırmızıya boyuyor; FF ve F her zaman
  kırmızı, DC ise şart tutmuşsa normal, tutmamışsa kırmızı. Şartın neye
  göre değerlendirildiğini OBİS söylemiyor (GANO değil — dersin alındığı
  dönemin ortalaması gibi görünüyor), bu yüzden mekanizmayı taklit etmiyor,
  işareti okuyoruz. Kırmızı DC "alttan ders" sayılır ama panoda FF'ten ayrı
  gösterilir: **şartlı kaldı**.
- **Ders programı çakışması kontrol edilir** (MADDE 9/1-b). Çakışma
  üretmeyenler: asenkron ortak zorunlu dersler (Türk Dili 1, Atatürk İ.İ.T 1,
  İngilizce 1) ve esnek yürütülen Matematik Uygulamaları 1. Gruplu derslerde
  (Fizik Lab. A/B) öğrenci boş gruba yazılabiliyorsa çakışma sayılmaz.
- **Devam zorunluluğu çakışmayı yumuşatır** (MADDE 10/2). Öğrenci dersi
  daha önce almışsa — **kodu değişmiş olsa bile** — ve **F dışında** bir
  notla kaldıysa derse devam etmiş sayılır; tekrarda yeniden devam
  aranmaz. Bu durumda o dersin saati çakışsa da öğrenci derse girmek
  zorunda olmadığı için çakışma engel değildir: bildirilir, ama
  **değiştirilmesi zorunlu değildir**. Devamsızlıktan kalma (F, DZ) bunun
  dışındadır. OBİS'in DVLT (devamlı tekrar) işareti de muafiyet sayılır.
  **Sınav saatleri bu kontrole dâhil değil** — sınav çakışması varsa ayrıca
  bakılmalıdır.
- **Devamsızlık hakkı çakışmayı yumuşatır** (MADDE 10/1). Teorik derste
  saatlerin %30'una, uygulamada %20'sine devamsızlık hakkı var. Çakışan
  saatler iki dersin hakkı toplamına sığıyorsa
  (`ortak ≤ A hakkı + B hakkı`) öğrenci ikisini birden alabilir. Sistem
  bunu ayrı bir kategori olarak gösterir, **kendiliğinden "sorun yok"
  demez**: hakkın tamamı programa harcanırsa hastalık/mazeret için pay
  kalmaz, bu yüzden karar danışmanındır. Çakışmasız alternatif varsa
  ayrıca önerilir.
- **Sadece I. Öğretim programı okunur.** II. öğretim varsa kapsam dışıdır.
- **Dönem kotası boş kalırsa uyarı çıkar.** Öğrenci döneminin AKTS'sini
  doldurmamışsa ve alabileceği açık ders varsa "DÖNEM KOTASI DOLMAMIŞ"
  uyarısı verilir. Ders seçilmez, yalnızca boşluk bildirilir.
- **Her sınıfın danışmanı çalıştırabilir.** Dönem kompozisyonu (hangi
  dönemde kaç zorunlu, kaç seçmeli, kaç TOS) müfredat belgesinden sekiz
  yarıyılın tamamı için türetiliyor; sabit değil. Kontenjan planı da
  öğrencilerin hedef dönemlerine göre otomatik gruplanıyor.
- **Kohort açığı: yarıyıl plandaki AKTS'ye ULAŞAMIYOR.** İki ayrı sebep,
  tek sonuç. Dersten *kalmış* olmak ikisinde de gerekmiyor - bu yüzden ne
  alttan yük ne de `akts_kaybi()` hesabına giriyorlardı.

  **(a) Müfredat AKTS'yi düşürüp payı YENİ bir derse taşıdı**, ama o ders
  daha önce girmiş öğrencinin planında yok (bölüm kararı: geriye dönük
  aldırılmıyor). Ölçüldü (2026-09):

  | Yarıyıl | Düşen | Payın taşındığı yeni ders |
  |---|---|---|
  | 1. | Fizik I 5→4, İngilizce I 3→2 | Fizik Laboratuvarı I (2) |
  | 2. | Fizik II 5→4, İngilizce II 3→2 | Fizik Laboratuvarı II (2) |
  | 5. | Cebir I 6→5, Dif. Geo I 6→5, Sayılar T. I 4→3 | Uygulamalı Matematik I (3) |
  | 6. | Cebir II 6→5, Dif. Geo II 6→5, Sayılar T. II 4→3 | Uygulamalı Matematik II (3) |

  Bu dört ders `yonetmelik.SONRADAN_EKLENEN_DERSLER` içinde, her biri
  *geçerli olduğu en erken giriş yılı* ile (2024). Başka bir kohort için
  liste değişirse tek yer güncellenir.

  **(b) AKTS'si ARTAN dersi öğrenci düşük değerken geçmiş.** Lineer Cebir
  I/II 6 → 5 → 6 oldu. Ölçüldü: **Lineer Cebir I'i 32, Lineer Cebir II'yi
  23 öğrenci 5 AKTS ile geçmiş**; müfredat ikisine de 6 diyor. Ders
  geçildiği için tekrar alınamaz, açık kapanmaz. Bu kaybın yönü diğer
  hepsinin tersi olduğundan `akts_kaybi()` hiç görmüyordu.

  **Hesap** (`yonetmelik.yariyil_acigi`), yarıyıl yarıyıl:

      eksik       = plan − geçilen − bu dönem seçilen
      zorunlu_ile = o yarıyılda hâlâ alabileceği (kohorta ait)
                    zorunluların GÜNCEL AKTS toplamı
      havuz_ile   = yarıyılın STANDART seçmeli + TOS kotasından kalan
      ulaşılabilir= geçilen + seçilen + zorunlu_ile + havuz_ile
      kalıcı      = plan − ulaşılabilir      (0'dan küçük olamaz)
      fazla       = ulaşılabilir − plan      (0'dan küçük olamaz)

  `zorunlu_ile` **katalogdan bağımsız**: bahar dersi güz katalogunda
  görünmez ama öğrenci onu baharda alacak. Katalog yalnızca "bu dönem
  hangisini seçebilir" sorusunu yanıtlar. Havuz kotası **kohorta göre
  şişirilmeden** alınır; şişirilmiş kota zaten çözümün kendisi, açığı
  ölçerken kullanılırsa açık sıfır çıkar ve danışmana hiçbir şey
  söylemeyiz.

  **`fazla` neden şart?** Mezuniyet AKTS'si bir TOPLAMDIR, yarıyıl sınırı
  yoktur: 5. yarıyıldan fazladan alınan ders 1. yarıyılın açığını da
  kapatır. Başlangıçta yalnız `kalıcı` paylar toplanıp plandan
  düşülüyordu; kotanın üstünde alınan AKTS hiçbir yere yazılmadığı için
  **pano kendi verdiği talimatı görmüyordu**: "1 ders fazladan al" deyip,
  ders yazıldığında sayı kıpırdamıyordu. Ölçüldü (2026-09): 230000004'e
  dört ek seçmeli eklendi, mezuniyet 239'da çakılı kaldı. Uyarı
  kapatılamadığı için eyleme dönüştürülemiyordu. Artık her ek ders
  mezuniyeti 4 AKTS yükseltiyor (236 → 240 → 244 → 248).

  `kohort_acigi()` sekiz yarıyılın kalıcı paylarını toplar, fazlaları
  mahsup eder ve **net** açığı verir; projeksiyon o neti düşer. Öğrencinin
  henüz *girmediği* yarıyıllar da sayılır: 2023 girişlinin 6. yarıyılı da
  Uygulamalı Matematik II yüzünden eksik kapanacak, bunu bugünden bilmek
  gerekiyor.

  **Doğrulama.** Kohort kuralı KAPALIYKEN toplam kalıcı açık 60 öğrencinin
  hepsinde **0** çıkıyor - hesap kendi başına kayıp uydurmuyor, açığın
  tamamı kohort farkından geliyor. Bu `test_pano.py` içinde sürekli
  denetleniyor; her açık kaleminin adlandırılmış bir sebebi olması ve
  `projeksiyon = plan toplamı − net açık` eşitliği de öyle.

  **Mezuniyet projeksiyonu artık bu sayıyı düşüyor**, `akts_kaybi()`'yi
  değil. İkisi aynı şeyi ölçmüyor: `akts_kaybi()` yalnız tekrar edilen ve
  kalınan dersleri sayar, müfredatın düşen payı yeni bir derse taşımış
  olmasını göremez. **İkisi birden düşülmez** - aynı AKTS iki kez
  eksilirdi. Müfredat belgesi yoksa eski yol yedek olarak devrede kalır.

  **Uyarı tektir**, yarıyıl başına ayrı değil: danışmanın vereceği karar
  tek ("fazladan kaç seçmeli yazayım?"), dört ayrı satır o kararı bölerdi.
  Mezuniyet asgarinin altına düşüyorsa **YAPILACAK** ("5. yarıyıl seçmeli
  havuzundan N ders FAZLADAN alınmalı", açık dersler adıyla), düşmüyorsa
  BİLGİ ("fazladan ders GEREKMİYOR"). Açığı hangi havuzun kapatacağı
  `ACIK_KAPATMA_YARIYILI` ile belirlenir (5 - güzde açık ve alt yarıyıl
  olduğu için üst sınıf da alabilir, MADDE 9/1-a).

  **Dönem kompozisyonu da kohort farkında.** `donem_yapisi(..., giris_yili)`
  kohortun almayacağı dersi zorunlulardan düşürür; yarıyıl toplamı
  değişmediği için açık seçmeli kotasına yansır: 5. yarıyılda 2023 girişli
  için zorunlu 26 yerine 23 AKTS, **seçmeli 1 yerine 2 ders**. Böylece
  "ZORUNLU DERS SEÇİLMEMİŞ" uyarısı da artık Uygulamalı Matematik I'i
  istemiyor.

  **Ders eşleştirmesi kod + ad.** `belge_karsiligi()` önce koda, tutmazsa
  ad benzerliğine bakar. Tek başına ikisi de yetmiyor: müfredat bazı
  derslerin kodunu değiştirdi (2709508 CEBİR I → 2709545) ve belge ad
  kısaltıyor ("Atatürk İlk. ve İnk. Tarihi I" ile transkriptteki
  "ATATÜRK İLKELERİ VE İNKILAP TARİHİ 1" benzerliği 0,857 - eşiğin
  altında). İkisi birlikte 60 öğrencinin geçtiği derslerin **tamamını**
  eşliyor.
- **AKTS'nin "ilk hâli" giriş yılına bağlıdır.** Bir dersin eski AKTS'si
  diye tek bir sayı yok. Ölçüldü (2026-09):

  | Ders | 2023 girişli | 2024 girişli / güncel |
  |---|---|---|
  | Fizik I / II | 5 | 4 |
  | İngilizce I / II | 3 | 2 |
  | Cebir I / II | 6 | 5 |
  | Diferensiyel Geometri I / II | 6 | 5 |
  | Sayılar Teorisi I / II | 4 | 3 |

  Müfredat yalnız AKTS düşürmedi, **ders de ekledi** (Fizik Laboratuvarı
  I/II, 2'şer AKTS). Sonuçta iki kohortta da 1-4. yarıyıl 120 AKTS
  tutuyor; 2024 girişli, hiç kalmamış gerçek bir öğrencinin OBİS'teki
  genel kredisi tam 120 çıkıyor ve müfredat belgesiyle birebir uyuşuyor.
  **Yani 2024 girişli için "ilk hâl" ile "son hâl" aynı; AKTS kaybı
  yok.** 2023 tabanını 2024 girişliye uygularsak hiç yaşamadığı bir kayıp
  uydurmuş oluruz.

  Sistem tabanı her kohort için ayrı kurar: önce o kohortun **kendi
  transkript kayıtları**, yoksa `veri/akts_referans.json` fotoğrafı, o da
  yoksa ders **değişmemiş** sayılır. Panodaki AKTS Değişimi sekmesi giriş
  yılına göre ayrı satır gösterir; aynı dersi farklı kohortlar farklı
  AKTS ile taşıyorsa "GİRİŞ YILINA GÖRE FARKLI" diye işaretlenir.

  **Not:** OBİS'in ders kayıt sayfası herkese GÜNCEL AKTS'yi gösterir,
  öğrencinin kendi kohortunun değerini değil (2023 ve 2024 girişlilerin
  sayfaları karşılaştırıldı, 35 ortak derste fark yok). Bu yüzden bir
  kohortun gerçek "ilk hâl"i ancak o kohortun **transkriptinden**
  okunabilir; `akts_referans.json` yalnız transkript yokken devreye
  giren bir yedektir.
- **Alt sınıflarda AKTS sınırı devreye girer.** Son sınıfta sınır yok, ama
  1-6. dönemde 30/45 AKTS sınırı var. Geriden gelen öğrencinin bütçesi
  alttan derslere gidiyorsa hedef dönemin zorunluları o döneme sığmaz;
  sistem bunu ders ders "seçilmemiş" diye yazmaz (uygulanamaz tavsiye
  olurdu), tek bir "zorunluları ileri kalıyor" notu verir.
