# Integrate the physically verified v20 data/hold sampler into PD484

Leaf run 39417934516 passed fresh native PCells and all physical gates:
560 DRC categories, unsimplified deep and flat 54-device LVS, LEF and
18 corruption controls. The independent native drawing check retained
46 primitive drawings and authorized only eight data/hold Nx8-to-Nx4 changes.
It also preserved all primitive positions, 1003 x 243.63 um outline and
external pin rectangles, with five corruption controls. Leaf GDS SHA256:
f290c143373f7e77b3b6eeff8bb9d43988ea3b1db6cd0ab2c67a50bc13fd3c32.

This parent replacement starts from the actually verified v19 GDS
247fd159b5a245c9dd8df13082cab62d4f185ea39102a62b9c4491ce230d999b.
It replaces the native sampler child shared by four existing placements.
Exactly 32 data/hold HBT reference Nx parameters change; Nx4 selectors and
all other device parameters, parent geometry, hierarchy transforms and
external interfaces remain unchanged. The serialized parent comparison,
all eight independent leaf comparisons and 16 placement checks remain.

The original full 484-device native DRC/deep-flat LVS and negative controls
must pass. Fresh whole-parent terminal, conductor, intrinsic MIM and RC
extraction must follow; the original v19 electrical failures remain evidence.
No old parasitics are substituted for the changed v20 geometry. Full loaded
early/late and device gates still decide whether the hypothesis helps.
Physical integration here is within CDR PD484, not mainchip or full serial x4
PHY acceptance. All computation and artifacts remain cloud-only.

## First parent DRC rejection and explicit overlay cleanup

Run 39418862656 passed generation and all actual child comparisons but
failed native DRC with 16 M3.a and 8 M3.b markers. The full report and GDS
remain in its immutable release. The resized leaf itself had passed DRC.

The next parent removes whole top-level Metal3 polygons only when they touch
those exact hash-bound markers and lie at least 5 um inside one of the four
sampler outlines. Every marker and all four samplers must be covered. These
are obsolete access overlays from the earlier parent wire widening.
The new leaf hierarchy is not edited. All remaining parent Metal3 polygons,
all other parent layers, labels and placements must match the declared
region subtraction after GDS serialization. An out-of-sampler removal
control must reject. Thus parent Metal3 is explicitly changed; the original
whole-parent-metal-unchanged claim does not apply to this revised candidate.

Unchanged full DRC and unsimplified deep/flat LVS must still pass. Fresh
extraction must include the removal. No rule waiver or electrical acceptance
is introduced by this repair.

The cleanup attempt in run 39420127278 stopped before serialization because
Region object equality did not establish geometric union identity. The proof
now uses exact empty symmetric difference, independently requires empty
removed/retained intersection, and rejects a one-grid added polygon. No
geometric tolerance, DRC rule or native LVS gate is relaxed.
