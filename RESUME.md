<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Aktif devam noktası — 20 Eylül 2026

Kullanıcı çalışmaya devam edilmesini ve incelemedeki her maddenin kapanmasını
istedi. Alttaki eski durdurma kaydı tarihseldir; yeni bir durdurma isteği yok.

- 20 Eylül 03:00 TRT. Dal `codex/complete-open-work`; son gönderilmiş commit
  `c966a43`. Ürün ve inceleme kapıları `docs/92-product-acceptance.md` içinde.
- ECO7 tam native route `eth256-eco7-route-20260920` aktif (PID 187301,
  tool session 98866). 01 detailed routing devam ediyor; bitince antenna,
  RCX, üç köşe STA ve GDS/Render otomatik devam eder. Yaklaşık 12 GB boş disk.
  Girdi `timing-eco7-cap/route-inputs.json`; seed'de stale SPEF/GDS/metrics yok.
- ECO7 kapı düzeyi watchdog-armed kontrol tamamlandı: 27306 cycle, RTL ile
  aynı cevap, hata kanalları sıfır. `ethernet-eco7-controls-20260920.json`.
  SDF/fault injection/WCET değildir. GL derleme/sim logları external-review
  klasöründeki `eth256-eco7-fi-{build,armed}.log`; binary `eth256-eco7-fi-gl`.
- Yeni kalıcı `hw/soc/flow/check_physical_eco.py` başlangıç antfix netlistinden
  ECO7'ye doğrudan PASS: 94492 orijinal instance, 441 comb + 21 FF eşdeğer
  değişim + 63 buf8. Orijinal port/alias/wire genişliği/pinler korunuyor;
  gerçek Liberty state/functions ve SRAM bus driver yönleri karşılaştırılıyor.
  26 pozitif/negatif kontrol; ilgili kanıt/dokümanlarla 186 PASS.
  Tüm girdi netlist/Liberty hashleri zorunlu; python -O denetimi kapatmıyor.
- Fresh remote c966a43 tam CI tamamlandı: 653 PASS / 26 SKIP, 806.065s;
  16 kapı PASS / 0 FAIL / 7 SKIP, tree-dirty=0.
  `fresh-clone-c966a43-20260920.json` tüm atlama nedenlerini ve log/XML
  hashlerini tutar; gerçek c966a43 ledger satırı ana kayda eklendi.
- Önceki fresh remote 686e379: 652 PASS / 27 SKIP; 16 CI kapısı PASS / 0 FAIL /
  7 SKIP. Sonraki clock-gate census snapshot fallback'i c966a43'te. F6 sayısal
  eşik geçilmiş olsa da tarihsel orijinal DEF/netlistler eksik: hâlâ açık.
  Claims: 20 re-derived / 15 hand-read / 7 missing build / 0 wrong.
- Orijinal 24-SRAM GDS değişmemiş upstream 5e6d592 KLayout main deck PASS0;
  eski pinned deck aynı GDS'de FAIL22280. `ihp-full-chip-drc-20260920.json`.
  Wrapper `threads` argümanı düzeltildi; gerçek SRAM run'ında 2 thread PASS0.
- Orijinal tam-chip Magic `eth256-decks-20260919`, PID78927 / session22051
  aktif. Sonuç çıkmadan iptal etmeyin; ardından eski KLayout/LVS adımlarını
  yeniden çalıştırması gereksiz olabilir, tamamlanan Magic'i önce kaydedin.
- Magic 2x2 SRAM kıyası session44110: upstream-helper FAIL57, pinned-helper
  FAIL499098 tamamlandı; upstream-raw aktif, pinned-raw sırada.
  Helper ile flatten edilen geometriler hariç tutulmuş değildir.
