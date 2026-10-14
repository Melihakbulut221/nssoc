<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# NSSOC cloud continuation — 13 October 2026

## Latest cloud-only checkpoint — 14 October 2026

### Newest state — supersedes every older live statement below

**Current concrete continuation:** native PLL snapshot experiment38503239727
dispatched on83e3270e035f886479d475a665280bce84b55979. Keep its handle; inspect
native evidence before assuming snapshot/KLU/OSDI compatibility. No local run.
TX independent38496978055 is TERMINAL:24cases,19engineeringPASS,5FAIL despite
workflowgreen. ColdresWCS CM fails in bothcompact andwire; coldHBT WCS compact
also has12VBE failures. HotresBCS wire CMmin1.799833864V fails1.8V. HotHBTBCS
wire has6VCE minima below.4V(worst.388441772V). Bits pass in allfive failures.
A new output_feedback prestage feed uses two real26um/2um rppd resistors from
actual stage outputs into its original HBT reference. Hypothesis: increase
negative common-mode feedback instead of waiving PVT bounds. No ideal current,
clamp, phase change, transistor deletion or changed limits. Existing19HBT stage
and actual extractedRC retained. Added source/connection/fault controls.
Feed itself has NOT been laid out; candidate screens are not finallayout proof.
Use tx-tree-physical-cloud.yml study=failing_corners streams=4
physical_profile=cascade158_kelvin_supply_direct
physical_final_profile=v10_kelvin_low_ports_loads_shunts_series
physical_final=matched clock_reference=stiff65 pre_bias=output_feedback.
First inspect hosted tests; any failure remains a rejection. Remaining mainchip
38490952579 and32:1wire38496981217 still live at last observed checkpoint.
All three full-goal scopes remainOPEN; continue only on hosted runners.


**New hosted PLL continuation method under test:** run_cloud_pll865_snapshot.py
restores the exact native07 1us circuit, all32 original IHP model files and
three exact OSDIs, and original ngspice47 executable. No circuit, source,
startup, timestep or electrical-limit changes. The ngspice manual documents
snsave/snload across processes but warns against XSPICE devices; actual865
compatibility remains UNPROVEN until the native experiment passes.
Hosted workflow inputpll_snapshot=true compares continuous0-50ns with a
25ns checkpoint, same-process resume and fresh-process restore to50ns.
All24 original selected probes, no fitted phase; fixed1mV waveform/1psedge
method limits and four corruption controls. This is only restart-method
validation, never1us lock/full-device safety/PVT/PHY acceptance. Both original
failed readers and prefix diagnosis remain preserved. Do not dispatch full
segmented acquisition before reviewing actual native waveforms and snapshot
proof; do not assume snsave works with KLU/OSDI from documentation alone.
Native budget19000s leaves publication time before hosted6h hard ceiling.
Run only on GitHub; localworkspace remains empty. Existing TX38496978055,
32:1wire38496981217 and chiproute38490952579 retain their handles.


**Latest verified cloud outcome:** PLL prefix38501501029 onb2242dc77f4ba386cf16582deba163393d5c06e3
completed diagnosis and hosted source/license checks successfully. Summary
638969192,archive638969080; exact full summary pinned in
pcie-pll753-parent-rounded-credit-20261010.json underparent865_cloud_prefix_20261014.
748851 complete rows end233.92609375ns;40 trailing bytes excluded with hash,
never padded. Five corruption controls plus explicit partial-row controlPASS.
Feedback median frequency falls100.206270MHz(25-50ns) to100.068033MHz
(200-230ns); last short-window error~680ppm, not100ppm lock. VCTRL lastwindow
0.427578..0.593801V. Missing800-1000ns windows, phase/slip criteria and full
1us safety remain OPEN. Next PLL work: exact source-bound hosted native865
acquisition with valid runtime/resource plan, not another prefix acceptance
or redundantKLU change. Base finite50ns proof remains separate.
TX independent run38496978055 additionally fails hot_low_res_bcs physical_wire:
final CMmin1.799833864V<1.8V, although bits/devices pass. Exact summary638961839
now retained in V10series receipt; don't waive the small violation. Remaining
independent wire cases,32:1wire38496981217 and chiproute38490952579 stilllive
at this checkpoint. Preserve these original handles before any next dispatch.
Local cleanup complete as recorded below, all computation hosted. Fullserial
PHY,assembledchiprouting,finalsetup/hold all remain OPEN.


**Newest cloud-only cleanup and diagnostic checkpoint:** four legacy LVS `.cir`
files outside the checkout in its parent were archived, fetched back and
byte-for-byte verified, then ONLY those exact unchanged files removed.
Release cloud-migration-final-checkout-20261013 holds
parent-lvs-leftovers-20261014.tar.gz(asset638960993,14788bytes,
SHA12ab296f0bd74fae6bb559982b43421ccd30e9f7dfd69e8200e92da499199080)
and receipt638961046. Workspace empty; no local ngspice/OpenROAD/Yosys/KLayout/
Magic/Netgen process. Existing 8hour heartbeat already enforces cloud-only.
Corrected split-archive PLL run38501008048 reached waveform decoding but
FAILED strict complete-row gate: historical cancellation truncated final row.
Do not erase this failure or use partial data for acquisition acceptance.
Reader now has explicit interrupted-diagnostic-only mode: excludes incomplete
final row with byte count and hash, preserves original capture and strict
normal decoding. Added control proves no padded/fabricated row. All five
original corruption controls remain. Next hosted dispatch must inspect this
partial prefix; absent800-1000ns acquisition and whole-wave safety remainOPEN.
Independent cold TX failures and original active route/tree handles below
remain authoritative; no new circuit acceptance or completed layout claim.


**Latest correction and failures (14 October):** hosted PLL prefix38500020789
FAILED at archive member lookup, before waveform analysis. Archive002 contains
native07 bench/control/logs; wave.raw is in archive003(asset634833900,
121865817bytes,SHA867100a4e8844477ae6003fa84bb7c10801099afb335b8dd3d1b56a6a99450fb).
Both archive/member hashes remain required; reader now explicitly loads both.
Failed receipt638933688 is retained. A corrected hosted dispatch is needed;
never treat this data-location failure as a circuit result.
Independent TX38496978055 has two compact electrical FAILURES:
cold_high_res_wcs final CMmax2.062756V>2.05V;
cold_high_hbt_wcs CMmax2.056945V>2.05V and twelve HBT Vbe>1V
(max1.023357V). Original limits unchanged; exact summaries638905051/638908223
are preserved in the V10series receipt. Base6/6 and hot halfstep remain only
narrow successes; full independent PVT has NOT passed. Continue existing wire
cases and full32:1nominal38496981217; do not duplicate jobs. Full32compact
summary638926257 passed component screen only. Mainchip38490952579 still
running at this checkpoint. Local workspace verified empty; no local CAD.
FullserialPHY, chiprouting and finalsetup/hold remain OPEN.


**Current live readback and numerical evidence:** PLL865prefix diagnostic
38500020789 dispatched on c5e1df33127620ce8d3f54b4f4ca07ed63885ed9.
It runs ONLY on GitHub; five corruption controls before exact native prefix
analysis. Source/license tests run in the same workflow; push check38499990970
has the same source. Read its final summary before claiming any diagnosis.
Hot0.25ps TX38496975171 completed BOTHcasesPASS: compact232.880883552mV,
wire103.821631612mV versus original.5ps232.866874337/103.786226760mV.
Original768bit samples, device/interface gates, no diagnostics. Differences
are worst-margin comparisons, NOT whole-wave convergence/PHY acceptance.
Exact summaries638864869/638899224 and archive/raw hashes are appended as
`hot_half_maxstep_control` to the V10series composition receipt.
IndependentHBT/resistor38496978055 and full32:1nominal38496981217 retain their
original handles. Main-chip halo38490952579 also remains native-running.
Do not duplicate these jobs; inspect native engineering results individually.
All three full-goal scopes remain OPEN; local workspace remains empty.


