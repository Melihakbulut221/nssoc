<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Aktif devam noktası — 20 Eylül 2026

Kullanıcı yeniden devam edilmesini istedi; aşağıdaki 19 Eylül durdurma kaydı
tarihseldir. Çalışma devam ediyor; eski durdurma talimatını yeniden uygulamayın.

- 20 Eylül 02:12 TRT güncellemesi. Dal `codex/complete-open-work`;
  son gönderilmiş kaynak `d609e9a`. Netlist arşivi/F6 yükleyicisi hazırlanıyor.
- Tam kontrol listesi `docs/92-product-acceptance.md`; F6 ve ürün kapıları açık.
- Orijinal 24 makrolu baseline: `interfaces-eth256-resume-20260919-184950`.
  Çıkarılmış timing FAIL; bağımsız LVS PASS (SRAM içleri black-box), XOR 0.
  Kayıtlar `docs/evidence/ethernet-{extracted-layout,lvs}-20260920.json`.
- ECO2 `eth256-eco2-route-20260920`: native RCX ve ayrı süreçlerde STA bitti.
  Üç köşede hold PASS; fast minimum +0,0080 ns. Slow setup -1,0635 ns,
  328 setup, 15 cap ve 89 slew ihlali: hâlâ FAIL. Stage 14 Magic streamout
  sürüyor; GDS/deck tamamlandı demeyin. Kendi final artifactlarıyla kaydedin.
- `timing-eco4-wns` tamamlandı: 200 sizing işlemi, GRT slow setup -0,848798 ns.
  Antfix kaynağına göre 306 comb + 20 FF master değişimi ve 25 buffer.
  Bağlantı/Liberty state karşılaştırması ve iki negatif kontrol PASS.
  `timing-eco5-wns` ECO4'ten devam ediyor: repair_tns=0, max_iterations=400,
  sizing-only. Global-route tahmini extracted signoff değildir.
- ECO1 eksik RC nedeniyle REDDEDİLDİ; ECO3 sınırsız outer-loop nedeniyle
  durduruldu, son çıktı yok. Bu adayların iyimser ölçümlerini kullanmayın.
- Orijinal baseline Magic DRC `eth256-decks-20260919` aktif (PID 78927).
- Aynı baseline yeni kilitli IHP KLayout deck'i ile full-chip:
  `hw/soc/out/external-review-20260919/full-upstream-drc-20260920`, PID 124084.
  Eski pinned deck KLayout PID 94783 RAM/swap için SIGSTOP ile BEKLİYOR.
  `sequence_drc_memory.py` watcher'ı (log `drc-memory-sequencing.log`)
  yeni deck bitince eskiyi SIGCONT ile devam ettirecek; watcher durumunu izleyin.
  PID'ler yeniden açılışta geçersiz olabilir; süreç kimliğini kontrol edin.
- Magic SRAM 2x2 deneyi `magic-sram-comparison-20260920`: yeni/eski deck,
  resmi read_sram_gds flatten helper'ı açık/kapalı. İlk upstream-helper arm
  aktif; henüz sonuç yok. Kurulu PDK değişmedi, hiçbir hücre dışlanmadı.
- Dört çıplak SRAM yeni kilitli KLayout deck'iyle 0 marker. Bu tam SoC PASS
  değildir. `docs/93`, kilitli downloader ve fail-closed DRC wrapper GitHub'da.
- F6: 2,185,152-byte tam gerçek baseline netlist arşivi + hash/kaynak/lisans
  kaydı eklendi. Yedi mevcut TMR graph testi snapshot-only denemede PASS.
  Yeni loader/manifest/doc/evidence/DRC testleri 182 PASS. Gerçek temiz klon
  sayısı henüz ölçülmedi. Eski signoff-6x2 / s70-rom0-syn çıktıları eksik;
  yeni netlist bu tarihsel kanıtların yerine geçirilemez.
- Temiz d609e9a local CI: 16 PASS / 0 FAIL / 7 SKIP, tree-dirty=0.
  Yeni kaynak değişiklikleri için commit sonrası temiz klon CI çalıştırın.
- PCIe Gen3 x4 fiziksel IP hâlâ yok. docs/91 ek IHP VHiSSI araştırması
  2,5 Gb/s SerDes gösteriyor; Gen3 x4 makro değil. Mimari seçim bekleniyor.
- Run logları ve deney scriptleri `hw/soc/out/external-review-20260919/`.
  `record_extracted_layout.py` gibi eski generator'ları körlemesine yeniden
  çalıştırmayın; zenginleştirilmiş kanıtı ezebilirler.

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
