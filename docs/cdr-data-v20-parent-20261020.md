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