**Verified latest PLL resume point and hosted diagnostic:**865PBUF10 finite50ns
native01 PASS, independent functional/electrical PASS, zero-source startup and
clean diagnostics. Immutable batch007(asset634874106,669884bytes,
SHAe59ca7de8b8f79a200b226fc7f817bc6eee415ebc563cb811ad5c0be1ae832c6).
Finite capture took5041.802s locally. native04 acquisition failed RAM floor;
native07 is terminalCANCELLED by parentSIGTERM,returncode-15,not currentlylive.
Native07 log reaches233.927ns only;1us final800-1000ns criteria are unobserved.
All exact native07 bytes are batch002(asset634832275,141989022bytes,
SHA6021e860444f74adae386a07f85254169bb6e75ab03fd981dff8cc52c098f6ce).
Bench already usesKLU, reltol1e-4/abstol1e-12, maxstep.3125ps; never add a
newKLU trial or silently coarsen timestep. Current raw149771119bytes pinned
SHA7c1f37bd9e29e794f2a33c67fe5efaa3f0c021bc907484d1d7efa60521d25ba8.
New `read_cloud_pll_acquisition_prefix.py` diagnoses this exact saved prefix
ON GITHUB, with five corruption controls, full archive/member hashes and
explicitly missing final acquisition windows. Dispatch existing workflow
cloud-migration-checks.yml withpll_prefix_readback=true. No new nativePLL
simulation yet. Inspect frequency/VCTRL direction before expensive replay.
FullserialPHY,assembledchiprouting,finalsetuphold remainOPEN;cloud-only.


**PLL continuation correction:**744/753 terminal readback below is HISTORICAL.
Later physical853(reset96) and865(PBUF10) descendants exist. Do NOT roll back
to compact753. The latest migration roots to inspect are
pcie-acquisition-resource-recovery-20261012,pcie-parent865-acquisition-20261011,
pcie-pbuf10-native865-20261012,pcie-pbuf10-acquisition-20261012. The migration
snapshot explicitly stopped acquisition retry01 on12October for cloud-only
handoff. Find its terminal/partial capture and input manifests before hosted
replay; old process/unit names are not live handles.
Gate source asset632607200(8611bytes,SHA54901cd0d7aa00a98fb0d6a95e2516a2e7781368d61acc80da0597fe63c89fa2)
requires independent finite865 pass before a1us diagnostic at.3125ps; no
external VCTRL clamp. Acquisition criteria: final800-900/900-1000ns windows,
100ppm,50ps phase range,no ordinal slips,VCTRL.4..1.5V. Selected24probes alone
cannot qualify all-device safety/PVT or fullPHY. Preserve the failed-source
negative gate. No new PLL simulation dispatched in this readback.


**Newest authoritative findings:** slow-corner mapping38496628841 completed;
79055cells, PCIe slow setup-0.991351ns versus-0.991500baseline (only0.149ps),
fast hold-0.109062ns unchanged. Not adopted. Full corners/critical path pinned
in `abc_slow_corner_completed_screen` ofpcie-ack-window-proof-and-screen-20261014.json.
Actual endpoint is advertiser.refresh[0], FF1304820; further blindABC sweeps
are not justified. Inspect full ready/arbiter/reset cone before the next ECO.
**PLL historical-state correction:**744native05 was finitePASS;753native03
was finiteFAIL, with a separate limited phase-window review. Newer compact
parent753native02 ALSO FAILED electrical and functional/phase checks. None is
running. Exact terminal records, raw hashes and independent reviews recovered
from migration batch259(asset635605533,68.8MB),316(asset635797234,1.46MB), and
744records628261905 are in `cloud_terminal_readback_20261014` of the existing
PLL753evidence receipt. Repair from compact753native02, not the older pending
snapshot or the unchanged wide parent. No PLL lock/fullPHY acceptance.
Native TX hot0.25ps38496975171: compact has passed, wired stilllive at lastread.
Independent corners38496978055 and32tree38496981217 retain original handles.
Main-chip halo38490952579 remains native-running; release summary638701652 is
an INTERMEDIATE placement/STA checkpoint, NOT a terminal route result.
All work stays cloud-only. FullserialPHY/main-chiproute/finalsetuphold OPEN.


**Current dispatch handles (do not restart queued/live jobs):**
- 38496975171: V10 4:1 hot-low compact/wire at0.25ps maxstep; compare against
  original hot-low0.5ps summaries638812939/638828378, same bit oracle/phases.
- 38496978055: V10 4:1 independent HBT/resistor and mixed PVT corners,24cases,
  at most4parallel. Every engineering gate still applies.
- 38496981217: V10 full32:1 compact/wire nominal, actual30prestage macros.
  All three run on31d4d70464ed0c395ca9c4564e81e101fee849da, same
  cascade158_kelvin_supply_direct / v10_kelvin_low_ports_loads_shunts_series /
  stiff65 / matched physical. Read terminal native captures, not workflow color.
- 38496983888: source/license/capture checks for31d4d704.
- 38496628841: paired typical/slow ABC mapping on96b1ee51; native preparation
  has started. OriginalD4000,32joint controls,all3STA corners.
- 38490952579: main-chip halo1 native routing remains running, original source.
V10six-case base measurements: compact/wire nominal280.128025493/234.097230665mV;
hot232.866874337/103.786226760mV; cold273.459379164/263.748860088mV.
All6pass original768samples/device/interface/diagnostics. Narrow hot margin
requires the above numerical/process checks before any acceptance expansion.
Unchanged schematic divider14 nine-job push38496930380 was cancelled after
inspecting its exact workflow; it does not exercise the new physical V10.
Legacy schematic/native study jobs now require explicit dispatch; standard CI
and all explicit physical/timing jobs remain enabled. No local artifacts.
FullserialGen3x4 PHY, assembled main-chip routing and finalsetup/hold OPEN.


**Newest PHY result:** V10series loaded38495318320/38495321089 completed all6
component cases successfully. Hot extracted-wire minimum103.786226760mV,
0wrong-sign/0below100mV among768original samples; all native device/interface
and diagnostic gates pass. Six captures/asset hashes are appended as
`loaded_temperature_voltage_screen` to the V10series composition receipt.
This does NOT close fullPHY: intermacro wiring/clocks still ideal, no fullx4.
Dispatch next: `hot_low_quarter_step`4:1 numerical control, independent process
corners4:1, and nominal32:1 with identical V10/cascade158/stiff65 settings.
Study workflows require explicit dispatch to avoid unrelated default push jobs;
physical study parallelism capped4. DefaultACK push38496573724 was cancelled
after verifying its baseline/ack jobs; desired slow-corner mapping38496628841
is separate. Sourcechecks38496631571 on96b1ee51.
Main-chip halo38490952579 remains live. All full-goal scopes remain OPEN.


**Newest synthesis finding:** ABC study38494637444 completed with no improvement:
79065cells and all6corner group minima identical, slowPCIe setup-0.991500ns,
fastPCIe hold-0.109062ns. Native trace proves D2000 was applied; its network
is combinational. Full native records/hashes are preserved as
`abc_delay_completed_screen` inpcie-ack-window-proof-and-screen-20261014.json.
Next paired study `abc_slow_corner` maps the SAME proved best RTL with the
pinned slow standard-cell Liberty, D4000, original FF mapping and constraints;
all3STA corners and32joint controls remain. Pending dispatch, not adoption.
V10loaded38495318320/38495321089: all3compact jobs completed; all3wire jobs live.
Main-chip halo38490952579 remains live. Continue cloud-only, no local files.
Full serial PHY, main-chip routing and final setup/hold remain OPEN.


**Latest advancement:** V10extraction38494852996 passed4017R/2636C and13faults;
composition38495079171 passed native54device binding. Receipt:
`docs/evidence/pcie-final-v10-kelvin-low-ports-loads-shunts-series-composition-20261013.json`.
**Loaded V10 hot/cold38495318320 and nominal38495321089 are now running** on
`84a5222afc769c035eec46335df3f8b74256dcb2`; streams4, matchedphysical,
`v10_kelvin_low_ports_loads_shunts_series`, cascade158direct, stiff65.
Source/license/capture checks38495323612 run on the same source.
Do not repeat extraction/composition or infer loaded acceptance from them.
ABC4000/2000study38494637444 remains running (jobs115627512925/115627513061).
Main-chip halo38490952579 remains running on its original source. All three
full-goal scopes remain OPEN. Continue cloud-only; local workspace stays empty.


- V8series loaded38492859554/38492856902 completed all6:5pass, hotwire fails50
  early samples, minimum88.993072473mV versus100mV. All devices/interfaces pass.
  Receipt `docs/evidence/pcie-v8-series-loaded-rejection-20261014.json` retains
  all6 captures and the next V10 trial. Do not repeat unchanged V8series.
