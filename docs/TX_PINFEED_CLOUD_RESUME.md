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
