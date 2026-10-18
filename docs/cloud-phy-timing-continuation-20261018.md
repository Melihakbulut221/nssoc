# Latest: real hybrid38 metal short identified and geometry corrected

Reader39106052671 found actual AVDD|SUB and tail short in native extraction, despite zero DRC. Metadata shows1.18um center spacing between1.2um-wide local SUB and AVDD columns, plus one legacy tap overlapping a tail column. New generator physically moves taps into available columns and enforces2um spacing for all distinct-net M4 columns. Source,38devices and native gates unchanged. This commit triggers the next `cdr-sampler-hybrid-physical-cloud` run; inspect it before parent integration. Evidence `cdr-hybrid-native-short-diagnosis-20261018.json` retains actual failing netlists.

Mainchip39084569446 terminal cancelled at six hours, with real `drt-run-0/soc_top.odb` and `drt-run-1/soc_top.odb` saved in the published archive (not final signoff). Reader39106213346 completed in cloud; inspect logs/state inventory to continue from a real saved route, not cold restart. Its result has not yet been reviewed. Existing RCX/STA workflow still awaits successful route/antenna/connectivity gates. Cloud-only, full objective OPEN.

Earlier checkpoint follows:

# Latest: hybrid38 DRC passed; native LVS diagnosis required

Hybrid local-tap run39105690621 passed all560 DRC categories with zero markers and rejected actual offgrid fault. Deep LVS extracted exactly38 devices on both sides but NoMatch, so physical acceptance is not granted. Full report preserved `cdr-hybrid-local-taps-lvs-failure-20261018.json`. This commit launches `cdr-hybrid-lvs-diagnosis-cloud.yml` to restore and read exact native extracted/reference/deck/cross-reference files on a hosted runner. Inspect that result before a geometry/source repair; do not rerun unchanged geometry or weaken LVS. Mainchip39084569446 is now terminal cancelled; inspect actual logs and failed publication before preparing resumable routing. All work cloud-only; goal remains OPEN.

Earlier checkpoint follows:

# Latest: hybrid physical LU.b failure retained; local body contacts added

Hybrid physical39105291849 failed two LU.b markers after successful real generation. Native source2f46efe4f1d24c6eb130d43fc2e75e5e266dc71c and full failure are in `cdr-hybrid-tail-initial-latchup-failure-20261018.json`. The successor adds3 real local2x2um substrate contacts alongside the MOS midpoints, retaining8 original contacts. Actual circuit now12HBT+3MOS+12R+11taps=38. Fresh560DRC/unsimplified deep-flat38LVS/twelvefaults/LEF required. This commit's workflow push starts the successor; inspect its exact result, no pass assumed. Cloud-only. Full PHY and final timing OPEN.

Earlier checkpoint follows:

# Latest: real hybrid sampler physical workflow prepared

New `cdr-sampler-hybrid-physical-cloud.yml` is push-triggered by this commit. Find its exact new run and inspect actual generation/DRC/LVS/12-fault results. It uses the exact schematic source that passed39104163004, native single-finger LVNMOS with real gate contact, finite taps and bbox-aware placement. No physical pass yet. Source/checker geometry deltas are pinned in `cdr-sampler-hybrid-physical-delta.json`; original gates remain. See `cdr-hybrid-tail-physical-20261018.md`. Preserve any failure before repair; do not accept old sampler/parent proof for this changed circuit. Mainchip39084569446 is still the existing handle; recheck terminal state, no duplicate live run. Cloud-only; full goal OPEN.

Earlier checkpoint follows:

# Current: cloud-only work; hybrid-tail sampler schematic passed

Checked 2026-10-18T06:41:26.112467+00:00. The user's latest instruction is to perform all work in the cloud and leave this workspace empty. `/home/hasanmelih/Documents/ChatGPT/nnsoc` was inspected empty, and no local CAD process is running. All new source changes use the GitHub Git Data API; native CAD, tests, archive restoration and generated artifacts must remain on hosted runners. Do not recreate a local checkout or download native archives. Do not touch the unrelated nssoc-upstream directory. The older goal wording requesting local work is superseded.

Hybrid sampler source0be3c44ebcb97d145774f80788401f4d998a1f1d/run39104163004 completed all five native schematic cases. The circuit preserves the original12 switching HBTs and12 resistors, replacing the reference and two tail HBTs with native LV NMOS (8u/.3u and32u/.3u, single finger). Nominal/hot_low/cold_high each passed768 original samples, zero wrong signs/under100mV; minimum signed margins183.632/173.642/180.392mV and maximum clock-to-valid20.469/23.281/18.594ps. All12 HBT and3MOS voltage/current gates passed,12 native OFF flags were read back, zero-source OP was zero, and no numeric diagnostics occurred. Both swapped-output and stopped-clock controls failed the actual data gate as required. Full reports and immutable asset hashes are in `docs/evidence/cdr-hybrid-tail-schematic-pass-20261018.json`.

This is an external-clock schematic screen, not a physical sampler, complete CDR, recovered clock, PVT qualification or full PHY. Next implement real hybrid primitive geometry with native MOS PCells, appropriate body contacts and bbox-aware placement. Start from `hw/soc/flow/make_pcie_sampler_left_v1.py` / `check_pcie_sampler_left_v1.py`, adapting the true circuit and census to12HBT+3MOS+12R plus actual taps. Existing20um placement pitch cannot be assumed safe for32um-wide MOS. Require fresh560-rule DRC, unsimplified deep/flat LVS and genuine negative controls, then new parent integration, full native RC and unchanged original loaded gates. Old394-device physical proofs/RC cannot be reused for the changed circuit.

