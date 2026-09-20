<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Aktif devam noktası — 20 Eylül 2026

Kullanıcı çalışmaya devam edilmesini ve incelemedeki her maddenin kapanmasını
istedi. Alttaki eski durdurma kaydı tarihseldir; yeni bir durdurma isteği yok.

## 20 Eylül 13:51 TRT — fallback tamam

Yeni entry0/length0 RTL89062/19904 ikisi de TAMAM/PASS: 28 kontrol, cause4,
ikincil imaj1, UART framing0, flashviol0, scrub0/0/0; normal/syn/fallback
ROMmanifestleri aynı. `logicrom-startup-clear-fallback-20260920.json` eklendi.
NativeGL26557 sürüyor; son50kcycle RAMsweep bilinir. Disk2.1GiB; yeni fiziksel
başlangıçtan önce eski salt-okunur geometrinin reversiblearşivlenmesi gerekiyor.
84a049d iki hostedrunPASS; ba9297a push/PR henüzrunning. Bootfix+kanıtları
commit/push yap, PRgövdesini actualGLFAIL+fixpending olarak yenile.

## 20 Eylül 13:43 TRT — düzeltme doğrulaması

Yeni normalRTL78147 TAMAM **28checksPASS**, yeniROM3084bytes. Synthesis67566
TAMAM:69441cells9391FF1080737.6076µm²stdcells,20macro; bootmanifestRTLileaynı.
**Yeni native4stateGL26557** `logicrom-startup-clear-gl` nativecellgatePASS,
compile0,fullrunaktif. Benchprogress artık PCcrash+RAMSEC/DED sayaçlarınıbasıyor;
10k'başlangıçsayaçX bekleniyor, 100k'dan sonra clear→0 veCPUbilinirliği izle.
**Fallback RTL89062/19904**, `logicrom-startup-clear-entry0`/`...-length0`
çalışıyor; manifest/28checks/rejection/secondaryimage şartlarınısonuçtadoğrula.

Eski130kdebug45540 TAMAM: 90kUARTpollknown;100kCPUcrashbusX,df/sleep/txX,
UART113framing1. Liberty-derived model25239 aynı100kXfailure; aynıişi1M'e
uzatmamak içinnedenkaydıile sonlandırıldı (`functional-model-diagnostic-stop.json`).
`logicrom-functional-model-control-20260920.json` kanıtınıekledim. Bu kontrolnative
modelPASSdeğil. Başlangıçsayaçlarının100cycleXolduğu kısa32225kontrolüdekanıtta.

ECO8 TAMAM: 2delaycellCLKleaf structuralPASS; **tüm3köşesetup/hold/electrical
estimatePASS**, slowsetup+.026116,fastminhold+.023359. **Yeni bootclearROM'unaait
değil**; ayrıntılıroute/RCX de yok. `logicrom-eco8-global-20260920.json`.
YeniROMiçinfizikselkoşu başlatılmadı;GLöncekihatanoktasınıaşınca yapılandır.
Eski initialseed `state/logicrom-irq-20260920.json` yalnıznl+emptymetrics;
yeniseedi yeni `logicrom-startup-clear-syn/soc_top.netlist.v`ileoluştur.

YeniHEDEFtests107PASS/5beklenenabsent-artifactSKIP; normalRTL28PASS.
SPDX475tagged366covered0missing0wrong (sonrakanıtsayısıarttı). Dosyalarhenüz
commitdeğil; docs68datedcorrection,docs95/92,boot.c,GLbenchprogress,kanıtlar,
ledger/indexveRESUME. Yeni kanıtlarınızba9297a'dansonra; commit/push/PRgüncelle.
Magic32138hâlâaktif~2h50/6hbound. Disk~2.5GiB; arşivlerdeeskiODB/DEF
restoreyollarıvar; nativeyönlendirmemakrolarıveaktifdosyalaraynıduruyor.

## 20 Eylül 13:36 TRT — kritik yeni boot bulgusu ve düzeltme

Son push **ba9297a** (native-cell gate ve corner araçları). Temiz remote clone:
**849 PASS / 26 SKIP**, frontdoor16/0/7, gerçek ledger/evidence eklendi.
Sonradan eklenen kanıtlar ve `hw/soc/tb/sw/boot.c` düzeltmesi henüz commit değil.

**Boot:** İlk native Icarus tam koşusu `logicrom-whole-gl2` TAMAM/FAIL,
5500.19 s, 1Mcycle: UART113,framing1,checks0,magic0. `inputs_unchanged=true`.
`logicrom-whole-gl-failure-20260920.json` ve docs92/95 düzeltmesi eklendi.
Canonical Icarus31541 aynı113 karakter/framing1/140kcycle duruşunu tekrar etti;
aynı işi uzatmamak için yalnız model sonlandırıldı (`native-boot-duplicate-stop.json`),
sonuç terminated/false; önceki tam FAIL korunuyor.

- **Tanı45540** `logicrom-icarus-boot-stop-diagnostic`: 130k sınır/3600s;
  aynı eski netlist/flash, rawPC/alerts/sleep/UART/flash sayaçlarını her10kbasar.
  90kCPU UARTpoll,ilk113karaktersonuframing1; 100kçıktısını al.
- **Kısa kontrol32225 tamam:** `logicrom-icarus-startup-counters`, ilk100cycle
  `cnt[0]/cnt[2]=000X`, diğer4counter0. RAM SEC/DED startup X ile zehirleniyor.
  `soc_scrub.v` if-event RTL X optimism yorumunun mappedmodelde geçerli
  olmadığını gösteriyor. `boot.c` eski kodu bu sayaçları okuyup print edip
  ancak sonra clear ediyordu; şüpheliCPUbozulmanoktası tam bu okumalar.
- **Düzeltme:** boot.c güç-açılışında (`cnt==0`) RAM kaynaklarına SCR_CLR
  write'ını koşulsuz yapar; önce sayaçları okumaz. Warm boot (`cnt>0`) kayıtları,
  ROM sayaçları ve scrub enable aynı. Yeni UART metni "boot: cleared RAM
  startup scrub record". Eski docs68loglarını silme; datedcorrection ekle.
- **RTL78147** `logicrom-startup-clear-rtl`: logicROM, RDREG/REQ_REG/RF_SYNPRE/
  WAKE_GNT1, çalışıyor; loader3084bytes üretti. Bu yeni fixedROM için
  **synthesis67566** `logicrom-startup-clear-syn` başladı (SOC_ETH_SRAM1,
  RAMsram, hardenedmem/ROM). İkisi bitince yeni kalıcı GL runner ile
  eşleşen iki klasörü kullan, eski ROM'a ait netlist/layout'u aktarma.
- **İzole model kontrolü25239** `logicrom-liberty-functional-control2`:
  aynı eski netlist/flash/nativeSRAM, stdcell işlevleri pinnedLiberty'den
  Yosys read_liberty/write_verilog ile; ICG statetable'literal latch_posedge
  ayrıdiagnosticmodel. İlkcontrol ICGeksik compileFAILkorundu. Bu kontrol
  native-cell kabul değil, model/sentez farkını ayırıyor. 60kprogress.
  Yanlışlıkla bu sonucu ürün/nativePASS sayma.

**Fiziksel (eski fixed loader + yeni IRQ):**
- ECO2(+75buf),ECO3(+17buf),ECO4(+4buf/35size,setupkötüleşti),ECO5
  (+4buf/126eşdeğermaster) structuralPASS; kanıtlarıdocs/evidence'e eklendi.
- ECO6 `logicrom-eco6-buffering`: +47positivebuf,70comb+2seqeşdeğersize;
  slowsetup−.152243,fasthold+.023361. 3slowrepairpass (buffering,size,buffering),
  removed/cloned/pinswap0, kaynakstate/pinLibexactPASS. Kanıt eklendi.
- ECO7 `logicrom-eco7-margin`: +18buf/36combsize, **tüm3köşeelectrical0**,
  slowsetup−.152243; yalnız2SRAMTXreadcaptureendpoint `_122875_`,`_122876_`
  negatif. Kanıt eklendi. NativeDRT/RCX yok.
- **ECO8 session97904 tamam**, `logicrom-eco8-capture-clock`: yalnız bu2FFCLK
  girişine birer dlygate4sd1, unchangedclockperiod/SDC. Structural/3corner
  **session49450** sonuçlarınıal. OldROMimage'dir; yeni bootclear ROM'una
  sonuçlar aktarılamaz. Önce bootdüzeltmesini doğrula; sonra yeniRTLlayout.

**Alan:** ~2.5GiB, yalnızbuworkspace içinde reversiblearchiveyapıldı.
- `inactive-verilator-build-cache-20260920.tar.gz`: 3bitmişcompile generatedC++/
  object/cache, SHA doğrulanıprawkaldırıldı; executables/inputs/logs/resultsaynı.
- `completed-clean-clone-workspaces-20260920.tar.gz`: 10eski tamamlanmış
  generatedclone,15200fileSHA/symlink doğrulandı; primarycheckout ve84/ba son2clone,
  dıştaki logs/XML/results kaldı. Manifest aynıbase'de.
- `old-estimate-geometry-[0-4]-20260920.tar.gz`: eski globalestimateECO2,4–17,
  19–21 ODB/DEF dosyaları SHA doğrulanarak arşive taşındı. ECO18/ECO22 native
  geometry, netlists, scripts, reports, constraints ve tümaktifgirdiler kaldı.
  **docs/evidence/local-geometry-archive-20260920.json** orijinalpath/hash/restore
  komutunu içerir. Eski bir ODB/DEF'e ihtiyaç varsa arşivden önce geri yükle.
  İlkarchivepreparation emptyfailedECO13dizininde assertoldu, hiçbirfiletaşımadı;
  retry yalnızproof/log/ODBolan bitmişdizinleri aldı. Archiveadaylarıactivefddeğil.