- **V10 Nx3 data-bank plus same improved series geometry:** physical38494057637
  on05a0a4c8 passed560-category zero-marker DRC, strict hierarchical/flat54device
  LVS and5faults. **Extraction38494852996 is live**, source
  `1fc2599ffdbbb10714071d9b511d963e92168420`; profilefinal_drive_v10, variant
  `critical_buses_kelvin_low_ports_loads_shunts_series`. Summary638777925 and
  archive638777738 are pinned inpcie-tx-cloud-extraction-input-20261013.json.
  V10 needs its own fresh RC, composition and all6loaded cases; do not reuseV8.
- Reset-dominance38493229154 passed fullregion induction and32joint ports but
  PCIe slow setup worsened-0.991500 to-1.260820ns;79984cells. Rejected. Evidence
  `reset_dominance_completed_screen` inpcie-ack-window-proof-and-screen-20261014.json.
- **ABC synthesis-target study38494637444 is live**, source
  `0d16d91b36f0d57adc65f393a78e71149072bb47`: same best proved EOP/window RTL,
  target-D4000 versus-D2000ps. Native help and original/modified exact command
  are captured. No -dff/retime, changed clock period, relaxed SDC or adopted logic.
  Profilesphysical_idle_credit_window_eop andphysical_idle_credit_window_eop_d2000.
  Source/license checks38494640061 passed. Inspect both paired outputs.
- **Main-chip halo38490952579 remains live**; inspect same handle, never restart
  because a poll takes too long. Parameters and source below remain authoritative.
- PLL broader scope was revisited: docs/evidence/pcie-pll753-parent-rounded-credit-20261010.json
  proves parent753DRC/LVS/faults and parent86R/317C, not loaded lock or fullPEX.
  Old delivery627947280 (26692374bytes, SHA9bd534fc389506982c6d05f3fd5a94175e8e5a3dd8c9dae00648aca459d0f4b3)
  was read inRAM. Its historical running statements are NOT current process proof.
  Latest migrated753/744 terminal evidence must be located before cloud replay;
  no new PLL job was dispatched and no PLL completion is claimed.


This section supersedes older running/pending statements below. The local
workspace is empty. No local checkout, CAD, tests or artifacts; metadata/source
edits stay in RAM and native work runs on GitHub. Final retirement backup:
`cloud-migration-final-checkout-20261013`. Never force-push or retry uncertain
mutations before reading the branch ref. Latest engineering source:
`895fc9a44b85c1a8ae3451f0fdfb28b1ec58d73f`.

### Live runs to inspect before dispatching anything again

- **38490952579 main-chip macro halo**, source
  `a011880cdadc7f4c22cf077383382880528b1f14`, job115615743460.
  Native replay/routing is in progress. `local_optimize_buffers`, GMIIhold2,
  seed13, critical0, guideoffset0, halo1; exact baseline placement hash enforced.
  Native `set_macro_extension 1` enlarges actual macro OBS. Same original layer
  derates, SDC, cells and zero-overflow gate. No detailed routing/STA acceptance.
- **38492859554 nominal** and **38492856902 hot/cold PHY**, source
  `a1d1ae9707cf567b638951cdabc3f54087014a85`.
  All3compact jobs completed; three extracted-wire jobs remain running.
  Profile `v8_kelvin_low_ports_loads_shunts_series`, prestage
  `cascade158_kelvin_supply_direct`, stiff65, streams4, matchedcompact/wire.
  Read allsix engineering summaries; a green workflow does not mean acceptance.
- **38493229154 reset-dominance proof and paired digital map**, source895fc9a4.
  Baseline `physical_idle_credit_window_eop`, candidate
  `physical_idle_credit_window_reset`; jobs115623078791/115623079002 live.
  Candidate ties only advertiser.link_up_i high beneath unchanged actual
  asynchronous local_reset=rst_ni&&link_up_i&&!retrain_done_i. All other link
  connections, original FC state, EOP candidate, latency and SDC preserved.
  `run_cloud_advert_reset.py` requires full-region state/output induction with
  arbitrary reset/link/clock traces, wrong-owner counterexample, full public
  port controls before native paired mapping. Never assume proof/timing passes.
- **38493231713 source/license/capture checks**, source895fc9a4, running.
  Earlier source checks38492861940 and38492081693 passed.

### Fresh physical evidence

Series-output candidate moves only R25/R26 fromy=-50 toy=-18um on combined
loads/shunts geometry. Physical38491698578 passed zero-marker560-category DRC,
strict hierarchical/flat54device LVS and5actual faults. Extraction38492320653
passed native4021R/2638C graph/capacitance checks and all13negative controls.
Composition38492591399 passed exact native device/wire binding. Receipt:
`docs/evidence/pcie-final-v8-kelvin-low-ports-loads-shunts-series-composition-20261013.json`.
Summary638734981 SHA3f7c9eff40f67dd43f7d16be4b6f92730ae6fb5c2cf6e90d9aacb386a10b7192;
archive638734847 SHA7d23c3d62afd75a822f007b6b4fb0a4179c11659bac4da3f26afc8477f2c976b.
Do not reuse prior geometry RC or call physical pass an electrical pass.

Prior combined loads/shunts run38489754238/38489752340 passed5/6: hotwire had
50early samples below100mV, minimum88.309416767mV; allHBT/MOS/interface gates
passed. Diagnosis38491313386 proved clock-to-MUX median17.390ps versus9.491ps
compact; source-to100mV maximum38.278ps misses original37.5ps early sample.
These exact records and subsequent physical/RC receipts are retained in
`docs/evidence/pcie-v8-loads-shunts-loaded-rejection-20261014.json`.
Next after a genuine6/6pass: independent native device/process corners,
numerical step agreement/fault controls, full32:1 and actual clock/intermacro
layout. Do not change bit oracle, sample phases or electrical thresholds.

### Rejected digital and route hypotheses

- Non-SOP owner38488788552 passed exact proofs/ports but setup worsened
  -0.991500 to-1.261001ns; rejected.
- Factored EOP38492079062 passed3region inductions, wrong-owner counterexample
  and32joint public-port tests but setup worsened-0.991500 to-1.015753ns;
  cells79065 to79564. Rejected. Fast PCIe hold unchanged-0.109062ns.
  Allcorner evidence, hashes and candidate identities for both studies and
  earlier rejected FC refresh/snapshot trials are in
  `docs/evidence/pcie-ack-window-proof-and-screen-20261014.json`.
  Best unplaced baseline is still `physical_idle_credit_window_eop`.
- Half-grid38472175339 failed with identical seed13placement/congestion hashes
  (132overflow). Exact OpenROADdcf36133 source uses grid_origin only when
  saving guides, not routing partition creation. False shift claim withdrawn;
  nonzero choices removed. Never repeat half_x/half_y. Receipt/correction:
  `half_grid_rejected_followup` in
  `docs/evidence/cloud-seed13-buffers-route-failure-20261014.json`.

Full serial Gen3x4 PHY, assembled PCIe/Ethernet main-chip routing, final
setup/hold and production acceptance remain OPEN. Ideal clock/intermacro
segments, schematic TX driver and unqualified RF/substrate extraction are
explicit gaps; passing a4:1 component does not close them.

## Controlling request and scope

The user requires **cloud-only execution**. The local workspace is empty.
Do not clone the repository locally, restore local CAD, run local tests, or
retain local artifacts. Use GitHub API metadata/source edits in memory and
GitHub-hosted runners for all native work. Repository: `Melihakbulut221/nssoc`,
branch `codex/complete-open-work`. Never force-push or blind-retry a mutation.
On uncertain publication, inspect the remote ref before proceeding.

**Full serial PCIe Gen3 x4 PHY, assembled main-chip PCIe/Ethernet route and
final setup/hold remain OPEN.** Compact/4:1 component gates do not prove a
32:1/x4 PHY, actual PLL/CDR clocking, ESD, qualified RF/substrate PEX, or chip
production acceptance. Main-chip packet-interface work is a separate scope.

The previous long continuation log is preserved unchanged at
https://github.com/Melihakbulut221/nssoc/blob/a45de762a05b9625fe9308aac90805544988c81d/CLOUD_RESUME.md
and all immutable results/failures remain in Git history and release assets.
This concise checkpoint supersedes stale running/pending statements there.

## Active physical candidates: inspect these runs before dispatch

