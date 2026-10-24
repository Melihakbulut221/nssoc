# TX driver pin-feed cloud checkpoint

All native work remains on GitHub-hosted runners. Local workspace stays empty.
This isolated branch is codex/tx-via3-rail-diagnosis; root integration has not been changed.

- Immutable native geometry readback passed: run 40069547963, source ca44176dd617623c4e642eaade106c91dbebf675. Ten measured rail anchors and four negative ownership controls passed.
- Actual 128 driver power feeds passed physical gates: run 40070667147, source 74bc46d2e9518821a12c66b6a071add579ccf2df. All 64 AVDD and 64 AVSS accesses use native centred three-column V1, a 2um lateral access and 6um Metal4 feed to their original Metal5 rail. Every original material shape, intrinsic dimension, reference circuit and public port is preserved.
- Physical DRC: all 560 categories, zero markers. Deep and flat unsimplified LVS: 8088 devices, 165 exact ports, no extraction diagnostics. Actual source-access-open, AVDD-to-AVSS short, changed MOS width and offgrid negative controls all rejected; independent missing-parallel-route geometry control rejected.
- Passed GDS SHA256: 35336560233371ba519a354d26eb43447435102a7b7cda1e8f0c81fddf979819.
- Physical receipt: docs/evidence/tx-driver-pinfeed-physical-pass-20261024.json.
- Earlier run 40069980392 was cancelled due a method precheck error, not a physical rejection. Its release and exact hashes are retained in docs/evidence/tx-driver-pinfeed-precheck-error-20261024.json.
- Fresh complete native wire/terminal extraction: run 40071267004, source 737bef27ae4bd8ddb0b2740f2e0562cb51f8991b. Check terminal status; failed source must not advance.
- tx-driverpinfeed-followthrough-cloud.yml waits for exactly that source to pass, then runs fresh native intrinsic binding and full RC extraction with all original 19 intrinsic and 13 raw-RC corruption controls. It never starts a transistor transient.
- After this: independent two-order RC precision, full composition and interface controls. Obtain parent review before any expensive full 34ns transient. Keep all original output sign/margin, CMOS common mode, HBT/MOS, waveform completeness and diagnostic gates.

Physical success is not electrical success, qualified PEX, a complete serial PHY or main-chip integration. The existing failed full-wave observations remain authoritative until an unchanged fresh full-wave test passes. Final-tail return access is a separate measured target; this candidate does not alter it.

## Precision/composition continuation prepared, not yet run

- Source-only continuation commits: c3c119729e8ce796356ca43813fc310fae92c162 (corrected precision launcher) and 59c8aa5c239e56c604cd3ba234df3fb1e5026892 (composition plus exact rail comparison). Both passed independent source/derivation/schema review.
- scripts/cloud_tx_output8088_driverpinfeed_precision_launch.py consumes only terminal-success fresh extraction run40071489977 at b00c6f400c60190ff4ddcba200bbe0d6f92c8fe7. It restores the exact generated intrinsic/RC adapters before use, preserves all13 corruption controls in both native cap-input orders and requires exact R/C multisets. All four actual wire-cell references use full_tx_output8088_driver_pinfeed_wires. Baseline source dependencies are SHA-locked.
- The first source-only precision edit expected three wire-cell references. Independent RAM derivation detected four before dispatch; c3c1197 corrected it. No native job consumed the incorrect adapter.
- scripts/cloud_tx_output8088_driverpinfeed_composition_launch.py requires a completed exact precision run via NSSOC_TX_PRECISION_SOURCE JSON containing run, source_head, summary_sha256 and parts_sha256. It preserves all25 composition controls and obtains exact R/C counts from the qualified fresh native source. The precision workflow must retain job name actual-full-parent-wire-rc.
- scripts/compare_tx_driverpinfeed_rail_access.py compares all128 original driver rail terminals and two original final-tail emitter points. Matching uses actual metal/coordinates, named terminal, model/parameters, full terminal geometry and independent full body-topology fingerprints. It also requires equality for all8088 native-device fingerprints, preserving original165 physical ports. Cross-run extraction IDs, cluster numbers, A-labels and w-node names are not identities.
- The comparison independently reproduces all10 prior AVDD/AVSS target-resistance results from immutable original native RC before reporting new values. It retains solver KCL/energy/reciprocity checks, six corrupt identity controls and original analytic solver controls. This is linear metal DC resistance, not loaded IR drop, RF-qualified PEX or transient acceptance.
- These files may be imported into another checkout without equating checkout HEAD to old producer HEAD. Producer run/head/release hashes remain immutable; generated files may already exist only when their bytes match exactly. Locked baseline dependency changes are rejected.
- No new precision/composition workflow has been dispatched at this checkpoint. First confirm both40071267004 and40071489977 completed successfully, then publish/launch precision; after its terminal pass, bind and launch composition/rail comparison.
- Native interface/deck/continuation adaptation follows successful precision/composition/R review. It must reopen the new8088 LVS database and bind all124 input legs/372 bases/64 driver handoffs/four output ports, preserve14182 columns,34ns/68001 minimum rows,604HBT/5376MOS and all original output/CM/device gates. New geometry starts a new trajectory; never reuse the old native checkpoint. Parent approval is required before expensive full34ns execution.

