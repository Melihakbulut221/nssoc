# Integrate the physically verified Nx4 clock selectors into the complete PD484

Leaf run 39391984326 passed actual 54-device native PCell generation,
independent drawing/parameter comparison, the 560-rule DRC deck, unsimplified
deep/flat LVS, LEF and fault controls including wrong selector finger count.
This is physical leaf evidence only; no sampling or full PHY acceptance.

The parent candidate starts from the exact v18 GDS
27321a65507bccd81228e05933676158794b3c099186535fd4f9b892afacb37e.
It replaces the common actual sampler child with the new verified hierarchy,
used at four unchanged native placements. The old/new external leaf pin
rectangles and 1003 x 243.63 um outline must match exactly; otherwise integration
is rejected. All parent-level shapes, labels and sixteen instance transforms
must remain exact after GDS serialization, with removal fault controls.

The full flattened reference changes exactly 32 clock selector Nx values, from
8 to 4, and no other transistor parameter or topology. The independent existing
checker compares all eight leaf sources and sixteen placements again, including
the actual new sampler drawings. The unchanged full-parent 484-device native
DRC/deep-flat LVS and fault suite must pass. Both prior rejected electrical
results and the original layout remain immutable.

Even if this integration passes, the changed child geometry requires fresh
whole-parent native terminal/plane/wire/MIM extraction and unchanged complete
early/late and negative electrical cases. Reusing v18 RC as v19 evidence is not
permitted. Full CDR, PLL, serial x4 PHY, routed chip timing and signoff remain open.