Magic32138 hâlâçalışıyor (10:54/6hbound, nativehalooldRTL). Henüzverdict yok.
Yeni sourceguard/model/parser/ECOcontrols74PASS, yeni evidencechecks65PASS/5skip.
Arşivindex yeni dosyalarla tekrarüret; git diffcheck/SPDX/frozenkontrol; RTLboot
ve yeniGL sonuçlarına göre commit/push/PRbodygüncelle. İş sürüyor; bırakma.

## 20 Eylül 13:11 TRT — yeni tasarım ve simülatör uyumluluğu

Son push `84a049d`; temiz GitHub klonu 831 PASS / 26 SKIP, kapılar
16 PASS / 0 FAIL / 7 SKIP. `fresh-clone-84a049d-20260920.json` ve gerçek
ledger satırı eklendi. Çalışma sürüyor; kullanıcı durdurma istemedi.

- Native yeni ROM+IRQ GRT tamam: `logicrom-irq-grt-20260920`, 36. adım,
  7845 s. Ayrıntılı route/RCX henüz yok. Eski ECO22 sonucu bu tasarıma ait değil.
- `logicrom-eco1-fanout2`: 712 fanout ihlali, 2611 pozitif tamponla sıfırlandı.
  97608 özgün hücre/9391 FF korunur, exact structural PASS; +61586.1792 µm².
  Üç bağımsız köşede slow setup -0.771703 ns; slew/cap FAIL devam.
- `logicrom-eco2-electrical`: 61 SRAM giriş tamponu +14 çıkış offload,
  native GRT tamam. Structural ve ayrı köşeler session45919;
  `validate_logicrom_eco2.py`, `logicrom-eco2-corners/result.json` kontrol et.
- ECO27 eski RTL: 33 yeni hücre/21 eşdeğer değişim structural PASS.
  **İlk olumlu yakalanmış-env raporu geçersiz kabul:** tam etkin ECO env ve
  seçilmiş STA köşesiyle slow setup -0.114930 ns, fast hold +0.001602 ns;
  slew2/cap1/fanout0. `eco27-exact-environment-reports` esas ölçüm;
  iki rapor da korunuyor. Timing PASS değil.
- Sabit tek route segmenti üzerinde multi/single corner farkı ve yedi
  gerçek IHP hücreli küçük kontrol tamam; generated-clock farkı var,
  ordinary path aynı. Upstream kök neden/waiver iddiası yok.
  Kalıcı `probe_generated_clock_corners.py`, `report_route_corners.py`,
  13 parser/path negatif kontrolü; evidence kaydı eklendi.
- **Verilator 5.051 native model uyumsuz:** `dfrbpq` modelindeki $recrem
  delayed_RESET_B C++ tarafında rastgele başlangıçta kalıyor; tek hücrede
  async reset yeniden uygulama FAIL, aynı model/stimulus Icarus13 PASS.
  Tam native model değiştirilmedi. `native-cell-canonical-{iverilog,verilator}`
  kontrolleri bunu doğrular. sim_logic_boot_gl artık full compile öncesi
  bu gate'i zorunlu tutar. 5 negatif/mock kontrol eklendi.
- Verilator koşuları (prototype25080,canonical17431,diagnostic14885)
  kalanları neden kaydıyla sonlandırıldı: `verilator-incompatible-model-stop.json`.
  Timeout/terminated sonuçlar PASS değil; rastgele sabit CPU/UART0 teşhis.
- Asıl Icarus73417 `logicrom-whole-gl2` 11:46 başlangıç/7200s sınır,
  buffered log henüz verdict yok. Yeni kalıcı **Icarus31541**
  `logicrom-gl-canonical-iverilog` 13:08 civarı, native-cell PASS, fullcompile0,
  unbuffered ilerleme 10k; 1Mcycle/14400s sınır. Preload yok. FullPASS bekleniyor.
- Magic32138 `halo-recovered-magic2-20260920` 10:54 başlangıç/6h sınır,
  hâlâ verdict yok; eski RTL halo geometrisi. Sonucu actualmarker parser ile doğrula.
- Son hedefli kontroller74 PASS; SPDX475 tagged355 covered/0missing0wrong;
  eski frozenpilot diff empty. Evidence index110+329 tarihsel kayıt.
- Disk ~2GiB. Completed hardlinkler değiştirilemez; yeni nativefullroute öncesi
  alan kontrolü yap. `completed-verilator-pch-20260920.tar.gz` SHA doğrulanmış
  yalnız derleme cache arşivi; aktif veya tek kanıt dosyası silinmedi.

## 20 Eylül 12:31 TRT — teslimat kontrolü ve eş geometri teşhisi

Boottool+negativecontrols+docs/evidence/ECOchecks212PASS, SPDX472tagged350covered,
0missing0wrong; frozenpilotdiffempty. Icarus100cycleactualcontrol compile0,
run1EXPECTED, resultpassedfalse/inputhashunchanged; hiçbirROM/RAMpreloadyok.
CanonicalVerilator17431 compile0 (~225s), 50kcycleprogress; 1Mcycle/1800s/run
limits, seeds1/29. FullPASSyok. PrototypeVerilator25080veIcarus73417aktif.

Single-slowECO26globalestimate−.535962setup/.034039hold, multi−1.239417
setup. Veri yolu tümraporsatırları aynı; forwardedcaptureclockarrivalfarklı.
Bu henüztoolbugkanıtıdeğil: ikiGRT farklıyenidenrouteyaptı. Şimdi5581
probe_fixed_routes.py, eco26-fixed-route-corners: ONEglobalroutesegmentfile
exported, multireportslow/fast/typ/slow, sonrafresh3singlecornerreadsegments.
Aynıyerleşim/routes/libvalues/SDC ilefarkıayırır; waiver/deckdeğişikliğiyok.
CPUilerlemeyi flash.frames/opcodeve160bitcrashbusile1000cyclesgösteren
ayrıdiagnosticsession48838; normalacceptancedeğil.
Newlogicphysical39327 PostGRTsetup~900+last-gasp,TNSazalıyor,WNS−2.26;
Magic32138halaaktif. D93hostedrtl/checksPASS,formal-and-bootnormal/fallback
adımıaktif (statussnapshotd93-hosted-status-1227.json). Alan~2GiB.

## 20 Eylül 12:28 TRT — aktif işler ve kalıcı gate boot aracı

Son push ad0bcc8; PR1 body pr-body-drc-progress.md ile güncellendi.
Önceki12:17başlığı elle yazılmış saat hatasıdır (fiilen12:13civarı yazıldı);
"PostGRT optimizer bitti" ifadesi de erken yorumdu: optimizer hâlâçalışıyor.

- Yeni kalıcı hw/soc/flow/sim_logic_boot_gl.py +tb_soc_logic_boot_gl.v+
  test_logic_boot_gl.py: aynıloader/manifest/generatedRTL kontrolü,20SRAM
  profilekontrolü,ELFstatusadreskontrolü,ROM/RAMpreloadyok,28check+UART+
  watchdog+exit+flashcheck. Icarus>=13required;Verilator ayrı2-statecontrol.
  --prepare-only gerçekinputsPASS,unit24PASS. Bu dosyalarhenüzcommitdeğil.
  CanonicalVerilatorsession17431 (logicrom-gl-canonical-verilator),compile
  sürüyor; two seed1/29,1800s/run. Icarus100cyclesexpectedFAILcontrol
  session56774. Ana4stateprototype73417 logicrom-whole-gl2devam7200sbound.
  PrototypeVerilator25080 logicrom-whole-verilator seed1aktif (compile140s).
  HiçbirfullGLbootPASSsonucuhenüzyok. Yeniunit+delivery82729bekleniyor.
- ECO23nativeTAMAM10813:0routeDRC/0critical,245antennanets270pinsFAIL,
  slowsetup−.0022915004nsFAIL; allholdPASS. record_eco23.py çalıştı.
- ECO26TAMAM23003 timing-eco26-macro-leaves2:41macroinputleaf+3offloadbuf,
  20statelessdelay+3buffersize;64newcells1473.2928µm²; structuralPASS.
  fast/typ/slow slew8/4/2,cap1fanout0; slowsetup−1.239417,fasthold−.346552.
  İlkdeneme mevcutGMIIlastdriverbufdeğildlygateolduğuiçinexportöncesiFAIL;
  retryexplicitpositivebuf/dlygatefamiliesdoğrulanır. record_eco26.pyçalıştı.
  Yerelmacrobufslewiyileşti,GMII2delayfastyiholdiyileştiripslowsetupbozdu.
- TahminiGMIIclockarrivalcornerdeğerleridikkatçekti: ECO26freshsingle-slow
  compare session35614 eco26-single-slow-estimate2. İlkprobe49845yalnız
  LibertycornerfiltreleyipRCcornerlistesinifiltrelemediğiiçinFAILED; retry
  _LAYER_RC_/_VIA_R_ aynıslowdeğerlerifiltreleyipyenidenindexliyor. Original
  dosyalarvekanıtlaraynı. Henüzestimatorbugkanıtıyok,waiveryok.
- NewROMIRQ39327 setupoptimizer600limitsonrasılast-gasppolish~900iter,
  worst−2.26; postexport/state_outyok. NativeDRTbaşlamadı. Üçcornerfresh
  STAsonragerçeknativeDRT/RCXgerekir. Boyut/clockconstraintsdeğişmedi.
- HaloMagic32138~95dk,6hbound,verdictbekleniyor.
- Disk~2.2GiB. Completedruns52file2.91GBlogicalshare,thencompletedECO23
  19file1.46GBlogicalshare,contents/pathsame. Bothrecordsdedupscriptvar.
  Activeinputsdeğiştirilmez;completedhardlinksimmutable.