TX reference/tail diagnosis39103565940 also completed. It matched31 actual same-macro reference HBTs and62 tails to the original immutable failed capture. Tail emitter means are higher than their reference emitters; tail VBE is lower. Thus the proposed excess-current explanation from a lower tail ground is not supported. This is diagnosis only: all28 original failures and full waveform rejection remain. See `docs/evidence/tx-return64-bias-return-diagnosis-20261018.json`. CDR left-path diagnosis39102905377 reproduced14 failures and weak retimed inputs (roughly16mV differential RMS); full original loaded39102038200 remains rejected.

Mainchip detailed route39084569446 status at this check: in_progress/None. Preserve this existing run; do not restart a live job due to a polling timeout. It started00:55:39Z with a360-minute hosted-job limit; no DRT snapshot is configured. If it terminates, inspect the real terminal logs/artifacts and preserve failure before deciding a successor or native continuation strategy. Prepared `replay-onehot-routed-extraction-cloud.yml` may run only after this exact route passes its DRC/antenna/connectivity gates with verified artifact hashes. It has not yet run. Full serial Gen3 x4, routed mainchip acceptance and final setup/hold remain OPEN.

Earlier checkpoint follows:

# Latest CDR loaded rejection — fresh path diagnosis next

Original loaded39102038200 at89c79686f7140e8d4700048fe825acf984864432 is TERMINAL FAILED. Both nominal native simulations returned0 with no numerical diagnostics and unchanged sources, but original data/device gates failed. Early wrongsign113/287/365/400 of765 each, phase+0.06670157257569277V wrong direction; late129/76/362/398, phase+0.07064891447538851V correct direction but sampling/device failures. Each has14 HBT VCE failures. Fresh physical placement changed native IDs: failures15,23,31,38,46,54,69,75,85,92,99,105,115,122. Do not reuse old risers device IDs. Clock-stop and VI-bias-off negatives were detected. Full immutable captures and receipts are preserved in `cdr-left-full-wire-rejection-20261018.json`.

`cdr-left-path-review-cloud` is being launched. It uses the exact left-output model,9946R7771C, actual native planes and original raw early/late captures. Reproduce original sampler and HBT gates, then inspect new supply/collector/base/retime input voltages. No new simulation, source threshold/phase fitting or scaled RC. The left-output physical/model chain remains a scoped pass, not an electrical improvement or full PHY acceptance.

TX39087664998 remains rejected; its exact waveform/physical analyses39102156220/39102430979 passed as diagnosis only. See `tx-return64-native-rejection-analysis-20261018.md` for the28 failed devices and next actual bias/headroom/high-speed-path work. Mainchip detailed route39084569446 remains live at last check. Preserve that job and use only its eventual successful exact route for prepared RCX/STA. Full PHY and final timing remain OPEN. This turn made progress by completing native evidence and identifying rejected candidates. All execution cloud-only; local workspace empty.

Earlier checkpoint follows:

# Latest TX physical localization complete — electrical rejection retained

Run39102430979 atfdf4610a24eb6d378c4f10a3e2f2ed99fc11bdf2 completed exact physical source/path mapping for all28 failed TX HBTs. Receipt `tx-return64-physical-paths-pass-20261018.json`; analysis `tx-return64-native-rejection-analysis-20261018.md`. Failures distribute across final f6,p4_3 four,p8_1/3/7/5 four each,p8_6 two. Final tail emitter means104mV and shortest return paths13.98/14.02ohm; VCE still356–357mV. Shortest paths are not effective impedance/delay. Need actual bias/headroom and level4/final timing repair; do not repeat return widening without evidence. Full native original gates remain failed.

CDR left-output loaded39102038200 and mainchip route39084569446 remain existing live handles at last verified check. Poll those exact runs. If CDR fails, retain all original cases and diagnose new captures/IDs; if it passes, continue full-loop/PVT/timestep qualification. Route must independently pass native routing gates before prepared current-route RCX/STA is dispatched with exact artifact hashes. Full serial Gen3 x4 and final mainchip timing remain open. All work cloud-only; no local checkout/native artifacts.

Earlier checkpoint follows:

# Latest TX diagnosis complete; actual physical paths next

TX return64 path diagnosis39102156220 at87dec08e69f69a4f9e788642ab1d297092a803dd passed exact original gate reproduction. Full receipt `tx-return64-path-review-pass-20261018.json`. All28 failed HBT terminals were measured. Final tail emittersxd0114/115 mean about104mV after widening, versus prior172mV; their original minimum VCE still fails around356–357mV. The repair therefore changed actual rail behavior but did not close the waveform or device gates. Other failed devices need exact current native-ID-to-macro mapping before changing them.

`tx-return64-physical-paths-cloud` is being launched against the exact return64 composition39087377122 and physical source671f86f8d41fafc474ecb879ba4438ced28c1ff7. It verifies every restored file against the simulated source and maps all28 devices to their actual macro and resistor/capacitance paths. Shortest resistor-path sums are not effective impedances/delays or acceptance. No model or waveform changes. Original TX nominal39087664998 remains rejected.

CDR loaded39102038200 and mainchip route39084569446 remain existing live handles; preserve them. Full goal remains open, work cloud-only.

Earlier checkpoint follows:

