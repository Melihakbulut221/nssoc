<!-- SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# NSSOC cloud continuation — 13 October 2026

The user requires cloud execution and removal of local NSSOC working data after
verified preservation. Use `Melihakbulut221/nssoc`, branch
`codex/complete-open-work`. Read this file and
`docs/evidence/cloud-closure-continuation-20261013.json` through the GitHub API
when the local workspace is empty. Do not recreate a local CAD checkout or
resume historical local producers. Only GitHub-hosted runners run CAD/tests.

## Current decision

**Both workstreams remain open.** Main route **38371498733** is terminal
FAILED (GRT-0116), with135native final overflow, after~2h45m. It was not a
platform timeout. Exact failedODB/congestion report/guides are preserved in
`cloud-local-optimize-buffers-route-failure-20261013.json`. Native marker/net
probe **38392685463** passed:107markers/135overflow,811involved nets.
The largest remaining clusters touch EthernetRX SRAM banks4/5 (32/33markers).
PCIe packet data flops also appear in endpoint paths. Existing placement
repair excludes every clock-connected cell and binds an older coordinate
diagnosis; do not widen its allowlist or reuse new coordinates blindly.
Do not rerun the identical candidate or waive congestion. No finalSTA exists.
New profile `local_data_endpoints` starts from the exact previous relocated
ODB, verifies all failed-ODB positions/connectivity and replays previous STA.
Its1821-cell source envelope includes227data DFFs; clock-output drivers,
delay cells, macros and all unselected cells remain fixed. Native placement
invariants, new STA and routing must pass; no acceptance yet.
Run **38395878470** is live on **e18933ba**; syntax and source checks
**38395882430** passed. Inspect its actual native replay/repair progress.
Do not dispatch another identical candidate while this run is live.
Native invariants and corruption controls passed:1747selected/744moved,
including33of227dataDFFs. New placement-estimated eth_rx slow setup regresses
+23.324ps to-4.524ps; retained as an open failure. StrictGRT is running.

v8 nominal **38389211866** passes every output sample (123.903mV minimum) but
one selectorVCE is399.203137mV, below400mV. Quarter-step **38390326921** and
PVT **38390345139** completed; read exact cases in the continuation JSON.
Hot_low wire has58wrong signs,128early margin failures and final-input common
mode1.736968..1.781254V; compact hot_low input CM passes. Cold_high wire output
passes but two selectorVCE gates fail. No limits/phases/oracle were changed.
Native identity38390363372 and voltage/current diagnosis38391010440 passed;
these are diagnostic proof, not acceptance. All failed captures remain.

**Unchanged cascade14 prestage, new dense geometry:** physical **38392202181**
passed nativeDRC/LVS/fault controls on **4a6a9a75**. Same19HBT/8R/27tap circuit;
interleaved resistors, shortKelvin return and12-column/two-row via arrays.
This targets measured upstream physical voltage loss. Native extraction
**38392967695** and native composition **38393689519** passed, retaining
54 devices / 3803 R / 2541 C. The loaded-tree prestage profile
`kelvin_dense_wide` binds its distinct immutable composition receipt.
Compare matched compact/wire streams4, final `v8_kelvin_dense_wide`, nominal
and temperature_voltage; discover existing runs before dispatch.
Loaded runs **38395107224** (nominal) and **38395110568** (hot/low and
cold/high) completed on **ad48b0d2**. Actual wire nominal and cold/high pass
all component gates:130.820/226.934mVminimum,0signal/device/interface failures.
Hot/low wire still fails128early output samples (minimum0.719mV), final-input
CM1.761..1.802V and two tailVCEs355.635/357.261mV. Compact hot/low also fails
two tailVCE gates399.271mV. No limits or phases were changed. Run read-only
`dense_v8_hot` voltage/current diagnosis before the next circuit change;
Diagnosis **38396710373** passed on **899557cc**. Actual hot native waveforms
show about66mVdrop between selector emitter andtailcollector, plus34mVtail
emitter lift. Investigate local tail/return physical losses and the remaining
input common-mode failure. No artificial RC or phase changes. Source checks
**38396713550** passed.
New final-v8 physical candidate `critical_buses_kelvin_tail_paths` widens
only tail M3(0.6to1.0um), tailTM1(1.64to3.0um) andlocalM5return(0.8to1.6um).
This addresses measured hot metal drops, with alldevices andgates unchanged.
Physical DRC/LVS/fault controls, fresh RC and loaded waveforms must pass.
Discover the existing physical run before dispatch.
No prestage dense electrical acceptance yet. Full32:1, actual clocks/CDR,
assembled PHY/layout and final chipSTA remain open. All work stays in GitHub;
local workspace remains empty.