- Newdocs92/95,evidenceECO23/ECO26+index105vekalıcıboottooluncommitted.
  Testsonuçlarınıal,actualgatecontrolüdoğrula,commit/push/PRrefresh.
  Ürün/PCIe/vendorSRAM/fizikselfinal/beam/F6kapılarıhâlâaçık.

## 20 Eylül 12:17 TRT — tamamlanan ölçümler ve aktif işler

Son push d93e64d. Temiz remote d93 TAMAM:818PASS26SKIP,16/0/7gates;
record_fresh_d93e64d.py çalıştı, kanıt/ledger eklendi. Hosted d93/0a hâlâ
in_progress (12:12 kontrolü); 7dd push/PR SUCCESS.

- ECO22 mainDRC TAMAM: process0, gerçekXML0marker,5520.114737s,
  pinnedunchangeddeck+inputhashPASS. record_eco22_drc.py çalıştı.
- ECO24 TAMAM:166buf8 eklendi,97330originalkorundu,3915.4752µm²delta.
  all3fanout0; electrical/timingFAIL, freshglobalestimateonly. docsrecordvar.
- ECO25 TAMAM:38positivebuffersize+2buf8,alloriginal97496korundu,
  area645.9264µm²; fast/typ/slow slew41/16/10,cap3/fanout0;
  fastsetup3.380961/hold−.308853,typsetup2.183183/hold−.001729,
  slowsetup−.117318/hold.191368ns. NativeclosureYOK. İlkvalidatorarea
  unchangedSRAMmasterLibertydeyokdiyehata; validate_eco25_retry.py
  yalnızchanged+newstandardcellareailePASS. Eskierror/scriptkorundu.
  record_eco25.py çalıştı; tekrarlamayın. Kalanpinlerviolating-drivers.tsv.
- FullmappedlogicROMboot session73417/devam; outputlogicrom-whole-gl2.
  Bufferedstdoutboşolmasıtakılmadeğil. Ayrı5000cycleprobe~94s/5000cycle;
  beklenen kısa-boundFAIL (firmwarebitmedi). Startup100cycleprobeaynı.
  Asıl7200swallboundmuhtemelenkısa; PASSyok, nativeuninitializedRAM.
- YeniROM+IRQ39327 PostGRT optimizer bitti, reGRT0overflow; sonexport
  bekleniyor. Sonrasında actual3cornerfreshSTA (statemergedstale değil).
- ECO23jumper10813 DRTbitti; 245antenna-net sürüyor,CheckAntennasactual
  kaydıvar; RCX başladı. Nativeelectricalraporbeklenir, antennaclosureFAIL.
- HaloMagic32138~80dk; sonucuyok, timeout6h. Baseline~4.5h.
- Disk1.2GiB: session28835 dedup_completed_runs.py tümFlowcomplete+final
  metricsruns'tabirebiraynıimmutablelargefileshashleyipshareediyor;
  active3tag açıkçaexcluded. Dosya/yol/bytekorunur. İşlemsonucu
  completed-runs-shared-20260920.json; completedhardlinksyerindedüzenlenmez.
- Yeni3+1evidence/docs/ledgerhenüzcommitdeğil; --write-evidence/test/push
  bekliyor. Frozenpilotdeğişmedi. Ürünkapılarınınhepsikapandıiddiasıyok.

## 20 Eylül 11:49 TRT — yeni fiziksel aday ve tüm-SoC gate boot aktif

Son gönderilmiş d93e64d, GitHubbranch/PR1 güncel; PRbody pr-body-pinned-lvs.md.
Freshd93session78779 aktif, run_fresh_d93e64d.py; sonraki kaydı gerçekXML'den
üretin. 0a temizklon816PASS26SKIP zaten commitd93 içinde. Hosted d93 ve0a
sonuçları henüz alınmadı;7ddpush/PR ikisiSUCCESS doğrulandı.

- Yeni ECO24 session93175, run_eco24_retry.py; çıktıBASE/timing-eco24-antenna-
  branches2. Kaynak ECO22native01DetailedRouting ODB/NL, tüm550antennadio
  korunur. 43 ölçülenfanoutnetine166pozitifbuf8eklendi, <=4yük/dal ağaç.
  Yalnız yeniin-memoryadaydaki95399signalwire kaldırıldı, PGspecialwires
  korunur; freshGRT/3cornerestimate. Orijinaldeğişmedi, henüzPASSyok.
  İlk deneme session49515 FAILED: OpenROAD insert_buffer isme sayısuffix
  ekler; exactrequestednameassertion patladı. Orijinalout/scriptkorundu.
  Yeni deneme inserteddriver'ı gerçekmovednetten bulur vebuf8masterıdoğrular.
  Sonrasında check_physical_eco.py ileaynıorijinalmantık/diodes+166bufkontrolü
  yapılacak; substitutions={} beklenir. Orijinalgirişnetsmapping/portskorunmalı.
- Yeni gerçek fullSoCgateboot session73417: BASE/run_logicrom_whole_gl2.py,
  logicrom-whole-gl2. Komut/inputhash/loader manifest inputs.json'da.
  Gerçek canonicalmapped69971cellnetlist ve aynınormalflash0.hex kullanıyor.
  ROM/RAMpreloadyok (yalnızhariciflashreadmemh); dörtRAMmacrobaştaX.
  Bench gerçekRAMmacroportundandatayıokur;checks28,fails0,exitmagic,UARTPASS,
  framing0,flashviol0,watchdog1/0/0,noalert/noDFbekler. Compile0vvpaktif;
  stdoutbuffered olduğundan run.log başta0byte; süreç~100%CPU. İki saat
  wallbound/1Mcyclebound. İlkprepareolmayan2Pmodeladıylahata; yeni2klasör
  doğruideal2Pikihelperi alır. Canonicalkaynakhenüzdeğişmedi, testprototype.
  GateblockPASSönceki ayrıölçüm, bufullSoC ölçümühenüzbaşarılısaymayın.
- LogicROM+IRQphysical session39327, taglogicrom-irq-grt-20260920 artık
 36-openroad-resizertimingpostgrt (önceki34tahminiyanlış). Önceki GRT0overflow,
 repair+antenna90diode/237jumper sonrası yenidenroute/timingrepair. Tamam
 olunca tekcornereskiSTAmetriclerini almadan üçcornerfreshraporhazırla;
 kendi nativeDRT/RCX adayı gerekiyor. Diskpreflightönemli (~3GiB).
- ECO23session10813:4jumperonlyiterationsaynı245net/270pinantenna.
 Unchangedmax8iterationbırakıldı; route0DRCamaantennaPASSyok.
- ECO22independentDRC31454 ~90dk/10GBRSS, Angle45kuralları, henüzXMLyok.
 HaloMagic32138 ~55dk, öncekibaseline4.5h; henüzverdict yok.
- Her şey yalnıznnsoc altında. Aktifrunları/lockedPDK/decks'i değiştirmeyin.
 Completedhardlinkedartifacts yerindedüzenlenmez. EksikPCIeIP,pads,DFT,debug,
 physicalclock,beam veF6artifaktlar hâlâaçık; bitmişürüniddiasıyok.

## 20 Eylül 11:38 TRT — doğrulanmış devam noktası

Son gönderilmiş commit0a79a3b09ad0374947829fff2100bb10711eac89, PR1 body
pr-body-lvs-audit.md. Aşağıdaki ek hazırlık/kanıt henüz commit değil.

- 7dd103d GitHubpush35497437243 vePR35497438504 tümjobs SUCCESS, boot/fallback
  dahil. 0a79a3b hostedpush35499417152/PR35499419473 en son RUNNING.
- Freshremote0a79a3b TAMAM:842total816PASS26SKIP,16/0/7gates,659.907sCI.
  record_fresh_0a79a3b.py çalıştı, docs/evidence JSON veledgerrow eklendi;
  tekrar çalıştırmayın. session67735DONE. Sonraki yeniwrapper kaynaklarını
  bu revizyonun testiylesaymayın; ayrı202PASS5SKIPtargetedlog var.
- Yeni kalıcı prepare_ihp_lvs.py ve53dosyalı ihp-lvs.lock.json sharedDRC
  downloader kullanır. Gerçekcache53/53hashPASS; locked-preparation.log.
  test_ihp_drc_preparation.py iki gerçeklockcheck eklendi. İnceleme hedefli
  lvs-repro-delivery-tests.log202PASS5SKIP, SPDX469/344/0/0.
- sram-lvs-reader-controls-20260920.json yeni: özgünIHPinvGDS+vendorCDL
  unmodifiedupstreamLVS+auditorPASS; disposableCDL'denNMOSsilmeFAIL.
  WLDRV dörtetiket8/2, unchangeddeckyalnız8/25okur. AYRIcopieddeckte
  yalnızMetal1text8/2uniondenemesi pinlerigetirdi, hâlâstrictFAIL.
  Pin-pairs A/A,VDD!/VDD,VSS!/VSS,Z/Z hepsiMatch fakatflag_missing_portsFAIL.
  OrijinalPDK/GDS/CDL/upstreamcachedeğişmedi. Bu DEĞİŞTİRİLMİŞokuyucu
  sadece teşhis; unmodifieddecksPASSsaymayın. IHPissue239OPENaynısorunları
  ve2025pinlayerbulgusunu içeriyor; yayınlanmışçözümkodu yok.
- docs92/93 yeniölçümlerle güncellendi. Artefactindexson98, yeni0afresh
  kaydından sonra tekrar --write-evidence gerekir. Source/deliverystaged
  değil. Commit/push/PRrefresh bekliyor.