- 57 upstream Magic işareti salt-okunur GDS ölçümünde tek tek eşlendi:
  21 DigiBnd / SRAM dışı contact 60nm, 36 SRAM contact 10nm active enclosure.
  Magic sınırları70/20nm, KLayout50/6nm; resmi SRAM PDF bölümü WIP.
  `magic-grid-query-20260920/run.log` internal grid'i 0.004999999888um ölçtü.
  `ihp-magic-sram-followup-20260920.json` hash/komutları ve pinned-helper
  FAIL'i kapsıyor. Geometri/kural değişimi veya waiver yapılmadı.
- ECO2 ayrı routed/extracted aday: tüm hold köşeleri PASS (min +0.007986ns),
  slow setup -1.063485ns, cap/slew/fanout FAIL. Router DRC0, antenna0,
  kendi scoped LVS PASS95044device94244net. DRC/XOR ayrı; baseline sonucunu
  ECO2/ECO7 için kullanmayın. ECO1 eksik RC nedeniyle geçersiz; ECO3 durduruldu.
- ECO7 GRT slow setup -0.845294ns, fast hold -0.157326ns; native signoff değil.
  `eco7-endpoint-probe` salt-okunur deney geçersiz: read_guides parasitic
  estimation desteklemiyor (GRT-0008); yalnız bu prob durduruldu, hiçbir
  ölçüm benimsenmedi. `eco7-endpoint-grt-probe` session95022 doğru GRT
  yeniden kurulumuyla aktif. WNS orijinalle karşılaştırılmalı. Kritik
  endpoint hold margin ölçümü hücre küçültme olasılığını araştırıyor.
- Deneyler `hw/soc/out/external-review-20260919`; eski record üreticilerini
  körlemesine çalıştırmayın, zenginleşmiş kayıtları ezerler. Yeni
  prepare_eco7.py seed ODB/NL hashleri sonraki kullanım için düzeltildi.
- PR1 açıklaması en yeni baseline/ECO2/ECO7 kapsamlarıyla güncellendi, draft.
  686e379 push SUCCESS; onun PR/formal ve c966a43 işlerindeki canlı sonucu
  tekrar sorgulayın. Yeni kod/kanıtları doğruladıktan sonra commit/push yapın.
- PCIe Gen3 x4 uyumlu controller/PHY IP yok. Ticari IP/uygun process veya
  mimari kararı gerekiyor. Önceki async IP/mimari ve tarihsel dosya soruları
  yanıtsız; placeholder PCIe, gerçek layout veya ürün değildir.
- Donmuş hw/rtl, hw/tb, hw/openlane, tt kaynaklarına dokunmayın.

## 03:26 TRT ek devam notu

- Son push `dd14c38`; 26 ECO guard testi ve 186 ilgili test PASS. PR güncel.
- ECO7 native (session98866, PID187301) ilk routing'i 0 DRC ile bitirdi;
  223 net /244 pin antenna ihlali buldu, otomatik antenna repair #1 sonrası
  reroute aktif. Final timing veya finalantenna PASS henüz yok.
- `eco7-endpoint-grt-probe` tamamlandı: GRT yeniden oluşturulunca WNS
  ECO7 ile tam aynı. Eski `read_guides` probu GRT-0008 nedeniyle geçersiz.
  `_111988_` endpoint fast hold +0.496228 ns. Kritik kaynak `_116300_`,
  CLINT SECDED mtime bit57; endpoint CPU fetch_addr_q[31].
- ECO8 `timing-eco8-critical-delay`: hold23732 dlygate4sd3->buf1,
  _116300_ dfrbpq1->2. Tam GRT bitti; slowsetup -0.7299956402,
  fasthold -0.1573263786. ECO7'ye karşı 1 comb +1 FF eşdeğerliği PASS.
  Native route yok. `validation-inputs.json`, `connectivity-check.json`.
