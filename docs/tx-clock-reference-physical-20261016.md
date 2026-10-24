## Latest — both clock reference layouts pass native physical gates; LEF audit retry live

Cloud-only observation: 2026-10-16T17:53:36.670133+00:00. Local workspace remains empty. Native physical
run38941785196 passed both l6p5 andl6p2, source4a6550887640d452523888967c76eb709ef60277.
Both have zeroDRC markers across560categories, raw deep/flat LVS matching all
six devices and four external ports, no extraction diagnostics, and six actual
negative controls rejected (wrongNx, wrongoffset, missingHBT, openCMpin,
supplyshort,offgrid). GDS outline126x89.63um; external avdd/cm/avss/sub,
internaler. l6p2GDS ee1cef81afe91c1afc2257198d090ec375fbe9c6cdf1c74011e7f2e5ac8146a0;
l6p5GDS bab73526a1ee84c84ee392e249b4d97ac267098de97f54938f8c0c20a4cb51a5.
Both source bodies use explicit BULK plus three finiteptap1 contacts. This is
physical comparison scope, not qualifiedsubstrate/electrical/PHY acceptance.
Receipts, native audits/netlists and source-bound geometry are recorded in
`docs/evidence/tx-clock-reference-physical-results-20261016.json`.

The original launchfailure38941349787 was recovered in the cloud: nested
AppImage/FUSE mount returned127 (Operation not permitted). HostPython
orchestration fixed it without changing geometry/rules. Published original
status spells FIVE_FAULTS although six controls ran; future source labels were
corrected to SIX_FAULTS inde582f38f303012ed055ae9cba71aebe7ecef119.

Independent GDS/LEF verifier added: scripts/cloud_tx_clock_reference_lef.py,
hw/soc/flow/check_pcie_tx_clock_reference_lef.py and workflow
.github/workflows/tx-clock-reference-lef-cloud.yml. It restores exact physical
receipts, independently reads actual GDS top bounds/fourpins/metalcoverage,
then uses nativeOpenROAD to check dimensions,pin geometry/types and obstruction
layers, plus actual missingpin/blockedpin/wrongoutline LEF negatives.
First run38942680498 failed both before GDS inspection: embedded generated
Python lost an escaped newline (SyntaxError). Preserved. Fix1962533295bab7741446cb7edce8aa28a829908e
uses a raw string and compiles generated source before native execution.
Corrected LEF-only run38942982120 is live; inspect exact results before rerun.
The passed DRC/LVS producer was not rerun. Clock macro still needs terminal
binding, fresh physicalRC, loaded fullcapture/PVT, and actual mainchip connections.

NativePLL38910378266 initial job117004666682 completed by saving the actual
process after14400seconds; fullcapture remainsfalse. Summary648110903 SHA
b4efbc1507bbcb670dce059bd9e043e82cf3eabd1bcc11126570fc7da6c71471;
parts648111021 SHAfd0d76c901416511f308e870a04b58c1c90b802dae4ea4b3b958e190016ea591.
Prefix558642328bytes, protected inputs and prior payload unchanged. Native
continuation job117113404119 is live in the same run, resuming actual state;
do not coldrestart. After completion inspect its latest descriptor, not this
older initial capsule. Full1us/frozen final acquisition windows remain required.

Other active jobs: three stage-repair sensitivity cases38940564417 and mainchip
full-signal reroute38930352215. Preserve healthy runs. No fullserialGen3x4,
mainchiproute or finalsetup/hold acceptance is established.

## Latest — clock reference actual geometry generated; native launch repair queued

Cloud-only observation: 2026-10-16T17:44:22.409278+00:00. The previous goal turn produced measured
fresh-RC failures and dispatched the three repairs; this turn adds a concrete
missing physical block and preserves its initial verification failure.

New generator `hw/soc/flow/make_pcie_tx_clock_reference_v1.py` instantiates
native npn13G2 Nx1, rppd offset w4/l6.5 or6.2um, rppd feed w4/l14.5um and
three explicit finite ptap1 contacts. Four external pins avdd/cm/avss/sub stay
distinct; er is internal. Both original reference/feed source hashes and exact
source rows are pinned; only candidate XOFFSET length changes. Actual GDS/LEF
and six-device physical reference are generated in cloud runners. No local files.

First run38941349787, sourceafe9f44d8779acf7485e251868824ed0525c82f5, generated
both layouts successfully but BOTH native DRC launches returned127 before
comparison. This is not a DRC/LVS pass or measured geometry violation. Source,
GDS, failed logs and receipt hashes remain in their published release archives
and `docs/evidence/tx-clock-reference-first-layout-20261016.json`.

Correction4a6550887640d452523888967c76eb709ef60277 runs the orchestration
checker with the host Python rather than nesting it inside the CAD AppImage;
native CAD tools still use the exact pinned AppImage. It restores and exposes
the original failed launch log from the hash-pinned cloud archive. New native
log excerpts are also included in the public JSON. No design or rule changes.
Corrected run38941785196 is queued/live; inspect before dispatching again.
Both variants must pass full560-rule DRC, raw six-device deep/flat LVS and
five actual faults: wrongNx, wrongoffset, missingHBT, openCMpin, supplyshort,
plus offgrid rejection (six controls total). No rules are waived. Status banner
says five faults because the initial name omitted counting offgrid; the required
loop contains all six controls. Rename this reporting label after the active
run completes; do not alter live artifacts or treat a label as proof.

Even if physical gates pass, LEF import validation, actual raw junction/body
binding, terminal-anchored fresh RC, loaded full34ns/fullPVT integration and
clock-source replacement remain required. This is a missing reference/feed
macro, not a completed PLL/CDR/four-lane serial PHY.

Other exact live handles: repair sensitivities38940564417 (three cases),
full-signal mainchip reroute38930352215, full1us nativePLL38910378266.
Preserve these healthy jobs. Full serialPHY/mainchip route/setup/hold remain open.

