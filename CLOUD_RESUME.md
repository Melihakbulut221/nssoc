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

**Full serial Gen3 x4 PHY, assembled main-chip routing and final setup/hold
remain OPEN.** All CAD/tests run in GitHub. The local workspace is empty.

### Completed loaded native-wave studies — both candidates rejected

- Isolated **local-tail finalv8 + cascade14 dense prestage**:
  **38402054648** nominal and **38402059863** hot/low and cold/high completed.
  Nominal and cold wire screens pass (132.196mV and231.217mV minimum).
  Hot wire fails:19wrong signs,128samples below100mV,two HBT minimum-VCE
  violations and low final-input common mode. Compact hot also fails two tails.
- Combined **cascade16 dense prestage + local-tail finalv8**:
  **38402506838** nominal and **38402511999** hot/cold completed.
  Nominal and cold wire screens pass (132.700mV and231.437mV minimum).
  Hot wire fails:10wrong signs,128samples below100mV,eight HBT minimum-VCE
  violations; final-input CM minimum1.797377V is below1.8V. Compact hot tails
  remain below0.4V; compact cold final-input CM maximum2.051158V exceeds2.05V.
- All12 exact compact/wire summaries, source scopes and SHA256 values are
  retained in JSON `completed_local_tail_comparison`. Original256bits,
  768samples, phases and every acceptance limit remain unchanged.
  Neither candidate is adopted. Green Actions denotes captured results,
  not engineering acceptance. Do not duplicate these unchanged studies.
- Diagnose actual voltage/headroom and propagation delay before selecting the
  next circuit or geometry candidate. Full32:1, actual clocks/CDR, RF/body/ESD
  and assembled serial PHY remain unproven. All work stays cloud-only.

### Latest completed loaded comparison — neither candidate accepted

Local-return finalv8 physical chain passed:38406919993 nativeDRC560/0,
strict hierarchical/flat54deviceLVS and5faultcontrols;38407758550 native
4038R/2663C and13controls;38408254672 exact54device composition.
First failed geometry38406101139 and its two M4/M5 markers are preserved.

- Baseline clock38408821480/38408827819 completed: nominal andcold wire
  pass, but hot wire fails14wrong signs/128low samples,two tailVCE minima
  372.080/368.592mV and final-inputCM1.758..1.801V. Rejected.
- Native XOFFSET length6.5to7.5um38409336938/38409346107: all three compact
  conditions pass. Wire hot removes HBT violations but fails22wrong signs,
  128low samples andinputCM. Nominal/cold wire each fail four selectorVCE
  limits (worst386.357mV/379.879mV). Rejected. No physical clock-reference
  integration claimed. Bits, clockphases and every limit stayed fixed.
- Source checks38409350848passed. All12exact cases are in JSON fields
  local_return_candidate and native_clock_offset75_candidate.
- Next: local_return_comparison DC diagnosis of actual local-tail/local-return
  andcascade14 dense prestage supply/return/internal paths. Never rerun these
  unchanged failed waveforms or relax the acceptance contract.

Continuation JSON now exceeds1MiB: if GitHub Contents API returns encoding
none, read the same blob through git/blobs/<sha>. Do not treat empty inline
content as data loss or recreate a local checkout. FullPHY and finalSTA OPEN.

### Active combined loaded study — two real upper-metal supply feeds

- Cascade14 supply-feed chain passed: physical38412608409, nativeRC
  38413237032(3810R/2545C), composition38414112027. Exact profile
  `kelvin_supply_feed` is bound. DC38415351214 measured avdd7.034/8.203ohm
  versus old8.029/9.196ohm. Native terminal numbering changed; bind roles
  through the exact models rather than reusing old instance IDs.
- Finalv8 local-return plus supply-feed chain passed: physical38414116532,
  nativeRC38415063817(4043R/2666C), composition38415678520. Exact profile
  `v8_kelvin_local_supply` is bound. Both54device circuits are unchanged.