- ECO9 `timing-eco9-buffer-repair` session76866: ECO8'den, setup resizer
  buffering ENABLED, pin swap/gate clone/buffer removal/last gasp disabled.
  max_iterations200, repairs_per_pass1, repair_tns0, timeout2400s. Şu an
  ilk GRT sürüyor. Çıkarsa gerçek instance delta'yı kontrol edin; sadece
  optimizer bayrağına güvenip removed-cell yok varsaymayın. Kalıcı checker
  yeni buffer olarak şu an yalnız buf8'i kabul eder; diğer doğru buffer
  boyutlarını gerekirse gerçek Liberty mantığıyla doğrulayarak destekleyin.
- `ibex-wb1-probe/sim-clkgate0-20260920`, session38286: eski WB1 FAIL
  deneyini yalnız SOC_CLKGATE=0 ile ayıran gerçek boot/self-test simülasyonu.
  SOC_MEM_RDREG=1, REQ_REG=1, RF_SYNPRE=1, APB_TIMEOUT=256; timeout1800s.
  Eski WB1 mtime a=b=0 ve test15 FAIL, halen geçersiz mimari adayı.
- `timer-irq-register-probe`, session55534: shipping top'un KOPYASINDA
  (WritebackStage=0) CLINT MTIP ile CPU arasına 1 free-running-clock FF
  koyan bağımsız simülasyon. Kaynak RTL/akış değiştirilmedi. Tüm boot ve
  interrupt testleri henüz bitmedi. inputs.json/source/script hashleri mevcut.
  Tek yeni state biti radiation qualification değildir, henüz ürün değişimi yok.
  RISC-V v20260120 Machine ISA 2.1.2.1, mtime/mtimecmp karşılaştırmasının MTIP'e
  gecikmeli yansımasına izin verir; bu yalnız mimari olasılığı destekler.
  Kaynak: https://docs.riscv.org/reference/isa/v20260120/priv/machine.html
- Magic full baseline PID78927 3sa19dk civarı hâlâ çalışıyor, native
  MAGIC_DRC_USE_GDS=false (DEF/LEF abstracts); macro transistor içleri bu
  full-chip run'da gerçek GDS ile test edilmiyor. Sonuç kapsamını doğru yazın.
  2x2 raw upstream kol PID189553 aktif; diğer iki helper kol FAIL57/499098.
- İncelenen daha küçük 2P64x32 SRAM daha hızlı değil: slow B_CLK->B_DOUT
  tablosunun ilk noktası 5.2125 ns, 256x16'da 5.0746 ns. Bu yüzden sırf
  küçülterek SRAM türünü değiştirmeyin; load/slew/timing tablosunu esas alın.

---

# Yeniden başlatma kontrol noktası — 19 Eylül 2026

Kullanıcı bilgisayarı kapatmak için çalışmayı durdurmamı istedi. Yerel fiziksel
akışın süreç ağacı (191882, 191884, 193127, 203234) SIGTERM ile durduruldu.
Yeni mühendislik çalışması başlatılmadı. Bu dosyayı okuyarak devam edin.

- Çalışma dizini: `/home/hasanmelih/Documents/ChatGPT/nnsoc`
- Dal: `codex/complete-open-work`
- Kontrol noktası öncesi kaynak HEAD: `882a4e0d68974deea41044dda6eca6e845826427`
- GitHub: https://github.com/Melihakbulut221/nssoc
- Taslak PR: https://github.com/Melihakbulut221/nssoc/pull/1
- İnceleme girdisi: `/home/hasanmelih/Downloads/nssoc-external-review.md`
- Kullanıcı kapsamı: açık işleri tamamla, değişiklikleri GitHub'a gönder;
  SpaceWire, I2C, Gigabit Ethernet ve GR801 benzeri PCIe Gen3 x4 hedefini takip et.
- `hw/rtl`, `hw/tb`, `hw/openlane`, `tt` donmuş kaynaklarını değiştirmeyin.

## Tam durma noktası ve fiziksel akışı sürdürme