| Work | Exact source / runs | Verified boundary and next action |
| --- | --- | --- |
| Short selector buses on unchanged v8 | Physical38452058065, extraction38453131275, composition38453569616 | All native physical/RC/composition gates passed. Loaded nominal38454523127 andhot/cold38454526301 completed ona45de762a05b9625fe9308aac90805544988c81d. Fiveof six engineering screens pass; hotwire fails128early samples, minimum20.841388mV. Allsix retained inpcie-final-v8-low-selects-loaded-tree-20261013.json. Native paired diagnosis is next; no adoption. |
| Nx3 data-bank v10, original low-critical buses | Nominal38452808927, hot/cold38452812892 on7f95123097589d5edb304e9c0cdde52720a8ac2b | 6captures retained; complete=true; failed cases=[('hot_low', 'physical_wire')]. Check exact receipt before adopting anything. |
| Main-chip alternative net ordering | 38448901835 on c19fc8b4c72e4db8ad20d6132ad73153f1ef856b | Latest live readback: in_progress/None. Seed13, capacity perturbation0, exact135-overflow buffer placement. Preserve native result; detailed routing/extraction/final STA still required. |
| Bounded-save32:1 nominal | 38441895491 on26e3692a27cb4aea7faa877b8df3388ddc06024d | Latest readback: in_progress/None. Compact passed; extracted-wire companion must complete. Do not restart a live job after observation timeout. |

Source/model/geometry/original-bit/license checks38454282998 PASSED before
launching the short-selector loaded runs. Earlier v10 binding checks
38452484468 and receipt checks38453573552 also PASSED.

## Exact analog evidence and unchanged limits

Both current4:1 candidates use `cascade158_kelvin_supply_direct` prestage,
`stiff65` native clock common-mode reference/feed and matched compact/wire.
Original256source bits,768samples at0.3/0.5/0.7UI, output100mV, interfaces150mV
and1.8..2.05V common-mode remain fixed. All native HBT/MOS limits, zero-start
OFF flags and simulator diagnostics remain gating. No phase-fitting or RC
scaling. Differential clocks/intermacro connections still have ideal parts.

- **v8 low-selects** changes only actual sp/sn TM2 buses to y32/40um. Native
  physical passed560DRC categories/zero markers, strict54-device hierarchical
  andflat LVS andfive actual physical/reference fault controls. FreshRC passed
  all13corruption controls. Composition has54devices/4043R/2661C.
  `docs/evidence/pcie-final-v8-kelvin-low-selects-composition-20261013.json`
  binds archive6675045bytes/SHAf591bc98448db872b00d8d0b7c2c2f7aa27625908e265f7431a98008dc10a3b6
  andsummaryasset638003525/SHA91b3d4ce252c81e4c28b06b081d8ba10e05a3f91106ec3211a7d9ffdb9e84d14.
  Do not substitute old low-criticalRC. Profile: `v8_kelvin_low_selects`.
- **v10** changes only twelve data HBTs toNx3; four selectorsNx6, two tailsNx8
  andreferenceNx1 remain. Physical38450309882/extraction38450839520/composition
  38451600151 passed native gates with54devices/4041R/2659C. Profile:
  `v10_kelvin_low_critical`; distinct composition receipt and
  `docs/evidence/pcie-final-v10-loaded-tree-20261013.json` preserve all completed
  captures. Threecompact andnominal/cold wire gates passed; consult hot result.
- **v9 rejected:** Nx2data improved hotwire minimum17.694to41.723mV but still
  failed110early samples. Coldcompact also failed12HBT VBE/current limits
  (maximum1.021886V/3.676749mA). Allsix captures remain in
  `docs/evidence/pcie-final-v9-loaded-tree-20261013.json`; no selective adoption.
- **Native delay diagnosis38451366659 passed:** summaryasset637967168 SHA
  024328b471f0d1ee06476f080849621df84af4d17bd1c1a593f620d9393058c6. All128changing
  bit events unambiguous. Compact/wire clock-toMUX-zero median8.606881/19.656687ps;
  MUX-toTX-zero5.956289/6.178540ps. Source-to100mV median26.362079/39.053899ps,
  wiremax41.441851ps versusfirstsample37.5ps. This motivated selector routing;
  it does not already prove the new geometry works. Hot pair receipt:
  `docs/evidence/pcie-final-v9-hot-loaded-tree-20261013.json`.

If short selectors pass, expand unchanged independent HBT/resistor/MOS corners,
quarter-step numerical agreement and actual physical faults, then full32:1
andphysical clock/tree integration. If they fail, preserve/read exact events
before selecting another geometry. Do not combine sizing/geometry changes
without measuring their separate effects and then retesting the combination.

## Main-chip route and timing evidence

The seed13 trial must reproduce placement SHA
660692b3e59756186bb017a62823999db593fa9d77b6e4181be9625fa7bfb707.
Pre-route asset637931919/SHA8db957ba8f6b07fd0cc12e31df23d0f6925306f3b7c96310ab9ff646676f7a7e
reproduces that exact placement and prior timing. Estimated slow setup is
still negative (PCIe -1.275681ns, system -0.589711ns); fast hold also negative
(PCIe -0.065767ns, system -0.054434ns). These are pre-route estimates, not
signoff. Same cells, SDC, PDK RC/capacity adjustment andzero-overflow gate.

Previous priority30 run38420407838 is terminal GRT-0116 failure, not live:
153layer overflow (M3=21,M4=16,M5=107,TM1=7,TM2=2). It was native max-overflow
attempt termination, not elapsed timeout. Failure receipt:
`docs/evidence/cloud-critical30-buffers-route-failure-20261013.json`.
Diagnosis38443872244 has113markers/155summed marker overflow/933nets; marker
andlayer totals are different native reports. Asset637840399. Prior same
buffer placement had135overflow; broad endpoint move produced420 andwas
rejected. Do not repeat unchanged rejected candidates or waive physical gates.

## 32:1 capture, publication and local retirement

Original32run38440472079 failed wire allocation (42.522GB reported). Oversized
save-command risk was fixed with bounded128-vector commands; its contribution
to that original failure still needs actualnative-log verification. Do not
assert causality from the memory warning alone. Corrected32run38441895491
compact has604native OFF flags,69541wave rows, complete original engineering
gates andzero diagnostics. Exact summaryasset637874261/SHA
 e9423a26a42909dfeb088124e76e072f7701fcc6f37c617dd9c8eadd381739d8 is bound by
`docs/evidence/pcie-bounded-save32-compact-20261013.json`. Wire remains separate.

All native artifacts are retained in immutable GitHub releases, including
failed cases; never label workflow success as electrical acceptance. Migration
finished with `COMPLETE_VERIFIED_CLOUD_HANDOFF_EMPTY_LOCAL_WORKSPACE`; do not
redo retirement or restore local CAD. The8hour cloud-only automation remains
the continuation mechanism. No full goal completion or production approval.


## Latest cloud-only follow-up

The empty local workspace and absence of local CAD processes were rechecked.
Low-selects hot wire has zero wrong-sign samples but128below100mV at0.3UI;
later0.5/0.7UI samples and all HBT/MOS limits pass. Shorter selector buses alone
do not close the amplitude failure. Preserve the compact/wire pair in
pcie-final-v8-low-selects-hot-loaded-tree-20261013.json; diagnosis workflow
study v8_low_selects_hot reads exact original archived waves with unchanged
bit oracle and thresholds.

cloud-migration-checks.yml with timing_readback=true restores the archived complete native STA
log/Tcl from run38371498733, verifying archive size/hash and both member hashes.
It publishes a small full-path log for setup/hold inspection while seed13
routing continues. It does not rerun STA or claim routed timing closure.

The new standalone readback workflow was not registered on the default branch
(dispatch404, no native run started). The readback job now uses the existing
registered cloud-migration-checks.yml workflow with timing_readback=true.
Low-selector native diagnosis38457021311 completed successfully on873a6350ca13c5d98981214033bc5b0af33d0add.


Native short-selector diagnosis38457021311 PASSED. Summaryasset638065261, SHA
acf780035a06b3be15e51beca4f7b9fa4360edf8f0d85a9d3a8926ccc0d64465;
all128 changing-bit events are unambiguous. Exact delay statistics(ps):
{"physical_compact": {"clock_to_mux_zero_ps": {"maximum": 9.581434892876144, "median": 9.491111200654228}, "mux_to_tx_zero_ps": {"maximum": 6.09829029383962, "median": 5.97122009132631}, "source_to_output_100mv_ps": {"maximum": 27.4264716742218, "median": 27.179796408673198}}, "physical_wire": {"clock_to_mux_zero_ps": {"maximum": 22.614831331883618, "median": 21.050944335681756}, "mux_to_tx_zero_ps": {"maximum": 6.513847561199617, "median": 6.17929948213888}, "source_to_output_100mv_ps": {"maximum": 42.797680763914016, "median": 40.40026853520598}}}

