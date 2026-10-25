# Full32 native input-driver physical handoffs

The all64-driver transient run39460427396 includes the extracted driver devices but still has ideal driver-to-core interconnect. This candidate begins replacing that boundary with actual geometry. It does not change or restart that running simulation.

The input core is physical run39447746971, GDS d202185d3691cd7778b8040492bab73492f44a1cfb0896c5f0b8f31350e6bdff, with all1674 devices and the four native p4 drive3 masters. The driver is physical run38905613449, GDS6f7a7cf92c1dc25a259acdbff779c7cce841128991abb780e13478aa84b4eb62:100 raw devices, including84 individual MOS and12 finite substrate/well contacts. The hierarchy contains one core and64 drivers,8074 reference devices.

The cloud generator copies the two native cell trees using KLayout's documented [Cell.copy_tree](https://www.klayout.de/doc/code/class_Cell.html) API and verifies per-layer flattened geometry. It derives every endpoint from original pin rectangles, translates the core by600um, and places four drivers per600um input-row group. It attempts three native via stacks and two TopMetal2 horizontal segments plus a TopMetal1 vertical segment per driver-to-core handoff. Candidate tracks are screened against actual flattened foreign metal and earlier routes with1.645um clearance. The report preserves all64 route outcomes, obstruction polygons, lengths and native instance positions.

The reopened GDS must reproduce the original native material plus exactly the added parent geometry. Missing-driver and swapped-input controls must reject; whenever new metal exists, a missing-parent-metal control must also reject.

This is construction and obstruction evidence only. A green workflow is not a full physical verification verdict. Driver power/body distribution, a complete parent reference and ports, original560-category DRC, deep/flat transistor LVS with actual opens/shorts, fresh whole-parent RC and the original fullwave electrical gates remain necessary. No existing source model, waveform acceptance threshold, rejected result, or signoff gate is changed. All generation and CAD run on GitHub; local workspace remains empty.
