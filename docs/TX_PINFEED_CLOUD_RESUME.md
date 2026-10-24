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
