## Latest — combined repair passes full nominal sensitivity; actual driver geometry running

Cloud-only observation: 2026-10-16T18:03:48.125931+00:00. Concrete progress: measured both individual
repairs, combined all-gate nominal sensitivity, native clock physical and LEF
verification. This is not full PHY or signoff completion. Local workspace empty.

Repair run38940564417 is complete. Samefull34ns/256bits/0.3,0.5,0.7UI/zeroOP,
62HBT/672MOS, unchanged limits and zero solver diagnostics for all three cases:
- series-only: final interface150.911949mV, no below150mV samples; two selector
  HBTs still failVCE(0.395836902/0.395848687V vs0.4V). Output206.002188mV.
- clock-only: zeroHBT/MOSfail; final135.839234mV with261below150mV samples.
- combined: all original engineering gates PASS. Output205.965768mV,
  CMOS175.745974mV, final150.815274mV withzero wrong-sign/below-limit samples,
  zeroHBT/MOSfail,77643rows. The final margin is only0.815274mV above its gate;
  this is a measured nominal sensitivity, not PVT or robust physical acceptance.
  Summary648144529 SHA41f61b9af953ca21a2ce387c5a63728be64fa98d2bef3905247e721efa217dbc;
  parts648144681 SHAc7d0c9f3f910ac99c6f0b82a0199b0c44485a80fd4a0a4b52c13da0874e67968.
Changed driver geometry still uses old wires in these sensitivities. Never
relabel component_screen_passed=false or adopt frozen wires as extracted RC.
All measured results/receipts: docs/evidence/tx-stage-repair-results-20261016.json.

Actual new driver geometry run38944147428, source4f17848a3ac042528fb92d978697808c0584ad22,
is running. Generator now supports --series-length l6p2 ONLY with --pullup-length
l2p4; all old defaults remain. Exactly XUP3.08to2.4um and XIN6.92to6.2um
changes are source-proved; other devices/gate damping unchanged. Actual resistor
PCell and pin accesses are regenerated. Requires all original four raw/aggregate
LVS deep/flat gates, DRC and faults plus old pullup/old series length mismatches.
Output/group: tx-input-driver-pullup-l2p4-series-l6p2, directory
hw/soc/out/cloud-tx-input-driver-pullup-l2p4-series-l6p2. Do not rerun a healthyjob.
After physical success, derive new native raw junctions/resistor bindings,
terminal graph/anchors, intrinsic model and fresh wireRC/composition from THIS
actual GDS. Reuse established audited methods, pin the new receipts, preserve
all corruption controls, and run unchanged full loaded gates with actual clock
macro extraction. The older l2p4 RC is not the new series geometry's RC.

Clock reference physical run38941785196 BOTH variants passed native six-device
DRC/LVS and six faults. Independent GDS/LEF run38943586211 BOTH passed:
exact126x89.63um outline, four pins avdd/cm/avss/sub, actual metal coverage,
OpenROAD geometry/types/obstructions, and three actualLEF mutations rejected.
Sourcea33610c0fb0030916d2a09b04aca331f00912547. First LEF run38942680498 failed
embedded-script syntax; second38942982120 passed GDS but lacked techLEF.
Both failures preserved. Exact upstream techLEF c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c,
28396bytes SHAe3470344dfac5347b176fb3f8e0f0548d17a66b8f433626a8987dcb2ae4828b6,
is now fetched in cloud and hash-checked. No geometry or rule waiver.
Clock LEF receipts and prior errors also recorded in the stage-repair evidence.
Clock raw terminal/body binding, physicalRC, loaded/PVT and actual mainchip
connections still required; LEF compatibility does not establish them.

Mainchip full-signal route38930352215 remains live. NativePLL38910378266 is in
continuation job117113404119 after a saved actual initial process (latest initial
summaryb4efbc1507bbcb670dce059bd9e043e82cf3eabd1bcc11126570fc7da6c71471).
Inspect exact handles and next-stage capsule before action. Full32:1/four-lane
serial PHY, full1us acquisition acceptance, mainchip route and finalsetup/hold
remain open. Keep all scopes and original checks intact.

# Source-bound final-selector and driver-series hypotheses

Native tree binding inventory38937012080 restores the exact original binding
SHAf54124fa051b49a32f0c3837ef8f771e6cda3ea9aba18417ba5cc932e856c3b9.
XD0001 and XD0003 both have C=$I50,B=sn,E=$I54,body=$4,Nx6. XD0002/4
use B=sp and C=$I51; both pairs share the final tail node driven by the two
Nx8 tail HBTs whose bases are mr. These are the final2:1 clock selectors,
not the first stage. The previous checkpoint's first-stage wording is corrected.
Native IDs alone were insufficient to establish a stage role.

Two bounded schematic hypotheses follow, starting from the actual fresh-RC
l2p4 physical driver model8eec4846d8cef0e3367c07f8e1a0f3413f4a628684bbb1a283c6f6883b95ad79:

- Driver XD86/XIN length6.92um to6.2um at unchanged width2um tests stronger
  differential drive into the physical tree. It may hurt common-mode or device
  stress. All other raw99devices and all260R295C remain unchanged.
- Native clock-reference XOFFSET length6.5um to6.2um at unchanged width4um
  tests lower reference common-mode and more final-selector VCE headroom.
  The native resistor feed, reference HBT, clock phase/amplitude and full
  waveform gates stay unchanged. No ideal offset source is introduced.