- AKTİF39327 logicrom-irq-grt: globalroute0overflow,967547usage/5891045
  capacity;33RepairDesignPostGRT ve ardından34ResizerTimingPostGRT. AraSTA
  corner.tcl yalnızilkfastcorner'ıyeniler; statejsonslow/typ değerleri
  eski prePNR olabilir, yeni3cornerPASSiddiaetmeyin. Sonrasında bağımsız
  üçcorneraynıODBraporuvegerçeknativeDRT/RCXgerekli.
- AKTİF10813ECO23jumper: ilkDRT0routeDRC,245antenna-net/270pinviol; ilk
  -jumper_onlyonarımısonrareroute. Antenna/electricalverdict henüzyok.
- AKTİF31454ECO22mainDRC: Acute/offgridkuralları,~75dk.32138haloMagic:
  DEF/LEFabstractcheck~45dk,öncekiaynıkapsam4.5saat. İkisininsonucubekliyor.
- Baselinecompleted yalnız7birebiraynıdosyada hardlinkdedup:script
  dedup_completed_baseline.py, recordbaseline-completed-dedup-20260920.json.
  CommittedevidenceSHA+finalstate+FAILverdictkorundu. Disk3.6GiBcivarı.
  Tamamlanmışdosyaları yerindedeğiştirmeyin. Başka projeye dokunulmadı.

## 20 Eylül 11:24 TRT — SRAM iç LVS teşhisi ve teslim kontrolü

Bu kayıt önceki notları günceller. Son gönderilmiş kaynak 7dd103d; bu notla
birlikte ek doğrulama commit'i hazırlanıyor. Kullanıcı durdurma istemedi.

- Yeni `sram-transistor-lvs-20260920.json`: 9 kontrollü ölçüm, 92 çıktı/girdi
  hash'i. İki tam-makro deep FAIL; iki flat 1200s timeout, NO VERDICT.
  Dummy minimum repro FAIL; DFPQD izole deep/flat bağlantı farkıyla FAIL.
  WLDRV izole iki modda 4MOS/circuit Match ama strict pin verdict FAIL;
  GDS top ports yok. Tam makro deep2NMOSeksikliği bağlam/hiyerarşi bağımlı.
  Hiçbir model/rule/pin waiver yok. KLayout CLI0.30.9/Python0.30.10 ayrımı var.
  run_sram-leaf-* session67598 tamamlandı. Auditor gerçek7raporureddetti.
- İlk leaf hazırlığı nestedCDL assertion'ında durdu; yeni repro2 bağımlı
  subckt'leri verbatim içeriyor. Tüm ölçümler ayrı dizinlerde; önceki hata
  saklandı. Upstream PR1121 OPEN, lvsres LVS mapping hâlâ yapılmamış.
- 191PASS/5SKIP hedefli test: lvs-delivery-tests.log. İlk yanlış yazılan
  test_artifact_digests.py invocation hiçbir test koşmadı; doğru dosya
  test_artefact_digests.py. SPDX468tag/341path/0missing/0wrong.
  Frozen hw/rtl,hw/tb,hw/openlane,tt origin/main karşısında değişmedi.
- docs92/93/95, ROM fallback/bundleprovenance, fresh7dd/ECO22LVS/halo kanıtları
  güncel. Artefact index97kanıt+329historical. Commit sonrası GitHub PRbody
  güncellenmeli. 7dd checks+rtl PASS; formal-and-boot ROM/fallback sürüyor.
  6e9180a push35496401002/PR35496402427 artık ikisiSUCCESS.
- AKTİF EDA:39327logicROM+IRQpostCTSsonrasıSTA;10813ECO23jumperDRT;
  31454ECO22DRCoffgridkuralları;32138haloMagic. Hiçbiri yeni finalverdict değil.
  Disk3.8GiB. Mevcut tamamlanmış dosyaları yerinde değiştirmeyin/hardlink.
- Sonraki: commit/push vePRupdate; fiziksel tamamlananları hash/metrics/log
  ile kaydet. Yeni logicROM+IRQ GRT sonrası kendi routing/RCX ve electrical
  kapanışını yürüt. Eski ECO22sonuçları ona uygulanmaz. PCIe/PDK/pads/DFT/
  debug/clock veF6historicalaçıkları hâlâ gerçekaçıklar.

## 20 Eylül 11:05 TRT — ROM gönderildi, fiziksel kontroller sürüyor

Bu bölüm önceki 10:40 notunun üzerindedir. Son gönderilmiş commit 7dd103d;
PR1 açıklaması pr-body-logicrom.md ile güncellendi. Kullanıcı durdurma istemedi.

- 7dd103d temiz REMOTE klon all CI tamamlandı: 825 toplam,799PASS/26SKIP;
  16 kapı PASS/0FAIL/7SKIP. fresh-clone-7dd103d-20260920.json ve gerçek
  ledger satırı hazır fakat henüz commit edilmedi. record_fresh_7dd103d.py
  çalıştı; tekrar çalıştırmayın. 7dd GitHub run35497437243 checks+rtl PASS,
  formal-and-boot en son sürüyordu; PR run35497438504 ayrıca izlenmeli.
- Kalıcı ROM entry0 ve length0 fallback ikisi de gerçek CPU'da PASS28,
  aynı loader manifesti. Normal RDREG1, fallbackler RDREG0. İlgili kanıt
  güncellendi, henüz yeni commit yok. Firmware fallback session13304 bitti.
- ECO22 LVS tamamlandı:97334device/96507net iki tarafta; 7 mismatch+illegal
  overlap sıfır. ethernet-eco22-lvs-20260920.json hazır. SRAM içleri blackbox.
  DRC session31454 hâlâ çalışıyor, 10:20 başladı; run_eco22_drc.py ve
  eco22-upstream-drc-20260920. Kendi XOR zaten commit7dd içinde PASS0.
- Halo recovery/finalize TAMAMLANDI: routeDRC0,antenna0,criticaldisconnect0;
  93459 orijinal hücre+1075antenna korunuyor. 256 kullanılmayan SRAM çıkışı
  raw disconnected; critical0. halo-routing-recovery-20260920.json hazır.
  Native son state halo-recovered-finalize-20260920/09-odb-cellfrequencytables.
- İlk halo Magic denemesi DRC başlamadan framework required gds yüzünden
  başarısız. Kendi Magic.StreamOut'u halo-recovered-stream-20260920 altında
  tamamlandı. Şimdi halo-recovered-magic2-20260920 aktif, session32138;
  run_recovered_halo_magic2.py, gerçek kendi GDS'si ve DEF/LEF DRC modu.
  Önceki orijinal aynı kapsam Magic4.5saat sürdü; henüz yeni verdict yok.
- Yeni IRQ+logicROM physical session39327: logicrom-irq-grt-20260920,
  run_logicrom_physical.py, 6işçi, post-GRT'ye kadar. Post-CTS bounded
  setup repair sürüyor; baştaWNS-6.050,10iter-4.709. Bunlar nihai timing değil.
- ECO23 session10813: eth256-eco23-jumper-20260920, run_eco23_jumper.py.
  Aynı ECO22 pre-route seed+aynı limits, tek değişiklik jumper-only antenna
  repair. STAPostPNR'ye kadar native; GDS aşaması yok. İlk DRT sürüyor.
- SRAM gerçek transistor LVS yeni ölçümü: sram256-transistor-lvs-pinned
  ve sram256-transistor-lvs-upstream deep modda ikisiFAIL;process0 aldatıcı.
  Her ikisi24Match/4Mismatch/3NoMatch/1Skipped(top). 3NoMatch hücre:
  RSC_CDLYX1_DUMMY (CDL LVSRES vs extracted metal1 resistor),
  RSC_DFPQD_MSAFFX2P (4PMOS connection mismatch), RSC_WLDRVX8 (2NMOS eksik).
  inspect_sram_lvs_mismatches.py ve sram256-lvs-deep-mismatches.json teşhisi
  tutuyor. Vendor/CDL/deck değiştirilmedi; no-waiver. Flat kontrolları
  session71392(upstream) ve78954(pinned) hâlâ sürüyor,20dk/6GiB sınırları var.
  Upstream5e6d592 53LVS dosyası git-blob+SHA256 ile indirildi:
  hw/soc/tools/ihp-lvs-5e6d592; lock BASE/ihp-lvs-upstream.lock.json.
- Yeni henüz commit edilmemiş kalıcı guard hw/soc/flow/audit_klayout_lvs.py
  (opsiyonel klayout Python gerekir) ve sw/tests/test_klayout_lvs_audit.py:
  17PASS, gerçek iki deep rapordaFAIL/exit1. Süreç dönüş kodu dışında
  karşılaştırma database+strict deck verdict'i okur. Genel extraction
  doğruluğunu/kural-yeterliliğini iddia etmez. Flat sonuçlarını da audit edin.
- Disk ~3.9GiB. Yalnız tamamlanmış kayıtlı run dosyalarındaki birebir
  kopyalar hardlink yapıldı; yollar/içerikler korunuyor. Yeni dedup kayıtları:
  completed-stage,eco22-lvs-final,halo-finalized,halo-stream,eco2-eco7-stage.
  Tamamlanmış çıktıları yerinde değiştirmeyin. Eski/aktif dosya silinmedi.
- Generated config-recovered-halo-magic-20260920.json yalnız bu projenin
  .git/info/exclude'una eklendi; kaynak dosyası değil, ölçüm girdisi.
- Sonraki: dört transistor-LVS sonucu/audit/kanıt, ROM/fresh/ECO22LVS/halo
  notlarını docs92/93/95'e ekle; artefact_digests --write-evidence;
  hedefli test+SPDX+frozen diff; commit/push. Aktif EDA işleri sürmeli.

## 20 Eylül 10:40 TRT — kalıcı ROM entegrasyonu

