// Panonun JavaScript'ini gercekten calistirip her gorunumu cizdirir.
//
// Neden gerekli: rapor.py icindeki SAYFA ham (raw) olmayan bir Python
// dizgisi. Icine kacan tek bir ters egik cizgi + tirnak (\') sessizce
// cokuyor, tarayici hicbir sey yazmadan bos sayfa gosteriyor. Python
// testleri bunu goremez; sayfayi CALISTIRMAK gerekir.
//
//   node pano_calistir.js <pano.html>
//
// Cikis kodu 0 = her gorunum cizildi.
const fs = require('fs');

const yol = process.argv[2];
if (!yol) { console.log('kullanim: node pano_calistir.js <pano.html>'); process.exit(2); }
const html = fs.readFileSync(yol, 'utf8');

function json(id) {
  const re = new RegExp('<script id="' + id +
                        '" type="application/json">([\\s\\S]*?)</script>');
  const m = html.match(re);
  if (!m) throw new Error('veri blogu yok: ' + id);
  return JSON.parse(m[1]);
}

const kod = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)]
  .map(m => m[1]).join('\n');
if (!kod.trim()) { console.log('  [HATA] sayfada <script> yok'); process.exit(1); }

const N = {};
function dg(id) {
  if (!N[id]) N[id] = {
    id, innerHTML: '', textContent: '', value: '', checked: false,
    classList: { add(){}, remove(){}, contains(){ return false; } },
    addEventListener(){}, focus(){}, closest(){ return null; }, dataset: {},
  };
  return N[id];
}
global.document = {
  getElementById: dg, addEventListener(){},
  querySelectorAll(){ return { forEach(){} }; },
  createElement(){ return dg('gecici'); },
};
global.window = global;

const veriler = ['veri', 'kontenjan', 'program', 'katalog', 'aktsdegisim'];
let hata = 0;
function kontrol(ad, tamam, ek) {
  console.log((tamam ? '  [OK]  ' : '  [HATA] ') + ad + (ek ? '  ' + ek : ''));
  if (!tamam) hata++;
}

for (const i of veriler) {
  try {
    dg(i).textContent = JSON.stringify(json(i));
    kontrol('veri blogu okundu: ' + i, true);
  } catch (e) { kontrol('veri blogu okundu: ' + i, false, e.message); }
}

let c;
try {
  c = new Function(kod + '\n;return {aktsCiz, aktsGovde, derslerCiz, ' +
    'derslerGovde, cakismaCiz, yoneticiCiz, secimCiz, secimGovde, ' +
    'cozulmeliCiz, cozulmeliGovde, ' +
    'listeCiz, detayCiz, ozetGovde, transkriptGovde, sekmeCubugu, ' +
    'ilerlemeCubugu, yariyilSeridi, miniGosterge, kopyalanacakMetin, ' +
    'dagilimlar, OGRENCILER};')();
  kontrol('sayfa JavaScript sozdizimi temiz', true);
} catch (e) {
  kontrol('sayfa JavaScript sozdizimi temiz', false, e.message);
  process.exit(1);
}

// Her gorunum cizilebiliyor ve bos degil mi?
const gorunumler = [
  ['yoneticiCiz', null],
  ['cakismaCiz', 'cakisma-govde'],
  ['derslerCiz', 'dersler-govde'],
  ['cozulmeliCiz', 'cozulmeli-govde'],
  ['secimCiz', 'secim-govde'],
  ['aktsCiz', 'akts-govde'],
];
for (const [fn, govde] of gorunumler) {
  try {
    dg('ana').innerHTML = '';
    if (govde) dg(govde).innerHTML = '';
    c[fn]();
    const n = dg('ana').innerHTML.length + (govde ? dg(govde).innerHTML.length : 0);
    // Bos veriyle cagrildiginda gorunum "veri yok" mesaji basar; onemli
    // olan patlamamasi ve bir sey yazmasi.
    kontrol(fn + ' cizildi', n >= 100, n + ' karakter');
  } catch (e) { kontrol(fn + ' cizildi', false, e.message); }
}

