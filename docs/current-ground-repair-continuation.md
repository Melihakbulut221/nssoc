## Current continuation: full-wave stage diagnosis complete; balanced bias rejected; slave drive trial source published

All native CAD, SPICE, GDS/ODB, raw waves and native archives remain GitHub-only. Local source/API/derived text are RAM-only; workspace remains empty. Full serial PCIe Gen3 x4 PHY, accepted mainchip route and final setup/hold remain OPEN.

MAINCHIP: keep following corrected complete-engine build41493369685/source851db8f517c03cffd0afeb6527e281bd9353f5d2 on codex/mainchip-guide-batch-engine, release431773741. Its build status is recorded below; never restart on observation timeout. Two-worker lifetime patch is not yet qualified on a routed chip, and no new route/timing improvement is claimed. Current retained chip remains92DRT=64short+28spacing and21antenna nets; all1691protected clock wires were unchanged in recovery41440285882. After actual successful engine build and runtime authentication, require full143820net/154480instance/no-route roundtrip and original protected wire/clock comparison plus full DRT/antenna before full64 routing. Do not silently change old c.ENGINE or drop frozen-source/runtime checks.

BALANCED BIAS41494299114/source df723c791fec2621585c80fb56409d65b5811b44 completed and FAILED original electrical acceptance. Engine returned0, whole transient complete, sources unchanged; all native records sealed in release431779366. Derived13166113737=1409781bytes SHA904b21b197686f66d1911c758dabbbd14dbda350f9104c9040e05fae96d04ec4. Complete measurement, engine, derivation, publication and failure records are preserved here.

Balanced C critical Vce .421640/.420208V exceeds0.4V; D .389873/.386994V still fails. This does not mean all other device gates passed: the comparison JSON retains every failed HBT gate including all-time overvoltage. Phase14.590486mV<30mV still fails. A/B/C/D output maxima45.78125/41.71875/51.09375/54.21875ps exceed37.5ps; wrong signs0/0/1/33 and below100mV129/128/128/128of765. XOR comparisons also fail. This provisional fixed-parent-RC experiment is rejected and not promoted to geometry; the original and pull-up-only failure remain intact.

SAMPLER STAGE DIAGNOSIS41497066977/sourcef3bbcddef55b19194cce675f91a0bb265b577bce SUCCESS. Derived13166219492=1776044bytes SHA9464d8a319a1b733724f8cdacabe95bf3c79ce3141d9c15bb25d4a265b52189d. The full original native wave from41441047354 was authenticated and parsed in cloud. All48 master/slave data and selector HBTs were joined by actual full500 LVS mapping41450661063, native IDs, parameters and all terminal clusters. Every original per-bit sampler delay and original scalar measurement reproduced. All16 selector-pair local crossing comparisons had unique matches, no missing/ambiguous reference edges. Native clock-crossing delay bounds1.5625..4.6875ps. Full per-bit native samples/crossing brackets and source controls are retained here; no new transient/layout or changed acceptance gate.

Representative worst A/B/C edges already have correct-polarity master output and slave input while slave output is still old or below100mV. D also has a late upstream input. This supports testing slave drive/load response, not asserting a sole cause or claiming timing closure.

NEXT SOURCE522ac9b2736a3445c839ac6dfcf25bf245ab78d1, branchcodex/cdr-slave-drive-trial, six changed files read back byte-exact. Independent source-controls run41498753635; branch-creation checks41498680552 (actual parent sourcedf723c79; NOT a test of new source522ac9b2). Follow exact handles. Native trial has NOT yet been dispatched in this checkpoint: first verify actual source-control result24primitive roundtrips/14card refusals plus original29definitions/5blocks/9files/13admission refusals, then independently reserve exact-source release and dispatch execute=true once. Preserve run identity if visibility times out.

The next experiment starts from original authenticated collector Via2 freshRC41439516945, not either failed bias model. Eight slave load resistors SA/SB/SC/SD_S_RP/RN L2.6->1.9um,W32 unchanged; sixteen slave tail MOS SA/SB/SC/SD_S_T0..3 W36->48um,L0.3 unchanged. Provisional consistent AD/AS12.24p->16.32p and PD/PS72.68um->96.68um use parent0.34um diffusion extension. Exact target IDs/parameters/native terminals required. Whole-model and contract reversal prove all other476devices and every parent wireR/C card unchanged. No HBT/reference bias/master/input divider/stimulus/clock/150fF load/gate changes.

Sheet-only resistance ratio1.9/2.6 and nominal width/current48/36 give I*R ratio0.97436; nonlinear/device/contact/wire behavior may invalidate this hypothesis. Actual full waveform and voltage/current-density gates decide. This is a provisional parameter trial without matching GDS or recomputed wire parasitics. Even a numerical pass requires real schematic/GDS, DRC/LVS, canonical terminal mapping, freshRC and original loaded simulation before promotion. Closed-loop serial PHY/PVT/ESD/EM/integration/STA remain open.

Readonly8hour monitor keeps automatic_native_dispatch=false. Do not mistake successful diagnosis or source controls for accepted electrical/physical behavior.

Observed at 2026-11-02T18:19:49.824516+00:00:
- 41493369685: in_progress/None
- 41494299114: completed/failure
- 41497066977: completed/success
- 41498680552: in_progress/None
- 41498753635: completed/success