Bu not en yeni devam noktasıdır; aşağıdaki eski notlardaki RUNNING/PID/session
bilgilerini güncel süreç olarak kullanmayın. Son gönderilmiş commit 6e9180a.

- İnternet ve GitHub erişimi çalışıyor. 82ab25c push/PR CI başarılı;
  6e9180a push/PR işleri 35496401002 / 35496402427 en son sorguda sürüyordu.
- Kalıcı logic-ROM kaynak entegrasyonu hazır: docs/95 ve
  logic-boot-rom-integration-20260920.json. 151 ilgili +72 fiziksel kaynak
  testi, RTL tam CPU 28 kontrol, native-cell ROM 4113 okuma/17 yazma reddi
  PASS. Sentez 69971 hücre/9391 FF/1079801.1882um²; 4 RAM+16 ETH SRAM,
  ROM SRAM yok. Varsayılan legacy tarihsel profile dokunmaz.
- İlk PNR lint denemesi 17 gerçek parser hatası içeriyordu; process0 sonucu
  kabul edilmedi. prepare_interfaces.py artık kaynak başına dil seçiyor;
  lint2 hata checker dahil PASS0error/0latch,1139warning. Vendor/frozen
  kaynaklar değişmedi. PNR config config-interfaces-logicrom.json.
- Yeni native yerleştirme session39327: run_logicrom_physical.py,
  tag logicrom-irq-grt-20260920, 6 işçi. Yosys.JsonHeader'dan post-GRT
  resizer'a; doğrulanmış synth netlisti seed. Henüz layout/timing PASS yok.
- CPU geometry fallback session13304, run_logic_rom_fallbacks.py: entry0,
  sonra length0; normal koşu zaten PASS. Tamamlanınca JSON/log/manifest
  kimliklerini entegrasyon kanıtına ekleyin. Aynı testler CI'de de logic-ROM.
- Halo devam session68039, run_halo_continuation.py, ayrı
  halo-route-continuation klasörü. Orijinal sekiz antenna iterasyonu
  korunuyor; yeni son durum tamamlanmadan Magic sonucunu varsaymayın.
  Sonraki native adımlar Odb.RemoveRoutingObstructions→Odb.CellFrequencyTables,
  ardından aynı kapsam Magic.DRC. Eski prepare_halo_magic.py eski eksik native
  state'i bekler; yeni tamamlanmış state'e uyarlamadan kullanmayın.
- ECO22 XOR tamamlandı PASS0. record_eco22_xor.py ve final dedup çalıştırıldı;
  12 dosya/1.32GB birebir hardlink paylaşıldı. Tamamlanmış hardlink çıktıları
  yerinde düzenlemeyin. Kendi DRC session31454, LVS session50247 aktif.
  DRC 5e6d592 kilitli main/deep/2thread; output eco22-upstream-drc-20260920.
  LVS henüz son karşılaştırmayı bekliyor (97334device/96507net iki tarafta).
- Disk ~4GB; yeni büyük native/GDS işi öncesi bitmiş LVS final kopyalarını
  doğrulanmış byte-identical stage dosyalarıyla paylaşın. Aktif iş/snapshot,
  tarihsel dosya veya diğer projelere dokunmayın.
- ECO22 elektrik ihlalleri gerçek ve açık. eco22-fanout-attribution.json:
  43 fanout ihlalinde son route antenna yükleri var. Sonraki deney aynı
  pre-route seed'de jumper-only antenna repair olabilir; henüz başlatılmadı.
- Tüm betikler hw/soc/out/external-review-20260919 altında. Mevcut record
  üreticilerini körlemesine yeniden çalıştırmayın. Docs92 tüm kapıları tutar.


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

## 04:40 TRT ek devam notu

- ECO7 native tamamlandı: route DRC0, bağımsız antenna0; üç köşe holdPASS,
  slowsetup -0.5292779698ns /109ihlal. Slow slew30/cap10/fanout881 açık.
  docs/evidence/ethernet-eco7-extracted-20260920.json; yeni geometry için
  bağımsız DRC/XOR/LVS henüz yok. Exact post-route bağlantı kontrolü PASS.
- ECO12/13/14 tamamlandı. 35 testli guard artık pozitif stateless dlygate'i
  gerçek Liberty işlevi/state/pin ile kontrol ediyor. ECO13 1489clockbuffer
  ile fanout843->101; ECO14 165buffer ile fanout/cap0 ama slowsetup
  -2.2517917057ns geriledi. Yeni küçük tamponlar kritik yolu yavaşlatıyor.
  ECO15 timing-eco15-buffer-strength session34170 AKTİF: sadece ECO14'ün
  yeni buf1/buf4 hücrelerini buf8 yapıp tam GRT; çıkışta aynı guard gerekir.
- Ethernet gerçek CPU/GMII loopback GL probe session69172/PID222300 AKTİF:
  ethernet-gate-probe/gl-run.log. ECO13 NL, 50MHz core/125MHz GMII,
  8frame/2171payloadbyte, CRC/FIFOwrap/IRQ. Timeout2400; henüz verdict yok.
- Magic SRAM 2x2 tamamlandı: pinned-raw557149FAIL; upstream-raw57916FAIL,
  upstream-helper57FAIL,pinned-helper499098FAIL. Kayıt tüm kolları içeriyor.
  Full baseline Magic PID78927 hâlâ aktif (DEF/LEFabstract, GDSmacro değil).
- WB1+CLKGATE0 replay mtime0/test15FAIL, yalnız VVP212210 SIGTERM ile
  durduruldu; rootcause bulunmadı, shippingWB0 değişmedi. İlgili timer
  prototip kaydı güncel; NOVERDICT timeout ile FAIL ayrımı korunuyor.
- Disk ~6.5GB boş; yeni full native flow öncesi alan kontrolü yapın.

## 2026-09-20 04:54 TRT — yeni ölçüm noktası

- GitHub push803614b tamamlandı. c2429b6 hosted push/PR PASS;
  53ad0cb ve803614b hosted jobs son kontrolde hâlâ aktif.
- Full baseline Magic TAMAMLANDI:642FAIL,436LEFfootprintiçinde206dışarıda,
  dışarıdakilerin tamamı<=0.5um. Yeni ihp-magic-full-chip-20260920.json
  raporun tamamını/koordinatları ve exactinputları içeriyor. Sonraki aynı
  historicalKLayout tekrarı PID226046 SIGTERM ile durduruldu; ana flowFAIL
  beklenen sonuç. Bu invocationtamamengreen değil. Başka Magicjob kalmadı.
- ECO15 TAMAMLANDI,156equivbufupsizes,guardPASS. Slowsetup-.2921467595,
  fasthold-.1445643646;fanout/cap0,slew53/30/30. Native extraction değil.
- ECO16 timing-eco16-corner-repair/session32665/PID225999 AKTİF.
  Source15,slowcommandcorner setup +fastcommandcorner hold;3000stimeout.
  Ara optimizer değeri finaldeğil. Çıkışta validation_sizing_candidate.py
  değil: validate_sizing_candidate.py timing-eco16-corner-repair kullanın.
- Gerçek EthernetCPU RTLprobe175253cyclePASS,signature00043b07,
  8frame/2171byte/8CRC,allalarms0. GL session69172/PID222300 halen AKTİF,
  gl-run.log boş (yalnız sonuçta yazıyor),timeout2400s başlangıç~04:26.
  Timeout olursa NO VERDICT olarak saklayın; başarısız protokol diye yazmayın.
- Kalıcı hw/soc/flow/ethernet_cpu_probe.py +firmware+GMII monitor eklendi.
  Üretilen GL/RTL benchbytes orijinalprototypeileaynı. Reproducer-v3 gerçek
  RTL175253cycleaynısonuç,ROMbinarygateileaynı.19negative/positiveunitPASS.
  docs/evidence/ethernet-cpu-loopback-20260920.json RTLtam,GLpending.
- İlk SPDXdenetimi yenimonitorunApachetaginireddetti; CERN-OHL-W-2.0
  yapıldı ve450tagged/319pathcovered/0missing/0wrong. Verilogmonitorheaderi
  generatedbench'tençıkarıldığı için testbenchbyteshiçdeğişmedi; sourcehash
  geçmişi kayıtta açıklanıyor. 179ilgili testPASS, manifestyenidenrefreshgerekir.
- Disk6.1GB; başka projenin dosyasına dokunmadan bir yeni native run için
  alanı kontrol edin. YeniMagicraporu routehaloalanprojeksiyonu20336.064um²/
  layer; HALO GERÇEKLENMEDİ, pinaccessdelikleri ve reroute+Magichenüz yok.

## 2026-09-20 05:33 TRT — CPU test tamamlandı, ECO18 yeniden yönlendiriliyor

- Son push df0c190. Gerçek Ethernet GL session69172 tamamlandı PASS:
  175252 cycle, RTL175253; aynı 23 functional field,8frame/2171byte/8CRC,
  signature00043b07,window292..173456. Zero-delay, FI/SDF/PHY değil.
  evidence/ethernet-cpu-loopback-20260920.json artık her iki sonucu içeriyor.
- Fresh remote df0c190 replay707PASS26SKIP, CI16PASS0FAIL7SKIP.
  Authentic ledger row02:03Z df0c190 korundu;35guard+19probe kapsamı.
  Sonraki43guard ayrı: primary input driver sayımı ve inout ret kontrolü.
- ECO16 final slowsetup-1.975127ns/fast hold-.327806ns: seçilmedi.
  ECO17 üç RX enable delay->buf1, ECO18 iki buf1->buf8; exactguardPASS.
  ECO18 GRT slowsetup-.188810ns, fasthold-.327806ns,cap/fanout0,
  slew47/28/29. Native sonuç değildir; record tüm köşe/hashleri içeriyor.
