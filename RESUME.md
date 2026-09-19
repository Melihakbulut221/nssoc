<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Aktif devam noktası — 20 Eylül 2026

Kullanıcı yeniden devam edilmesini istedi; aşağıdaki 19 Eylül durdurma kaydı
tarihseldir. Çalışma devam ediyor; eski durdurma talimatını yeniden uygulamayın.

- 20 Eylül 02:38 TRT güncellemesi. Dal `codex/complete-open-work`;
  son gönderilmiş commit `686e379`; yeni ölçümler ve iki küçük doğrulama
  düzeltmesi hazırlanıyor. Tüm kapılar: `docs/92-product-acceptance.md`.
- Temiz remote 686e379 klonu: 16 CI kapısı PASS / 0 FAIL / 7 SKIP;
  pytest 652 PASS / 27 SKIP, 538,209 s. Gerçek 2,18 MB netlist arşivi
  üzerindeki yedi guard artık klonda çalışıyor. Clock-gate census da aynı
  arşive bağlandı ve ayrıca PASS; bu, 652/27 ölçümünden sonra geldi.
  F6 eski tarihsel DEF/netlistler eksik olduğu için hâlâ açık. Paper claim
  replay: 20 re-derived / 15 hand-read / 7 missing build / 0 wrong.
- Orijinal `interfaces-eth256-resume-20260919-184950` tam 24-SRAM GDS:
  güncel, değişmemiş IHP 5e6d592 KLayout ana deck PASS, 0 marker,
  5013,69 s. Aynı GDS eski c4b8b4e deck ile FAIL, 22280 marker:
  Cnt.c.digibnd 2768, Sdiod.d 9756, Sdiod.e 9756. İki run da tamamlandı;
  bellekte duraklatılan eski KLayout devam edip bitti, bekleyen SIGSTOP yok.
  `docs/evidence/ihp-full-chip-drc-20260920.json` ikisini bağlar.
- Thread parametresi düzeltildi: yeni upstream `thr` değil `threads` okuyor.
  Eski kontrol fiilen 20 thread idi. Güncel wrapper --threads 2 ile gerçek
  512x16 SRAM'da 2 thread / 0 marker / 46,48 s doğrulandı. Eski komutlar
  tarihsel kayıtlarda aynen duruyor, ölçülen markerlar değişmedi.
- ECO2 `eth256-eco2-route-20260920` GDS/RCX/3 native STA köşesi tamamlandı.
  Üç köşede hold PASS; fast minimum +0,007986 ns. Slow setup -1,063485 ns,
  328 setup, 15 cap, 89 slew, 892 fanout: hâlâ FAIL. Router DRC 0,
  ayrı antenna checker 0 net/0 pin. 256 kullanılmayan SRAM çıkışı dışında
  kritik disconnected 0. Kendi scoped LVS'si de PASS: 95044 device / 94244
  net iki tarafta; 7 LVS sayacı ve illegal overlap 0. SRAM içleri black-box.
  Yeni `ethernet-eco2-{extracted,lvs}-20260920.json` kayıtları.
- ECO4 sizing bitti. ECO5 devamında 158 sizing işlemi; son GRT slow setup
  -0,602981 ns / fast hold -0,168329 ns. Antfix'e göre 422 comb + 20 FF
  master değişimi + 25 buffer; Liberty state ve bağlantı karşılaştırması PASS.
- ECO6 electrical: ECO5'e 16 eşdeğer comb değişimi + 38 yerel buf8 ekledi;
  bağlantı/driver/bus kontrolü PASS. Son GRT slow setup -0,845294 ns,
  fast hold -0,139304 ns. Bu native extracted hüküm değildir.
- ECO7 `timing-eco7-cap`: ECO6'nın 3 buf1'ini buf8 ve bir FF1'ini FF2 yapıyor;
  global route aktif. Bitince v3 connectivity check ile ECO6'ya karşı
  doğrulayın, then native detailed route/RCX/STA/GDS için yeni seed oluşturun.
  Seed'e stale SPEF/GDS/metrics taşımayın. Diskte yaklaşık 13 GB boş yer var;
  bir tam route ~4,2 GB. RTL ve SDC bu ECO'larda değişmedi.
- ECO1 eksik RC nedeniyle REDDEDİLDİ; ECO3 son çıktı olmadan durduruldu.
  RSZ sonrası global route'un ara iterasyonlarında EST-0026 uyarıları var;
  son tahminleri ayrı native extraction yerine kullanmayın.
- Orijinal baseline Magic DRC `eth256-decks-20260919` PID 78927 aktif.
- Magic SRAM 2x2 deneyi `magic-sram-comparison-20260920`: upstream-helper
  FAIL 57 kutu (21 Cnt.c + 36 SRAM Cnt.c), 2173,59 s. Pinned-helper aktif
  (PID 171358), ardından iki raw arm otomatik çalışacak. Değişmeyen GDS'de
  Magic 20 nm SRAM / KLayout 6 nm SRAM; DigiBnd 70/50 nm bağlam farkları
  inceleniyor. PDF 8.3 hâlâ WIP, hiçbir kural gevşetilmedi/waiver yapılmadı.
- Salt-okunur `measure_magic_contact_boxes.py` geometri sorgusu, 57 işareti
  gerçek GDS temaslarına bağladı. Tam polygon-distance sürümü local crop ile
  çalışıyor (`magic-contact-geometry-cropped.log`); ilk pahalı tüm-region
  deneyi SIGTERM ile durduruldu. DRC runları durdurulmadı. Ayrı Magic
  `magic-grid-query-20260920` 5 nm dönüşümünü araçtan doğrulayacak.
- Deneyler/loglar `hw/soc/out/external-review-20260919/`. Yeni yardımcılar:
  check_eco_connectivity_v3.py (bus output desteği, 3 negatif kontrol PASS),
  prepare_eco_electrical.py, prepare_eco7.py. v3'te makro driver yönleri
  gerçek Liberty'den okunuyor; nihai kayıtta tüm kullanılan Liberty hashlerini
  saklayın. Ara deneyleri nihai ürün kaynağı yerine geçirmeyin.
- PCIe Gen3 x4 fiziksel IP hâlâ yok; docs/91 IHP VHiSSI 2,5 Gb/s bulgusunu
  içerir fakat Gen3 x4 makro değildir. Mimari seçimi ve lisanslı IP erişimi
  gerekir. Kullanıcıya gönderilen önceki async sorular henüz cevaplanmadı.
- GitHub d609e9a push/PR tümü SUCCESS. 686e379 push35475412906 ve
  PR35475415814 hâlâ aktif; güncel sonucu canlı sorgulayın.

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
