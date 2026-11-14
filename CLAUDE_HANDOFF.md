# NSSOC — Claude için ayrıntılı teknik devir

> **14 Kasım 2026 güncellemesi:** Bu belgenin aşağıdaki 4 Kasım durum dökümü tarihsel kayıttır. Güncel devam noktası ve çalışma numaraları için önce [CLOUD_RESUME.md](CLOUD_RESUME.md) dosyasının en üst kaydını okuyun ve GitHub'daki canlı durumu yeniden doğrulayın. Önceki paket arayüzlü çipin [SRAM içlerini kapsayan mühendislik transistor LVS'si geçti](docs/full-chip-engineering-lvs-20261114.md); [tam çip hata kontrolleri](docs/full-chip-native-fault-controls-20261114.md) de geçti. Bu sonuç yeni yönlendirmeye, tam seri PHY'ye, nihai zamanlamaya veya üretici onayına aktarılmaz. Aşağıdaki “aktif iş yok” ifadesini güncel durum olarak kullanmayın.

     
Hazırlanma: 4 Kasım 2026. Canlı GitHub durum kontrolü: **2026-11-04 02:07 UTC / 05:07 Türkiye saati**.

> **Proje bitmedi. Tam seri PCIe Gen3 x4 PHY, ana çipin son yönlendirmesi ve nihai setup/hold kapanışı açık.** Son dört native işin dördü de **completed/failure** durumunda. Bu belge hazırlanırken GitHub Actions API'sinde queued/in_progress iş bulunmadı. Aşağıdaki yeni sonuçlar, eski v360 devam notlarının “çalışıyor” bilgisinin yerini alır. Bu devir sırasında yeni CAD/simülasyon işi başlatılmadı.

## 1. Amaç, kullanıcının talebi ve çalışma biçimi

Amaç, GR801 benzeri yetenekleri hedefleyen açık kaynaklı NSSOC geliştirmek; PCIe Gen3 x4, Gigabit Ethernet, SpaceWire, I2C ve diğer hedef arayüzleri gerçek RTL, fiziksel tasarım ve doğrulama zinciriyle tamamlamak. Bu bir mevcut GR801 tasarımının doğrulanmış birebir kopyası veya tamamlanmış ürün iddiası değildir.

Kullanıcı özellikle tam PCIe/Ethernet entegrasyonu, seri PHY, yönlendirme, setup/hold, LVS ve üretim açıklarının kapanmasını istiyor. Son isteği işi Claude'a devretmek için bu ayrıntılı MD'nin hazırlanması.

Son çalışma tercihi **her şeyi bulutta yapmak ve yerelde proje/native çıktı bırakmamak**. Önceki “yerelde yap” talimatlarının ardından bu tercih değişti. Yerel çalışma dizini `/home/hasanmelih/Documents/ChatGPT/nnsoc` boş olarak doğrulandı; kurtarılacak yerel checkout veya çalışan yerel CAD süreci varsayma. Bu belge ve türetilmiş durum kayıtları GitHub'a API ile, yerel proje oluşturmadan yayımlandı.

Kaynak ve küçük JSON/metin raporlarını API üzerinden bellekte okumak mevcut koordinasyon yöntemidir. Native GDS/ODB/SPICE çalışma arşivleri, dalga biçimleri, motor binary'leri ve büyük fiziksel çıktılar **buluttaki işlerde** indirilip açılmalıdır. Kaynak depodaki şema dosyalarını okumakla native çalışma arşivini yerel bilgisayara almak aynı işlem değildir.

GitHub'a değişiklik gönderme yetkisi önceki kullanıcı taleplerinde verildi. Ancak tamamlanmış saymak için gerçek kabul kanıtı gerekir; test eşiğini gevşetmek, saatleri yavaşlatmak veya eksik blokları blackbox bırakmak kapanış değildir.

## 2. Depo ve başlangıç noktası

- Depo: https://github.com/Melihakbulut221/nssoc
- Ana devam dalı: https://github.com/Melihakbulut221/nssoc/tree/codex/complete-open-work
- Actions: https://github.com/Melihakbulut221/nssoc/actions
- Releases: https://github.com/Melihakbulut221/nssoc/releases
- Bu belge: https://github.com/Melihakbulut221/nssoc/blob/codex/complete-open-work/CLAUDE_HANDOFF.md
- Devir öncesi kök commit: **799bb41b3cbc50ab6d3feb26ecb4e98c01f96350**, checkpoint **v360**.
- Eski devam belgesi, değişmez bağlantı: https://github.com/Melihakbulut221/nssoc/blob/799bb41b3cbc50ab6d3feb26ecb4e98c01f96350/CLOUD_RESUME.md

**Default branch'in bütün son çalışmaları içerdiğini varsayma.** Deneylerin kaynakları ayrı dallarda ve aşağıdaki exact commit'lerde. Kök dalda bir raporun bulunması, deney dalındaki bütün kodun köke taşındığı anlamına gelmez. Birleştirmeden önce diff ve bağımlılık manifestlerini incele.