- İlk native18 tag eth256-eco18-route-20260920 FAIL90s/exit2:
  DRT-0222 hold24736/X net24735; netin tek OUTPUT terminali,0BTerm,
  6eski guide var. Eski run/seed korunuyor. prune_orphan_guides.tcl11testPASS,
  yalnız6guide temizlendi; Verilog+DEF before/after SHA256 birebir aynı.
- YENİ native session70998/PID239069 AKTİF, tag
  eth256-eco18-clean-route-20260920. Driver: BASE/run_eco18_clean_native.py,
  log/supervisor aynı tag altında BASE'de. Kaynak ECO18 NL/PNL/SDC aynı;
  ODB timing-eco18-clean-guides/soc_top.odb. İş pinaccess aşamasında.
  Minimum boşdisk768MiB, başlangıç5.78GB; başka fullnative paralel başlatma.
  BASE=hw/soc/out/external-review-20260919. Yeni extracted/DRC sonuçları
  yokken ECO7yi en son TAMAMLANMIŞ native olarak tutun.
- Magic baseline642FAIL ve 4 SRAM comparison FAIL önceki nottaki gibi;
  aktif Magic kalmadı. PDN geometry attribution probe henüz tamamlanmadı.
  odb.dbWireShapeItr bu bindingde yok; yarım scripti sonuç saymayın.
- Hosted803614b pushPASS;PR ve df0c190 push/PR son okumada sürüyordu.
  Frozen dosyalara dokunulmadı. Kullanıcı tüm maddeler için devam istiyor.

## 2026-09-20 05:43 TRT — GitHub ve F7 halo hazırlığı

- Push5df16f8 tamamlandı; PR1 body GLPASS/fresh707/43guard/guidecleanup11
  ile güncellendi. İlgili233testPASS; SPDX452tagged0wrong;31TTmanifestOK,
  git diff origin/main -- hw/rtl hw/tb hw/openlane tt boş.
- ECO18clean native session70998 devam: detailed route iteration1.
  Erken iteration violation sayılarını finalDRC saymayın; supervisor disk
  sınırını izliyor. Son tamamlanmış native hâlâECO7.
- F7 saltokunur attribution tamam:206outside markerın tümü aynıkatman
  signalroute geometryilemesafe0;PGdeğil. BASE/attribute_magic_routes.py,
  magic-route-attribution.json. Standardcellpins/LEFobs dahil değil,
  tekbaşına DRCsebep ispatı değil. dbWirePathItr/dbITermShapeItr çalışıyor;
  dbTransform.apply PythonRect ile bu bindingde çalışmadı, kullanma.
- Yeni hw/soc/flow/macro_route_halo.py +17geometrytestPASS. Orijinal
  baseline07postGRT ODB'den24macro içinM2/M3/M4 .6umoutside ring, .45um
  signalpin corridor clearance üretir. 2766obs;M2area17407.428um²,
  M3/M4each20336.064um². Before/afterNLbyteeşit; DEFyalnızBLOCKAGESfarklı.
  TekrarüretimODBsha32420646... birebir. Yerleşim/hücre/bağlantı aynı.
- Halo BASE/macro-halo-baseline/grt session27713/PID242724 AKTİF,
  timeout1800,4thread,ilk50extraGRTiterasyonu deneniyor. Kaynakbaseline,
  ECO18değil. Macrohaloorijinal206markerden178full23partial5nonegeometric
  overlap;5nonepinchannels. Magicsonucuyok,436insidehedefdeğil.
- Yeni docs/evidence/ihp-routing-halo-20260920.json hazırlanmış sonuçları
  saklar; aktiftimingloglarınıfinalsaymaz. ROADMAP/docs92 güncel.
  Yeni halo source/evidence henüz commit edilmedi; digestrefresh+check gerekir.

## 2026-09-20 06:01 TRT — halo native ve kaynak CI sürüyor

- Push5675eea tamamlandı. Yeni halo tool17tests, ilgili231testPASS,
  SPDX454tagged0wrong. PR1 haloGRT/native +df0PR/803hostedPASS ile güncel.
- HaloGRT session27713 TAMAMLANDI exit0:5m49s,93112routednets,overflow0,
  NLsha d30fdb18...before/afteraynı93459cell. Slowsetup-2.045908ns,
  fasthold-.151081ns GRTtahmini;timingkapanmadı. Record güncellendi.
- Halo native session11114/PIDsupervisorJSONdan okunabilir AKTİF,
  tag eth256-halo-route-20260920,DRT_THREADS4. SonadımOdb.CellFrequencyTables
  (fillsonrası10), extraction/GDSyok. AyrıMagicsonra. Diskstop1536MiB.
  BASE/run_halo_native.py; pnrcfg config-fpeth256-halo-20260920.json.
- Nativehalo bittiğinde BASE/prepare_halo_magic.py hazır (HENÜZÇALIŞMADI).
  Nativeexit0/routeDRC0/criticaldisconnected0 ister; yeniMagicseed/config
  oluşturur, SYN_NETLISTactualstateNLdenalır (10stepklasöründeNLyok!).
  Sonra BASE/run_halo_magic.py; Magic.DRCtekadım,DEF/LEFabstractaynıdeck.
  Process exit0 DRCpassdeğil: magiccountayrıcaokunmalı.
- ECO18 session70998 sürüyor,3.iterasyona geçti. Bittiğinde exactcellguard
  BASE/check_postroute_connectivity.py iletiming-eco18-rx-enable-drive NL
  karşısonNLçalıştır, eco18-postroute-connectivity.jsonüret. Sonra
  BASE/record_eco18_extracted.pyhazır;nativefinal16olmaksızınçalıştırma.
- Diskkorumaiçin YALNIZtamamlanmışECO7/ECO2finalkopyaları aynırunstep
  dosyalarınaSHAeşitliksonrasıhardlinkyapıldı. 12+12dosya,2.61GBkazanıldı;
  bütünpathlervebyteskorundu. BASE/eco7-final-dedup.json/eco2-final-dedup.json.
  Bu tamamlanmış çıktıları yerinde EDİTETME; yenitagkullan. Aktifrundokunulmadı.
- Freshremote5675eea sourceCI session37828 AKTİF. İlkclonebitmedenerken
  CIbaşlatmaexit127, hiçtestçalışmadı; premature-startlog+correctionJSONkorundu.
  Cloneexit0+HEAD5675eea doğrulanınca doğruçalışmabaşlatıldı; ...-ci.log/XML.
  Önceki707/26 sonucu buna ait değil; yeni sonuçbekleniyor.
- IHPissue1024liveOPEN (2026-06-26updated),794CLOSED(2026-04-20updated)
  saltokunurghsnapshotlarıBASE'de. 1024KLayout6nm/Magic20nmfarkınıbildiriyor;
  794remainingcontactsdispositionıiçeriyor, waive değil. docs93'eekleniyor.

## 2026-09-20 06:07 TRT — kaynak doğrulaması tamam

- `89b4a38` GitHub'a gönderildi. Temiz `5675eea` klonu, session37828:
  exit 0; 743 PASS, 26 SKIP, toplam 769 test, 568.991 saniye. CI: 16/0/7.
  Gerçek 03:05Z ledger satırı kopyalandı; kayıt:
  `docs/evidence/fresh-clone-5675eea-20260920.json`. Klon tamamlanmadan
  yapılan ilk başlatmada test çalışmadı; exit127 ve düzeltme kaydı saklanıyor.
- Halo aracının 17 testi bu temiz klonun kapsamına dahil. Global-route
  sonrası 93.459 hücreli netlistin SHA'sı `d30fdb18...` ile aynı; hiçbir
  hücre, port veya alias değişmedi. Halo native akışı ilk DRT iterasyonunda;
  ECO18 ise ilk anten onarımı sonrasında yeniden yönlendiriliyor.
- `BASE/prepare_eco18_physical_checks.py` hazır, henüz çalıştırılmadı.
  ECO18 native akışı exit0 ve final16 durumunu ürettikten sonra aynı aday
  için ayrı XOR ve scoped LVS sürücüleri hazırlar. Sürücüler yalnız kendi
  process-group'larını durdurur; iki saatlik süre ve 1024 MiB boş disk
  sınırı vardır. Başlamak için 2048 MiB gerekir. SRAM içleri yine black-box
  kapsamındadır. Halo Magic hazırlığı ayrı `prepare_halo_magic.py` dosyasında.

## 2026-09-20 06:17 TRT — CI bağımlılığı ve devam noktası

- `8db1db6` GitHub'a gönderildi. README'deki eski üç-atlama cümlesi
  tarihsel olarak işaretlendi; 5675eea temiz klonunun 743/26 ve 16/0/7
  kayıtlarına bağlandı. Yeni Tcl testleri için `checks.yml` açıkça `tcl`
  kuruyor: apt paket incelemesinde Yosys yalnız `libtcl8.6` gerektiriyor.
  Workflow YAML parse kontrolü ve 118 ilgili test PASS; SPDX 0 eksik/yanlış.
  Bu küçük bağımlılık değişikliği tam suite'in yeni bir ölçümü sayılmıyor.
- ECO18 native ikinci anten-onarım döngüsünde. Antenna net sayıları
  247 -> 28; yeni final sonuç henüz yok. Halo native ilk DRT iterasyonunda.
  Her ikisinin sürücü/log/session bilgileri önceki devam notlarında.
- Fiziksel sonuçlar gelince önce exact post-route bağlantı kontrolü ve
  native üç-köşe kaydı; ardından aynı aday için XOR/LVS. Halo native
  tamamlandıktan sonra ayrı Magic ölçümü. Başka eski adayın DRC veya timing
  sonucunu yeni adaya taşımayın. Her hazırlık script'i henüz çalışmamışsa
  kayıt bunu söylüyor; hazırlık, sonuç değildir.

