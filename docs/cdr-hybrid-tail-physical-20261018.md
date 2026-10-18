# Native hybrid-tail sampler physical candidate

The12HBT/3LVNMOS/12rppd schematic candidate passed three native schematic cases and two real fault controls in39104163004. This new physical candidate uses that exact source, not the old all-HBT geometry. The native PDK `nmos` PCell uses totalw/onefinger and retains its source/drain and poly gate geometry. A real poly extension/contact reaches each gate; eight finite native substrate taps keep SUB distinct from AVSS and extracted BULK. Placement checks actual primitive bounding boxes with at least12um clearance and adapts the x position. Existing Metal3 escapes, Metal4 columns, Metal5 buses and actual TopMetal2 output shunts remain.

The physical proof must pass all560 main-rule DRC categories, unsimplified deep and flat35-device LVS (12HBT+3NMOS+12resistors+8taps), all10 external pins and native LEF inspection. Twelve negative controls include MOS width, gate and body changes, load/input/clock/tap corruption, physical open/short/offgrid faults and missing LEF pin. Frozen source-delta manifests prevent unrecorded edits; native extracted device types are counted independently. The expected35-device total does not reuse the old circuit's evidence.

Native MOS construction reference: https://github.com/IHP-GmbH/IHP-Open-PDK/blob/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.tech/klayout/python/sg13g2_pycell_lib/ihp/nmos_code.py . Gate access follows the already used PFD construction but requires fresh native LV-device DRC/LVS here.

No physical pass is assumed before actual runner results. Even a physical pass needs fresh parent geometry, native terminals, full raw RC and original loaded waveform gates; it is not complete CDR, recovered-clock, PVT, PHY or chip signoff. All generation, compilation, CAD and artifact restoration happen on hosted runners. No local CAD or source checkout.


## First native physical result and actual tap repair

Run39105291849/source2f46efe4f1d24c6eb130d43fc2e75e5e266dc71c generated the real MOS layout, then failed two LU.b markers out of560 DRC categories. No LVS acceptance was reached. Exact summary/parts/report are preserved in `docs/evidence/cdr-hybrid-tail-initial-latchup-failure-20261018.json`. Native NMOS active lengths span8/32/32um vertically; the original remote tap row leaves upper tail regions too far from a body contact. This disproves reuse of the original eight-tap geometry for these MOS devices.

Successor adds one native2um by2um ptap1 beside the vertical midpoint of each MOS, physically routed to SUB. All original eight taps remain:11 finite contacts and38 total devices. Reference, native extracted census and deep/flat LVS requirements are updated to that actual circuit addition; no rule or electrical limit is relaxed. Original twelve negative controls remain. Await actual native proof before parent integration. All other MOS widths, lengths, gates and signal circuit remain unchanged.