## Guarded cloud continuation launched

Precision run40072842481 at12a42514bee086c800ba8f296a09b2b78556275f now waits for exact fresh intrinsic/RC run40071489977 success. It starts no native precision before the original gates pass. The composition followthrough waits for exactly40072842481 at that HEAD, then pins the successful release hashes and runs the25 composition controls plus130 actual-rail DC comparisons. Any failed prerequisite prevents advancement. These workflows run only on the isolated branch; no34ns transient is launched.

## Fresh wire/anchor terminal pass

Run40071267004 completed successfully at737bef27ae4bd8ddb0b2740f2e0562cb51f8991b. Its actual repaired geometry binds8088 devices,28620 terminals,20532 metal terminals,8088 body terminals,165 physical ports,13370 reference planes and703 conductor components. All six native anchor corruption controls were rejected. The exact receipt is docs/evidence/tx-output8088-driverpinfeed-native-anchors-pass-20261024.json (same bytes as the source-controlled followthrough receipt generation).

Summary asset671560373 SHA256 b40767d0a3dc77124ff0ae6ebf4f11f5c79fd4241492cbabc6b52ee30ffe4f8b; parts671560437 SHA256823af2aa83ea8cc284b21f9513233cbe8ab5e792628f01af7c23eebb99aaf74f.
Fresh intrinsic/RC40071489977 is running. Precision40072842481 at12a42514bee086c800ba8f296a09b2b78556275f waits for it; composition/rail40072977220 at380763d925826786ff567e4e9bce75f770eaedc0 waits for precision. No new loaded waveform or electrical pass is available yet.

## Fresh intrinsic and RC terminal pass

Run40071489977 completed successfully atb00c6f400c60190ff4ddcba200bbe0d6f92c8fe7. All8088 native devices/65 body nets and19 intrinsic corruption controls passed. Fresh RC contains141246 resistors and100546 capacitors; all13 raw corruption controls passed. Exact native source receipt: docs/evidence/tx-driver-pinfeed-fresh-intrinsic-rc-pass-20261024.json. The committed anchor receipt byteSHA2cb3982c513e7941d149c8a6daa3a2669500ebbc60c19459eb2887482a4d18eb exactly matches the receipt generated and preserved by this native run.

Precision40072842481 and composition/rail40072977220 remain active. No new DC resistance result or loaded electrical acceptance yet. The future fresh native interface source and exact preparation/continuation caveats are in docs/TX_PINFEED_NATIVE_CONTINUATION.md; no interface workflow or34ns transient was started.

## Qualified bounded precision/composition/DC snapshot

Both workflows completed successfully: precision40072842481 at12a42514bee086c800ba8f296a09b2b78556275f, composition/rail40072977220 at380763d925826786ff567e4e9bce75f770eaedc0. Both native cap-input orders preserve exactly141246R/100546C and pass13 corruption controls each. All25 composition controls passed. All8088 native device/full-terminal/body-topology fingerprints equal the original, and the prior10 target resistance values were independently reproduced.

All64 AVDD driver accesses improved:20.8286087722–22.5362348471 ohm before,14.0721811816–15.7798072565 ohm after; minimum reduction29.9802856885%. All64 AVSS accesses improved:19.8678275847–21.9054852845 ohm before,12.8609699392–14.8986276390 ohm after; minimum reduction31.9867720552%. This is a partial reduction of actual metal DC access resistance, not removal of every bottleneck or loaded IR/timing acceptance.