The helper proves exact source identity and rejects changed gate damping,
wire resistance, clock HBT or missing offset resistance. These are proposed
parameter sensitivities, not a passing circuit or layout. First inspect the
active actual l2p4 loaded run38936139904; use its complete source-bound result
as the baseline for separate series/clock/combined experiments. Do not change
healthy runs or repeat the previously rejected data8_select10 sizing study
38773059353. Every original34ns/256bits/672MOS/62HBT/zeroOP/source phase and
engineering limit remains required; a useful outcome needs new matching
physical geometry/extraction and PVT validation.

## Latest — final-selector identity proved; repair experiments prepared behind live parent

Cloud-only observation: 2026-10-16T17:24:38.631113+00:00. Actual loaded38936139904, nine-size
full-signal route38930352215 and native full1usPLL38910378266 remain live.
This turn made concrete source/provenance progress and validated controls.
Do not restart healthy jobs. Local project directory remains empty.

Native tree inventory38937012080 proves XD0001/3 are the same final2:1 selector
branch: C=$I50,B=sn,E=$I54,S=$4,Nx6. XD0002/4 are its sp-side pair.
Both share the final tail, whose two Nx8 devices are biased from mr. These
are not the first stage; the prior checkpoint's loose first-stage wording was
incorrect and is corrected. Original binding SHA remains
f54124fa051b49a32f0c3837ef8f771e6cda3ea9aba18417ba5cc932e856c3b9.
Inventory summary648005147 SHA01e8c9875a5a52f3192c030219d015b01b551328e513490c49f5c3863363fa23;
parts648005240 SHA0682c2493974518fcb66ac477e5274e7309b4ef957d3bb3b28d3dbd034d0b0c6.

Source-controls38937989660 PASSED. Exact physical l2p4 parent model is pinned;
XD86/XIN6.92to6.2um (w2um) and native clock XOFFSET6.5to6.2um (w4um)
are two separate hypotheses. Four real undeclared changes (gate damping,
wireR,clockHBT,missingoffset) are rejected. No electrical pass or changed
physical layout is claimed. Summary648024877 SHAe1aaab5f517f86b905fa09e40013e0a2f53407f63563c72d1b123d5a0636780a;
parts648025107 SHA2267f433d0900d946989188cda78385843952b44c7c3fefacaf958d0dafdc4d6.
Helper: scripts/cloud_tx_driver_stage_repair.py.

The parent-gated experiment controller and workflow are READY, not yet run:
`scripts/cloud_tx_driver_stage_repair_loaded.py` and
`.github/workflows/tx-stage-repair-loaded-cloud.yml`.
Source60995212a4a0d6f3a97854a6ed51a3ffb001e5d6 compiled successfully in
push preflight38938382706; the three native cases were intentionally skipped
on push. Next, inspect actual l2p4 job117092015460 in38936139904. If its full
original capture is complete with engineering failures and zero solver
diagnostics, fetch/hash the published l2p4 summary, then dispatch exactly once
with `parent_summary_sha` set to that verified SHA. Matrix runs series,clock,
andcombined with the same full34ns/256bits/originalphases/672MOS/62HBT and
all limits. Four shared method/feed files are pinned unchanged from parent
9e6679b30a0f31556d0ea32097cefd1c480dc47e. Only selected native resistor
geometry parameters change; old wires for altered geometry remain explicitly
nonphysical, component_screen_passed staysfalse, diagnostic_screen_passed
records actual original gates. No source ramp, phase fit or ideal offset added.
If parent passes or has numerical failures, reassess instead of dispatching.

Do not repeat rejected data8_select10 study38773059353: all three wire corner
cases failed. No full32:1/four-lane PHY, qualifiedRC/PVT, clocks/CDR or final
mainchip setup/hold closure is established. Source-bound diagnosis is saved in
`docs/evidence/tx-stage-repair-controls-20261016.json`.


## Latest — actual fresh-RC loaded failures measured; three repairs dispatched

Cloud-only observation: 2026-10-16T17:34:21.058263+00:00. Local project directory is empty. No local
checkout, CAD/simulation, archive download or result files were created.

Actual new-layout/new-RC run38936139904 completed both variants. Workflow
success means the measurements completed; both electrical screens FAILED.
Both retain full34ns, zero-sourceOP, all62HBT/672MOS and zero solver diagnostics.
l2p4: output177.607481mV, CMOS158.449132mV, final135.912543mV with261
samples below150mV. Final selectors XD0001/XD0003 have minimumVCE
0.393131217/0.393142646V against0.4V; twoHBTfail, zeroMOSfail.
l2p7: output171.248904mV, CMOS163.403028mV, final133.802350mV with288
samples below150mV; twelveHBTfail, zeroMOSfail. These are actual fresh-RC
results, distinct from the older frozen-wire parameter sensitivity.
Receipts and complete failed-device measurements are recorded in
`docs/evidence/tx-driver-pullup-loaded-results-20261016.json`.

The verified l2p4 summary SHA35ac8412aebccfceeb6b115c3bbf1ebbd820341bdfd00b97ed58af99c4bcadd2
was supplied to the prepared repair workflow exactly once. New run38940564417,
sourcef384f3ac1d2862c6e2fd098351e957fc36c48766, runs separate series,clock,and
combined sensitivities. Inspect this run before dispatching anything else.
Keep original full capture, gates and failure evidence. These altered resistor
geometries have no matching new layout/RC yet; even a diagnostic pass is not
physical acceptance. If useful, implement actual matching geometry and repeat
native LVS/DRC/extraction and full loaded/PVT checks before integration.

Mainchip full-signal routing38930352215 and native full1usPLL38910378266 were
still in_progress at this observation. Preserve healthy jobs. Follow the exact
independent geometry/all-endpoint timing review and native PLL continuation
instructions below after actual completion. Full serial Gen3x4, mainchip routing
and final setup/hold remain open; no production acceptance is claimed.