Timing readback38457177829 restored and verified both original files, then
failed because the caller selected PHASE markers instead of actual CORNER
markers. Failure retained. Corrected caller uses CORNER and requires allsix
slow/typical/fast min/max phases. Raw fullSTA log remainsasset638067970
SHA80055c3fb2022a1366d03f8a010d0c671fe603c57b3ca6ca64350b5a44668374.
It includes one unconstrained endpoint and SRAM slew violations. PCIe worst
setup contains a long logic chain; PCIe worst hold has justINV+O21AI.
These are placement estimates; no constraint relaxation or closure.


## Verified latest timing readback

Corrected run38457514399 onbad1063138a4233ffca9b64b7c1e0f577558176a PASSED
both source/license/model checks and exact archived timing readback. Optional
archive-migration job was not requested and is skipped. Summaryasset638073464
SHAe759439142daa150c9d12cbd8cc67cda55850f61afb81375b8b30619cdb9566d;
complete original logasset638073598, SHA
80055c3fb2022a1366d03f8a010d0c671fe603c57b3ca6ca64350b5a44668374.
Allsix corners reproduce old placement estimates; slowmax -1.275681ns,
fastmin -0.065767ns. Next inspect the full critical paths and bind synthesized
cell names to actual RTL/netlist before selecting an ECO. PCIe setup includes
six consecutive AND2 stages near its endpoint; hold includes INV+O21AI. The
unconstrained endpoint and SRAM slew violations must also be resolved without
weakening constraints. No new timing/layout acceptance.

Main route38448901835 and32:1wire38441895491 remain in progress at last readback;
do not duplicate them. Authoritative cloud-migration-final-checkout-20261013
retirement-progress.json was reread and digest verified: status
COMPLETE_VERIFIED_CLOUD_HANDOFF_EMPTY_LOCAL_WORKSPACE. Local directory remains
empty. The existing8hour automation is ACTIVE and explicitly cloud-only.


Next cloud timing readback also restores the exact placementODB and runs native
OpenDB on the same pinned runtime to bind every reported timing cell to its
actual master, placed bbox, pin nets and full incident-net endpoint census.
The STA report and ODB hashes must remain unchanged. This gives RTL-facing
net names before any ECO choice; no cell, clock or constraint is modified.


## Native credit carry mapping and next candidate

Native readback38459016095 onb1d25755562e391f27f934f237a8d339221c5faa
PASSED all505reported cell/master bindings and complete incident-net census.
Nativecells asset638101934,2051537bytes,
SHA135e57abe41fc3323988677b4a81eac8f2a1e560be296ddfb84fcbce8ea7897f.
Exact original ODB/STA hashes remain unchanged. Prior failed readers
38458086604/38458327263/38458689640 remain in releases: escaping/import
and rendered array spelling errors were reader failures, not chip failures.

Worst setup: credit_data_consumed_o[29] to credit_header_consumed_o[23].
Worst hold: replay next_store_sequence_plus_one[11] to next_store_sequence[11].
Setup suffix is six AND2s then NAND2 passing the late credit enable through
previous carries. All seven original output nets must remain equivalent.

run_cloud_credit_prefix.py keeps those seven gates/outputs; inserts balanced
AND prefixes of seven early data inputs and applies the unchanged late enable
at each original gate. Actual Liberty SAT proves all seven outputs for all256
assignments of eight cutpoints. Replacing final NAND byAND must fail proof.
Existing instances are temporarily FIRM for added-cell legalization; audit
requires exact original geometry, all non-target pins, boundary nets and power
geometry, then restores statuses. Same archived3corner STA/SDC/libraries.
No candidate adoption, route, final hold or fullPHY closure is claimed.

Launch existing cloud-migration-checks.yml with credit_prefix_eco=true.
All native work is hosted. Do not launch full routing until measurements exist.


Credit-prefix candidate dispatched as run38460825316 on
9588d4421d7d574edfd7f5e687b72431f7628b8b. Latest authoritative status: completed/success.
Job115515232477 runs native proof/geometry/STA; source checks already passed.
Keep this exact handle; do not start another candidate or rerun on a polling
timeout. Read result.json in release cloud-results-38460825316-1-credit-prefix-eco
when published. Check all7output SAT proof and actual wrong-gate negative
control, exact retained geometry/power audit, allcorner/group deltas and all
remaining violations before any adoption. No accepted timing gain yet.


## Completed credit-prefix screen: real proof, timing still open

Run38460825316 PASSED its native work and controls. Exact full receipt:
docs/evidence/cloud-credit-prefix-screen-20261013.json. Summaryasset638141166
SHAa0413b69f0d2b827eedf1f74950bfd30e02cf004cb411eb7544c9553175b8b31;
archive638140287,201763214bytes. CandidateODB
SHAdc4d9bcaf7ca617b31ece0c7504a591d41ddff0e5558821e2a6cb7815940d074.
14new AND gates,113791retained instances with exact original geometry/power.
Actual Liberty SAT proves allseven original outputs at all256cutpoint inputs;
actual final NAND-toAND negative control fails as required.

Worst slow PCIe setup changes only -1.275681to-1.275034ns. No reported group
worst slack regresses; fast PCIe hold remains-0.065767ns, CPUhold-0.054434ns.
The previous header-consumed[23] endpoint drops out of the topthree paths, but
its exact new slack has NOT been explicitly measured. Do not infer its closure.
The next worst paths bind to credit_data_consumed_o[18] -> replay read_pos[2]
and[1]. A third new endpoint1165551 is not in the prior505cell binding.

Next: preserve all failures and inspect the newly critical control paths.
Potential RTL change to evaluate: clear read_pos whenever replay is idle,
instead of waiting for credit-grant/start. That can remove credit-grant timing
from the reset-to-zero cone but changes invalid-cycle output values; it needs
transaction-level equivalence and complete reset/ACK/replay/backpressure tests
plus fresh native mapping/timing. It is a proposal, NOT implemented/adopted.
Do not repeat the single-header ECO as though it closes all credit/control
paths; whole-chip setup/hold, routing and fullserialPHY remain open.


## Isolated replay idle-clear evaluation

run_cloud_replay_idle.py creates a cloud-only source overlay. Production RTL
is unchanged. It clears read_pos while !sending, removing its two start/grant
reset assignments. The proposed observation contract compares all control,
handshake and credit outputs every cycle; tx_data/SOP/EOP only while tx_valid.
Independent wrappers apply that mask; actual internal tx_eop feedback remains
unchanged. clk2fflogic preserves explicit clocks and asynchronous reset.

The full baseline/candidate replay and reliable-packet scoreboards run with
zero skipped tests. A real wrong-idle-index candidate must fail both sequential
proof and actual replay scoreboards. Any incomplete proof is retained as FAIL.
This does not prove mapping, timing, full parameter coverage or fullchip PHY.
Workflow: cloud-migration-checks.yml input replay_idle=true. Do not promote
the overlay or repeat existing native layout jobs before reading these results.


Replay idle-clear run38462752171 is active on5a29ee88c0e88b6aa8fcab7a43ff0566d984deba.
Do not promote overlay before reading sequential proof and all actual ports.
The native metal-DC workflow now accepts final_low_selects, restoring the exact
v8low-selects composition to identify remaining physical conductor resistance.
This is a read-only DC diagnosis, not loaded acceptance or altered RC.


## Cloud-only cleanup and authoritative continuation refresh

The latest instruction remains cloud-only. On 2026-10-13 the main workspace
was verified empty and no local CAD process was running. Two older checkouts
of this same repository (Documents/nssoc-public and Documents/nssoc), plus six
specific generated CAD temporary files outside the workspace, were archived
in memory, uploaded, downloaded, and SHA-256 verified before deletion.
All 2783 regular files were rehashed locally before deletion; 82721707 logical
bytes were removed. No local archive or checkout was created. Other repositories
and the user's original Downloads documents are outside this cleanup scope.