# Live cloud handles — 2026-10-18 continuation

Goal turn classification: PROGRESS. Full fresh left-output CDR physical/RC/model chain completed and original loaded tests are running as39102038200 at89c79686f7140e8d4700048fe825acf984864432. Syntax/source-delta guard passed; four native cases are live. Preserve these handles; do not start duplicates.

TX return64 remains electrically rejected. Fresh path diagnosis39102156220 at87dec08e69f69a4f9e788642ab1d297092a803dd is live after exact builder-source guard passed. Its predecessor39102038162 failed before waveform evaluation because the reader referenced the previous builder filename. Exact log/summary/manifest failure is retained in `tx-return64-reader-source-failure-20261018.json`; the successor binds the actual module pinned by the waveform. No numerical result or acceptance threshold changed. Once diagnosis succeeds, inspect all28 failed native HBT terminal voltages and actual interface groups before any next TX geometry/device change; old8-device mapping is stale.

Mainchip detailed route39084569446 remains live at this check, job117548333285. No routed timing result yet. All compute remains GitHub-hosted. Local workspace is empty. Eight-hour heartbeat remains ACTIVE/cloud-only and now reaches this current checkpoint from CLOUD_RESUME.md. Full serial Gen3 x4, mainchip final routed verification and setup/hold closure are not yet achieved.

Earlier checkpoint follows:

# Current cloud continuation — full left-output CDR model under original loaded tests

Cloud only; local workspace remains empty. Complete fresh chain: physical39100869702; planes39101130061; wire inputs39101294329; binding39101439659; wire RC39101439688; MIM capture39101632182; strict raw audit39101758700; composition39101898339 at89c27652c1802afd7336278872964cc418edbb9a. Composition394devices9946R7771C,11 intrinsic MIM models,15 fault controls. Full receipts retained. Physical top `nssoc_cdr_pd394_left_outputs_v1`, model `nssoc_cdr_pd394_left_mim_wire_v1`.

`cdr-left-mim-loaded-cloud` is being launched for original early/late256-bit34.25ns cases plus clock-stop/VI-bias-off faults. `cdr-left-loaded-source-delta.json` binds exact adaptation of the original v3 evaluator; clocks, loads, all original acceptance gates remain unchanged. Inspect terminal cases before any geometry/device change; preserve failures. Physical/model checks alone are not electrical or PHY acceptance. If nominal passes, full-loop/PVT/timestep and RF/body qualification remain required.

TX return64 nominal39087664998 is now TERMINAL REJECTED:227/768 wrong signs,253 below100mV,28HBT voltage failures, no MOS failures, native return0/no numerical diagnostics. Lower16/8 and CMOS interfaces pass but level4/final fail. New receipt `tx-return64-full-wire-rejection-20261018.json`. `tx-return64-path-review-cloud` is being launched to reproduce original gates and localize the actual failed terminals; do not reuse old8-device IDs/review. Swapped-leaf negative capture remains correctly rejected. Mainchip detailed route39084569446 is still live; preserve it. After successful native route, dispatch prepared RCX/STA only with that exact route's summary/parts hashes. Full PHY, routed mainchip/final timing remain OPEN.

Earlier checkpoint follows:

# Current cloud continuation — complete left-output PD394 physical pass

The full parent39100869702 at9d8c12b19e23dd0e0ebf2e52ce6187b7d52969a2 passed native560-category DRC,394-device deep/flat LVS and five original reference/geometry faults. All four actual left-output samplers are assembled with84 local supply risers. Full receipt `cdr-retimed-left-parent-physical-pass-20261018.json`; new top `nssoc_cdr_pd394_left_outputs_v1`. Fresh actual158-plane/51-net binding is being launched in `cdr-retimed-left-planes-cloud`; after it succeeds, regenerate wire inputs, model binding, raw RC/MIM audit/composition and original loaded gates. This is not electrical acceptance.

Both previous risers path diagnoses39100228873 are now preserved in `cdr-risers-path-review-pass-20261018.json`. Actual TX return64 swapped-leaf fault39087664998 completed and original bits rejected it; receipt `tx-return64-swapped-leaf-fault-20261018.json`. The nominal TX job and mainchip detailed route39084569446 remain live. Preserve their handles. Full PHY, routed all-corner timing, qualified RC and signoff remain open. Everything runs in cloud; local workspace empty.

Earlier checkpoint follows:

# Current cloud continuation — left-output sampler passed; full parent under test

Cloud-only; local workspace remains empty. Leaf39100436556 at107da2e6dc973db54cb259db1e3301bd7a98bb98 passed native560-category DRC,35-device deep/flat LVS,LEF and ten faults. Receipt `cdr-sampler-left-v1-physical-pass-20261018.json`. New parent workflow `cdr-retimed-left-parent-cloud` restores all four actual new sampler leaves and regenerates complete394-device placement/routes plus original84 supply risers. See `cdr-left-parent-20261018.md`. First inspect that workflow result; if physical passes, rebuild fresh planes/binding/wire/MIM RC/composition before original loaded electrical gates. No electrical success is asserted.

Risers path review39100228873 completed both cases successfully as diagnosis only; original loaded39099179881 remains rejected with14 HBT failures each. First-pair input differential RMS about124mV versus16–19mV at the retimed pair motivated actual output routing changes. Preserve original failed captures and gates. Mainchip39084569446 and TX39087664998 remain live handles. The prepared current-route RCX/STA workflow requires the actual successful route manifest hashes before dispatch; native preflight39099942605 passed but no actual routed timing result exists yet. Full serial PHY, mainchip signoff and final setup/hold remain open.