| Hat | Dal | Son kullanılan exact kaynak |
|---|---|---|
| Genel devam/dokümantasyon | `codex/complete-open-work` | `799bb41b3cbc50ab6d3feb26ecb4e98c01f96350` (bu devir commit'inden önce) |
| Ana çip full64 yönlendirme | `codex/mainchip-guide-tiled-full64` | `9430a57873e78d3c283b531da8e8e74da416f297` |
| Actual650 CDR N1 | `codex/cdr-mos650-full-composition` | `9bba58288772dd2bee9dab142e391d0616737973` |
| Actual650 CDR N2 | `codex/cdr-mos650-full-composition-n2` | `81555c8ba8357f2874fab2c5bb0c3378305e3501` |
| Postroute sınıf restorasyonu/netlist | `codex/mainchip-postroute-handoff` | `4b0310839b5e718f1a2c66c1725cfeaff75a4ffb` |

v360 monitor envanteri 922 satır, shard 000–004 ve `automatic_native_dispatch=false` içeriyordu. Son düzeltilmiş handoff işi ve bu terminal sonuçlar eski checkpoint metninde tam yer almıyor. Bu MD bir **devir güncellemesi**, tüm eski envanteri yeniden üreten v361 checkpoint'i değildir. Önceki 8 saatlik monitor bilgisinden otomatik onarımın çalıştığı sonucunu çıkarma; masaüstü otomasyonunun etkinliği bu devirde yeniden doğrulanmadı.

## 3. En son gerçek sonuçlar

| İş | Sonuç | Kaynak / temel durma nedeni |
|---|---|---|
| [41699812301](https://github.com/Melihakbulut221/nssoc/actions/runs/41699812301) | Failure | Full64 route; supervisor bellek ölçüm penceresi tükendiği için SIGTERM |
| [41733225660](https://github.com/Melihakbulut221/nssoc/actions/runs/41733225660) | Failure | N1 transient motoru exit 0; veri, faz ve cihaz kabulü başarısız |
| [41734419971](https://github.com/Melihakbulut221/nssoc/actions/runs/41734419971) | Failure | N2 transient motoru exit 0; N1'e çok yakın elektriksel başarısızlık |
| [41739641054](https://github.com/Melihakbulut221/nssoc/actions/runs/41739641054) | Failure | DEF wire-clause parser varsayımı prepare aşamasını durdurdu |

**Şu anda bu dört işin bitmesini beklemiyoruz; bitmiş başarısızlıkların nedenlerini düzeltmek gerekiyor.** En son işlerin tamamlanması üretim veya timing kabulü değil.

Makine tarafından okunabilir devir kanıtı: [CLAUDE_HANDOFF_EVIDENCE.json](CLAUDE_HANDOFF_EVIDENCE.json). Bu dosya seçilmiş ölçümleri içerir; tam native raporların yerine geçmez.

## 4. Ana çip yönlendirmesi: nerede kaldı?

### 4.1 Son adayın kapsamı

Kaynak `9430a578...`, iş 41699812301. 154480 instance, 143820 net, 1691 korunan clock/fixed net. Orijinal 153129 instance üzerine 1351 anten diyodu eklenmiş durumda. Güncel daraltılmış onarım **47 net**; eski geniş 828-owner planıyla karıştırma. Full64 router stratejisi ve 11 faz korunuyor. Guide engine parçalama bir GCell örtüşmeyle yapılıyor.

Native rapor:
`native/bulk-postdrt-snapshot-inner-result.json`

Durum:
`FAIL_GUIDE_ENGINE_ACTUAL_FULL64_ROUTE_OBSERVATION`

Prepare, freeze-import, freeze-audit, reverse-import, reverse-audit-clear geçti. Route başladı, tamamlanmadı. Sonraki restore, route-audit, final-check ve measure tamamlandı denemez.

### 4.2 Yeni gerçek hata

Route supervisor tarafından **11754.290770678 saniyede**, yaklaşık 3 saat 15 dakika 54 saniye sonra sonlandırılmış:

```text
supervision_failure: memory_sample_unavailable
memory_read_error:
  SupervisionFailure("CounterError('Total memory snapshot bounded window exhausted')")
returncode: -15
```

Bellek örnekleme toplam bütçesi 0.1 saniye. Son başarılı örnek:

- Süreç grubu RSS: 7018548 KiB, yaklaşık 6.69 GiB.
- Kullanılabilir RAM: 8176584 KiB, yaklaşık 7.80 GiB.
- RSS üst sınırı: 11534336 KiB, 11 GiB.
- Asgari kullanılabilir RAM: 2097152 KiB.
- Son başarılı örnek süresi: 0.000857521 saniye.
- Route süre sınırı 14400 saniyeydi; hata bu sınıra gelmeden oluştu.
- Cleanup sonrasında canlı çocuk süreç kalmadığı raporlandı.

**Bu olay gerçek RAM tükenmesini kanıtlamıyor.** Önceki 41552715162 işindeki 11793076 KiB RSS / 11 GiB sınırı olayı farklıdır. Yeni sonucu “yine OOM” diye özetlemek yanlış olur.

Ek çıktı koruma hataları:

```text
preserve:bulk-postdrt-antenna/narrow47-route-actual.tcl
preserve:bulk-postdrt-antenna/narrow47-route-original.tcl
AssertionError('unexpected output')
scripts/mainchip_full64_output_preservation.py:25
```

Native capsule/artifact var; bu iki allowlist hatası ayrıca düzeltilmeli. Kısmi snapshot bulunması yönlendirmenin bittiği anlamına gelmez.

### 4.3 Claude'un sıradaki adımı

1. Supervisor'ın toplam 0.1 saniyelik ölçüm penceresini ve geçici proc/cgroup okuma gecikmesine davranışını incele.
2. Gerçek RSS/süre/çocuk süreç güvenliğini koruyarak sınırlı retry/deadline politikası ekle; korumaları tümden kapatma.
3. Çıktı koruma manifestine iki gerçek Tcl çıktısının neden uymadığını düzelt; rastgele dosyaları serbest bırakma.
4. Mevcut kısmi çıktıyı exact kaynak/member/hash ile incele; devam edilebilir bir checkpoint olup olmadığını kanıtla.
5. Sonra yeni kontrollü native iş. Aynı kaynağı değişikliksiz tekrar tekrar başlatma.
6. Tam route sonrasında DRC/antenna, sınıf restorasyonu, yeni netlist, RC ve timing zincirini tamamla.

İlgili kaynaklar, `9430a578...` dalında:

- `scripts/cloud_mainchip_guide_full64_route.py`
- `scripts/mainchip_guide_full64_inner.py`
- `scripts/mainchip_route47_native.py`
- `scripts/mainchip_route47_contract.py`
- `scripts/mainchip_route47_import.py`
- `scripts/mainchip_route47_memory.py`
- `scripts/mainchip_full64_output_preservation.py`
- `scripts/mainchip_guide_engine_acquisition.py`
- `scripts/mainchip_guide_route_qualification.py`
- `scripts/mainchip-guide-engine-built-inputs.json`
- `scripts/mainchip-guide-engine-qualified-inputs.json`

Dondurulmuş host/orijinal projeksiyon kaynağı:
`7a0776718ec37a106b7dfde0cbd477c6a2a5522f`.

Burada `scripts/mainchip_bulk_postdrt_antenna_native.py`,
`scripts/mainchip_bulk_postdrt_antenna_inner.py`,
`scripts/mainchip_original_clock_restoration.py` ve
`hw/soc/pcie-evidence/20261025-gen12-record-qualified-source/scripts/cloud_pcie_gen12_training_records_telemetry.py`
önemli. Wrapper'ın yalnız kendi dalındaki dosyalardan çalıştığını varsayma; embedded/frozen source bağımlılıklarını takip et.

## 5. Postroute netlist aktarımı: ikinci parser hatasında durdu

Amaç, fiziksel diyotları koruyarak eski geçici route sınıflarını geri yüklemek, gerçek netlist çıkarmak, temiz library DB'ye yeniden okuyup bütün instance/master/pin/port/net incidence eşitliğini doğrulamak.

İlk native iş [41738314531](https://github.com/Melihakbulut221/nssoc/actions/runs/41738314531), kaynak `50f1ebf8d1c940abff985f971aeae670eeb4a9ec`, candidate FIXED overlay'den korunan net listesini otomatik türettiği için 1691 kapsamını aşarak durdu.

Düzeltme `4b0310839b5e718f1a2c66c1725cfeaff75a4ffb`: korunan 1691 net yalnız exact orijinal `p.INPUT` üzerinden seçiliyor ve tüm snapshot'lara açıkça geçiriliyor. Kaynak kontrol işi [41739416744](https://github.com/Melihakbulut221/nssoc/actions/runs/41739416744) geçti. Önceki kaynak kontrolü 41738123187 altı rejection vakasını da kapsıyordu.

Düzeltilmiş native iş **41739641054** bu ilk hatayı geçti ama prepare içinde yaklaşık 145.57 saniyede şu ikinci hata çıktı:

```text
mainchip_postroute_handoff_native.py:66
  target = c.classes(original[name])

mainchip_original_clock_restoration.py:121
  assert len(hits) == 1, 'exactly one supported encoded wire clause'

AssertionError: exactly one supported encoded wire clause
```

Çağrı tüm net kayıtlarına uygulanıyor; parser tam bir desteklenen wire clause varsayıyor. Offending kayıtta sıfır mı, birden çok mu clause bulunduğu henüz çıkarılmadı. **Netin bozuk olduğunu veya assert'in gereksiz olduğunu varsayma.**

Aynı işte `handoff-logical-diode-pg.json`:

- 1351 ek diyot için logical supply bindings verified = true.
- **physical supply connectivity verified = false.**

Bu kontrol yalnız logical bağlantı; metal PG sürekliliği, transistor LVS veya tam çip LVS değildir.

Sıradaki işlem: native prepare'a başarısız net adı ve route-clause dökümünü güvenli türetilmiş rapor olarak ekle; orijinal DEF sözdizimini bozmadan meşru sıfır/çoklu kayıtları ele al. Protected-net kapsamını veya eşitlik testlerini sessizce azaltma. Tam native export/read-link ve topology mutation testleri henüz başarıyla çalışmış değil.

Kaynaklar:

- `scripts/cloud_mainchip_postroute_handoff.py`
- `scripts/mainchip_postroute_handoff_inner.py`
- `scripts/mainchip_postroute_handoff_native.py`
- `scripts/mainchip_postroute_handoff_contract.py`
- `scripts/check_mainchip_postroute_handoff.py`
- `scripts/mainchip-handoff-route-inputs.json`
- `scripts/mainchip-snapshot-reload-pins.json`
- `docs/mainchip-postroute-handoff.md`

Mevcut qualification girdisi yeni full64 çıktısı değil; eski tamamlanmış [41440285882](https://github.com/Melihakbulut221/nssoc/actions/runs/41440285882), kaynak `0990e2971dee0333598a59a033dfe4f1f1f4215b`, release 431403455. Bu eski adayda **92 DRC (64 short, 28 spacing), 27 antenna / 21 net** vardı. Bunlar yeni route'un son sayıları değil.

Handoff uygulaması iki FLOORPLAN importuyla original global sınıfları geri yüklemeyi, complete DEF karşılaştırmayı, `write_verilog -include_pwr_gnd`, `odb.dbChip.destroy` sonrası library-only DB'ye read/link yapmayı hedefliyor. Physical cells/diodes dışlanmamalı. Gerçek native uyumluluk ve beş topology fault kontrolü hâlâ tamamlanacak.

## 6. Actual650 CDR: simülasyon artık çalışıyor; devre kabulü geçmiyor

### 6.1 Geçmiş önkoşulların doğru kapsamı

Aşağıdakiler yararlı ilerleme; hiçbiri kendi başına tam PCIe PHY kabulü değil:

| Kanıt | İş / kaynak | Kapsam |
|---|---|---|
| Güncel macro GDS | 41709759119 / `087721d42112ed108543d2da053ee6d0e2f20a9c` | `nssoc_cdr_pd500_resistor_v59`, 1624572 byte GDS |
| Macro fiziksel kontrol | [41710162510](https://github.com/Melihakbulut221/nssoc/actions/runs/41710162510) / `b3d9d1d284b1e8464d5359e7e21991aef21a787c` | 560 DRC kategorisinde 0; deep/flat 650 LVS; 13 fault |
| Güncel wire bağlantıları | 41712243960 / `f3aece4ae3b048df220cb51277d74fcd026940ed` | 2046 terminal, 1428 anchor, 200 GC, 50 gate group, 113 metal component |
| Intrinsic partition | 41717942914 / `30392de6e292c690fe73f469c32c236a5ce51b1c` | 160 DC/AC, 13696 karşılaştırma, N1/2/4/8/16; eşpotansiyel önkoşul |
| Gate network reduction | 41725473326 / `8d7874d8c9740725ed1e4cd8c3631ec1c81bc2e6` | 250 net, 503 native DC/AC/noise/power, 2 fault |
| MIM-aware metal | 41728568165 / `1b40bf2db3844d6281c467022b248a2871ced6df` | 28634 R, 18476 C, 7 MIM; iki native order, wire/MIM fault kontrolleri |

Macro: 200 NMOS + 124 HBT + 98 direnç + 7 MIM + 221 ptap = 650 öğe, 25 port. Gate reduction nominal 7 ohm/square ve 15 ohm/contact kullanır; extrinsic poly capacitance, malzeme PVT ve substrate R tam signoff seviyesinde kabul edilmiş değil. Güncel GDS SHA256:
`c335182048dc1696821ab875fb34447e5b5a9ba0f1a24d5d16d572680906c16c`.

### 6.2 Eski startup hatası ile yeni elektriksel hatayı ayır

İlk full650 iş 41732402949, kaynak `b3768d5f3201cf661b15bc85f431ba46be3eee48`: KLU / eksik spinit, NaN/singular, yaklaşık 3.125 fs ve yalnız iki satır. Motor exit 0 bile olsa geçerli transient değildi.

Yeni N1 ve N2 Sparse + doğru startup ortamıyla transienti tamamladı:

- N1: 6640.517 saniye, yaklaşık 1 saat 50 dakika; returncode 0.
- N2: 7789.928 saniye, yaklaşık 2 saat 10 dakika; returncode 0.
- Native diagnostics listeleri boş, startup values finite.
- Her ikisi `REJECTED_WHOLE_MIM_ACTUAL650_LOADED`.
- Her ikisinde `data_passed=false`, `devices_passed=false`, `phase_passed=false`.

Hata `scripts/cdr_mos650_full650_loaded.py` içindeki `measure_wave` line 243 / `run_loaded` line 321:

```text
Actual whole-wire retimed sampling, loaded phase/current or device gate failed
```

### 6.3 Yeni ölçümler: aynı hatanın N1/N2'de tekrarı

| Ölçüm | N1 | N2 | Beklenen |
|---|---:|---:|---|
| Phase average | 14.018782 mV | 14.018650 mV | signed minimum 30 mV |
| VI mean signed current | 42.087206 µA | 42.086893 µA | minimum 50 µA |
| VI mean output difference | 11.828373 mV | 11.828277 mV | minimum 5 mV; bu tek ölçüm geçse de toplam VI fail |
| XOR x wrong-sign | 388 / 765 | 388 / 765 | 0 |
| XOR y wrong-sign | 44 / 765 | 44 / 765 | 0 |
| XOR x below 100 mV | 727 / 765 | 727 / 765 | 0 |
| XOR y below 100 mV | 664 / 765 | 664 / 765 | 0 |
| Sampler a/b/c/d wrong-sign | 0 / 0 / 1 / 34 | 0 / 0 / 1 / 34 | her biri 0 |

Sampler a/b/c/d below-100mV sayıları iki deneyde de 129/128/129/128. Stage total tail minimum yaklaşık 1.500868 mA; stage gate 0.5 mA. **Bu stage-current sınırı geçtiği için bütün cihaz kontrolleri geçti denemez**; `devices_passed=false` veren bireysel HBT/MOS/MIM kayıtlarını ayrıntılandırmak gerekiyor.

N2 fiziksel farklı bir devre değil: aynı 200 MOS'un intrinsic modeli iki adet m=0.5 parçaya bölünüyor; toplam m=1 korunuyor. Bir MOS parçasının akımını doğrudan fiziksel stage toplam akımı gibi yorumlama. N1/N2 yakınlığı, bu nominal vakadaki başarısızlığın yalnız bu partition seçimiyle giderilmediğini gösteriyor. N4/N8/N16 loaded yakınsama veya tüm PVT geçişi henüz kanıtlanmış değil.

Bench orijinal 256 bit, 2 ns başlangıç, 34.25 ns stop, 0.3125 ps maksimum step, `nominal_late`; **harici 8 GHz clock kullanıyor, closed_loop=false**. Bunu recovered-clock veya PCIe bit-error-rate/compliance kabulü sayma. 27°C / 125°C / −40°C dahil on-case kapsamın tamamı çalışıp geçmedi.

### 6.4 Claude'un sıradaki analog işi

1. `loaded-n1-nominal_late.json` ve N2 raporundaki bütün başarısız bireysel device/mos/cap kayıtlarını küçük failure census'a çıkar.
2. Sampler a→b→c→d ve XOR x/y için gerçek saat fazı, gecikme, signed margin ve beklenen bit hizalamasını native dalgadan takip et. Ölçüm oracle'ının doğruluğunu da korunan stimulus/orijinal beklenen dizilerle kontrol et.
3. Aynı koşullarda hangi stage'in marjı çökerttiğini bul; kör boyut/direnç taraması yerine ölçüme dayalı değişiklik yap.
4. Elektriksel eşikleri gevşetme. Faz gate 30 mV, sampler/XOR 100 mV, VI 50 µA gibi sözleşmeler korunmalı.
5. Yeni geometri varsa DRC/LVS/RC'yi o geometri için yeniden üret. Nominal düzeldikten sonra diğer vakalar ve gerekli partition yakınsamasını tamamla.
6. Sonra gerçek VCO/PLL ile closed-loop bağlantıya geç; external-clock pass bunun yerine geçmez.

Kaynaklar:
`scripts/cdr_mos650_gate_ac.py`,
`scripts/cdr_mos650_full650.py`,
`scripts/cdr_mos650_full650_loaded.py`,
`scripts/cdr_mos650_spice_syntax.py`,
`scripts/cdr-mos650-gate-ac-inputs.json`,
`scripts/cdr-mos650-gate-ac-pins.json`.

N2 ayrıca `scripts/cdr_mos650_archive_transport.py` kullanıyor; 1.8e9-byte parçalar ve `archive-parts.json` ile parça/tüm-arşiv hash kontrolü var. N1 tek arşiv yayınlama yolu büyük dosyada ayrıca incelenmeli; elektriksel fail ile olası taşıma sorununu karıştırma.

## 7. PLL / ilk divider: kapanmamış ikinci analog bağımlılık

Okunacak kök belgeler:

- [CDR–PLL bağlantı incelemesi](docs/pcie-cdr-pll-connection-audit-20261104.md)
- `docs/evidence/pcie-cdr-pll-connection-audit-20261104.json`
- `docs/evidence/pll-first-divider15-terminal-column-map-20261024.json`

RHI120-C8 yakalaması [40071288423](https://github.com/Melihakbulut221/nssoc/actions/runs/40071288423), kaynak `c61befbd80140a2e22a821f6a35dd31e3a5b36e9`:

- 3,201,410 satır, 5106 sütun, 1 µs, 0.3125 ps maksimum step.
- Raw 130771392219 byte; SHA256 `60f5318b08315751f7d3bede13223c12e4f4a13378e8d3d76e647f768446d8be`.
- Orijinal 0.9–1.0 µs pencerede feedback **104.152221297 MHz**.
- Phase span **5.002708790 ns**.
- Orijinal 100 ppm frequency ve 50 ps phase gate başarısız. No-slip/control-window geçişi acquisition'ı kurtarmıyor.
- Eski PLL845'in 110.440674 MHz / 9.190319 ns sonucu başka yakalama; birbirine karıştırma.

Terminal map 15 HBT + 4 collector load + 54 ayrı voltage sütunu içeriyor. SHA256:
`d405e7125ae9b838dc258d65ccfc91c03d0f3e9e03ccaed59a741dfb75058df5`.
**Tekil Ic/Ib/Ie akımları kaydedilmemiş.**

Gözlemler: 10 mV eşiğinde 8648 interval içinde 159 double-transition; conditioned clock yaklaşık −85.9/+91.1 mV ve 1.36428 V common-mode. VCO yaklaşık −244/+253 mV, 1.08058 V common-mode. Master/slave clock-route farkı en çok yaklaşık 1.35 mV; büyük route skew'u kök neden olarak desteklemiyor. Emitter farkı 11.9–15.2 mV nedeniyle bazı olaylarda etkili VBE ayrımı 38.3–49.2 mV'ye düşüyor. Tail Vce yaklaşık 0.446–0.45 V, Vbc yaklaşık +0.38 V; headroom/steering/regeneration incelemesi gerekli, tek neden kanıtlanmadı.

Gerçek fiziksel ilk dört collector load W8/L2.8 µm; generic latch dosyasındaki L2.12 µm'yi sessizce kullanma. İkinci dört load W8/L3.2 µm ayrı adayın parçası. İlk conditioner XSP/XSN W4/L3.6 µm, XUP/XUN W1/L4 µm.

Kaynaklar:
`hw/soc/analog/pcie/clock_div2_conditioned_hbt_v3.spice`,
`clock_div2_hbt.spice`,
`rx_sampler_hbt_v2.spice`,
`clock_div4_hbt_v10.spice`,
`hw/soc/flow/make_pcie_clock_div4_load3p2_v2.py`.
Kısa isimli SPICE dosyaları aynı analog/pcie dizinindedir.

### Hazır küçük native giriş bulundu; sonraki deney henüz yazılmadı

Tam hazırlanmış deck + model + RC için 130 GB raw'u indirmek gerekmiyor. Hazırlama işi [39920519407](https://github.com/Melihakbulut221/nssoc/actions/runs/39920519407), kaynak `efe9885e87bce9eb82a1c6decc4ed85ab2d65160`, release **421575365**:

https://github.com/Melihakbulut221/nssoc/releases/tag/cloud-results-39920519407-1-pll-rhi120-c8-preparation

- Native parça asset 668392118; 2052397 byte; SHA256 `a7b33b0742783e477c5c7472c8f3a984e1ffce7eeb9280d358b7a6c1ee026c41`.
- Parts manifest asset 668391994; SHA256 `92a85edae348ad4e3ebfb62b372f627dde16ef9aadb4fcb55cedc1422a9d4657`.
- Summary asset 668391906; SHA256 `63c6b8d34ecf277dce223427c72bdb943ed0dc010c80f496d8feb33f268f94dd`.
- Archive: `candidate-circuit.cir`, `terminal-instrumentation.json`, `composition/pll845-mim-wire.spice`, `composition/composition.json`, 38 model/kaynak dosyası.
- 845 device + 4 auxiliary contact, 3381 R, 5105 C, 26 MIM.
- Composition SHA256 `2e365bed864f6762e46ebe96b64b888b49b25558cec106a5eebde110fcca81fa`.
- Candidate circuit SHA256 `690d1e9cf8ab1c7fcf1e0d6a5450df1c04dbb0eeef1f6b38018845cffd7671c6`.

Release legacy `target_commitish` branch adı gösteriyor; tag object exact commit'e çözülerek doğrulanmıştı. Yalnız target_commitish metnine güvenme.

Önerilen ama **henüz uygulanmamış/çalıştırılmamış** deney: gerçek loaded VCO + conditioner + iki latch + downstream feedback korunarak 15 HBT'ye 45 Ic/Ib/Ie probu eklemek; voltajlarıyla birlikte incelemek. Ideal clock replay ile nihai onarım kanıtlanamaz. Veri hacmini azaltmak için late-window kayıt düşünülebilir, ama acquisition penceresini kısaltıp orijinal tam 1 µs kabulünü geçmiş sayma.

İlgili runtime/preparation kaynakları:
`scripts/cloud_pll_rhi120_c8_preparation.py`,
`cloud_pll_rhi120_c8_op.py`,
`cloud_pll_rhi120_c8_initial.py`,
`cloud_pll_rhi120_c8_sparse.py`,
`scripts/cloud_tx_companion_replay.py`,
`scripts/run_cloud_pll865_snapshot.py`.
Native subprocess environment'ına GitHub credential aktarma; wrapper sınırını kontrol et.

## 8. PCIe, Ethernet ve ana çip entegrasyonunun gerçek sınırı

Kök incelemesinde `soc_top.v` tarafında `pcie_link_up_i`, training/retrain_done ve byte RX data/valid gibi dışarıdan sağlanan durum/veri sınırı var. Bu, içeride dört fiziksel lane'den başlayıp kendi training/clock recovery'sini yapan tam link kanıtı değil. Exact dosya yolu/instance zincirini kaynak aramasıyla tekrar teyit et; belgelerdeki controller sınırıyla analog seri pinleri aynı şey değil.

Shared serial front için 41223635170 işinde 50 pozitif RTL testi, 2 mutation ve 2 hierarchy kanıtı vardı. Recovered clock/raw bits dışarıdan geliyor; bütün LTSSM, equalization, lane assignment ve normatif Gen3 x4 compliance kapanmış değil.

Tamamlanacak zincir:

1. Stabil gerçek PLL/divider ve CDR closed-loop.
2. Tam TX/RX SERDES, PCS ve dört lane clock/data ownership.
3. Eğitim/LTSSM, equalization, lane bonding/deskew, recovery ve reset/CDC.
4. Controller/data-link replay/credit/error yönetiminin seri uçtan ana çip transaction'a uçtan uca doğrulanması.
5. Analog pad/ESD, supplies, padframe, layout instance/pin bağlantıları.
6. Aynı tam entegre çip üzerinde extraction, DRC/LVS, antenna ve original-clock setup/hold.

Bunların bir kısmında RTL/modül/test bulunması mümkündür; **tamamı yok** diye de iddia etme. Eksik olan kabul kanıtını module→instance→GDS/LEF→net→test ilişkisiyle çıkar. `docs/pcie-serial-integration-boundary.md` başlangıç belgesidir.

Ethernet için geçmiş RTL/FIFO/MBIST ve fiziksel çalışmalar mevcut, fakat bu devirde güncel kökün uçtan uca Gigabit Ethernet entegrasyonu yeniden denetlenmedi. “Tam layout entegrasyonu/timing kapandı” deme. Kullanıcının geçmişte aktardığı 1311 setup / 60 hold eski Ethernet denemesine aittir; güncel full64 veya final çip sayısı değildir.

PCI-SIG Base 3.0 normatif metnine yetkili erişim önceki çalışmada açık bağımlılıktı. Ücretsiz overview'u tam compliance oracle gibi kullanma. Erişim durumu değişmiş olabilir; doğrula ve kapsamı açık yaz.

## 9. Nihai RC ve setup/hold için korunacak sözleşme

Önce tamamlanmış ve doğru netlist'i yeniden okunmuş fiziksel aday gerekir. Eski route12 adapter'ı 153130 instance, sıfır ek diyot ve eski netlist'e bağlı. Yeni 154480-instance adayı ona assert gevşeterek sokma.

İlgili eski kaynak:
`scripts/cloud_mainchip_route12_postroute_geometry.py`,
`scripts/cloud_mainchip_route12_postroute.py`.

Eski netlist SHA256:
`3c053c4cda51a001b926cce347b97de5c825cbff2082de550eeb9e31ff7fe5cd`.

Yeni akışta:

- Exact ODB/netlist identity ve tüm physical cell/diode bağlantıları doğrulansın.
- Yeni geometriye fresh extraction; eski SPEF/STA metriğini yeniden etiketleme.
- Orijinal clocks **20/4/8/8 ns**, **%5 derate**.
- Corners: `nom_slow_1p08V_125C`, `nom_typ_1p20V_25C`, `nom_fast_1p32V_m40C`.
- Setup ve hold worst slack ≥ 0; setup/hold/max-cap/max-slew/max-fanout ihlal sayıları 0; bütün sayılar finite.
- Propagated clock ve aynı ODB/netlist'in extraction öncesi/sonrası korunması.
- Source: `hw/soc/pnr/mainchip_completed_postroute_flow.py`, LibreLane 3.0.5, `MainchipCompletedPostroute`, `OnehotRouteRCX`, `OnehotRoutedSTA`.
- PDK revision: `c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c`.
- Portable AppImage SHA256: `d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466`.
- Orijinal SDC SHA256: `19fdfb6dab9889037a4d1f486dadd4c46ac9ccc109a64c78422376c116233597`.

Nominal RC ile üç timing corner geçmek, RCmin/RCmax veya foundry signoff'un tamamını otomatik kanıtlamaz. Yeni route'un final setup/hold sayısı henüz yok; eski sayıları güncel diye raporlama.

## 10. Tam ürün için unutulmaması gereken diğer açıklar

Bu devir son kritik hatlara odaklandı; bütün ürünün yeniden denetimi değildir. Geçmiş kullanıcı kapsamı aşağıdakileri de içeriyor. Her biri için kaynak ve güncel, aynı tasarıma bağlı kabul kanıtı çıkarılmadan “kapalı” işaretleme:

- Tam çip transistor LVS: SRAM, I/O tap referansı/geometri, supplies ve analog/digital bağlantılar.
- SRAM tam PVT Liberty/karakterizasyon, gerçek RC, bütün SRAM/FIFO MBIST ve hata kapsaması.
- Core ile bütünleşik padframe, ESD ve fiziksel güç ağı.
- DFT/test erişimi, reset/CDC/RDC ve üretim testi kapsamı.
- Ethernet/SpaceWire/I2C ve diğer hedef arayüzlerin RTL→sentez→yerleşim→port→timing zinciri.
- DRC/antenna kapanışı; yalnız alt macro DRC geçişi tam çip geçişi değildir.
- Üretici/PDK signoff ve tapeout/üretim onayı. Bu onay verilmiş değil; sadece kod üreterek resmi üretici onayı alınmış sayılamaz.

Kullanıcının eski inceleme ekleri:

- `/home/hasanmelih/Downloads/nssoc-external-review.md`
- `/home/hasanmelih/Downloads/nssoc-audit-2026-09-20 (2).md`

Bu devir sırasında ekler yeniden okunmadı; bulutta kopyaları veya repoda karşılıkları var mı doğrulanmadı. İlk ürün envanterinde bunları bulup her maddeyi mevcut kanıta eşleştir. Ekteki metni, kullanıcının gerçek talebi ve sonradan değişen çalışma tercihleriyle birlikte yorumla; “eklerin hepsi bitti” iddiasında bulunma.

## 11. Neden haftalardır aynı yerde görünüyordu?

Kapanışı geciktiren tek bir problem yok:

- Analog macro DRC/LVS, partition doğrulaması veya test sayısı artışı **tam çalışan PHY** demek değil. Önkoşullarda ilerleme olurken ürün kabulü aynı yerde kalabiliyor.
- Gerçek extracted transient saatler sürüyor; yeni N1/N2 yaklaşık iki saat sonunda fiziksel/elektriksel yetersizliği gösterdi.
- Fiziksel diyot/net değişikliği önceki netlist/RC/STA bağını geçersiz kılıyor; yeni adayın aynı-tasarım kanıt zinciri kurulmalı.
- Araç/wrapper tarafında yeni engeller çıktı: supervisor'ın çok dar bellek örnekleme penceresi, çıktı allowlist'i, DEF parser'ın tek-clause varsayımı.
- Kaynak kontrol testlerinin geçmesi native gerçek verinin geçmesini garantilemedi; handoff'ta bunun iki somut örneği var.
- Çok sayıda checkpoint ve belge, bitiş ölçütü yerine geçmemeli. Eski “in_progress” notları terminal sonuçla güncellenmediğinde aynı iş hâlâ ilerliyormuş izlenimi oluşabiliyor.

Buradan sonraki raporlama her değişiklik için “hangi başarısız gate, hangi exact adayda, hangi ölçümle kapandı?” sorusunu yanıtlamalı. Yeni iş açılması veya yeni belge yazılması tek başına tasarım ilerlemesi olarak raporlanmamalı.

## 12. Kanıtları bulma ve bulutta yeniden üretme

Ana workflow: `.github/workflows/cloud-evidence-summary.yml`. Her deney dalındaki workflow input sözleşmesini exact commit'ten oku; aynı isimli workflow farklı kaynaklarda farklı native görevi çalıştırabilir.

Salt-okunur başlangıç komutları (gh kimliği gerekli; gizli token'ları loglama):

```bash
gh api repos/Melihakbulut221/nssoc/git/ref/heads/codex/complete-open-work
gh api repos/Melihakbulut221/nssoc/actions/runs/41699812301
gh api repos/Melihakbulut221/nssoc/actions/runs/41733225660
gh api repos/Melihakbulut221/nssoc/actions/runs/41734419971
gh api repos/Melihakbulut221/nssoc/actions/runs/41739641054
gh api repos/Melihakbulut221/nssoc/actions/runs/41739641054/artifacts
gh api repos/Melihakbulut221/nssoc/releases/433331790
```

Native artifact download/untar ve CAD yürütmesini **cloud runner** içinde yap. Yerel `gh run download`, native clone/checkout veya disk cache'i oluşturan log araçları bu son tercihle uyumlu değil. Küçük derived ZIP'ler gerekiyorsa API ile RAM'de okunabilir. Derived ve native arşivleri yalnız adlarına bakarak karıştırma.

Kaynak değişiklikleri önce kontrollü source tests ile doğrulanıyor; ardından exact branch/head için native workflow dispatch, run/source/release eşleştirmesi ve içerik hash kontrolü yapılıyor. Önceki release/member hash'lerini yeni adaya körlemesine kopyalama. Workflow inputs ve reserved release gereksinimini kaynak üzerinden öğren; bu MD bilinmeyen dispatch parametrelerini uydurmuyor.

Dokümantasyon commit'leri `[skip ci]` kullanıyor. 8 saatlik gözlem yeni native iş yaratmıyor. Otomatik düzeltici çalışıyor varsayımıyla bekleme.

### Son terminal artifact ve release pinleri

| İş | Derived artifact / byte | SHA256 |
|---|---|---|
| 41699812301 | 13282143086 / 519206 | `56dd70992717c11450952a84b08ebf03137880d91bb61273952fbb93e36458ef` |
| 41733225660 | 13284168776 / 283198; final 13283894221 aynı içerik | `16507783bfb8a7065095bc34668748ce6686436f963290a6e42bcdc488c5488a` |
| 41734419971 | final 13285864693 / 315180 | `4bdbc6bb328a5a584f3b58168e78506368ae78345923d0937630505088fa6233` |
| 41739641054 | 13279979878 / 214399 | `6f067f6e23bdcab6ce57e6df71b8199329274a9e53e476871d50c80b537a72f1` |

Release bağlantıları:

- [Route / 433106055](https://github.com/Melihakbulut221/nssoc/releases/tag/cloud-results-41699812301-1-mainchip-bulk-postdrt-antenna)
- [N1 / 433297951](https://github.com/Melihakbulut221/nssoc/releases/tag/cloud-results-41733225660-1-cdr-mos650-gate-ac)
- [N2 / 433304261](https://github.com/Melihakbulut221/nssoc/releases/tag/cloud-results-41734419971-1-cdr-mos650-gate-ac)
- [Handoff / 433331790](https://github.com/Melihakbulut221/nssoc/releases/tag/cloud-results-41739641054-1-mainchip-bulk-postdrt-antenna)

Native fallback artifact'ları **yalnız bulutta**:

| İş | Artifact | Byte | SHA256 |
|---|---:|---:|---|
| Route | 13282928499 | 3880569190 | `63bbfb7ed142cd29cf0188fa786ca5eba57bc15ea477d2f71874b47c0ec65e1e` |
| N1 | 13283214752 | 4452396795 | `ac342f4945a262a4c0fb2440634aa600b8d3f07c6c257c9d3d6e648a319b2402` |
| N2 | 13286900871 | 5113234766 | `71965c84fd3935bf3404a4197be41a027113d7dc885a2fa146ecea1bb35c2d87` |
| Handoff | 13280653573 | 404886115 | `bedd79399592d27f94a0253c62a62889f90ca9ecf9dc402a8e1d33fd499c1592` |

Artifacts süreli olabilir. Devralırken expired durumunu ve release'deki gerçek asset envanterini tekrar kontrol et; release kaydı bulunması bütün native parçaların yüklendiğini tek başına garanti etmez. Tüm parça hash'lerini ve yeniden birleşmiş arşivi doğrula.

## 13. Claude için ilk oturum planı ve bitiş ölçütü

1. Bu belgeyi, exact kaynakları ve yeni terminal raporlarını oku. Eski v360 “çalışıyor” durumunu başlangıç gerçeği olarak alma.
2. Kök/dal head'lerini ve aktif işleri tekrar kontrol et; başka çalışanın değişikliğini üzerine yazma. Sonuçları eski source ile eşleştirmeden kullanma.
3. Route supervisor/output-preservation ve handoff parser hatalarını küçük, test edilebilir düzeltmelerle çöz. Gerçek native girdide doğrula.
4. N1/N2 başarısız device census ve bit/phase izini çıkar. Geometri/model/ölçüm hatası ayrımını kanıtla; ona göre analog onarım yap.
5. Loaded PLL ilk-divider akım teşhisini gerçek devre üzerinde tamamla; frequency/phase/acquisition gate'lerini geç.
6. Tam CDR/VCO/PLL closed-loop, seri dört lane ve controller/top bağlantısını doğrula.
7. Tamamlanmış ana çip adayını fresh netlist/RC/STA + tam çip DRC/LVS/antenna zincirine sok. Aynı kaynak/geometriye ait kanıtları birleştir.
8. Eski iki audit'in bütün maddelerini kanıt tablosuna dönüştür; SRAM, I/O, DFT ve üretim bağımlılıklarını unutma.
9. Her terminal işte kaynak SHA, gerçek gate sonucu, artifact/release hash ve sıradaki somut nedeni yaz. Başarısızlığı başarılı gibi yeniden etiketleme.

**İşin bittiği nokta:** sadece kaynak testleri veya macro kontrolleri değil; gerçek seri Gen3 x4 ve Ethernet'in hedef ana çipte bağlantısı, o adayın yönlendirmesi, geçerli modeller/RC ile original-clock setup/hold kapanışı, fiziksel doğrulamalar ve ürün kapsamındaki diğer kabul maddelerinin ayrı ayrı kanıtlanması. Üretici onayı gibi dış bağımlılıklar varsa tamamlanmış saymak yerine açıkça belirt.

Bu devir anında uygulama çalışması yukarıdaki dört terminal başarısızlıkta duruyor. Yeni PLL akım deneyi, yeni route/handoff düzeltmesi ve yeni native dispatch bu devirde yapılmadı.