Permanent backup in release cloud-migration-final-checkout-20261013:
- asset638208020, legacy-nssoc-and-cad-residue-20261013.tar.gz
- 44933911 bytes; SHA256
  9fa1750273df0519c0e90f4cd14482bae75754056d18609bcc4777353ab0e203
- cleanup-manifest.json inside the archive binds every retained file/path/hash.

Replay idle-clear run38462752171 completed with a harness failure, not a pass.
The corrected run38463387304 on c2df40e58c2d0a7ad5c9eb9e9d51e099b4c4f4d4
passed its observable sequential equivalence and complete port controls.
Summaryasset638181971,59757 bytes,SHA256
96858095d6bb10040b8b40ac528d9b45f742bb97048fb4021524ad3777d5e2f3;
status PASS_OBSERVABLE_REPLAY_EQUIVALENCE_AND_COMPLETE_PORT_CONTROLS_NOT_TIMING.
Production RTL is unchanged. This result does not establish mapping or timing.
Next bind the exact proved candidate and baseline to a native whole-chip mapping
recipe; verify frozen capsule replay bytes before using any older synthesis
capsule. Do not present an older full-chip baseline as current physical evidence.

Metal DC run38463066637 completed with
PASS_SOURCE_BOUND_METAL_DC_DIAGNOSIS_NOT_ACCEPTANCE.
Summaryasset638172478,339654 bytes,SHA256
68c5d1276b3df10a6d8396be2d2b7eb4f95672cb456e7de8e6516199681b2ffd.
Use native resistor-to-geometry binding before selecting further metal changes;
this read-only diagnosis does not close the hot loaded-wire amplitude failure.

Main-chip route38448901835 and bounded-save32 wire38441895491 were rechecked:
both are still in progress. Preserve these handles and do not duplicate them.
The eight-hour automation remains ACTIVE and already requires cloud-only work.
Full serial PHY, main-chip routing and final setup/hold remain OPEN.


## Physical replay proof and paired full-chip mapping

The physical replay source differs materially from canonical RTL: it contains
registered byte prefetch, registered metadata and the successor address.
Run38465877636 on a1c6064078350d4834a9f933535e63e00bfbb372 passed1850/1850
observable equivalence points,11 baseline and11 candidate port tests, zero
skips. Actual wrong-idle-index mutation failed formal(2unproven) andall7ports.
Summaryasset638224436,SHA554699985261db8de530b8eb1aeb0846deded73a7a506abf5616788da8f681d9.
Sourceca334ee560f34a0d7484467d8a09ccbe7fc7b2113360f4bee7308f39bbac8e85,
candidate1bfa8971728d65ec2cfad2337d083298d7bcec8e56ce1fe4dc19f38fbcaa2edc.
Canonical proof is a separate result; neither proves mapped or routed timing.

The old ACK capsule uses WAKE1 top and registered credit-offer RTL, differing
from actual current physical19. New physical_baseline/physical_idle mapping
profiles restore the real RX-return-metadata map10 recipe and bind every read
source hash. Original top b782a7f... andcredit ba8adb6... must be used.
The original map-result10 retained a KeyError audit failure despite synthesis
returncode0. Its separately pinned map-audit14 is the corrected mapping audit,
bound by physical-result19; do not relabel the earlier failed audit.
Only the proved replay source changes in physical_idle. These are fresh paired
whole-chip synthesis/unplaced screens, not old-placement or final timing proof.
Use registered pcie-ack-cloud-mapping.yml with study=replay_idle. Preserve all
success/failure receipts and do not adopt without measurements.


Paired physical-source mapping dispatched as38466891418 on
9044757dcf8b34281f8e22228a76c79c296ce870. Actual live jobs:
115535880904 physical_idle;115535881391 physical_baseline. Both in progress.
Keep these handles; do not duplicate on observation timeout. Each restores
the same source-bound map10 recipe, same20SRAMs, five clocks and3corner
unplaced screen. New releases use cloud-results-38466891418-1-ack-map-PROFILE
with summary JSON plus full archive. Read actual status/errors before adoption.
The baseline proof run38465877636 and source/license checks both passed.
Main route38448901835 and32wire38441895491 remain live at this readback.
All work continues cloud-only; the local workspace remains empty.


## Measured paired mapping and physical-metal follow-up (14 October local time)

Run38466891418 completed both physical profiles. Sources restored correctly:
original map-audit14 status PASS_MAPPED_RETURN_METADATA_NATIVE_TIEZERO_AND_CLOCK_AUDIT.
Both contain16dual-port ETH SRAMs and4main SRAMs. No physical adoption.
Baseline79195mapped cells;idle79851(+656). Native unplaced slow PCIe setup
-1.240848 -> -1.147148ns (93.700ps improvement), but slow CPU setup margin
1.125990 ->0.251289ns. Typical RXhold -0.360791 ->-0.368361ns; fast RXhold
-0.347760 ->-0.351201ns. Fast PCIe hold remains-0.109062ns. Other negative
hold groups remain; this is unplaced before clock-tree/physical ECOs, not
a regression comparison against the currently routed placement. Do not adopt
or infer closure from the passing workflow. Candidate worst slow PCIe path
starts at pcie_link_up_i, ends at FF1165499; map to actual RTL before next ECO.
Baseline summary638249417 SHA817df9e748bbe9fe7a25180421feaae58840df41ba1d2a0cdf04fe700b9b46a4;
archive638249192,16809418bytes,SHA3d13294ba8abeb24721e289af6a14e3e41b26006060787f825e0e6b59057bec3.
Candidate summary638251056 SHAaccb288b74cf7c53529440c55bb7695d9e4e7038be6026764b417b22fc0ae372;
archive638250779,16909757bytes,checksumasset638250939. Native screen logs
SHAfe86ca5a5a4f179f8e8fe08fa830d663fae00c0a61fd64f2035a676ba3e01ee5
andfeab9c60c6ff59366e208508ffe00523773d5ec70aa30c5f5fb2ee5fffdd9ff8.

Native geometry binding38467961171 on9eb8abc869311b03d49a26ace606fd3157bf0cca PASSED.
Summaryasset638255303,797500bytes,SHA
6e769267cce4651d5428dd2d519045d7b87bfadd5b0411cc27c1226f07ad34aa.
All4043native resistors bind to unchanged composed wire graph; dominant edge
endpoints bind to native Magic coordinates and actual overlapping paint.
Scale5anchor-DBU/raw-unit;max terminal quantization2DBU. Actual shifted-port
and1percent-resistor-corruption controls rejected. Endpoint paint is NOT
proof of a unique layer or a straight physical edge. Max terminal-pair R:
ea/eb15.564287ohm,tail11.179695ohm,qn17.571188ohm,qp17.395588ohm.

Next physical candidate critical_buses_kelvin_low_selects_m3 onfinal_drive_v8
inherits exact low-selects geometry and increases only qn/qp/ea/eb M3 access
width0.6to1.0um. Tail already1.0um; all54devices and other routing unchanged.
Requires actual560category DRC,strictLVS,fivephysical faults, freshRC and
original loaded PVT. No RC scaling or acceptance claimed.


Native layout candidate dispatched38468734943 on
be7cc6a116619e8f9525f87a0af57cc045f385be; live job115542012002.
The earlier dispatch returned422 before any run because the new input was not
yet published; this is the sole actual native run, not a duplicate. Read the
layout-final_drive_v8-critical_buses_kelvin_low_selects_m3 release when done.
If native layout passes, bind its exact archive in extraction input before
freshRC/composition/loaded tests. No result yet; do not reuse low-selects RC.

Candidate mapping archive638250779 SHA256
3b639453fc6b011703961c444b8a06e6f7823714d9b22db331017d3bcf8f53eb.
Actual mapped FF1165499 hasQ u_pcie.credit_data_limit_o[2],D40788,Q14152;
its input path starts at pcie_link_up_i with0.8ns input delay, passes roughly
24logic/buffer stages and reachesD near4.725657ns against3.578509nsrequired.
Input link_up has one immediate buffer sink, so this is not simply an unbuffered
port fanout. The credit update/consume validation cone is the next RTL target.
Before repeating a static per-class credit-write optimization, inspect prior
pcie-fc-static-commit-20261012 results: its earlier formal proof exists, while
older published receipts still described mapping work as active. Preserve
source/profile separation and all earlier failed audits.