Earlier checkpoint follows:

# Current cloud continuation — supply-risers nominal failures retained

Cloud only. Loaded run39099179881 at8668ffd75d5d2b8b754bc869560dafdd6b7265bc completed: both nominal cases remain rejected despite physical/RC/model passes. Early wrong-sign counts98/282/368/398 of765; late108/74/370/396. Both still have14 failed HBT operating points. Early phase direction fails; late passes. No numerical warnings; source hashes unchanged. Full receipts in `cdr-risers-full-wire-rejection-20261018.json`. New `cdr-risers-path-review-cloud` reads those exact native captures and reproduces every original gate before identifying the next physical/circuit change. Do not treat84 added supply risers as a successful electrical repair.

The exact-route extraction/STA downstream code is prepared. Native preflight39099942605 at a0d535237ed6f16f4aaddb192208466b6788b8b4 passed the actual bundled STA transform and3 malformed-script controls (`onehot-routed-extraction-preflight-20261018.json`). Actual RCX/STA has NOT executed. Only dispatch `replay-onehot-routed-extraction-cloud.yml` after detailed route39084569446 succeeds and its exact summary/parts SHA256 are bound. Do not use the older113791-instance extractor. See `onehot-routed-extraction-preparation-20261018.md` for scope and nominal-RC qualification limits.

Existing mainchip detailed route39084569446 and nominal TX return64 case39087664998 remain live. TX swapped-leaf fault job117557594283 completed, with original-bit rejection recorded in asset652523864, but its normal case is still required. Keep all handles. Full serial Gen3 x4, routed integration and final setup/hold remain open.

Earlier checkpoint follows:

# Current cloud continuation — supply-risers loaded tests launched

Cloud only; local workspace stays empty. Actual local supply repair adds84 physical3.2um TopMetal1 risers in14 leaves and23 TopMetal2 shunts. All394 intrinsic devices, source circuit, signal routes and public interfaces are preserved. Physical top: `nssoc_cdr_pd394_supply_risers_v1`.

The complete fresh proof chain passed: physical39097910516 (560-category DRC,394-device deep/flat LVS,5 physical faults); planes39098142196 (158 planes,51 nets,19 controls); wire inputs39098288016 (1134 terminals,776 points,111 wire components); binding39098476742 (394 devices,8 controls); wire RC39098476688 (9839R7682C,13 controls); MIM capture39098638452 (9862R7693C,11 actual MIMs,5 controls); raw MIM audit39098788457 (13 wire+9 MIM controls); composition39098971322 at8105b9e4011dc880bc5290d272be20d195b38fe3 (15 controls, all raw tokens preserved, one intrinsic model per actual device).

New simulation model `nssoc_cdr_pd394_risers_mim_wire_v1`. `cdr-risers-mim-loaded-cloud` is being launched for original early/late256-bit34.25ns tests and actual clock-stop/VI-bias-off faults. `cdr-risers-loaded-source-delta.json` binds byte-exact adaptation of the original v3 evaluator: only artifact/model identities and fresh independently audited RC counts change. All original sampling/phase/current/device gates, transistor models, clocks and loads remain unchanged. A physical/model pass does not prove loaded behavior. If nominal runs fail, inspect exact new raw captures before any next change; never reuse old native IDs, RC, hardcoded failure counts or altered acceptance windows. If nominal runs pass, the remaining PVT/constant/timestep and real recovered-clock loop gates are still required.

Mainchip detailed route39084569446 and TX return64 waves39087664998 remain the existing live handles at last check. Preserve them; fresh routed geometry/logic/RC and final all-corner setup/hold are still required after the route terminates. Previous placement-estimated timing is not final signoff. Full serial Gen3 x4 PHY/mainchip integration and final timing remain open.

Earlier checkpoint follows:

# Current cloud continuation — native supply risers physical pass

Cloud only. The actual supply-risers candidate run39097910516 at057a9722af88ba51845fbac2640c19257a610faf passed560-category DRC,394-device deep/flat LVS and all five original physical faults. The new physical top is `nssoc_cdr_pd394_supply_risers_v1`; native geometry adds local M6 supply risers plus23 M7 shunts. The full receipt is `cdr-retimed-risers-parent-physical-pass-20261018.json`. This proves physical topology within the stated decks, not electrical improvement or full PHY acceptance.

The `cdr-retimed-risers-planes-cloud` workflow is being launched to bind all actual new terminals. Continue with fresh native wire inputs, intrinsic binding, raw wire/MIM extraction/audit/composition and original loaded early/late gates. Do not reuse AVSS256 RC or IDs. Original AVSS256 cases39096665471 remain rejected and their wave diagnosis39097444345 remains retained.

Mainchip39084569446 and TX39087664998 were live at last check; keep the same handles. Full PHY, mainchip routed signoff and final setup/hold remain open.

Earlier checkpoint follows:

# Current cloud continuation — native local supply risers under physical test

Cloud only; local workspace empty. AVSS256 path diagnosis39097444345 reproduced both failed nominal captures,14 HBT failures and original gates. Full receipt `cdr-avss256-path-review-pass-20261018.json` preserves raw capture identities and detailed voltage measurements. Latest repair is actual local supply routing, documented in `cdr-supply-risers-20261018.md`.