Both original final-tail emitter accesses remain exactly unchanged: XD5667=6.286958767402115 ohm; XD5674=6.275982084626478 ohm. Their remaining local access geometry still needs investigation. No34ns transistor run was dispatched.

Exact receipts and all comparison-output hashes: docs/evidence/tx-driver-pinfeed-precision-composition-rail-pass-20261024.json. Full added-path list and immutable native source heads: docs/TX_PINFEED_SOURCE_MANIFEST.json. The future interface controller remains source-only pending parent review; see docs/TX_PINFEED_NATIVE_CONTINUATION.md.

## Exact remaining-rail and current-geometry readback

Read-only run40075242137 at f9dfeee4ebdd1970109eee34b9289bc29fd0eef1 restores the qualified new composition, fresh raw ext/res.ext and current native GDS/LVS/wire database. It selects d0p/d0n/d31p/d31n AVDD/AVSS plus the two final-tail emitters by the independently matched original device/terminal geometry. The report preserves dominant resistance segments, original extractor node records and full same/foreign metal/via/hierarchy windows for ten actual terminals, with all four native ownership corruption controls.

The job was queued when this checkpoint was written. Do not claim it passed until its terminal result and immutable release hashes are verified. Next: identify actual residual segment coordinates and local via phase/clearance, then only add a physical candidate proven to belong to the intended rail. Preserve all original intrinsic dimensions and165 ports. No34ns transient or native interface controller has been run.

Cloud-only workspace contract remains enforced: local workspace contains zero entries; no GDS/raw archives/local CAD were downloaded or executed.

## Remaining-rail readback passed; physical branch/tail candidate queued

Readback40075242137 completed successfully with all four native ownership corruptions rejected. Exact summary asset671655169 SHA256 b8327a78d088a97d4d4864b552d5e9084d2b79b022088a49456e70908cc1f8eb; parts671655235 SHA256 0bcfc03e125fa14e7cf6dc1f1bae2a3e1ae5cf00ea0bf9bc963d0b5f6df3ea89. Original native terminal coordinates independently establish the5nm raw extraction grid.

Every sampled AVDD driver has a10.0055-ohm series branch segment; AVSS samples have4.84198-ohm and1.9965-ohm series sections. Their endpoint coordinates span the long existing M5 branches and vertical M4 feeds, not a remaining single V1 cut. Both final tails retain1.42924-ohm local emitter access. Native readback confirms same-net M2/M3 at each emitter and free M4/M5 routing to the existing AVSS strap, while TM1 directly above the emitter belongs to a foreign net.

Native physical candidate40077948550 at12dbfa546406f345bc594cf25af699bea5840634 is queued, not accepted. It adds128 real parallel TM1 branch feeds and two short M2-to-M5 tail feeds. Driver starts are selected only beyond the opposite supply's native vertical TM1 trunk; every endpoint is re-probed and every candidate is checked against full foreign-metal/cut geometry before insertion. Tail rows are derived from actual existing V2 cut phase. All original M1/V1, device geometry, port shapes, circuit dimensions, clocks and biases remain unchanged.

The candidate requires the complete560-category DRC deck, deep and flat unsimplified8088-device LVS, exact165 ports and zero extraction diagnostics. Five physical negative controls are retained/added: driver access open, tail emitter access open, supply short, wrong width and off-grid. Missing added parallel geometry is rejected separately, never falsely claimed as an LVS open.

After terminal physical success, derive fresh wire/anchor sources from the exact new GDS hash and passed summary/parts hashes, rerun all28620-terminal/six-fault binding, intrinsic19 controls, raw RC13 controls, both precision orders and composition25 controls. Recompute all130 exact rail accesses and require original8088 device/full-terminal/body fingerprints to match. No old RC/node indices or native checkpoint may be reused as candidate evidence. The source-only interface controller still needs independent review or cloud controls. No34ns run is authorized by this checkpoint; parent review of combined new-rail results is required first.

## Independent branch/tail source review saved

