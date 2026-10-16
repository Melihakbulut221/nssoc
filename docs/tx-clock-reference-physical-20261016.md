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