Layout38468734943 completed PASS_REAL_LAYOUT_DRC_LVS_FAULTS_REQUIRES_NATIVE_EXTRACTION_AND_WAVEFORMS:
560DRC categories/zero markers,strict hierarchical/flat54device LVS andnative
fault controls passed. Summary638274567 SHA
86294df2695187b9548944e791d62d87c07b8038d682d9c8542db3fd38d58764.
Archive638274392,394008bytes,SHA
f10c0dea2b1b85c4f042442d0d0bfb434933e8a7fd8dd0be4a1f21c2a8360fd6.
Exact geometry is now pinned in pcie-tx-cloud-extraction-input-20261013.json
under final_drive_v8 /critical_buses_kelvin_low_selects_m3. Next extraction
uses that profile; there is still no new RC/electrical or fullPHY acceptance.

Fresh extraction38469474319 is live on05ee0349c8555b86032d7758beeb8143af96e8f9.
Do not duplicate it. Read extract-final_drive_v8-critical_buses_kelvin_low_selects_m3
release; require full nativeRC graph and13fault controls before composition.
Local workspace remains empty; all CAD/tests execute on hosted runners.


Extraction38469474319 PASSED actual graph/13fault controls on the widerM3
geometry:4331R,2817C,54native devices,17conductors,112geometry probes.
Summary638284870 SHA04b5ad7021d5072fcd7ab5b69ebd9c8f52798aaf1b7daa286c17cbc3920caa8f;
archive638284559,6297265bytes,SHA
347b6944f05e7bcbc938b606818b376c4623febd4d2eb36e21a5f1447fdc0f45.
This exact extraction is now pinned for composition underfinal_drive_v8 /
critical_buses_kelvin_low_selects_m3. Native body/substrateR andRF qualification
remain outside this metal model. No loaded amplitude or fullPHY acceptance.


Composition38470027901 PASSED with54devices/4331R/2817C.
Receipt pcie-final-v8-kelvin-low-selects-m3-composition-20261013.json binds
summary638291781 SHA0bae6871c5dc048e441321b13c9de9e16e46b0565f5c7ee72f8a43539d6324dc
andarchive638291662,6700897bytes,SHA
29d0952fd201fb376ec30f851b0fa04241fe72a7e6e78bdb6cd8d0d0f5608eab.
New loaded profile v8_kelvin_low_selects_m3 uses this exact composition.
Run matched compact/wire4:1 trees with cascade158_kelvin_supply_direct and
stiff65, nominal plushot_low/cold_high, original256bits/768samples and
all unchanged native device/diagnostic limits. No acceptance until allwaves
are actually reviewed. Main32wire38441895491 androute38448901835 remain separate.


## Authoritative cloud continuation, 14 October

Main-chip seed13 run38448901835 is terminal: actual GRT-0116,132 total
overflow (M3=5,M4=20,M5=97,TM1=6,TM2=4). Not a timeout. Exact original
buffer placement SHA660692b3... retained; seed13 changes only net order.
Full failed native ODB, guide and congestion report preserved in receipt
cloud-seed13-buffers-route-failure-20261014.json. Do not rerun blindly.
Next inspect every marker/endpoint with registered congestion workflow
source_profile=seed13_buffers before choosing a physical correction.

WiderM3 loaded4:1 runs on661cb6c49e69e96524afd0d437e2ee7392c8896c:
- nominal38471108761, matched compact/wire;
- hot/cold38471122722, matched compact/wire;
- source/license/restore checks38471139570.
Exact v8_kelvin_low_selects_m3, cascade158_kelvin_supply_direct, stiff65.
Keep these handles and original acceptance thresholds; no wave results yet.
Older32wire38441895491 remains live at this readback, no duplicate.
All work is cloud-only. Local workspace verified empty and no CAD processes.
FullserialPHY, main-chip route and finalsetup/hold all remain OPEN.


## Late credit update verdict candidate

Source-bound congestion probe38471402795 andchecks38471414652 completed
successfully; inspect native diagnosis release before further routing.

New hosted run_cloud_credit_late_verdict.py restores exact ba8adb6... credit
RTL from physical_idle mapping archive638250779 (SHA3b639453...).
Only the joint header/data update verdict is factored:
(A || consume*B)*(C || consume*D) becomes
A*C || consume*((A||B)*(C||D)). Keeps early joint verdicts before late consume.
Static bank writes, every clock/reset and port behavior remain the same by
construction, but formal proof and complete tests are REQUIRED, not assumed.

Workflow cloud-migration-checks.yml inputcredit_late_verdict=true runs direct
physical-source equivalence, both baseline/candidate against frozen serial
reference, all port tests for both, and actual complemented-verdict negative
formal/port controls. All outputs compared; no validity masking in this proof.
No production RTL edits, physical adoption or timing claim. If positive
evidence passes, bind exact candidate into a paired native full-chip mapping
and compare all clockgroups/corners, not only the target PCIe setup.

WiderM3 wire jobs38471108761/38471122722 remain active at last readback;
compact jobs ended but electrical summary still requires review.


## Native132overflow diagnosis and controlled grid comparison

Native probe38471402795 passed:105actual markers sum132overflow, all
7.2um square gcells. Summaryasset638313529 SHA ca29ac20363e4f419ee3577dbd91085e48b541f91ca8d89f48e4bae72d46f01b.
Metal5 final layer overflow97; marker report uses layer '-' and must not
be relabeled as a unique metal layer. SRAM-region hotspots remain.

Next registered newer-postcts-cloud inputgrid_profile=half_xy,
routing_seed=13,placement_profile=local_optimize_buffers,ethernet_hold_depth=2,
macro_routing_profile=baseline,critical_nets_percentage=0.
Only grid origin changes3.6um peraxis relative to terminal seed13 run.
Exact same placement SHA660692b3..., SDC, LEF OBS, RC and reduction settings.
New native per-edge capacities follow shiftedpartition; no artificial increase.
Every baseline diagnosis marker and savedODB/report hash is bound first.
Requires zero globaloverflow, detailedrouting and actual extracted STA later.
OpenROAD documents grid_origin units as DBU:
https://openroad.readthedocs.io/en/latest/main/src/grt/README.html

Credit verdict proof/control run38471835755 is active onea1a231d...;
source/licensechecks already passed. Do not duplicate or adopt prematurely.
WiderM3 compact nominal/cold/hot all component_screen_passed=true,
minimum original-oracle margins281.361/272.648/229.882mV respectively.
Three physical_wire captures stillrunning; no newphysicalacceptance.


## Proved credit verdict and next paired mapping

Run38471835755 on ea1a231dc4cc2d7bf8cc806a98d7913638fdb231 PASSED:
direct physical-source2361/2361points; baseline andcandidate each285/285
against frozen serial reference;5/5baseline and5/5candidate porttests,zero skips.
Real complemented-verdict mutant fails3formalpoints andall5porttests.
Summaryasset638322232 SHA 658337c2e7cb3455e29a88248a8d738489013b4848925e7688dfc0c49a3cda35;archive638321969,208341bytes.
Exact candidateSHA7fc31891f0ae48a8df5247b6df72388ff12cf2603de9f9dc9654b30a0256d38a.
No timing improvement claimed from equivalence proof.

Existing pcie-ack-cloud-mapping workflow study=credit_verdict compares
physical_idle versusphysical_idle_credit. Both use exact actualphysical
map10recipe plus previouslyproved replayidle; onlycreditjointverdict differs.
Proof hash and actual complete positive/negative controls pinned before synthesis.
Review all3corner/5clock results,cellcount,SRAMs andendpoint cones. No adoption.

Main-chip half_xy seed13 route38472175339 on45a0dd0a... is active.
Do not restart on observationtimeouts. Allrunlogs/failures remain hosted.


## WiderM3 loaded result: rejected, all six captures reviewed

Both38471108761 and38471122722 completed. Five of six component screens
pass; hot physicalwire fails128of768samples at0.3UI,minimum16.686602mV
against unchanged100mVlimit. Later0.5/0.7phases pass; allHBT/MOS/interfaces
pass anddiagnostics empty. Actions success means simulation finished only.
Previouslowselects hot20.841388mV alsofailed: widerM3 is not the closure fix.
Full per-case immutable summary/archive hashes are in
pcie-v8-wider-m3-loaded-rejection-20261014.json. Keep every failed capture.
Next analog choice needs to reduce real mux settling delay without phase
fitting orRCscaling. WiderM3 alone is disproved; inspect shorter actual
terminal/interconnect geometry and loadedclock path before another change.

