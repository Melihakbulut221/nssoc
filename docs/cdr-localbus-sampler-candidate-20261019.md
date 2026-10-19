# Shorter internal sampler buses — physical candidate, not PHY acceptance

The native stage comparison39245298065 traces each master/slave input emitter
through real clock-selector collectors to the actual MOS tail drains. It
reproduces the fixed original folded rejection and preserves every input hash.

| Wire quantity | Previous v10 | Folded v11 |
|---|---:|---:|
| Master input-emitter incident C |256.175fF|387.457fF|
| Master input-emitter non-reference cross-network C |112.265fF|217.407fF|
| Master clock-tail incident C |358.791fF|433.623fF|
| Slave input-emitter incident C |327.420fF|366.899fF|
| Slave clock-tail incident C |380.426fF|437.987fF|

Internal-node-to-internal-node capacitance within each listed conductor was0
in this extracted model. The cross-network values above are incident minus
reference and internal capacitance. They are model measurements, not qualified
RF/body PEX or a proof that a single capacitance explains all data errors.
Shortest resistor path sums and total wireR are not effective RC delays.

The new sampler localbus v15 candidate keeps every folded native primitive,
its placement, intrinsic parameters and public port positions. Only internal
horizontal buses move toward their highest actual terminal, retaining20um
vertical clearance and6um bus pitch. Internal columns may shorten but never
lengthen; public clock/data/power/bias bus Y positions stay unchanged. All
native via arrays and metal widths remain. The original clock-open boundary
cut remains intact.

The independent GDS check requires all54 native drawings and placements,
reference and public pins to remain identical, and checks the declared new
TM2 bus rectangles against actual GDS. Original560 DRC categories, deep/flat
54-device LVS, LEF and16 physical/reference negative controls remain.

This is a real geometry candidate intended to reduce internal wire loading.
It has no accepted electrical result. Passing leaf DRC/LVS requires fresh
parent integration, native extraction and the complete unchanged loaded
waveform gates before any timing claim. Full CDR recovery and Gen3x4 remain open.