The `cdr-retimed-risers-parent-cloud` workflow is being launched. It adds native3.2um TopMetal1 risers to existing Metal4 supply escapes in14 leaves plus regenerated23 M7 supply shunts. Public pins/circuit394 devices remain. Check generation, full560-category DRC, deep/flat LVS and all original physical faults. Only after a physical pass rebuild planes/binding/raw MIM RC/composition and unchanged loaded tests. Do not promote earlier AVSS256 nominal failures or reuse their RC/native IDs.

Mainchip route39084569446 and TX return64 waves39087664998 are still live; preserve those handles. Full serial PHY, routing and final setup/hold remain open.

Earlier checkpoint follows:

# Current cloud continuation — AVSS256 loaded rejection retained

Cloud only. The local workspace remains empty; no native archive, scratch source or CAD process belongs on this computer.

AVSS256 loaded run **39096665471** at240fe07e683b058f72890888840c7cfec66ceba9 completed with both nominal cases rejected. Early sampler wrong-sign counts are103/282/366/390 of765; late115/76/367/398. Both retain14 HBT operating-point failures. Late phase direction passes; early direction fails. No numerical warnings were reported and source readback stayed unchanged. Actual clock-stop and VI-bias-off cases pass their negative-control gates; these do not turn a failed nominal model into an accepted PHY.

The fresh native geometry/RC chain remains valid as a development model, not electrical acceptance. In particular a wider global AVSS rail did not close the data problem. Preserve all raw captures and controls in `cdr-avss256-full-wire-rejection-20261018.json`. The new `cdr-avss256-path-review-cloud` workflow replays the original sample/device checks from those captures and measures actual rail drops, collector/base differences and differential-pair voltages. It changes no RC, timing, stimulus, gate or native waveform. Choose further geometry changes from that diagnosis, not from the physical pass alone.

Mainchip route **39084569446** and TX return64 **39087664998** remain live. Keep their handles and inspect final native receipts before any downstream RC/STA. Full serial PHY, mainchip routing and final setup/hold remain incomplete.

Earlier checkpoint follows:

# Current cloud continuation — AVSS256 fresh model ready for loaded tests

All work remains in GitHub; local workspace is empty. Do not clone or restore archives locally. The full serial PHY, routed mainchip and final setup/hold goal remains active and incomplete.

Actual AVSS256 physical39095310936 and fresh plane39095575427/wire-input39095714858 proofs passed. Binding39095906267 passed394 devices/8 controls. Wire RC39095906254 passed9632R7544C/13 controls. MIM capture39096104344 passed9655R7555C/11 native MIM identities; strict audit39096272120 passed22 controls. Composition**39096513384** at68e0b52e1f0ff3256bbf0327090d6e9d3ebdb752 passed15 controls and all raw wire tokens. New model `nssoc_cdr_pd394_avss256_mim_wire_v1`; physical top `nssoc_cdr_pd394_compact_avss256_v1`.

The `cdr-avss256-mim-loaded-cloud` workflow is being launched with original early/late256bits34.25ns and clock-stop/VI-bias-off faults. Check terminal reports, all native warnings, sampler counts,122 HBT operating points, VI direction and source hashes. Do not infer success from workflow dispatch, physical passes or unchanged R/C counts. If nominal cases fail, diagnose exact raw waves before changing geometry; keep all prior failures. Original compact cases39093685328 remain rejected with14 failed HBTs, despite its successful physical and raw-RC chain.

Existing mainchip DRT39084569446 and TX return64 waves39087664998 were still live at the last authoritative check. Continue the same handles. DRT needs native route/antenna/connectivity gates followed by fresh route logic/geometry/LVS and extracted all-corner STA. The old113791-instance RC extractor source38788529905 is not this141654-instance candidate and must not be reused. Original20/4/8/8ns clocks and5percent derate remain fixed. Current placement-estimated timing is not final closure.

Earlier checkpoint follows:

# Current cloud continuation — AVSS256 physical pass

Cloud only: local workspace remains empty. Last meaningful progress is actual geometry modification and native physical proof, not full PHY closure.

Run39094373443 completed both original compact CDR wave diagnoses. Full receipt `cdr-compact-path-review-pass-20261018.json` reproduces failed sampling and fourteen HBT violations. Both nominal compact waveforms in39093685328 remain rejected; actual clock-stop and VI-bias-off fault cases passed their negative-control gates.

The next physical candidate widens only the global TopMetal1 AVSS rail64um to256um, preserves original32um Y end extensions, all394 devices, original child drawings, via arrays and public pins. A first generation failed because square caps crossed the origin;39095085264 is preserved in `cdr-avss256-origin-rejection-20261018.json`. Attempt39095164547 predates the cap fix and also failed. Neither failure is suppressed.

Corrected native physical run**39095310936** at4e54a64dfdc700cad7f27574f4f0438d983d00e6 passed560 DRC, deep/flat394-device LVS and five original physical faults. Receipt `cdr-retimed-avss256-parent-physical-pass-20261018.json` binds the new GDS/LEF, all sources and native evidence. New top: `nssoc_cdr_pd394_compact_avss256_v1`.

Fresh `cdr-retimed-avss256-planes-cloud` is being launched. Continue with newly bound intrinsic terminals, full metal/MIM RC, native raw-wire controls, composition, and original early/late256-bit34.25ns tests. Do not reuse prior native IDs, R/C values or adjust acceptance gates. Four signal routes lengthened192um, so improved electrical behavior is unproven.