Aktif aday: `hw/soc/pnr/runs/interfaces-eth256-20260919`.
**29-openroad-resizertimingpostcts tamamlandı** ve `state_out.json`, ODB, DEF,
netlist ve SDC yazıldı. **30-openroad-stamidpnr-2 başladı ama tamamlanmadı**;
`state_out.json` yok. Sentez, yerleştirme, CTS ve aşama 29 tekrar gerekmiyor.
Yarım kalan analiz aşaması baştan çalıştırılacak; optimizer belleği saklanmıyor.

Önce yerel dosyaların korunmuş olduğunu doğrulayın:

```bash
cd /home/hasanmelih/Documents/ChatGPT/nnsoc
git status --short
sha256sum -c checkpoints/20260919-shutdown/local-artifacts.sha256
```

Ardından yeni, benzersiz etiket ile aşama 30'un girdisini kullanın:

```bash
resume_tag="interfaces-eth256-resume-$(date -u +%Y%m%d-%H%M%S)"
SOC_INTERFACE_FLOW=1 \
PNR_CONFIG="$PWD/hw/soc/pnr/config-interfaces-synpre.json" \
SYN_NETLIST="$PWD/hw/soc/out/interfaces-eth256-20260919/soc_top.netlist.v" \
PNR_STATE="$PWD/hw/soc/pnr/state/${resume_tag}.json" \
  bash hw/soc/flow/pnr_soc_top.sh "$resume_tag" \
    -F OpenROAD.STAMidPNR-2 \
    -i "$PWD/hw/soc/pnr/runs/interfaces-eth256-20260919/30-openroad-stamidpnr-2/state_in.json" \
    > "hw/soc/out/external-review-20260919/${resume_tag}.log" 2>&1
```

Bu komut kontrol noktası kaydedilirken çalıştırılmadı. LibreLane 3.0.5 yinelenen
adımları `-1`, `-2` ile adlandırır; hedef stage 30'dur. Eski run'ı ezmeyin.
Ana log: `hw/soc/out/interfaces-eth256-20260919/layout.log`.
Sürücü logu: `hw/soc/out/external-review-20260919/eth256-implementation-driver.log`.

**Büyük run dosyaları, sanal ortamlar ve test çıktıları gitignore kapsamındadır;
yalnızca bu bilgisayarın diskindedir.** GitHub kontrol noktası bunları yedeklemez.
Disk temizliği yapmayın. Hash listesi devam için gereken yerel çıktıları işaretler.

## Son tamamlanan doğrulamalar

Durdurma öncesinde temiz klon testi de kendiliğinden tamamlandı:

- Klon: `hw/soc/out/external-review-20260919/fresh-clone-sram256-fixed`
- Klon HEAD: `882a4e0d68974deea41044dda6eca6e845826427`
- `scripts/ci_local.sh all --record`: **16 passed, 0 failed, 7 skipped**,
  kayıt `2026-09-19T17:15Z`, `tree-dirty=0,pandoc=no,tex=tectonic`.
- Tam pytest XML: 645 toplam, **611 passed, 34 skipped**, 0 hata/başarısız,
  191.298 saniye. XML: `hw/soc/out/external-review-20260919/fresh-clone-sram256-fixed-pytest.xml`.
- Log: `hw/soc/out/external-review-20260919/fresh-clone-sram256-fixed-ci.log`.
- Bu başarı henüz kök `ci-local-log.tsv`, `docs/evidence/verification-20260919.json`
  ve ilgili dokümanlara aktarılmadı. Devamda gerçek kayıt ve hashlerle aktarın;
  yalnızca gerekli değişikliklerden sonra tekrar test edin.

Önceki tamamlanan doğrulamalar: 479 RTL başarılı/15 atlanan; yeni 256x16
Ethernet SRAM eşlemesinde 6 native gate paket testi başarılı; 4 tam SoC
netlist koruma testi başarılı; 135 ilgili kanıt/doküman testi başarılı;
son guard düzeltmesi sonrası 115 ilgili test başarılı. Kaynak ve test kapsamı
`docs/89-external-review-follow-up.md`, `docs/90-gigabit-ethernet.md` ve
`docs/evidence/verification-20260919.json` içinde ayrılmıştır.