## 2026-09-20 06:24 TRT — kalıcı rota-kılavuzu düzeltmesi

- `interface_flow.py` artık gelecek `Interfaces` çağrılarında DRT için
  `read_current_odb` sonrasına `prune_orphan_guides.tcl` ekliyor. Özgün
  LibreLane script'inin geri kalanı byte-identical. Eksik/çift anchor
  reddediliyor; Tcl metakarakterli helper yolu gerçek tclsh ile doğrulandı.
  `test_interface_flow.py` ve `test_orphan_guides.py`: toplam 16 PASS.
  Gerçek kurulu LibreLane template denetimi de PASS; log BASE altında.
- İlk ad hoc karşılaştırma bir ek newline'ı silmediği için assertion
  verdi; karşılaştırma iki tam ek satırı çıkaracak şekilde düzeltildi.
  Akış kodunda bu nedenle değişiklik yapılmadı; düzeltme evidence kaydında.
- O sırada çalışan ECO18-clean ve halo süreçleri bu hook eklenmeden önce
  başlamıştı. Mevcut `COMMANDS` dosyaları orijinal LibreLane `drt.tcl`
  yolunu gösterir; bu akışları yeni hook çalışmış gibi raporlamayın.
- Son değişiklikler henüz commit edilmedi: interface_flow.py, yeni test,
  docs90 ve clock-repair evidence. Manifest refresh ve ilgili kontroller
  gerekir. Son başarılı push bilgisi `git log`/remote'dan doğrulanmalı.

## 2026-09-20 06:45 TRT — ECO18 native bitti, bağımsız kontroller sürüyor

- Önceki 06:24 değişiklikleri `e68f93d` olarak GitHub'a gönderilmişti.
  ECO18-clean native exit0, 4410.31 saniye. `ethernet-eco18-extracted` kaydı
  oluşturuldu: slow setup -0.785313/4, fast hold -0.039599/4; elektriksel
  ihlaller sürüyor. Route/antenna/critical-disconnected 0. Exact guard:
  96584 özgün hücre aynı, +562 anten +251774 filler/decap. 10 GMII portunun
  max/min budget'ları üç köşede PASS. Ürün kapanışı değildir.
- Yeni kalıcı araç `hw/soc/flow/check_postroute_connectivity.py`, 20 yeni
  test ve gerçek ECO18 replay PASS. Boyutlandırma kontrolleriyle toplam63.
  Yeni script verdict dosyasını overwrite etmez. Henüz bu checkpoint'in
  değişiklikleri commit edilmedi; git durumunu kontrol edin.
- BASE/eco18-final-dedup.json: 12 final kopyası aynı-run stage dosyalarına
  byte-identical hardlink oldu; 1318843222 byte paylaşılır. Dosya yolu ve
  SHA değişmedi. Tamamlanmış çıktıları yerinde değiştirmeyin.
- Aktif ECO18 bağımsız işler: XOR session12160, LVS session40919, güncel
  IHP main-deck DRC session46578. BASE/run_eco18_{xor,lvs,drc}.py sürücüler;
  log/supervisor adları eth256-eco18-{xor,lvs,drc}-20260920. DRC asıl çıktısı
  `hw/soc/out/eco18-upstream-drc-20260920`, iki thread; tüm ana kurallar,
  önerilenler kapalı, hash-kilitli upstream deck. Henüz verdict yok.
- Halo native session11114: ilk optimizasyon iterasyonunda, dört thread.
  Bitince daha önce hazırlanan prepare_halo_magic.py -> run_halo_magic.py.
  Route DRC0 olmadan Magic hazırlığı çalışmaz. Yeni sonuçları baseline
  642 ile aynı deck/scope'ta karşılaştırın; 436 makro-içi kutu ayrı sorun.
- ECO19 (46 sizing) +ECO20 (5 sizing) structural PASS; clock-repair evidence
  içine record_eco19_20.py ile eklendi. ECO20 slow GRT -0.061945ns, fast
  GRT hold -0.330479ns (GMII output; native çıktılar farklı). Yerel tahmin,
  native kapanış değil. Alan farkları +529.81/-18.15um2.
- ECO21 `timing-eco21-rx-slew`, session82295 halen GRT'de. İstenen12
  değişikliğin üçü olmayan master (_o21ai_2/_nand3_2/_a22oi_2) yüzünden
  STA-0119 uyarısıyla atlandı; script durmamış. Özgün log/isteği koruyun,
  gerçek delta9 olmalı; validatorla ölçün, 12 yapılmış demeyin. Bu üç
  sürücüde slew düzeltildi sayılmamalı. Sonraki hazırlıklarda master
  bulunabilirliği açıkça doğrulanmalı. Native aday henüz seçilmedi.
- PR gövdesi 743/26 temiz klon ve yeni STA sonucuyla güncellendi. e68f93d
  hosted push/PR son bakışta devam ediyordu; son SHA yeşil demeyin.

## 2026-09-20 07:01 TRT — XOR/LVS tamam, ECO22 native başladı

- `cfa6c2e` GitHub'a gönderildi. Gerçek temiz remote klon HEAD
  `cfa6c2ea56d1a5299149d50d1ae55359504bb8a6`: 794 total, 768 PASS,
  26 SKIP, 545.622s; CI16/0/7. `record_fresh_cfa6c2e.py` çalıştı,
  evidence ve gerçek ledger satırı eklendi. session1032 exit0 tamamlandı.
- ECO18 XOR session12160 exit0; metric0 ve bağımsız XML items0.
  `ethernet-eco18-xor-20260920.json` oluşturuldu. Scoped LVS session40919
  exit0, 97150 device/96311net, 7 LVS+illegal-overlap0. SRAM içleri
  black-box. `ethernet-eco18-lvs-20260920.json` oluşturuldu. Bağımsız
  updated main-deck DRC session46578 halen çalışıyor; klasör
  `hw/soc/out/eco18-upstream-drc-20260920`, iki thread. Gate sonucu henüz yok.
- ECO21 GRT tamam: actual9 sizing PASS, üç olmayan master uyarısı kayıtta.
  GRT slow -0.067914ns, fast hold -0.330479ns. `record_eco21.py` çalıştı.
- ECO22 `timing-eco22-antenna-headroom`: 74 driverda196 pozitifbuf8,
  <=3 load/branch. 71 antenna-fanout neti +3 zayıf gate, hiçbir diode
  kaldırılmadı/limit gevşetilmedi. 96584 özgün hücre değişmedi; native
  aday96780cell. Structural guardPASS. GRT slow -0.173740ns, fast hold
  -0.329420ns, fast1cap ve slewFAIL. Alan+4623.09um2. `record_eco22.py`
  çalıştı; branch-repairs.tsv ve route-inputs.json yerelBASE altında.
- ECO22 native AKTİF session62541, `run_eco22_native.py`, tag
  `eth256-eco22-route-20260920`, DRT12 thread. Yeni guide-cleanup hook
  gerçekten çalıştı: logda REMOVED_ORPHAN_GUIDES6. DRT→KLayout.Render;
  supervisor kendi PG'sini free<768MiB veya6h halinde durdurur. Başlangıç
  preflight4800MiB; yeterli alan sağlandı. Sonuç gelince yeni postrouteguard
  (çıkış dosyası exclusive-create), native3corner record, yeniDRC/XOR/LVS.
- Halo native session11114 ikinci optimizasyon iterasyonunda. Sonra
  prepare_halo_magic.py→run_halo_magic.py; henüz çalıştırılmadı.
- Veri kaybı olmadan tamamlanmış final duplicate paylaşımı: ECO18XOR ve
  ECO18LVS için12şer dosya/1318843222byte; ayrıca baseline native,
  ECO2LVS ve eskiKLayout finalinde37dosya/3933909447byte. Kayıtlar
  `eco18-{xor,lvs}-final-dedup.json`, `completed-checks-final-dedup.json`.
  Her yol veSHA256 aynı. Sadece listelenen tamamlanmış runlar; başka
  proje/aktifçıktı yok. Şu an yaklaşık7GiB boş; immutable çıktıları
  yerinde değiştirmeyin (hardlink). Önceki tüm dedup kayıtları korunur.
- e68f93d hosted checks veRTL geçiyor; formal-and-boot push/PR sonbakışta
  sürüyordu. SonSHA tümhosted yeşil denmedi. PR gövdesi enson768 güncellemesi
  öncesinde743/26 idi; cfa768 veXOR/LVS tamam bilgisiyle güncellenecek.
- Bu checkpoint sonrası docs/evidence/ledger değişiklikleri için manifest
  refresh, doc/digesttest, SPDX, commit/push gerekir. KaynakRTL aynı,
  frozenpilot değişmedi; ürünün PCIeIP/pads/DFT/debug/clock/silicon/PDK
  gereksinimleri ve F6 tarihselartifakt eksiği açık. Tam ürün demeyin.

## 2026-09-20 07:16 TRT — harici IRQ ve bulunan CRT hatası üzerinde aktif çalışma

- `4c78404` push başarılı; 768/26 ve16/0/7 temiz-klon, ECO18XOR0,
  scopedLVS97150/96311 sonuçları PR gövdesine işlendi. Main-deck DRC
  session46578, halo native11114 ve ECO22native62541 çalışıyor.
- Ürün listesindeki harici IRQ için prototip BASE/external-irq-probe.
  `prepare_external_irq_probe.py` ikiFF sync topkopyası +gerçekCPUfirmware
  +GPIO üzerinden harici kaynak modeli hazırladı. Mevcut CRT'nin normal
  IRQ stub'ı t0'ı marker ile eziyor ve saklamıyormuş. Ölçümnegatifkontrol:
  unfixed-run.log 5126cycle, sig=e1700002, mask/exit=0x100;4assertion,
  2WFIwake, traps/NMI/WDOG/alerts0. Sadece t0 korunması başarısız.