Creditpaired native mapping38472422176 ondb5369c1d... is active; compare
physical_idle tophysical_idle_credit, not olderphysical/postCTS timing.
Main-chip halfgrid route38472175339 andold32wire38441895491 remain live
at lastreadback. No duplicatejobs. Allwork stays hosted; localfolderempty.

Earlier staticFC experiment metadata readback completed from archive
634829840 SHA213a563d... entirely inRAM. decision13/rejection14 show
soc_pcie_fc_tx staticadvertisement writes regressedPCIeslowsetup219.546ps;
rejected andnotadopted. It is a differentmodule from current
soc_pcie_credit_tx peercreditverdict factoring; do not repeat orconflate.


## Shorter vertical HBT bank candidate

All widerM3 loadedcases reviewed and rejected for hot16.686602mV early
margin; do not treat completed Actions as electricalpass. Next profile
critical_buses_kelvin_low_selects_rows onfinal_drive_v8 restores original
lowselects widths, same54devices andallresistor positions, horizontal38.4um
bankpitch. Only verticalHBT rowpitch14to7.2um changes; pairedsubstrate taps
follow their devices. This shortens verticalroutes withoutthe widerM3 change.
No acceptance assumed: actual560categoryDRC,strictLVS,fivephysicalfaults
then freshnativeRC/composition/originalloadedPVT allrequired. Keep anyfails.

Existing jobs: pairedcreditmap38472422176, halfgridroute38472175339,
32wire38441895491 andlatestsourcechecks38472705185 wereconfirmedlive.
Do not duplicate them. Allwork remains cloud-only andlocalworkspaceempty.


Shortrow layout38473056743 on6bba98b5ade3a86cc3b214464fc3cc9682dc83a3
PASSED actual560categoryDRC/0markers,strict hierarchicalandflat54device
LVS andallfiveactualfaultcontrols. Summary638346326 SHA
0fccdbf22b4c1dac693a9191e1a563b5cd9a0c8d7aa7470ef9ad4098035eb4b9;archive638346125,393868bytes,SHA
402f298041bf5ff608b99c61a6ddd45061593b2f28adcbcd2b3ea1c196f116cc.
The exact new geometry is pinned for nativeextraction underfinal_drive_v8 /
critical_buses_kelvin_low_selects_rows. Freshgraph/13faultcontrols thencompositionand
originalloadedPVT stillrequired. No oldRC reused.
Pairedcreditmapbaseline completed;candidate remainslive atlastreadback.


Shortrow extraction38473550498 PASSED nativegraphand13rawfaultcontrols:
54devices,4047R,2663C,17conductors,112geometryprobes.
Summary638353146SHA2a90508c7bdce213f8e914e59f586a5af35a4f8f80ac018624555c01255af6f7;
archive638352934,6291650bytes,SHA9cdc769b9563ef69ad53230faef41667aa8736133ffa6211071872f1d66d42b8.
Exact extraction nowboundforcomposition; qualifiedsubstrate/RFPEXstillopen.

Creditpairedmapping38472422176 completed: physical_idle79851cells versus
physical_idle_credit79578cells. Both20SRAMs andsameoriginalclocklimits.
FreshunplacedslowPCIe -1.147148to-1.101756ns (45.392psbetter);CPUslow
0.251289to1.251946ns. FastholdPCIeunchanged-0.109062ns;RXfasthold
-0.351201to-0.352538ns (1.337psworse). Othernegativeholdgroupsremain.
No physicaladoption orfinaltimingclosure; inspectcriticalendpoint before
furtherRTL orphysicalrepair. BaselinelogSHAfeab9c60c6ff59366e208508ffe00523773d5ec70aa30c5f5fb2ee5fffdd9ff8;
candidatelogSHA935b57971096ec5778a08ccc802f07a93a3ff04cac3731eb571df3db8a8dbcfc.
Baselinearchive638343458 SHA01f84410750b738a588590740a383c966d88f191c9e1fe657392baebf7857a20;
candidatearchive638346608 SHAed43f52d14422ffb15c450350b5b697b61031ff50cee16d1e051a3e4374aa2be.
Summaryassets638343730/638346820 preservecompletecurrentnativechecks.


## Short-row composition passed; original loaded PVT next

Composition38473990143 one22dce0403... PASSED54native devices/4047R/2663C.
Summary638361292 SHAb278f40d11c45ae4b6ead5b8180d11dfac640f133a748fa798f563d1160fdca2;
archive638361053,6679358bytes,SHA
c9b1decbdc1a9802561933283299d27c48b8c5e097b418b29af7cc46868feaa0.
New v8_kelvin_low_selects_rows profile binds this exact composition.
Run matchedcompact/wire4:1 trees withcascade158_kelvin_supply_direct,stiff65,
nominalandhot/cold, alloriginal256bits/768samples/native devicegates.
No analogacceptance untilactualwavesreviewed.

Pairedcreditmap criticalpath nowmoved toadvertisement transmitter:
link_up input -> FF1165056 Q=u_pcie.advertiser.sent_data_o[4].
Actual source soc_pcie_fc_tx SHA599755ec5824cdea24379dbac7de7eff20cb5dd738cc4f4fd2767c8ddf73b904
inmetadata-late-select candidate02, differentfromcanonical6b5e82a0... .
Arrival4.669152ns/required3.567396ns atslow. PriorstaticFC bankwrite
experimentregressed219.546ps andmustnotberepeatedblindly. Inspectactual
acceptedEOP/ready arbitration cone. Anychange mustretain EOPcommitsemantics
andbackpressure, includecompletepositiveandactualnegativecontrols.


Loadedshortrow runsdispatched onf7829dfe3fdc77c771667b9acd984b123d7dc466:
nominal38474355636;hot/cold38474364222;sourcechecks38474375229.
Keep exacthandles. Sameoriginalgates andmatchedcompact/wire4:1profile.
Mainhalfgridroute38472175339 and32wire38441895491 remainseparate.

Nextdigital diagnosis (proposal only, NOT implemented): physicalbufferedflow
sourceSHA459d69ddaf287004099f91edf1d0c57d35fd324edf4fa9838cb994d398dd2509
already has registeredTXegress. Do not insert a duplicate stage blindly.
Arbiter chosen=locked?owner:flow_valid&&(!advert_valid||prefer_flow);
advert_ready=local_reset&&!chosen&&selected_ready. Late flow_valid from
creditlogic reaches FCacceptedEOPsent_data update. For a reachable valid
advertisement EOP (index5), firstbyte must already have acquiredadvertiser
lock; investigate/prove invariant advert_valid&&advert_eop -> locked&&!owner.
If proved with actualadvertiserandactualarbiter underarbitraryflowrequests,
reset/linkdrop/backpressure, EOPready may use the establishedowner directly,
removing unsensitizable flow-choice logic through an RTL refinement.
No falsepath/clockexception. Must retainactual acceptedEOP commitsemantics,
completebuffered/FC portscoreboards and realbad-owner negativecontrols;
fullobservable sequentialequivalence required before mappedcomparison.
Current exactFCsource is599755ec... in frozenACKcapsule; canonicaldiffers.


## Full32:1 native-macroRC nominal study completed

Old32wire run38441895491 is now TERMINAL/SUCCESS: 13877.539s native
transient,69541rows,604nativeOFFflags,allcomponentengineeringgates PASS.
All768originaloracle samples pass;minoutput158.150641mV,zero wrongsigns
andzero below100mV. Allinterfacelimits/allHBT/allMOSpass,diagnosticsempty.
Summary638367450 SHA5ecfa6f1b20e11cbcdfd9903405b00f5cb6b6cbdf9de05e41afb6864411a3e57;
archive638365881,2136119128bytes,SHA
4f5479f8be043bfa476d88ebc486ee0ceb8db29018959eb61fdc887e5f84aae5.
Fullreceiptpcie-32-native-wire-nominal-20261014.json. Do not duplicate.

Scope remains30cascade14 kelvin_supply_feed macros plusv8lowcritical final.
Intermacro connectionsanddifferentialclockphases areideal; noassembledtree
GDS/PEX,PLL/CDR,jitterBER/RFsubstrate/ESD/fullx4orchipacceptance. This is
real32:1nominalmacroRC progress, notclosure. Currentnewshortrow4:1PVT
38474355636/38474364222 remainsactive andusesdifferentcascade158prestage.
Latestchecks38474375229 passed. Mainhalfgridroute38472175339 remainsactive.