Mainchip route39084569446 and TX return64 waves39087664998 remain live at this checkpoint. Keep those handles; do not restart on polling timeouts. Full serial PHY, recovered clock and extracted final setup/hold remain open. Focused hosted CPU/PCIe/Ethernet plus base/full lint39093810293 passed; this is not whole-chip signoff.

Earlier checkpoint follows:

# Current cloud continuation — hosted validation and loaded rejection

The local NSSOC workspace is empty and has no running CAD process. Verified handoff receipt asset 636387277 records nine batches and 3008078533 logical bytes transferred. All future source edits, simulations, archive restores and CAD runs stay in GitHub. Do not recreate a local checkout.

**CI correction validated:** run 39093810293 at 672a0fdac578ff1cf7fe0c9c19fe90df52fb03b9 passed base/full lint and the actual asynchronous CPU/PCIe/Ethernet test. Exact receipts retain the original failure, the missing full-profile setup failure, and the corrected pass. This is not warning-free RTL or physical signoff.

**Compact PD394 loaded rejection:** run 39093685328 at 596f28e75a1dfdfa47277bbda69486c741c898f1 ran original early/late 256-bit, 34.25 ns waveforms on all394 devices and the newly audited9655R7555C model. Both nominal cases were rejected with unchanged source and no simulator diagnostics. Four sampler bit/sign gates and fourteen HBT operating limits still fail. Late phase/VI direction passed but does not override data/device failures. Clock-stopped fault was detected; inspect VI-off terminal result separately. Preserve raw full waveforms and original gates.

The new `cdr-compact-path-review-cloud` workflow reads those exact early/late waves on hosted runners, reproduces original sampler counts and transistor voltages, then diagnoses actual supply drops and clock/data paths. No new stimulus, fitted latency, changed threshold or ideal internal waveform is permitted. It uses fresh compact native IDs and source-bound artifact digests. Shortest resistor paths are not effective resistance; wire capacitance excludes intrinsic device load.

Continue existing mainchip detailed routing39084569446 and TX return64 loaded run39087664998 without duplicate restarts. They were still running at this checkpoint. Mainchip requires successful route/antenna/connectivity, independent physical checks and full extracted all-corner timing. Complete serial PHY, clock recovery, qualified PEX and final setup/hold remain open.

Earlier checkpoint for provenance:

# Cloud continuation — compact CDR audit passed

All work remains on GitHub-hosted runners. Local workspace is empty; do not restore native archives or run CAD locally. Branch `codex/complete-open-work`.

Compact CDR capture 39092549964 passed. Independent raw RC audit 39093269827 passed with **9655 R, 7555 C, 11 native MIM devices, 13 unchanged wire corruption controls and 9 intrinsic MIM controls**. Receipt `docs/evidence/cdr-compact-mim-parent-audit-pass-20261018.json` pins complete report and archive. Composition is being launched with the fresh compact binding (39091922547), never the old v3 native IDs. After composition, run original 256-bit early/late waveforms and actual faults using the compact planes (39091442653) and new R/C counts. Original clock/common mode/load/device thresholds must stay unchanged. Physical and raw RC passes are not loaded electrical acceptance or qualified PEX.

Hosted CI diagnosis 39092549976 identified missing generated Ibex RTL in the broad RTL preparation, and two stale warning locations. Commit de827731830dd919dba41e730f4add89608e4070 fixes preparation via `soc-rtl-prepare` and relocates the same two ledger entries in all eight profiles. Focused validation 39093269754 is running; inspect its actual result before claiming a pass. No older CI run was cancelled. Full CI may remain queued behind existing jobs.

Keep the existing mainchip detailed-route run **39084569446** and TX return64 native-wave run **39087664998**; do not restart while live. Neither routing closure nor serial PHY is established by dispatch. Mainchip needs routed RC and unchanged all-corner STA after native route completes. Prior placement-estimated setup/hold violations are still open. PLL acquisition and full recovered-clock/device qualification remain open.

Prior continuation notes follow unchanged for provenance:

# Cloud-only continuation state

All execution, CAD outputs, native waves and source changes remain on GitHub. The local workspace is empty. Do not clone or restore artifacts locally. The goal remains complete serial PCIe Gen3 x4, routed PCIe/Ethernet mainchip and final setup/hold. None is closed by this checkpoint.

## Current native jobs and latest terminal results