A separate source review found no concrete blocker at producer12dbfa546406f345bc594cf25af699bea5840634. All seven locked source hashes match, and the qualified readback/native/anchor source hashes agree. Native same/foreign endpoint checks, serialized M1/V1/intrinsic/port preservation, actual tail cut phase and all physical gates remain intact. Full review receipt: docs/evidence/tx-branch-tail-source-review-pending-20261024.json.

Run40077948550 remains queued with zero native steps at this checkpoint. Source review does not qualify generation, physical closure or electrical improvement. Existing jobs remain untouched; no duplicate native dispatch and no34ns transient. The cloud monitor tracks workflow tx-output8088-branch-tail-feed-cloud.yml, native job diagnose, source12dbfa54. Follow the guarded fresh-RC continuation above when the terminal physical result is available.

## Branch/tail physical pass; exact fresh wire/anchors started

Physical40077948550 completed SUCCESS. All130 added feeds passed560-category DRC with0markers, deep/flat unsimplified LVS8088/8088, exact165ports, no extraction diagnostics, and all five physical negatives. New GDS9ed77cbd9cf7eff9939e9a9b94c6e516d98937b0174776f4a3dd6380c04d3ac0. Exact physical receipt docs/evidence/tx-branch-tail-physical-pass-20261024.json contains summary352e9db493ee6d6f3c818dc51abb3bc075236996a4e40b87c1cd481bf86a9c99 and partsc4d25899d89431d8af5d0974a12f7f00c9bade88125b53aababd923033b2b08d.

Fresh wire/anchor40078861177 atb91a3f312d2538faf232164cdf9493b0cac61422 is queued. Workflow tx-output8088-branch-tail-feed-wires-anchors-cloud.yml; job diagnose. The actual new GDS hash and all physical evidence are pinned. Independent source review verifies all seven method hashes, exact native extractor/binder derivations and unchanged8088/28620/165/703/768/six-fault gates. Receipt docs/evidence/tx-branch-tail-wire-source-review-20261024.json. This source review does not claim the new graph/anchors passed.

After exact terminal wire/anchor success, generate a new branchtailfeed intrinsic/RC followthrough from scripts/cloud_tx_driverpinfeed_followthrough.py using the new wire run/head, distinct branch-tail-feed wire cell/path names and identical19/13 native gates. It must consume the new source, then fresh two-order precision/composition and130 DC comparisons before any34ns decision. No new transient was started.

## Guarded fresh intrinsic, precision and composition/DC continuation published

Observed 2026-10-24T09:01:12.439556+00:00. The new whole-parent wire/anchor run40078861177 is in_progress; it has not been claimed qualified. The native physical result above remains the latest accepted branch/tail result.

- wire_anchors: run40078861177 at b91a3f312d2538faf232164cdf9493b0cac61422; workflow tx-output8088-branch-tail-feed-wires-anchors-cloud.yml; job diagnose; observed in_progress.
- intrinsic_rc: run40079922239 at 1b3c71745361e40f508024f9ba76e49bc0804769; workflow tx-branchtailfeed-followthrough-cloud.yml; job native-physical; observed queued.
- precision: run40080002978 at 00b9d3dc879253faece67d3db3136daeb4811203; workflow tx-output8088-branchtailfeed-precision-cloud.yml; job actual-full-parent-wire-rc; observed queued.
- composition_dc: run40080181306 at 69d4dcfa957ccc6d19ab2ee6766bdd9a0ac7c147; workflow tx-output8088-branchtailfeed-composition-cloud.yml; job actual-whole-parent-composition; observed queued.

Each downstream runtime waits for its exact immutable predecessor run, head and attempt1 to finish successfully, then validates published summary/parts digests and original engineering gates. The source-only publication while a predecessor is pending does not qualify any result. No native stage was duplicated. The intrinsic/RC adapter received independent review: all11 method locks and exact namespace-only derivation match the qualified preceding pipeline; native19 intrinsic and13 raw-RC faults remain unchanged. See docs/evidence/tx-branchtailfeed-followthrough-source-review-20261024.json.

Precision retains both native capacitor orders and all13 faults in each row. Composition retains all8088 full intrinsic/terminal/body identities,165 ports and25 corruption controls, followed by the unchanged analytic DC solver and130 exact rail bindings. The new comparison additionally restores the immutable previous-pinfeed report and compares every target/fingerprint, so incremental branch/tail resistance improvement can be measured without reusing old RC or nodes. Its bounded independent source review is pending.