- Next original-bit loaded comparison: matched compact/wire, streams4,
  prestage`kelvin_supply_feed`, final`v8_kelvin_local_supply`, native clock
  reference`offset75`, nominal andhot/cold. Preserve every earlier failure.
  Both feeds require actual electrical/PVT proof; no acceptance from DC.
- Dispatched on `aca3bac7193aa1957fd91295d126147f53b38166`: nominal **38417298237**,
  hot/cold **38417305677**, source/migration checks **38417310283**.
  Results pending; do not duplicate these studies. This dispatch record
  is superseded by the completed summaries in continuation JSON.
- Local retirement reverified: workspace and NSSOC temporary directories empty,
  no local CAD processes; retirement receipt SHA256
  `23f8d33591444bb1d22d18a8668142de3c52e906b4dddfbf98118b614d78bcbd`.


### New native internal-route candidate

Hot/cold full-wave diagnoses38420038719/38420042839 completed with exact
source binding and corruption controls. Cold final selector collectors lose
about103mV mean versuscompact, while emitter means rise17-21mV; allfour
selector VCE minima fail. Hot clock-to-MUX transitions takeabout21-24ps,
versusabout9.5ps compact; source-to100mV events reachabout40-44ps andmiss37.5ps.

Candidate `critical_buses_kelvin_local_internal` on final_drive_v8 addsreal
parallel eaM4 andebM5 local routes at16/20um, eachjoining nineactualterminals.
It inherits localreturn/supply/tailgeometry andall54devices unchanged.
Native DRC/strictLVS/physicalfaults run **38421020866** onb93f626c
passed; summarySHA4f595f2018ed2e7c380cb1495fb23d661370185bd09e7d8a4059fbe4318612b3.
The407594byte physical archiveSHA8c389ea1e016eb090f2d3c760aebc53731ea7cdb10cf42a78a755dc74a4d2754
is bound for fresh native RC extraction **38421789099** on5ebf5c2b.
Physical report confirms560DRC categories/zero markers andstrict54device
hierarchical/flatLVS plusfivefaultcontrols. Electrical acceptance remains unproven.
Native extraction38421789099passed:54devices,4233R/2742C,112geometryprobes,
all13corruptioncontrols. SummarySHAacb026e1b983eaa0765e80600137e789f02fffe9d646e3a0d87528cefc4364b8.
Exact6307738byte archiveSHAfdc429e0d10f8f51657d07bd0f1e400f2c588215cd1f6621458a910475b804c4
is nowbound fornativecomposition; next matchedloadedPVT requires its output.
Body/well resistance andRF/point-attachment qualification remain open.
Latest source/license/migrationchecks **38421374578** passed onb1e9e234.
This is a physical hypothesis, not adopted circuitry or fullPHY completion.
Main-chip timing-priority route **38420407838** is active ondb3a36b3.

### Exact physical sources for these studies

- Local-tail finalv8: physical **38400244543**, RC **38400976763**, composition
  **38401482919** passed;54native devices/4000R/2643C. Adds real M4 local
  tail shunt and M5-to-TM1 return feed, preserving the circuit.
- Cascade16: physical **38400973160**, RC **38401479870**, composition
  **38402050497** passed;54native devices/3803R/2541C. Only two native
  outputpulldown lengths change14to16um; other19HBT/6R and27taps unchanged.
  Explicit circuit binding and regression reject a validlyhashed cascade14
  report when cascade16 is requested. No electrical acceptance from LVS.
- Prior wider-tail runs38398957797/38398961815 completed: nominal134.431mV
  andcold232.281mV pass allcomponentgates;hot has2wrong signs,128early margins,
  two tailVCE failures360.980/362.383mV andlowinputCM1.760..1.802V. Rejected;
  all captures retained. Earlier metalDC showed widening alone insufficient.

### Main-chip route — incremental endpoint candidate rejected