## Preservation and local retirement

**Completed on 13 October 2026:** the local workspace is empty and the
NSSOC temporary output/controller directories have been removed. All nine
final source/Git archive groups passed hosted per-member readback. The
[retirement receipt](https://github.com/Melihakbulut221/nssoc/releases/download/cloud-migration-final-checkout-20261013/retirement-progress.json)
binds 36,067 final entries and 3,008,078,533 logical bytes. The preceding
all-family reconstruction run 38364679770 passed all four groups.

- Main output migration completed: 397,166 planned paths, 448 archive batches,
  274,984,789,765 logical original bytes removed after immutable remote receipt
  verification. This is a logical byte count, not an allocated disk-space claim.
- PNR and tool-file migrations completed earlier; their independent hosted
  readbacks passed. Historical sources, links, scratch and external checkouts
  have separate receipts under `docs/evidence/cloud-*-cleanup-20261013.json`.
- Final all-family reconstruction:
  [38364679770](https://github.com/Melihakbulut221/nssoc/actions/runs/38364679770).
  All four groups completed successfully; this validates archival recovery,
  not chip signoff.
- Temporary `/dev/shm/nssoc*` and `/tmp/nssoc*` preservation uses release
  `cloud-migration-transients-20261013`. The first two batches had local full
  remote readback; subsequent batches use hosted per-member readback. Each
  manifest binds an immutable archive, original paths, modes and hashes.
- Final checkout preservation uses release
  `cloud-migration-final-checkout-20261013`. It includes **all Git objects**,
  sources and controller state, including original-location records for six
  ancillary `/tmp` scripts. Do not infer that cleanup completed from this file:
  the authoritative proof is that release's `retirement-progress.json`, with
  status `COMPLETE_VERIFIED_CLOUD_HANDOFF_EMPTY_LOCAL_WORKSPACE`.
- Final checkout deletion requires completed transfers, pushed clean source,
  a dispatched cloud reconstruction, stopped local controllers, and exact
  hosted archive member proof for each batch. Original files are rehashed
  immediately before unlinking. Links are preserved as metadata; targets are
  never followed. Changed or newly created files stop final completion.
- If interrupted during final retirement, the temporary restart controller is
  `/tmp/nssoc-final-checkout-20261013/resume.py`; run it with
  `PYTHONDONTWRITEBYTECODE=1` only to resume transfer/cleanup. It is deleted on
  success. Its code, inventory and manifests also reside in the final-checkout
  release. Do not restart a full migration blindly.

The eight-hour task automation now reads cloud state and prohibits local CAD
and recloning. It reports meaningful changes, not unchanged polling results.

## Historical engineering entries — superseded by Current decision

Earlier live-status entries below are dated work history; they are not current
run state. Read Current decision and the continuation JSON first.

### Engineering state — still open

Full serial PCIe Gen3 x4 PHY, main-chip PCIe/Ethernet detailed routing and final
setup/hold are **not complete**. Component screens are not full PHY, qualified
RF/body extraction, assembled analog clock/CDR/ESD integration or foundry
acceptance.

- Main routing run `38347061685` failed with GRT-0116: the native SRAM M5
  reservation regressed total overflow from 147 to 158 (M5 itself fell from
  108 to 94). Exact failure ODB and marker hashes are preserved in
  `cloud-reserved-m5-route-failure-20261013.json`; use congestion probe
  profile `reserved_m5` to diagnose it. Broader placement run `38334595459`
  is terminal: both jobs exceeded the six-hour hosted limit, verified in job
  annotations. No route acceptance; do not repeat these broad placements.
  A targeted `local_optimize_buffers` candidate expands the local endpoint
  selection to data buffers/inverters while preserving all clock cells and
  unchanged logical/physical invariants. Inspect the current checkpoint.
- Combined via-array loaded tree `38360782776`: compact control passed; wire
  case rejected with 69 wrong signs, all 128 early samples below 100 mV, and
  six HBT minimum-VCE failures. All interface amplitude/common-mode gates
  passed. Original bits, sample phases and limits remain unchanged.
- Dense final MUX: native physical run `38362060912` passed DRC, strict LVS and
  five fault controls. Native extraction `38362407566` passed graph checks and
  13 corruption controls, producing **2875 R / 1986 C**. Exact composition
  `38364385250` passed, retaining 54 native devices. Loaded-tree run `38365522474` completed: compact passed; wire rejected.
  Wrong signs fell to zero, but 128 early samples remain below 100 mV
  (minimum 4.927 mV), and four HBT minimum-VCE gates fail. Both interface
  gates pass. The candidate is not adopted.
- Use `tx-tree-physical-cloud.yml` with `streams=4`,
  `physical_profile=power_trunks_vias`, `physical_final=matched`,
  `physical_final_profile=kelvin_dense`. Discover an existing run before
  dispatching. Run `38365522474` is the completed nominal comparison; do
  not duplicate it. Each compact/wire job publishes complete immutable captures.

Persist meaningful source fixes and evidence to the same branch; use release
assets for large results. Do not download bulk CAD results onto this computer.

## Latest cloud experiments

- Wider two-row via geometry: physical 38371051654, native RC 38371728150
  (3889 R / 2593 C) and exact 54-device composition 38372215192 passed.
  Loaded-tree comparison **38372656723** completed: compact passed; actual
  wire candidate rejected. There are zero wrong signs, but **127 early samples
  below 100 mV** (minimum **14.320 mV**) and **four HBT minimum-VCE failures**.
  Both interface gates pass. Original sample phases and limits are unchanged.
  Source-bound summary hashes and exact failing-device values are in the
  continuation JSON. Diagnose actual conductor losses before another geometry
  change; artificial RC reductions are diagnostic only, never acceptance.
- Data-buffer local placement route **38371498733** is live. Its exact source
  envelope contains 1563 eligible endpoints before clock exclusion; 1505
  cells are selected and 960 moved. Connectivity, masters, all unselected
  positions and both native corruption controls passed. Placement-estimated
  timing still has violations and is not routed timing closure.
- Four-row via geometry 38370105586 is rejected with 38 M3 spacing markers.
  No physical rule or waveform acceptance threshold was relaxed.
- Source licence/inventory/REUSE and migration regression checks
  38372661182 passed on b9091be1. No local checkout or test files were created.

## Conductor-loss diagnosis and next physical candidate

- Native metal comparison **38375278729** passed both dense profiles. Wider
  via columns reduce the worst internal terminal-pair resistances by about
  0.88–0.95 ohm; 15.93–18.82 ohm remains in the wider candidate.
- Unmodified actual control **38375733511** completed: raw-wave hash, complete
  review and contract exactly reproduce **38372656723**. Its seven initial
  sensitivity preparations failed before simulation on the appended
  capacitance-only `wire_cref`; failed captures are retained.
- Corrected sensitivity **38376209270** completed all seven cases. Actual
  source models, all C/device lines, original bits/phases/limits are bound.
  All final metal R scaled by0.01 yields **208.441 mV**, zero signal/device/
  interface violations. This artificial model is **not physical acceptance**.
  Internal-only scaling removes all four HBT failures but leaves59early
  samples below100mV (minimum76.063mV); supply-only reaches64.125mV with
  two HBT failures. Return-only creates19HBT failures and fails an interface.
- New actual geometry **38377693620** widens only `qn`, `qp`, `ea`, `eb`,
  `tail` TM1 trunks from1.64to3.0um on existing4.8um lanes. It keeps devices,
  return/bias geometry, via arrays and extraction coefficients unchanged.
  Source **e1903ed4** passed all560DRCcategories with0markers, strict
  hierarchical/flat54-deviceLVS andfivephysicalfaultcontrols.
  Native RC extraction **38378229860** is running on **fea63a53**. Inspect
  every native graph/C check and13corruptioncontrols, then bind composition
  and rerun original fixed-phase waveforms. No electrical adoption yet.
- Source licence/inventory/REUSE and migration regression **38376372112**
  passed on126bf5a6. Local workspace remains empty; all CAD/tests are hosted.

## Latest physical feedback

- Signal-trunk native extraction **38378229860** and54-device composition
  **38378560821** passed, retaining3889R/2593C.
- Actual waveform **38378858151** rejects TM1-only widening: minimum
  **7.343mV**,128early samples below100mV,fourHBTminimum-VCEfailures.
  Compact control and both interfaces pass. No geometry adoption.
- Static diagnosis **38378860794** measures0.45–1.07ohm less internalR,
  so resistance improvement alone did not predict the loaded waveform.
  Native resistor-node source inspection **38379231148** is preserved.
- Actual M3 sweep **38379810177**:0.8um and1.0um pass560-categoryDRC,
  strict54-deviceLVS andfivefaultcontrols;1.2um fails16M3.bmarkers.
- New **M3-only** geometry **38380208915** retains1.0umM3 but restores
  original1.64uminternalTM1 to separate the two changes. Source **b788a975**.
  Native geometry gates must pass before new RC/composition/waveforms.
- Licence/inventory/REUSE and migration checks **38378864232** passed.
  Main-chip route **38371498733** isin_progress at this check.
  FullserialPHY,detailedmain-chiproute andfinalsetup/hold remainOPEN.

M3-only physical run **38380208915** passed all 560 DRC categories with
zero markers, strict hierarchical/flat LVS, and five fault controls.
Native extraction **38380642029** is **in_progress**, using source
**21c8aac8** and the exact physical archive receipt. Inspect this existing
run before dispatching anything else. A physical pass is not electrical
acceptance: new native RC, composition and fixed-phase waveforms are required.

## v6 physical continuation

- Corrected v6 run **38383289620** passed all 560 DRC categories with zero
  markers, strict hierarchical/flat 54-device LVS and native fault controls.
  The first run **38382891663** failed an ea-to-avdd short because the resistor
  spacing/interleaving condition omitted v6; **73cf305a** fixes that condition.
- v6 reduces 16 data/selector HBTs from Nx8 to Nx4; the reference, tail HBTs,
  eight resistors and 27 substrate contacts retain their original contracts.
  It is an unscreened electrical candidate, not a completed serial PHY.
- v6 extraction **38384179434** passed native graph and 13 corruption controls
  with **3893 R / 2594 C**. Composition **38384468517** passed, preserving all
  54 devices. Its distinct receipt is `pcie-final-v6-kelvin-dense-wide-composition-20261013.json`.
- Run the unchanged loaded-tree oracle using final profile `v6_kelvin_dense_wide`,
  matched compact/wire, streams4 and prestage `power_trunks_vias`. Discover an
  existing run before dispatching; electrical acceptance remains unproven.
- The local workspace was checked again and remains empty. All CAD and tests
  continue on GitHub-hosted runners. Routing run **38371498733** is still live.

## Loaded v6 and rejected M3-only geometry

- M3-only widening **38381257427**: compact passed, extracted wire failed.
  Zero wrong signs, **127 samples below 100 mV**, minimum **6.725 mV**, four
  HBT minimum-VCE failures; both interface gates passed. It is rejected.
- v6 loaded comparison **38384881419**, source **03fd06b3**, uses the actual
  native v6 model and its own newly extracted RC. Nominal streams4 compact
  and wire controls are running with the original bit/phase/device limits.
  It has no electrical acceptance yet. Source checks: **38384885565**.
- Profile-corruption regression rejects a validly hashed v5 report when v6
  is requested. Device accounting uses the actual Nx4 emitter multiplicity.

- v6 compact control completed: **768 samples, 278.590 mV minimum**, zero
  bit/amplitude/device/interface violations and no simulator diagnostics.
  The wire job in **38384881419** is still actively simulating. Compact pass
  is not physical acceptance. Source/REUSE/migration checks **38384885565** passed.

## v6 complete result and v7 continuation

- v6 wire **38384881419** completed: all **768 output samples pass**, minimum
  **140.606 mV**, no wrong signs, both interface gates pass and no numerical
  diagnostics. Overall engineering screen still **fails**: tail HBTs
  `xmux.xd0006` and `xmux.xd0007` reach **388.383 / 387.043 mV VCE**,
  below the unchanged 400 mV limit. This supersedes the earlier live status.
- Exact hosted native-model readback **38385901575** proves both failed
  instances are Nx8 tail HBTs with collector `n_66`, base `iref`, emitter
  `avss`. Do not infer roles from instance names across different extractions.
- v7 keeps twelve data HBTs Nx4, reference/tails and all R/taps unchanged;
  only the four selectors grow Nx4 to Nx8. Recovering tail headroom is a
  hypothesis, not acceptance. Physical run **38386165678** is dispatched.
  Follow exact physical -> new RC -> new composition -> unchanged loaded
  compact/wire gates. v6 failed captures are retained; no limit is relaxed.

- Physical-tree workflow now also supports distinct `study` selections for
  temperature/voltage, 12 independent HBT/resistor corners, six MOS corners,
  quarter-step convergence and three actual circuit faults. Defaults remain
  nominal; expanded studies are available but have not yet run for v7. They
  are engineering screens, not qualified RF/body/temperature wire extraction.