No34ns transient appears in this chain. Parent must review the combined qualified new geometry, fresh RC/precision/composition and actual DC reductions before any loaded native waveform job. Keep pending/failure receipts and original gates; never report source review as native acceptance. Local workspace remains empty; all native and archived evidence stays on GitHub.

## Fresh precision/composition source review completed

Independent review at69d4dcfa957ccc6d19ab2ee6766bdd9a0ac7c147 found no concrete blocker: all10 composition method hashes match; prior pinfeed summary/parts were independently fetched and hashed. The additive comparison checks all130 original targets and full native device fingerprints, reproduces prior resistance values and reports incremental reduction without changing native models or numerical gates. Precision/composition adapters retain exact original logic after declared namespaces and immutable producer substitutions. Receipt docs/evidence/tx-branchtailfeed-precision-composition-source-review-20261024.json. Native jobs remain pending/in progress; this is source review, not fresh RC or electrical acceptance. No34ns transient.

## Exact fresh wire graph and all original anchors passed

Run40078861177 atb91a3f312d2538faf232164cdf9493b0cac61422 completed SUCCESS at09:21UTC. Immutable summary asset671820495 SHA256 bbd49748b6d504a76a3c349ea13aa627a83ba415effaf9db3d633008fdd4b615 and parts671820592 SHA256 4ee8acdd851be108a48cd3715fafe3e4d412a09aef1ec6a04409e94dac7ceba1 were independently fetched in RAM and verified. All8088 devices,28620 terminals (20532 metal/8088 body),165 ports,13370 reference planes,703 conductors and768 electrical nets are retained. Six actual anchor corruptions are rejected. Geometry hash is exactly the passed branch/tail GDS; no geometry change or native-label component union is allowed. Compact receipt docs/evidence/tx-branch-tail-fresh-native-anchors-pass-20261024.json links full cloud evidence.

Fresh intrinsic/RC40079922239 and guarded precision40080002978 have started; composition40080181306 remains queued at this observation. No fresh RC/precision/DC result is claimed yet. Existing guards now advance automatically from the accepted wire predecessor. No34ns transient or local artifact.

## Fresh intrinsic and raw wire RC passed

Run40079922239 at1b3c71745361e40f508024f9ba76e49bc0804769 completed SUCCESS at09:30UTC. All8088 original devices,28620 terminals,165 ports,65 body nets,703 wire conductors and19 intrinsic faults passed. Actual new geometry produced141473 resistors and100694 capacitors; all native R-edge values, per-point ground C, mutual attachments/values and collapsed C were conserved. All13 actual raw-RC corruption controls rejected. Qualified double-total producer hash remains1a44bd5c70af3800213419c2e3b2213285523a74fcc4b92bc9cf7314d93a592c. Compact immutable receipt docs/evidence/tx-branchtailfeed-fresh-intrinsic-rc-pass-20261024.json records all three reports, assets, generated sources and counts.

This is fresh wire-only RC, not full PEX/substrate/RF or loaded electrical acceptance. Two-order precision40080002978 remains in progress; composition/DC40080181306 follows its exact successful terminal guard. No34ns transient.

## Branch/tail precision, composition and all130 DC comparisons passed

Precision40080002978 at00b9d3dc879253faece67d3db3136daeb4811203 and composition40080181306 at69d4dcfa957ccc6d19ab2ee6766bdd9a0ac7c147 completed SUCCESS. Both native capacitor enumeration orders retained141473R/100694C, every original device/port/conductor and13 actual raw corruptions each, with no geometry, threshold or RC-record changes. All25 whole-parent composition corruptions rejected. New composed model SHA256 8286d54832432603f78739f30d0087e99a46f026d82a37ecd5e450d2167231c8; composition SHA256 093dba5b465ee54cc8232d28c196be13eaf7c74637ed742989c44d75976e9708.

All64 AVDD driver terminals improved from previous pinfeed14.072181–15.779807 ohm to9.305691–10.873965 ohm; minimum additional reduction30.4754%, minimum total reduction51.4488% from original via3. All64 AVSS terminals improved12.860970–14.898628 to10.175040–12.019540 ohm; additional reduction at least18.2648%, total at least44.6419%. Final tails XD5667 and XD5674 improved6.286959→5.518343 and6.275982→5.506715 ohm, respectively. Every original8088 device/full-terminal/body fingerprint remains matched; six identity corruptions and analytic numerical controls remain intact. Exact receipts/hashes and full cloud comparison output references: docs/evidence/tx-branchtailfeed-precision-composition-rail-pass-20261024.json.