## Mevcut tasarım ve tamamlanmamış işler

Ethernet 125 MHz GMII MAC, CRC, pad, IFG ve 2 KiB TX/RX asenkron FIFO içerir.
CPU döngü testi 159269 çevrimde geçti. Eski 4 adet 1024x16 SRAM'ın slow TX
zamanlaması yetersizdi. Artık **16 adet 256x16 Ethernet SRAM + 8 ECC SRAM =
24 makro**, die 3326.4 x 2475.9 um. Tam sentez 65667 hücre, 9352 FF, 3 ICG;
standart hücre alanı 1045780.5456 um² (makrolar hariç).
Standalone slow TX setup -0.434501 ns'den +1.520293 ns'ye düzeldi; bu fiziksel
signoff değildir. Yerleştirme sonrası tüm corner/setup/hold sonuçları bekleniyor.

- Yeni 24 makrolu akışın routing/extraction/GDS aşamalarını bitirin.
- LibreLane 3.0.5 `STAMidPNR` yalnız ilk corner'ı raporlar. `state_out.json`
  içindeki miras kalan corner metriklerini yeni ölçüm sanmayın. Son STAPostPNR
  üç corner'ı ayrı çalıştırır. Resizer üç PNR corner'ını kullanır.
- `verify_interfaces_layout.sh` ile tamamlanmış state üzerinden bağımsız
  Magic/KLayout/XOR/LVS kontrollerini çalıştırın. Gerçek failure'ları saklayın.
- `layout_overview.py` kontrol noktasında korunmuş küçük, henüz görsel olarak
  doğrulanmamış değişiklik içerir: 24 makroluk lejand için dinamik iki sütun,
  yeterli sayfa yüksekliği, kısa Ethernet bank etiketleri. Son DEF ile render
  edip görsel doğrulayın. Durdurma isteği sırasında bu kod değiştirilmedi.
- Temiz klonun yeni başarılı sonuçlarını kanıt dosyalarına ekleyip
  `docs/80-artefact-digests.tsv` manifestini güncelleyin.
- Yeni fiziksel sonuçları kaynak hashleriyle kaydedin, PR açıklamasını düzeltin,
  commit/push ve GitHub CI durumunu doğrulayın. Kontrol noktası commit'i için
  CI sonucu beklenmedi; buluttaki CI bilgisayar kapalıyken devam edebilir.
- F6: 34 skip halen var; eksik tarihsel netlist/DEF/raporlar gerçek tool
  eksikliği değildir. Sırf sayı azaltmak için PASS'a çevirmeyin.
- QSPI gerçek I/O constraint'leri mevcut, native extracted hold/setup
  sorunları açık. Flash/board/pad karakterizasyonu ve gerçek çözüm gerekir;
  yeşil sonuç için kısıtları gevşetmeyin.
- PCIe araştırması `docs/91-pcie-gen3-feasibility.md` içinde tamamlandı.
  Erişilebilir SG13G2 Gen3 x4 controller+PHY bulunamadı. Ticari IP/uygun
  process veya farklı FPGA köprü mimarisi gerekiyor. PIPE/boş blackbox
  PCIe implementasyonu değildir; PCIe RTL/layout tamamlandı demeyin.

Eski 8 makrolu `interfaces-export2-20260919` GDS'si mevcut ancak güncel RTL'yi
kanıtlamaz. Router DRC/XOR/antenna/disconnected 0; KLayout/Magic ve timing
başarısızlıkları saklanmıştır; LVS makro pinleri/standart hücre kapsamındadır.
Eski 12 makrolu `interfaces-eth-pnr2-20260919` adayının çalışması daha önce
iptal edildi; onu sürdürmeyin. Ayrıntılar docs/88, 89, 90 ve kanıtlardadır.
`publish_record.py`/`collect_final.py` gibi eski yardımcıları körlemesine
çalıştırmayın: zenginleştirilmiş kanıt kayıtlarını ezebilirler.

