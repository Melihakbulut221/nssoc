# Cloud continuation — checkpoint v237

Updated: 2026-11-01T11:15:04.583818+00:00

Latest user instruction: all work in the cloud; leave no local project data. This overrides the older goal's local-work wording. All native acquisition, CAD, geometry analysis and simulations must run on GitHub-hosted runners. Local coordination is source/API-derived text in RAM only. Do not download native archives, ODB/DEF/GDS, transistor models or waveforms locally, even into RAM. The project workspace and project-named temporary entries have been rechecked empty, with no native CAD processes.

## Current PHY execution
Observe run 41299745896, branch codex/cdr-hbt-load, source 12f3e0f3bf7010289dc0f993ac71dbfa55cc19e4. Independently reserved release 430521829/tag cloud-results-41299745896-1-cdr-sampler-load. Do not duplicate it. Controls 41299445254 passed all inherited suites plus 243 HBT mutation refusals and 40 actual changed-emitter bindings. The candidate changes 40 connected buffer/XOR HBT Nx values on the authenticated 12-divider/200-MOS parent. All original electrical gates, including current normalized by the actual candidate emitter counts, remain intact. Retained RC is exploratory screening, not fresh physical verification.

The native job was still in progress at the v237 observation. Treat its complete terminal publication and original-gate measurements as authoritative, not workflow color or source controls. New geometry and fresh extraction remain necessary.

## Mainchip route has terminated; preserve its checkpoint
Run 41292673925/source 7a0776718ec37a106b7dfde0cbd477c6a2a5522f is completed FAILURE. Release 430474717/tag cloud-results-41292673925-1-mainchip-bulk-postdrt-antenna contains the complete native archive. The bounded route returned and saved four raw route-partial/routed-fixed DEF/ODB files. Last router report: 397 DRC violations. This is not DRC closure or final signoff.

Raw routed-fixed.odb and route-partial.odb: 214409779 bytes, SHA256 b87a2d43fe33dd8ca99f0faa2bdf38337ae30d6c5b72a337472919ac57f64e63.
Raw routed-fixed.def and route-partial.def: 186123105 bytes, SHA256 0ac5108f828158156a858086a2edaff204020a14e17cb491d0ab173131345511.

The subsequent restore-plan failed at scripts/mainchip_original_clock_restoration.py:215, assertion that each selected wired record has FIXED class. Failure cleanup hit the same assertion. restore-import, restored-audit, final-check and final-audit did not run. No restored candidate or final timing result is accepted.

Next route work: authenticate the saved native checkpoint and investigate actual per-net encoded class and shape differences on GitHub. Do not simply relax the assertion. Prove protected geometry, original 1691 clock records, untouched wires, 1351 diode ownership, power/connectivity and original final gates. Repair class restoration against this saved result if justified. Do not reroute all 828 nets blindly. A saved ODB does not prove persistence of TritonRoute optimizer history; stage 2/restart must be independently qualified. See docs/mainchip-routing-restart-review.md and docs/mainchip-bounded-route-terminal.md.

Never download the mixed bulk-postdrt-antenna artifact locally: it contains native archives. Safe terminal text proof, complete job logs and metadata are preserved under docs/evidence/bounded-route-native-terminal-41292673925. Native archive parts remain on the release.

## Previously qualified evidence to retain
- Rejected divider native run 41295928971: actual engine return 0, no diagnostics, device/VI pass, all six data stages fail; phase 29.329406448 mV also fails the original 30 mV gate. Complete proof 19d07ce5f55be3d0c09014f56df9e76a51c9aa1a, imported in v235.
- Corrected wave reader 41298781054/source eb9b2602db8d971e405310142ab88d3fc652d308 passed 33 controls and reproduced all original data/phase measurements. Full proof 502461e773ddb66c63bf64222c37beea6dcd3a4b. The preceding reader 41298254630 had a loop-variable phase-report bug and remains rejected; its original evidence was preserved. Do not use its erroneous 1.0 V phase report.
- Initial HBT controls 41299284469 failed before fixtures due to missing actual_context(ctx) argument; corrected controls 41299445254/source 12f3 passed. Full rejected and successful proofs remain in v236. No native computation ran from the failed source.
- Four actual MOS unit widths 8/9/8.890/8.885 um passed all 20 native stages in 41290670037: four zero-DRC checks, eight deep/flat unsimplified LVS matches, exact junction parameters and eight negative controls. Full proof 6e9362d5c95e1c2b2fca62d9c71aec8ac4e099e4/release 430461761. This is not the whole 650-device layout. Keep the original 221 taps; do not blindly add one tap per split unit.
- Original 64-bound route 41270471645 timed out at 14400.811 s; no optimized ODB was saved there. Its 129 intermediate violations cannot be treated as this newer checkpoint's result.

## Unchanged acceptance and remaining scope
UI 125 ps; sampler 100 mV/37.5 ps; XOR 100 mV/75 ps. HBT active VCE >=0.4 V, abs VCE <=1.6 V, abs VBE <=1 V, strict Ic/emitter <3 mA with actual Nx. MOS terminal <=1.32 V, active VDS >=0, individual tail currents >=0, sixteen stage current sums >=0.5 mA. Seven MIM <=1.6 V; phase >=30 mV; PLL 62.5 ps. Final STA 20/4/8/8 ns +5%, three PVT corners, zero setup/hold/transition/capacitance violations.

Full serial PLL/CDR/SERDES, training/LTSSM, replay/credit, lane mapping/descrambler/TX and serial soc_top ownership remain open. The routed packet-interface SoC is not full serial PHY integration. No production/silicon/radiation approval is claimed. Authorized specification access request is already pending; do not ask again.

Use independent same-source controls and an independently created/read-back empty exact-source release before native acquisition/dispatch. Never blindly retry dispatch or publication after a timeout. Proof branches must be created directly at their final [skip ci] commit; do not create an interim source ref that triggers duplicate CI.

Inventory: 650 monitored runs. The eight-hour cloud monitor remains read-only with automatic_native_dispatch:false. Full serial PHY, routed serial-integrated chip and final setup/hold remain OPEN.