The source-only fresh interface adapter received independent review at738a5819: allfive methods and original binder hash match, with actual new GDS/LVS probes and original endpoint controls intact. Receipt docs/evidence/tx-branchtailfeed-interface-source-review-20261024.json. It still has no workflow and has not run. Parent review of the combined qualified geometry/RC/DC results is now the next coordination gate before native interface readback and any34ns decision. No34ns transient, loaded electrical, fullPEX/substrate/RF/fullPHY or mainchip acceptance has been claimed. All work/evidence remains on GitHub; local workspace is empty.

## Root-reviewed native interface verification dispatched by guarded workflow

Root independently verified composition40080181306 summary671874144, source69d4dcfa, all25 controls and retained scope flags, then authorized native interface readback only. New workflow .github/workflows/tx-output8088-branchtailfeed-interfaces-cloud.yml uses job actual-native-interface-binding and unchanged independently reviewed controller7159533f35a4e2b02e6572806edbf4f9085a8b6c0f8f1b0519f9d12cbf25dd40. It checks exact terminal composition run/head/attempt, summary/parts/model/composition digests and all original counts before reopening actual new GDS/LVS. Original binder, physical/device/interface/fault gates and source hashes remain unchanged. Record terminal native result before any success claim. No34ns or fault transient is included.

Native interface auto-run40083738813 is queued at exact source11ed6ba3e7ecd4b184ee0161c5b8a1699c539a56, attempt1. Workflow tx-output8088-branchtailfeed-interfaces-cloud.yml; job actual-native-interface-binding. Do not dispatch a duplicate. Its exact reviewed composition pin is40080181306/69d4dcfa957ccc6d19ab2ee6766bdd9a0ac7c147, summary0eaf95458de7e0ffda91a80bc022830994972e933a0a6d2cb064dd9839ee2c43, partsaddebff74d0c1612cb2eda6cd3ccaf0cf20761bcfdb96bb5cce6d07805ac2f3a, model8286d54832432603f78739f30d0087e99a46f026d82a37ecd5e450d2167231c8. Preserve terminal native interface proof and descriptor before adapting any original34ns/fault job. No transient has been authorized by this workflow.

## Actual fresh native interface and all12 fault controls passed

Run40083738813 at11ed6ba3e7ecd4b184ee0161c5b8a1699c539a56 completed SUCCESS at10:06:33UTC. Native reopening of the real130-feed GDS/LVS and exact new8088-device composition passed all28620 original terminal identities,124 input legs,372 data bases,64 driver handoffs and four output/supply/bias ports. All eight identity controls, two actual wrong-endpoint probes and two output-polarity/supply controls rejected. Every protected source remained unchanged. Current/historical physical controls remain explicitly separated.

Immutable summary671922034 SHA256 e872278654de17a300e5004c463a1ad37b5c9e1116ed7d8720e2872f8124c2b9; parts671922116 SHA256 278156444c2bd2159f6f029f8f3a9d51ad156d1a84a751ea41e4e75e6b5b6a51. Native interfaces.json SHA25613bfff54e68a5355547fc64e4ebdd64e347c5b54a43b8c924b9ece724b009aaf; model8286d54832432603f78739f30d0087e99a46f026d82a37ecd5e450d2167231c8. Original-compatible full-report receipt docs/evidence/tx-output8088-branchtailfeed-interfaces-pass-20261024.json and explicit future preparation descriptor docs/evidence/tx-branchtailfeed-native-interface-descriptor-20261024.json are ready for parent.

Next action is a newly prepared original34ns normal/fault pair using the exact fresh model/interface hashes, all original10 adapter faults,604HBT/5376MOS observations,14182-column/minimum68001-row contract, stimuli, clocks, solver, loads, timestep and engineering gates. Existing old-model CRIU/native capsules must not be rebound to changed model bytes. No preparation or34ns/fault transient was dispatched here. Native interface success is not loaded electrical, fullPEX, fullPHY or mainchip acceptance. Local workspace remains empty.