## Araçlar

- PDK `~/.ciel/ihp-sg13g2`, pin `c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c`.
- LibreLane 3.0.5: `/home/hasanmelih/Documents/caravel-lif-crossbar/.venv-flow`.
- OpenROAD shims: `~/.local/opt/llbin`; OpenROAD 26Q1-2938-g0e2d771c5e.
- Pytest: repo `.venv/bin/python`; cocotb PATH: repo `hw/.venv/bin`.
- Native Icarus 13: `~/.local/opt/iverilog13/usr/bin`.
- Yosys .33: `~/.local/bin/yosys`; formal OSS araçları:
  `/home/hasanmelih/Documents/gt2n-soc/tools/oss-cad-suite`.
- Komut/path sözleşmeleri: `tools.soc.mk printvars`.


## 19 Eylül: kullanıcı devam ettirdi

Önceki durdurma kaydı tarihseldir. Çalışma yeniden başlatıldı; 23 hash doğrulandı.
Son gönderilen commit `e2193ec`; ek ölçüm kayıtları henüz commit edilmedi.
Yeni temiz klon: `fresh-clone-resume-e2193ec`, 612 başarılı / 34 atlanan test,
16 başarılı / 0 başarısız / 7 atlanan ön kapı kontrolü.

- Ana fiziksel aday: `interfaces-eth256-resume-20260919-184950`. Post-GRT timing repair sürüyor.
- BAŞARISIZ optimizasyon deneyi: `interfaces-eth256-repairs4-20260919-191325`. OpenROAD SizeUpMove assertion
  ile durdu; state_out oluşmadı, bu adayı sürdürmeyin. Aynı post-antenna ODB girdisi ve aynı
  resolved configuration; yalnız setup optimizasyonunda `-max_iterations 120`
  ve `-max_repairs_per_pass 4`. Deney yalnız onarım adımını hedefliyordu fakat çöktü;
  tamamlanmış fiziksel doğrulama değildir. Ana adayın sınırı 600'dür.
- Deney sürücüsü: `hw/soc/out/external-review-20260919/repair_experiment.py`.
- İki log da `hw/soc/out/external-review-20260919/<run-tag>.log` altında.
- Devam etmeden süreçleri ve bu iki run'ın en yeni `state_out.json` dosyasını
  kontrol edin; eski aşama 30'u körlemesine tekrar başlatmayın.

Önemli tanı düzeltmesi: bağımsız STA'da yalnız `_env.tcl` yüklemek yeterli değil.
Native süreç `_LAYER_RC_*`, `_VIA_R_*`, `_LIB_CORNER_*`, `_SDC_IN` gibi hazırlanmış
model değişkenleri de alır. Eksik özel RC ile ölçülen -0.72 ns slow setup,
native değerlerle aynı ODB'de -6.66 ns oldu. Kaydedilmiş global routes mevcut;
sorun onların eksikliği değildi. Ayrıntı `docs/evidence/timing-replay-20260919.json`.
Önceki `eth256-postcts-probe-20260919` özel probu da native RC'yi taşımadığı için
native timing sonucu olarak kullanılmamalı. Yerel akışın kendi raporları ve
son extracted STA esas alınacak. Kısıtlar gevşetilmedi.

## 03:41 TRT ek devam notu

- Buffer guard tüm gerçek buf1/2/4/8/16 fonksiyonlarını kontrol ediyor;
  31 test PASS. ECO7 gerçek replay PASS; ilk checker hashinin dd14c38
  geçmişi korunarak kayıt zenginleştirildi. İlgili test seçimi 97 PASS/5 SKIP.
- ECO9 tamamlandı (session76866): 74 buffer, 21 comb +2 FF, orijinal
  94555 instance korunuyor, guard PASS. Yeniden GRT sonrası slowsetup
  -0.5793694577, fasthold -0.2465108187, typhold -0.0236712878 ns.
  Ara optimizer WNS -0.375 final sonuç değildir. ECO8/9 hash/komutları
  docs/evidence/ethernet-eco8-estimate-20260920.json içinde. Native route yok.