**38395878470** completed with native GRT-0116 and **420 overflow**:
Metal2=4,Metal3=120,Metal4=47,Metal5=213,TopMetal1=25,TopMetal2=11.
Previous local_optimize_buffers had135; endpoint movement regressed congestion
and eth_rx setup estimate (+23.324ps to-4.524ps). Not adopted; not a timeout.
Exact failedODB/report/archive hashes are in JSON local_data_endpoints_terminal.
Native congestion diagnosis **38419533968** completed:151markers/420sum,
1034involvednets versus107markers/135sum/811nets before. Worst new bottlenecks
cluster onx2340um (maximum31overflow versus4before);427nets newlyinvolved.
The moved-endpoint candidate is rejected. Next isolated routing trial uses
exact prior buffer-only placementSHA660692b3..., native critical-net priority30.
PDK capacities, placement, SDC and zero-overflow gate remain unchanged; source
ODB hash mismatch aborts. This changes routing order preference, not acceptance.
Reference: https://openroad.readthedocs.io/en/latest/main/src/grt/README.html#global-route

Supply-feed loaded nominal/cold wire each still fail four selector VCE gates.
Compact nominal/hot/cold pass. All available exact summaries are in JSON
combined_supply_feed_loaded_study; hot wire failed17wrong signs/128low samples andinputCM minimum1.759834V.
Native DC38418508613 passed: final supply7.584/9.239ohm versus8.579/10.233.
This modest improvement does not close the loaded failures or full PHY.
Next loaded diagnosis: supply_feed_hot andsupply_feed_cold bind exact original
compact/wire captures; no resimulation, phase shifting or acceptance changes.

Earlier entries below are preserved work history; this section and the JSON
continuation are authoritative for what to inspect next.

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

## Current local-tail and prestage follow-up

Local-tail physical **38400244543** on **ee050fe7** passed560DRC/0markers,
strict54deviceLVS andfivefaultcontrols. Fresh nativeRC is next; discover the
existing extractionrun before dispatch. Wider-tail hot waveform already
fails2wrong signs,128early margins,two tailVCEs andlowinputCM; not adopted.
Separate **cascade16** changes only two native outputpulldown lengths14to16um
under unchanged densegeometry. It targets hotCM while retaining cold2.05V
maximum. This new circuit requires physical/RC/composition andalloriginal
loaded gates; discover its existingphysicalrun before dispatch.

## Latest verified gates

Wider-tail loaded runs38398957797/38398961815 completed: nominal134.431mV
andcold232.281mV pass allcomponentgates;hot has2wrong/128earlymarginfailures,
two tailVCE andinputCMfailures. Overall rejected; allcaptures retained.
Local-tail extraction **38400976763** passed with4000R/2643C and13controls.
Compose its own exact devices next, then isolate its loadedwave effect with
unchanged cascade14denseprestage before combining the newcircuit.
Cascade16 physical **38400973160** passed560DRC/0markers,strict54deviceLVS
andfivefaultcontrols. NewRC extraction is next. Discover existing composition/
extraction runs before dispatch. Mainroute38395878470 remains live.

## Local-tail waveform and cascade16 composition continuation

Local-tail composition **38401482919** passed54devices/4000R/2643C.
Final profile `v8_kelvin_local_tail` binds its immutable receipt. First
load it with unchanged prestage`kelvin_dense_wide`,matchedcompact/wire,
streams4,nominal andtemperature_voltage. Discover existingruns first.
Cascade16 extraction **38401479870** passed3803R/2541C/13controls. Compose
its exact newdevices next, then add an explicitcascade16prestage binding
before combined loaded PVT. No adoption from any of these component gates.

## Combined native circuit experiment

Isolated localtail loaded runs **38402054648** nominal and **38402059863**
hot/cold are live on **e0831791**; sourcechecks38402063326passed.
Cascade16 composition **38402050497** passed54devices/3803R/2541C.
The distinct prestage profile`cascade16_kelvin_dense_wide` binds the actual
newcircuit; regression rejects a validlyhashed oldcascade14 report. Run
matchedcompact/wire streams4 with final`v8_kelvin_local_tail`,nominal and
temperature_voltage,discovering existingjobs first. All original bit/phase,
1.8..2.05V CM anddevice gates remain unchanged. No component adoption yet.