- Mainchip detailed routing39084569446 (source92c6161af3fbb040ce6433ccae32ee614e6db1ab, nativejob117548333285) remains live at this checkpoint. Never restart while live. Exact zero-overflow GRT39082708488, original20/4/8/8ns clocks,5percent derate,20SRAM and NDR are retained. Route/antenna/disconnected-pin gates, independent route geometry/LVS and extracted all-corner timing still remain.
- TX return64 actual physical39086629991 passed all560DRC categories, deep/flat1674device LVS, five physical faults and exact six-rectangle drawing delta. Fresh extraction39086995085 passed377conductors/3262probes/4774terminals and13corruption controls with116611R77471C. Composition39087377122 passed six malformed-model controls, full native-net recovery and124leg/372base binding with two endpoint controls. Full source-bound receipts are retained.
- TX loaded run39087664998 (sourcec68680dcf8d645534d9c5f9bfd1673bdf0206cb0) is live. Builder/adapter byte-equivalence preflight passed. Native full-wire nominal117557594345 and swapped-leaf fault117557594283 run the complete original34ns/256bits, actual1674device116611R77471C core and eleven clock reference/feed macros. The nominal workflow explicitly fails any original electrical gate. No nominal result or improvement is assumed.
- CDR loaded run39086822540 completed FAILURE: both nominal cases rejected, simulator exit0/no diagnostics/sources unchanged; two actual fault controls detected faults. V3 has14failed-HBT VCE gates per nominal case, versus7in v2; supply-only repair did not close the defect. See cdr-v3-full-wire-rejection-20261018.md and its receipt. Do not rerun the same transient unchanged.
- CDR v3 original-wave path diagnosis39087834710 (source85ba0c49007edc11517c00f3e9dec31f8040c519) completed both cases. Exact original113475row/898column waves, all sampler counts/margins and all122HBT VCE minima reproduced; fourteen failing identities match. Select-input common mode about1.342V, XOR select-input common mode about1.169V; select-tail emitter means0.191/0.197V and collectors0.406V. The supply overlay does not provide sufficient active headroom. Full receipt: evidence/cdr-v3-path-review-pass-20261018.json.
- CDR boundary experiment39088526670 (sourceff9f2e6e4b6403ac563d1d47c3831c3c3e970254) completed FAILURE: all six native early/late profile cases were rejected. No profile is adopted. Full per-case summary/manifest digests and original electrical checks are retained in evidence/cdr-v3-boundary-six-rejections-20261018.json. Shared source-delta/clock preflight117560074432 passed before the matrix. Profiles clock145, select500 and clock145_select500 each test original early/late bits against the exact same394device9979R7761C model and original engineering gates. Only declared external clock common mode and/or select reference current changes. This is diagnostic, not original-interface or physical bias-generator acceptance. Previous39088317707 failed before native simulation on multiline PWL token parsing; original failures are retained and only continuation-marker parsing/formatting was fixed. See cdr-v3-boundary-headroom-experiment-20261018.md.

## Completed CDR v3 chain

Physical39084708980:23 actual TopMetal2 supply shunts,569via stacks; all560DRC categories pass; deep/flat394device LVS and five deliberate faults pass. Full flattened drawing delta is controlled. Native planes39085138687:158planes51nets1134terminals19faults. Whole-wire inputs39085392184 and native binding39085569056 pin actual v3 native IDs and dimensions.

Wire-only RC39085569087 is diagnostic only. MIM-aware capture39085974150 contains9979R7761C,11native MIMs,111components776points, five capture fault controls. Strict raw audit39086426677 passes native resistor identity/value, per-point C attachments, collapsed C conservation and22controls. Complete composition39086629993 passes15controls, preserves every wire token and binds each native MIM once. Full receipts under docs/evidence pin summaries/manifests and original output hashes. The subsequent original loaded v3 tests failed as recorded above. This is not RF/body PEX qualification, recovered-clock CDR or loaded-wave acceptance. Do not reuse old v2RC or native IDs.

## Mainchip completed and still unclosed

Targeted39080594759 retains97622logic cells. Slow setup8037/WS-5.54096ns; fast setup663/WS-0.901378ns; fast hold24/WS-0.391465ns including3r2r violations. These are placement estimates only. GRT39082708488 routes141375nets with zero final overflow and preserved NDR. Detailed routing and actual extracted final all-corner setup/hold are still pending.

## Preserved electrical failures

- CDRv2 loaded39081843889 failed both nominal cases: early sampler wrong100/277/345/365, late133/84/347/349 of765samples each; seven HBT active-VCE failures per case. Original fault detection passed. Full-wave review39083732157 reproduced every metric and found select-tail return rise about0.229/0.234V and already weak selector inputs. V3 supply reinforcement is an actual experiment, not an assumed complete cure.
- TX full-wire39067769686 failed227/768wrong-sign samples, level4/final interfaces and eight HBT VCE gates. Full-wave review39084981409 reproduced original results. Physical paths39085786545 maps six failures to final f and two to p8_7; final tail emitter return rise about0.172V with shortest raw return paths16.18605/16.22470ohm. Shortest path sums are not effective resistance. Do not reuse old high3/tight return64 models.
- PLL full1us39078674197 failed original800-900ns100ppm acquisition gate at135.380ppm; later900-1000ns89.850ppm cannot replace it. No native process/capsule remains. Local MIM-window capture is not complete clock RC.

## Required next work

1. Inspect terminal DRT once available; preserve failures and original zero DRC/antenna/disconnected-pin gates. Verify route logic, geometry/LVS, complete RC and extracted all-corner timing before acceptance.
2. All six declared boundary experiments39088526670 are terminal failures. Preserve their original metrics; do not repeat unchanged. Diagnose actual signal routing and circuit headroom together using the existing native waves before selecting a new physical repair. Any useful headroom setting requires a physically realizable clock/bias interface plus fresh native validation; do not adopt sensitivity as a qualified layout or original-boundary pass. The fourteen-device VCE rejection, original PVT/convergence and recovered-clock loop integration remain open.
3. Inspect TX full-wire nominal/fault39087664998 when terminal. Compare all original gates with baseline39067769686 and use original raw terminal waves for any next repair. No compact model or same-R/C-count shortcut replaces these actual new values.
4. Extend full PLL/clock MIM-aware RC and correct original acquisition failure. Full serial PHY requires actual clock distribution, recovered-clock CDR, all x4 lanes, analog pads/ESD and real mainchip links. External-clock PD tests or digital route alone do not prove this.