// Ogrenci detayi cizilebiliyor mu?
try {
  const o = c.OGRENCILER || [];
  kontrol('ogrenci verisi bos degil', o.length > 0, o.length + ' ogrenci');
  if (o.length) {
    dg('ana').innerHTML = '';
    c.detayCiz(o[0]);
    kontrol('ogrenci detayi cizildi', dg('ana').innerHTML.length >= 400,
            dg('ana').innerHTML.length + ' karakter');
  }
} catch (e) { kontrol('ogrenci detayi cizildi', false, e.message); }

// Transkript sekmesi: tam transkript ciziliyor mu, suzgecler isliyor mu?
function trGovdesi(ayar) {
  return new Function(kod + '\n;' + (ayar || '') +
    ';secilenNo = OGRENCILER[0].no;' +
    'return transkriptGovde(OGRENCILER[0]);')();
}
try {
  const o0 = (c.OGRENCILER || [])[0];
  const t = o0 && o0.transkript;
  if (!t) {
    kontrol('transkript verisi gomulu', false, 'ogrencide transkript yok');
  } else {
    const govde = trGovdesi('');
    // Yalniz govde satirlari: <thead> icindeki baslik satiri da
    // <tr> oldugu icin genel bir desen her donemde 1 fazla sayardi.
    const satir = s => [...s.matchAll(/class="tr-satir/g)].length;
    const donem = s => [...s.matchAll(/class="tr-donem"/g)].length;

    kontrol('transkript sekmesi ciziliyor', govde.length > 400,
            govde.length + ' karakter');
    kontrol('her donem bir bolum aciyor', donem(govde) === t.donemler.length,
            donem(govde) + ' vs ' + t.donemler.length);

    // Varsayilan: gecersiz denemeler GIZLI. Gosterilince satir artmali.
    const gecerliSayisi = t.donemler.reduce(
      (n, g) => n + g.dersler.filter(d => !d.gecersiz).length, 0);
    kontrol('gecersiz denemeler varsayilan olarak gizli',
            satir(govde) === gecerliSayisi,
            satir(govde) + ' vs ' + gecerliSayisi);
    const hepsiG = trGovdesi('trGecersiz=true');
    kontrol('"gecersizleri goster" daha fazla satir veriyor',
            satir(hepsiG) === t.deneme_sayisi,
            satir(hepsiG) + ' vs ' + t.deneme_sayisi);

    // Panodaki AKTS toplamlari transkript verisiyle tutmali.
    const beklenenAkts = t.donemler.reduce((n, g) => n + g.gecilen_akts, 0);
    kontrol('donem AKTS toplamlari gecilen_akts ile tutuyor',
            beklenenAkts === o0.gecilen_akts,
            beklenenAkts + ' vs ' + o0.gecilen_akts);

    // Arama: ilk dersin adinin ilk kelimesi en az bir satir birakmali.
    const ilk = t.donemler[0].dersler.filter(d => !d.gecersiz)[0];
    if (ilk) {
      const parca = (ilk.ad || '').trim().split(/\s+/)[0]
        .replace(/[İIıi]/g, 'i').toLocaleLowerCase('tr');
      const suz = trGovdesi('trArama=' + JSON.stringify(parca));
      kontrol('transkript aramasi suzuyor',
              satir(suz) > 0 && satir(suz) <= satir(govde),
              parca + ' -> ' + satir(suz) + ' / ' + satir(govde));
    }
    const yok = trGovdesi('trArama="zzzyokboyleders"');
    kontrol('eslesmeyen arama bos mesaj veriyor',
            satir(yok) === 0 && yok.indexOf('Eşleşen ders yok') >= 0);

    // Sekme cubugu iki sekme gostermeli ve baslangicta ozet etkin.
    const cubuk = new Function(kod +
      '\n;return sekmeCubugu(OGRENCILER[0]);')();
    kontrol('sekme cubugunda iki sekme var',
            [...cubuk.matchAll(/data-sekme=/g)].length === 2);
    // Oznitelik sirasina degil, hangi sekmenin etkin oldugu bilgisine
    // bak: araya aria-selected girince sira testi yalanci hata verdi.
    const etkin = t => {
      const p = cubuk.split('data-sekme="' + t + '"')[1] || '';
      return p.slice(0, 60);
    };
    kontrol('baslangicta ozet sekmesi etkin',
            etkin('ozet').includes('aria-selected="true"') &&
            etkin('ozet').includes('class="aktif"'));
    kontrol('transkript sekmesi etkin degil',
            etkin('transkript').includes('aria-selected="false"'));
    const trCubuk = new Function(kod +
      '\n;detaySekme="transkript";return sekmeCubugu(OGRENCILER[0]);')();
    kontrol('sekme degisince etkinlik tasiniyor',
            /data-sekme="transkript"[^>]*aria-selected="true"/.test(trCubuk) &&
            /data-sekme="ozet"[^>]*aria-selected="false"/.test(trCubuk));

    // Ozet govdesi hala dolu (sekmeye bolerken icerik kaybolmamali).
    const ozet = new Function(kod +
      '\n;return ozetGovde(OGRENCILER[0]);')();
    kontrol('ozet govdesi bos degil', ozet.length > 400,
            ozet.length + ' karakter');
  }
} catch (e) { kontrol('Transkript sekmesi', false, e.message); }

// AKTS sekmesi: her iki suzgec durumu ve arama
function aktsGovdesi(ayar) {
  return new Function(kod + '\n;' + ayar +
    ';aktsCiz();return document.getElementById("akts-govde").innerHTML;')();
}
const aktsVar = Object.keys((json('aktsdegisim').yariyillar) || {}).length > 0;
if (!aktsVar) {
  console.log('  (AKTS degisim verisi gomulmemis, sekme kontrolleri atlandi)');
} else try {
  const kapali = aktsGovdesi('aktsHepsi=false');
  const acik = aktsGovdesi('aktsHepsi=true');
  const say = s => [...s.matchAll(/<tr[^>]*>/g)].length;
  kontrol('AKTS sekmesi degisenleri listeliyor', say(kapali) > 0,
          say(kapali) + ' satir');
  kontrol('"degismeyenleri de goster" daha fazla satir veriyor',
          say(acik) > say(kapali), say(acik) + ' > ' + say(kapali));
  const bulunan = aktsGovdesi('aktsHepsi=false;aktsArama="cebir"');
  const bulunmayan = aktsGovdesi('aktsHepsi=false;aktsArama="zzzyok"');
  kontrol('AKTS aramasi suzuyor', say(bulunan) > 0 && say(bulunan) < say(kapali),
          say(bulunan) + ' satir');
  kontrol('bulunamayan arama bos donuyor', say(bulunmayan) === 0);
  kontrol('7. ve 8. yariyil bolumleri var',
          kapali.indexOf('7. yariyil') >= 0 && kapali.indexOf('8. yariyil') >= 0);
} catch (e) { kontrol('AKTS sekmesi suzgecleri', false, e.message); }

// Ders Alanlar sekmesi: ders -> ogrenci cevrimi ve suzgec
function secimGovdesi(ayar) {
  return new Function(kod + '\n;' + (ayar || '') +
    ';secimCiz();return document.getElementById("secim-govde").innerHTML;')();
}
try {
  const hepsi = secimGovdesi('');
  const kutuSay = s => [...s.matchAll(/class="ders-kutu"/g)].length;
  const satirSay = s => [...s.matchAll(/class="satir-secim"/g)].length;
  const dersler = kutuSay(hepsi), secimler = satirSay(hepsi);
  kontrol('Ders Alanlar dersleri listeliyor', dersler > 0,
          dersler + ' ders kutusu');
  // DIKKAT: "her ders >= 1 ogrenci" YANLIS bir iddia. Kimsenin almadigi
  // ama birinin ALMASI GEREKEN ders de kutu aciyor ("kimse almamis").
  // Dogru degismez: hicbir kutu tamamen bos kalmamali - ya ogrenci
  // satiri ya da "secmemis" notu tasimali.
  const bosKutu = hepsi.split('class="ders-kutu"').slice(1).filter(
    p => p.indexOf('satir-secim') < 0 && p.indexOf('seçmemiş') < 0).length;
  kontrol('bos ders kutusu yok', bosKutu === 0, bosKutu + ' bos kutu');

  // Toplam secim sayisi, ogrencilerin secilen_dersler toplamiyla tutmali.
  const beklenen = c.OGRENCILER.reduce(
    (t, o) => t + ((o.secilen_dersler || []).length), 0);
  kontrol('secim sayisi ogrenci verisiyle tutuyor', secimler === beklenen,
          secimler + ' vs ' + beklenen);

  // Ilk dersin adiyla arayinca en az o ders kalmali, hepsi degil.
  const ad = (hepsi.match(/<h4>[^<]*—\s*([^<]+?)\s*<span/) || [])[1];
  if (ad) {
    // Sayfa Turkce-duyarli kucultuyor; test de ayni olculer
    // olmali, yoksa 'İ' yuzunden yalanci hata verir.
    const parca = ad.trim().split(/\s+/)[0].replace(/[İIıi]/g, 'i').toLocaleLowerCase('tr');
    const suzulmus = secimGovdesi('secimArama=' + JSON.stringify(parca));
    kontrol('ders adiyla suzuluyor',
            kutuSay(suzulmus) > 0 && kutuSay(suzulmus) <= dersler,
            parca + ' -> ' + kutuSay(suzulmus) + ' / ' + dersler);
  }
  // Ogrenci adiyla arama da ders getirmeli.
  const kisi = (c.OGRENCILER[0] || {}).ad;
  if (kisi) {
    const kisiSuz = secimGovdesi(
      'secimArama=' + JSON.stringify(kisi.split(' ')[0]));
    kontrol('ogrenci adiyla da suzuluyor', kutuSay(kisiSuz) > 0,
            kutuSay(kisiSuz) + ' ders');
  }
  const yok = secimGovdesi('secimArama="zzzyokboyleders"');
  kontrol('eslesmeyen arama bos donuyor', kutuSay(yok) === 0);
} catch (e) { kontrol('Ders Alanlar sekmesi', false, e.message); }

// Cozulmeli Cakisma sekmesi: YALNIZ zorunlu olanlar girmeli
try {
  const coz = new Function(kod +
    '\n;cozulmeliCiz();' +
    'return document.getElementById("cozulmeli-govde").innerHTML;')();
  const kartSay = s => [...s.matchAll(/class="kart yapilacak"/g)].length;
  const ogrSay = s => [...s.matchAll(/class="ogrenci-ac"/g)].length;

  const bekOgr = c.OGRENCILER.filter(
    o => (o.cakismalar || []).some(x => x.cozulmeli)).length;
  const bekCift = c.OGRENCILER.reduce(
    (t, o) => t + (o.cakismalar || []).filter(x => x.cozulmeli).length, 0);

  if (!bekCift) {
    kontrol('cozulmeli cakisma yoksa bos mesaj', coz === '' || bekOgr === 0);
  } else {
    kontrol('cozulmeli sekmesi ogrencileri listeliyor',
            ogrSay(coz) === bekOgr, ogrSay(coz) + ' vs ' + bekOgr);
    kontrol('cozulmeli sekmesi ciftleri listeliyor',
            kartSay(coz) === bekCift, kartSay(coz) + ' vs ' + bekCift);
    // Zorunlu OLMAYAN cakismalar buraya sizmamali.
    const coz_ = new Set(), gev = new Set();
    c.OGRENCILER.forEach(o => (o.cakismalar || []).forEach(x => {
      (x.cozulmeli ? coz_ : gev).add(x.a_ad + ' ↔ ' + x.b_ad); }));
    const sizan = [...gev].filter(p => !coz_.has(p) && coz.indexOf(p) >= 0);
    kontrol('zorunlu olmayan cakisma sizmiyor', sizan.length === 0,
            sizan.slice(0, 2).join(' | '));
    // Her kartta oneri kutusu olmali (ya aday listesi ya "zorunlu ders")
    const onerisiz = coz.split('class="kart yapilacak"').slice(1)
      .filter(k => k.indexOf('class="oneri"') < 0).length;
    kontrol('her cozulmeli kartta oneri var', onerisiz === 0,
            onerisiz + ' onerisiz');
    // Cok cakismasi olan ustte
    const sira = [...coz.matchAll(/sayac-rozet">(\d+) çakışma/g)]
      .map(m => Number(m[1]));
    kontrol('cok cakismasi olan ustte',
            sira.every((n, i) => i === 0 || sira[i - 1] >= n),
            sira.join(','));
  }
} catch (e) { kontrol('Cozulmeli Cakisma sekmesi', false, e.message); }


// --- Mezuniyet ilerleme cubugu ---------------------------------------
// Cubugun parcalari overflow:hidden bir kutuda duruyor. Toplam genislik
// %100'u ASARSA fazlasi SESSIZCE kirpilir: anahtarda "ulasilamayan 1
// AKTS" yazar ama cubukta hicbir sey gorunmez. Bu yuzden yuzdeler
// toplaniyor.
try {
  const o = (c.OGRENCILER || []).filter(x => (x.projeksiyon || {}).toplam != null);
  kontrol('projeksiyonu olan ogrenci var', o.length > 0, o.length + ' ogrenci');
  let tasan = 0, esikSiz = 0, payYok = 0;
  for (const x of o) {
    const h = c.ilerlemeCubugu(x);
    const yuzdeler = [...h.matchAll(/width:([\d.]+)%/g)].map(m => Number(m[1]));
    const toplam = yuzdeler.reduce((a, b) => a + b, 0);
    if (toplam > 100.5) tasan++;
    if (h.indexOf('class="esik"') < 0) esikSiz++;
    if (h.indexOf('class="pay ') < 0) payYok++;
  }
  kontrol('cubuk parcalari %100u asmiyor', tasan === 0, tasan + ' tasan');
  kontrol('her cubukta asgari esigi var', esikSiz === 0, esikSiz + ' esiksiz');
  kontrol('her cubukta pay/eksik rozeti var', payYok === 0, payYok + ' rozetsiz');

  // Eksigi olan ogrencide KIRMIZI kuyruk gorunmeli - uyarinin gorsel
  // karsiligi bu; yoksa "6 AKTS eksik" yazip cubukta hicbir sey olmaz.
  const eksikli = o.filter(x => x.projeksiyon.yeterli === false);
  if (eksikli.length) {
    const kuyruksuz = eksikli.filter(
      x => c.ilerlemeCubugu(x).indexOf('c-kayip') < 0).length;
    kontrol('eksigi olanda kirmizi kuyruk var', kuyruksuz === 0,
            kuyruksuz + ' kuyruksuz / ' + eksikli.length);
    const k = c.ilerlemeCubugu(eksikli[0]);
    kontrol('eksik rozeti "eksik" diyor', k.indexOf('AKTS eksik') >= 0);
  } else {
    kontrol('asgarinin altinda ogrenci yok (atlandi)', true);
  }
} catch (e) { kontrol('ilerleme cubugu', false, e.message); }

// --- Yariyil seridi ---------------------------------------------------
try {
  const o = c.OGRENCILER || [];
  const seritli = o.filter(x => (x.yariyil_serit || []).length);
  kontrol('yariyil seridi verisi gomulu', seritli.length === o.length,
          seritli.length + ' / ' + o.length);
  let kutuHatasi = 0, hedefHatasi = 0, durumHatasi = 0;
  const gecerli = ['tamam', 'eksik', 'acik', 'bos'];
  for (const x of seritli) {
    const h = c.yariyilSeridi(x);
    const kutu = [...h.matchAll(/class="yy /g)].length;
    if (kutu !== x.yariyil_serit.length) kutuHatasi++;
    const hedef = [...h.matchAll(/ hedef"/g)].length;
    if (hedef > 1) hedefHatasi++;
    for (const yy of x.yariyil_serit) {
      if (gecerli.indexOf(yy.durum) < 0) durumHatasi++;
      // Kapanmayan acigi olan yariyil KIRMIZI olmali
      if (yy.kalici && yy.durum !== 'acik') durumHatasi++;
      // Plani dolduran yariyil acik degilse YESIL olmali
      if (!yy.kalici && yy.gecilen >= yy.plan && yy.durum !== 'tamam')
        durumHatasi++;
    }
  }
  kontrol('serit kutusu sayisi yariyil sayisiyla ayni', kutuHatasi === 0,
          kutuHatasi + ' hatali');
  kontrol('en fazla bir hedef yariyil isaretli', hedefHatasi === 0);
  kontrol('yariyil durumlari tutarli', durumHatasi === 0,
          durumHatasi + ' tutarsiz');

  // Seritteki toplam plan, panonun kullandigi plan toplamiyla ayni mi?
  const planlar = new Set(seritli.map(
    x => x.yariyil_serit.reduce((t, y) => t + y.plan, 0)));
  kontrol('tum ogrencilerde ayni plan toplami', planlar.size <= 1,
          [...planlar].join(','));
} catch (e) { kontrol('yariyil seridi', false, e.message); }

// --- Sol listedeki mini gosterge --------------------------------------
try {
  const o = c.OGRENCILER || [];
  let tasan = 0;
  for (const x of o) {
    const h = c.miniGosterge(x);
    if (!h) continue;
    const toplam = [...h.matchAll(/width:([\d.]+)%/g)]
      .map(m => Number(m[1])).reduce((a, b) => a + b, 0);
    if (toplam > 100.5) tasan++;
  }
  kontrol('mini gosterge %100u asmiyor', tasan === 0, tasan + ' tasan');
  dg('liste').innerHTML = '';
  c.listeCiz();
  const n = [...dg('liste').innerHTML.matchAll(/class="mini"/g)].length;
  kontrol('listede mini gosterge ciziliyor', n > 0, n + ' gosterge');
} catch (e) { kontrol('mini gosterge', false, e.message); }

// --- Ozeti kopyala ----------------------------------------------------
// Danisman gorusmede bu metni yapistiracak; uyarilarin HEPSI icinde
// olmali, yoksa panoda goruneni kopyalamamis oluruz.
try {
  const o = (c.OGRENCILER || []).filter(
    x => (x.uyarilar || []).some(u => u.onem !== 'bilgi'));
  if (!o.length) {
    kontrol('uyarisi olan ogrenci yok (atlandi)', true);
  } else {
    const x = o[0];
    const m = c.kopyalanacakMetin(x);
    kontrol('kopya metninde ogrenci kimligi var',
            m.indexOf(x.ad) >= 0 && m.indexOf(String(x.no)) >= 0);
    const bek = (x.uyarilar || []).filter(u => u.onem !== 'bilgi');
    const eksik = bek.filter(u => m.indexOf(u.baslik) < 0);
    kontrol('kopya metninde her uyari var', eksik.length === 0,
            eksik.length + ' eksik');
    kontrol('kopya metni salt okuma oldugunu soyluyor',
            m.indexOf('onaylanmadı') >= 0);
    kontrol('kopya metni tek satir degil', m.split('\n').length > 3,
            m.split('\n').length + ' satir');
  }
} catch (e) { kontrol('ozeti kopyala', false, e.message); }

// --- Yonetici ozeti dagilimlari ---------------------------------------
try {
  const h = c.dagilimlar();
  const o = c.OGRENCILER || [];
  const yap = o.filter(x => x.sayim.yapilacak).length;
  const dik = o.filter(x => !x.sayim.yapilacak && x.sayim.dikkat).length;
  const tem = o.length - yap - dik;
  kontrol('dagilim durum sayilari ust seritle tutuyor',
          h.indexOf('>' + yap + '</b>') >= 0
          && h.indexOf('>' + dik + '</b>') >= 0
          && h.indexOf('>' + tem + '</b>') >= 0,
          yap + '/' + dik + '/' + tem);
  const yukseklik = [...h.matchAll(/height:([\d.]+)%/g)].map(m => Number(m[1]));
  kontrol('dagilim cubuklari kutuyu asmiyor',
          yukseklik.every(v => v <= 100), Math.max(...yukseklik) + '%');
  kontrol('en buyuk dilim tam yukseklikte',
          Math.max(...yukseklik) === 100);
} catch (e) { kontrol('dagilimlar', false, e.message); }

// --- "Nasil okunur" metni bolume ozgu olmali ---------------------------
// Bu metin danismana GORUNUYOR. Bir zamanlar Matematik'in ders adlari
// ("Turk Dili 1, Ataturk I.I.T 1... Matematik Uygulamalari 1") dogrudan
// JavaScript'e gomuluydu; baska bir bolumun danismani onlari kendi
// bolumu icin dogru saniyordu.
try {
  const p = json('program');
  const ist = (p && p.istisnalar) || {};
  kontrol('istisna listeleri panoya gomulu',
          Array.isArray(ist.asenkron) && Array.isArray(ist.esnek));
  dg('ana').innerHTML = '';
  c.cakismaCiz();
  const kutu = /<div class="gerekce"><b>Nasıl okunur<\/b>([\s\S]*?)<\/div>/
    .exec(dg('ana').innerHTML);
  kontrol('nasil okunur kutusu ciziliyor', !!kutu);
  if (kutu) {
    const metin = kutu[1];
    const eksik = [...(ist.asenkron || []), ...(ist.esnek || [])]
      .filter(a => metin.indexOf(a) < 0);
    kontrol('profildeki her istisna metinde', eksik.length === 0,
            eksik.slice(0, 2).join(' | '));
  }
  // Kaynakta ders ADI sabit yazili OLMAMALI
  const sabitler = ['Türk Dili 1', 'Atatürk İ.İ.T', 'Matematik Uygulamaları'];
  const sizan = sabitler.filter(x => kod.indexOf(x) >= 0);
  kontrol('ders adi JavaScript icine gomulu degil', sizan.length === 0,
          sizan.join(' | '));
} catch (e) { kontrol('nasil okunur metni', false, e.message); }

// --- Yazdirma bicemi ---------------------------------------------------
// Danisman bu sayfayi yazdiriyor. Yan panel ve kaydirma kutulari
// yazdirmada kirpilirsa tablolarin yarisi kagida hic gelmez.
try {
  const yazdir = /@media\s+print\s*\{([\s\S]*?)\n\}/.exec(html);
  kontrol('yazdirma bicemi var', !!yazdir);
  if (yazdir) {
    const b = yazdir[1];
    kontrol('yazdirmada yan panel gizli', b.indexOf('.yan') >= 0);
    kontrol('yazdirmada kaydirma acilmis',
            b.indexOf('overflow:visible') >= 0);
  }
} catch (e) { kontrol('yazdirma bicemi', false, e.message); }

console.log('');
console.log(hata ? '  ' + hata + ' kontrol BASARISIZ.' : '  Tum pano kontrolleri gecti.');
process.exit(hata ? 1 : 0);