- ECO7 route hâlâ aktif; antenna onarımından sonraki ek routing sürüyor.
  Magic full ve raw SRAM kolları aktif. CPU prob'ları timeout1800 ile aktif;
  timer IRQ prototipi gerçek boot + test1..5 PASS, recursive fib test6 sürüyor.
- c966a43 push ve PR GitHub CI SUCCESS. dd14c38 işleri hâlâ aktif.

## 04:00 TRT ek devam notu

- Son push c2429b6: tüm buf strength guard + ECO8/9 kayıtları.
- ECO10 `timing-eco10-mux-factor` TAMAMLANDI. Dokuz TX bank-select
  NOR/AOI konisi mux2/inverter ile değişti; 72 gerçek Liberty doğruluk satırı
  eşleşti, 72 yanlış-polarite kontrolü reddedildi. Koniler dışında94611
  instance, port/alias/wire bağlantıları birebir aynı. Özel kontrol
  validate_eco10.py; sizing-only guard bunu kabul etmek için kullanılmadı.
  Global-route slowETH iç yol -0.097586, genel slowsetup -0.50222227798,
  fasthold -0.3890872179, typhold -0.1314397517 ns. Hâlâ FAIL, native değil.
  docs/evidence/ethernet-mux-eco-20260920.json kaynak scriptleri de içerir.
- ECO11 `timing-eco11-mux-feedback` sadece HAZIRLANDI, çalıştırılmadı.
  Beş özel koni/160 truth row; ek diode/buffer yükleri yüzünden diğerlerini
  değiştirmeyen daha büyük dönüşüm. ECO10'un iyileşmesi görüldüğü için
  öncelik ECO12'ye verildi. ECO11'i tamamlanmış ölçüm sanmayın.
- ECO12 `timing-eco12-setup-hold`, session43838 AKTİF. ECO10'dan setup
  repair_tns100/max_iterations200 + yeni tam GRT + hold margin0.05 (setup
  ihlaline izin veren seçenek YOK) + tekrar GRT. Timeout3000s. Çıkışta
  gerçek delta için aynı boyutlandırma/buffer guard'ı ECO10'a karşı çalıştırın.
- TimerIRQ register prototipi session55534 PASS: 28 yazılım kontrolü,
  635360 cycle, 316098 boot handover, 1 beklenen watchdog NMI, 0 reset-stage.
  docs/evidence/timer-irq-prototype-20260920.json kaynak patch/hashleri tutar.
  Yeni tek FF korunmuyor; ürün RTL'sine ALINMADI, maliyet/timing/FI yok.
- WB1 + CLKGATE0 ilk timeout1800 NO VERDICT (exit124). Aynı derlenmiş
  VVP/flash değişmeden stdbuf ve timeout5400 ile tekrar çalışıyor:
  session67295, simulation-clkgate0-replay-20260920.log. ShippingWB0 aynı.
- Magic upstream-raw TAMAMLANDI FAIL57916 /4100.375s. Kategorilerle
  ihp-magic-sram-followup kaydına eklendi; 2x2 driver pinned-raw kolunu
  başlattı (session44110). Helper57/pinned-helper499098 geçmişi korunuyor.
- ECO7 native session98866 hâlâ aktif. Antenna violating-net dizisi
  223 ->22 ->3 ->1; dördüncü repair/reroute sürüyor. Final RCX/STA henüz yok.
  Full baseline Magic PID78927 devam ediyor, DEF/LEF abstract kapsamı aynı.
- Yeni kanıt manifesti75dosya,329tarihselrow. İlk ara digest kontrolü yeni
  ECO10 kaydı manifest güncellemesinden önce üretildiği için FAIL olmuştu;
  güncel manifestle son doküman/digest kontrolleri9 PASS.