No goal completion, qualified PEX, final timing or manufacturing approval is claimed. Green workflow status alone is insufficient.

## Cloud-only workspace verification

At 2026-10-18T02:21:24.411022+00:00, the project workspace /home/hasanmelih/Documents/ChatGPT/nnsoc was verified empty, including hidden entries, and no local CAD/simulation process was observed. Migration release cloud-migration-final-checkout-20261013 retains receipt636387277 and the hosted archive-member verification records. No native archive was restored locally. Continue all builds, simulations and artifact storage on GitHub-hosted infrastructure. Mainchip39084569446 and TX39087664998 were still in progress during this check.

## Compact sampler repair and full PD394 integration

- First compact sampler39090257244/source6a9a5f6d2ece8ceb6bfe36b46075a61126a609ba: all560DRC categories passed but35device LVS failed. Preserved receipt cdr-sampler-compact-first-lvs-rejection-20261018.json. Hosted diagnosis39090663060/source227b9a1cc6cc8cec2d38618f67448d0d751bbadd restored native evidence and found five M4 tap/signal overlaps. Extracted netlist merged QN|QP|SUB. Do not adopt this rejected GDS.
- Actual repair moves tap origin30to22um while retaining candidate device pitch20um, tap pitch60um, bus pitch6um and560um outline width. All native primitive drawings, exact source circuit, widths and via arrays remain. Corrected native run39090817026/source724ba3ec3d613c3a03ee254e9eee116d53d343ce passed all560DRC, deep/flat unsimplified35device LVS, all ten original fault controls and native LEF. An independent GDS route audit reproduces all five shorts in the failed GDS and none in either original or corrected GDS. Area560x191.03um versus880x267.03um. This physical pass is not an electrical pass.
- Full pass receipt: docs/evidence/cdr-sampler-compact-physical-pass-20261018.json; summary652264047, parts652264185, archive652264354. Archives stay in GitHub releases. No native archive downloaded locally.
- Full parent run39091146421/source5ed04963e6af13a88faad51a97cd32e768d9de99/nativejob117567985660 completed SUCCESS: all560DRC, deep/flat394deviceLVS and five actual fault controls passed. Physical scope only. Receipt docs/evidence/cdr-retimed-compact-parent-physical-pass-20261018.json pins summary652274416/manifest652274517/archive652274582; outline1592.2x4784.3um. It replaces all four sampler instances through docs/evidence/cdr-retimed-compact-parent-children-20261018.json, preserving the other seven verified child types. New top nssoc_cdr_retimed_pd394_compact_supply_v1. Native41source cards/16macros/394devices/25ports and all original parent physical gates remain. Placement optimization, all signal routes and23supply shunts regenerate from actual new child pins; no old RC or native IDs may be reused.

Next: inspect this exact parent job, preserve any rejection, then bind all158native planes/51nets/1134terminals against its own flattened LVS. Regenerate complete wire inputs,394device dimension/terminal binding, actual MIM-aware native RC, raw RC audit and composition before running both original loaded early/late cases and original faults. Reference method scripts cloud_cdr_retimed_planes_v3.py/cloud_cdr_retimed_wire_inputs_v3.py/cloud_cdr_retimed_binding_v3.py/cloud_cdr_mim_parent_rc_v3.py remain unchanged; new candidate needs its own source-bound artifacts. Do not substitute the small sampler physical pass for full PHY, mainchip or electrical acceptance.

Compact-parent native158plane/51net/1134terminal binding is now defined by scripts/cloud_cdr_retimed_compact_planes.py and its cloud workflow. It restores only the newly passed physical source39091146421 and reruns all19original mapping corruption controls. No old native IDs, wire values or loaded-wave results are reused.

Compact-parent planes39091442653/source13f9f272290fbf5d9825193339639d628035b054 passed158interfaces/51nets/1134terminals and19controls. Fresh whole-wire inputs39091676406/sourcec46a608114f2b6a717f3baf82fdd91e7d3d72886 passed394devices/111physical conductors/776points, with751actual metal terminals and383retained intrinsic-body dispositions. The2.35MB full summary remains release asset652288166; the compact source receipt pins its digest and every output. Fresh native model binding and wire-only RC audit workflows now target only this new geometry. Wire-only extraction remains a prerequisite/diagnostic; the loaded model requires fresh MIM-aware capture,22control raw audit and15control composition afterward.

Compact model binding39091922547/source36b86c4137d4fb2070695dc6988f2c741c079ee9 passed394actual devices/1134terminals and8model-corruption controls. Whole-wire RC39091922509 at the same source passed9632R/7544C,111components/776points, exact raw edge/value/point and collapsed-C conservation plus13corruptions. Fresh receipts pin summary652302935/manifest652302992 and summary652301354/manifest652301444. The MIM-aware capture workflow now targets these new artifacts and eleven actual MIMs. Wire-only results do not replace it.

No CI run was cancelled. A proposed redundant-run cancellation stopped at its preflight assertion because completed CI failures were present; no cancel API call or cancellation-record commit occurred. The queued native jobs then ran and passed normally. General CI39088317644 RTL job117560038990 reports1168passed/one invalid soc_pcie_ethernet suite/22skipped; newer39089804846 formal-and-boot failed prepared whole-SoC lint. Preserve and investigate exact artifacts12121864262 and12122960491. Hosted ci-failure-review-20261018 reads these logs in cloud. Independent mainchipDRT39084569446 and TX39087664998 are untouched.