- `fix_external_irq_probe_crt.py`: normalIRQstub stackframe açıp t0'ı
  marker yüklemeden önce saklıyor; ortakIRQsonunda geri yüklüyor. Minimal
  platformun NMI fallback'ı da aynı giriş sözleşmesine getirildi. Gerçek
  SOC_PLATFORM NMI ve exception handler zaten t0 saklıyordu, değişmedi.
  fixed-run.log 5138cycle, sig=e1700002, mask/exit0, diğerkontrolleraynı.
  Bu ikiCPUrun tamam; sessions5585/86186. Komutlar run_{unfixed,fixed}.sh.
- Ana kaynakta ŞİMDİ UNCOMMITTED değişiklikler var: soc_top giriş
  irq_external_i +ungated clk_i/rst_sys_n ile2FFsync→Ibex machine-external11;
  CRT vec11 ve tümnormalIRQstublarında t0 düzeltmesi;3RTLbench yeniIRQ0tie;
  GLbench FI_GL_EXTERNAL_IRQ şartlı0tie ve fi_core_gl.sh netlistportdetect;
  test_soc_npu_guards markerregex artık t0-save prologue'u kabul ediyor;
  tb/sw/external_irq.c prototipfirmware kopyası. Frozenpilot değişmedi.
- Bu yeniIRQ RTL'si mevcut ECO18/ECO22 layoutlarında YOK. Bunlar önceki
  kaynakrevizyonunun ölçümleridir. YeniRTL'nin fiziksel entegrasyonu ayrı
  profil/run ister; eski layout sonuçlarını yeniRTL'ye taşımayın.
- Kalıcı external_irq_probe.py/monitor ve tests/docs94 henüz yazılmadı.
  soc_top yorum docs/94'e gönderiyor: doküman mutlaka eklenecek. CPUprobe
  kalıcı araca taşınıp canonicalRTL/CRT üzerinde tekrar çalıştırılacak;
  GLprobe ve negatifkontrol planı var. Henüz IRQ için commit/push YOK.
- Aynı koşullu whole-SoC synthesis maliyet kontrolü başladı: session97957,
  BASE/external-irq-probe/syn_reference.sh 20 .../syn-reference. Env
  SOC_MEM=sram IBEX_REGFILE=secded IBEX_RF_SYNPRE=1 SOC_MEM_RDREG=1
  SOC_REQ_REG=1 SOC_MEM_HARDEN=1 SOC_ROM_HARDEN=1 SOC_WAKE_GNT=1
  SOC_ETH_SRAM=1. timeout2400. Log syn-reference-supervisor.log, asıl syn.log.
  Kaynak top eskiRTL'nin immutable soc_top-reference.v kopyası. Aynı
  ayarlarla syn_irq.sh/yeni topkopyası sonra çalıştırılacak; henüzbaşlamadı.
- Aktif eski physical işler canonical soc_interfaces.sdc okuyor. Bu dosyayı
  onlar sürerken DEĞİŞTİRMEYİN. YeniIRQ için ayrı wrapperSDC hazırlanabilir:
  önce legacyinterfaces source, sonra yalnızirq_external_i portundan false
  path (asenkron dışpin→ilkFF); FF0→FF1 timing aktif kalmalı. Eski pin yoksa
  wrapper failclosed, yeni config açıkça bu wrapper'ı kullanmalı. Henüzbu
  SDC yazılmadı. Pad/MTBF/SEU/radiation hiçbiriprotoilekapanmaz.

## 2026-09-20 07:42 TRT — harici IRQ kaynağı doğrulandı, teslim hazırlanıyor

- Önceki 07:16 notundaki kalıcı araç/doküman/sentez bekleyenleri tamamlandı:
  external_irq_probe.py, monitor, firmware, docs94, wrapperSDC ve18 parser/
  prepare kontrolü var. CI olumlu+eski-t0 negatif RTL koşuları ve logupload içerir.
- CanonicalRTL ve native-cellGL ikisi5138cyclePASS,21işlevselalan aynı.
  Negatifkontrol5126cycle, yalnızmask/exit0x100; EXPECTED t0 FAILURE.
  BASE/external-irq-delivered ve-negative. GL session33167 exit0.
- Matchedsyn tamam: baseline65562cell/9352FF/1046590.2972um²,
  variant65731/9354/1046193.2838um². +169cell,+2FF,-397.0134um²,
  globalABCmappingetkisi, IRQdevresi negatifalan demeyin.24SRAMalanıhariç.
  Variantprototop canonicalile yalnızcomments/whitespacedifferent.
- SDCscope standaloneOpenSTA3.1.0pass; actualsta.vFF118600/118601.
  Typidealclocksetup19.443762/hold-0.033690ns. Holds başarısızlık,
  fizikselkapanışdeğil. İlkOpenROADtechsizhata ve yanlışnetlist.vcellnames
  diagnostic saklandı; yalnızirq-sdc-corrected.log kabul.
- Normalcanonicalbringup session54611 exit0:28check/0mask,
  642152cycle,boot322818,expectedWDOGNMI1,stage2/3=0.
- docs/evidence/external-irq-20260920.json tümkanıt+komut+hash içerir.
  SDC/monitorSPDX hardwareCERN-OHL-W-2.0 düzeltildi; saltlicensecomment
  değişiminin eskiölçümhashleri kayıtta tutuldu. SPDX462tag/329covered/0wrong.
  164targetedtestPASS (IRQ/NPU/doc/digest); docsindex94linkfix dahil.
- Aktif eski physical: ECO22native62541,halo11114,ECO18DRC46578.
  Bunlarınhiçbiri yeniIRQRTL'sini içermiyor. OriginalSDCdeğişmedi.
  YeniIRQcommit/push,cleanremoteCIreplay vePRupdate henüz yapılacak.

## 2026-09-20 10:15 TRT — bağlantı kesintisi ve sistem yeniden başlatması sonrası kurtarma

- Kaynak ağacı kesinti sonrası temizdi; HEAD ve GitHub branch aynı:
  82ab25c38f39916153b43fcc1a6ae29ac0fab9bc. Önceki07:42 notunun
  commit/push/PR bekliyor cümlesi artık eski: hepsi kesinti öncesi yapılmış.
- Hosted82ab25c push35489687890 vePR35489689118 success. Cleanremoteclone
  813total,787PASS26SKIP,16/0/7frontdoor; fresh-clone-82ab25c kanıtı
  oluşturuldu, cloneledgerrow ci-local-log.tsv'ye aynen eklendi.
- ECO18 mainDRC tamamPASS0XMLmarker; lockedinputhashler doğrulandı.
  docs/evidence/ethernet-eco18-drc-20260920.json yeni kayıt.
- ECO22native tamam08:29exit0: tüm3corner setup/holdPASS,
  worstsetup+.1586286702/hold+.0455355766ns; elektrikslewmax23,
  capmax9,fanout43fail. RouteDRC/antenna/criticaldisconnect0.
  Postroutechecker96780orijinalcellkorundu+550antenna+251459fill.
  docs/evidence/ethernet-eco22-extracted-20260920.json. Finalduplicate12
  dosya1,320,628,120bytehardlinkdedup; yol/içerik değişmedi. ~4.5GBfree.
- LogicbootROMprototype tümkoşular kesinti öncesi bitmiş: RTL/nativeGL
  block4113read17rejectedwrite,2048adresfrozenencoderoracle; CPU28check
  642152cyclePASS ve aynıbinary. Synthesislogic4236cell115FF44551.08um²,
  SRAMcontrol649cell78FF10870.0704um²+4macro(alanhariç). Logic0memory/
  0SRAM, noROMpreload. docs/evidence/logic-boot-rom-prototype-20260920.json
  kaydı eklendi. SADECE BASE/logic-boot-rom-probe kopyatop, canonical
  entegrasyon henüz yapılmadı. Sonraki geliştirme budur.
- Halo eskiRUNNINGsupervisor stale; reboot sonrası hiçbirEDAprocessyoktu.
  İlk native01stage hiçstate_outyazmamış ama drt-run-1/soc_top.odb+0DRC
  kayıtvar. Stage1antenna894ekli. BASE/halo-interruption-20260920.json
  eski supervisor/log/hashleri koruyor. Başarılıexport BASE/halo-recovered-
  checkpoint/export-with-libs.tcl; ilkexport eksikderivedcornershatası
  korunmuş. Lib/RCderivedenv eskihaloGRTscriptindenderlendi, kurallaraynı.
  Recoveredpostroutecheck93459original+894antennaPASS,2766obstruction.
- AKTİF YENİ İŞ: session68039, python3 BASE/run_halo_continuation.py.
  BASE/halo-route-continuation/continue.tcl copiedupstreamDRT: tamamlanan
  run1yenidenkoşmuyor, orijinal8antennaiterationlimitinin2.sindenbaşlıyor,
  12thread. Inputorijinalrun1ODB, çıktılar ayrıBASE/halo-route-continuation.
  Supervisor/tag halo-route-continuation-20260920,4h/1024MiBbound.
  Sonrasında nativeOdb.RemoveRoutingObstructions→Odb.CellFrequencyTables
  kalancheckler ve SAMEinstalledMagicDEF/LEFDRC gerekir; eski
  prepare_halo_magic.py eski tamamlanmamış run tag'ına bakar, doğrudankoşmayın.
- YeniIRQveROM eskiECO22layoutundadeğil. PCIePHY/controller,pads,DFT,
  debug,physicalclock,silicon/beam veF6 tarihselartifakt açıkları sürüyor.
