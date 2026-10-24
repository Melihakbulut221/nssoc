# Routed load diagnosis before another ECO

The latest actual route39202263552 retains0 route DRC/disconnected pins but
does not meet original setup/hold/electrical gates. The source-measured worst
slow path includes a single-fanout o21ai_1 driving0.387187pF with4.278654ns
cell delay. The worst fast PCIe output path includes a single-fanout nand4_1
driving0.456549pF with2.528471ns cell delay. These are observations, not proof
that only cell strength is responsible.

The cloud-only onehot-routed-load-geometry workflow restores that exact
hashed routed ODB and all three original maximum-path reports. It selects
the union of top32 eligible weak data drivers per corner with the unchanged
existing selector; annotates native pin centers, actual sink membership,
wire total length and driver-to-sink Manhattan distance; and verifies the
source files did not change. This sample excludes clock trees and does not
claim a complete violation census or capacitance breakdown.

Use those results to choose physical data buffering/placement repairs, then
prove native logic, route again and re-extract all corners. Keep original
clock periods, uncertainty, loads and derating. Repair setup/electrical paths
before checking hold across all corners; preserve previous failed candidates.

OpenROAD documents buffering long nets and repairing electrical limits in
[Gate Resizer](https://openroad.readthedocs.io/en/latest/main/src/rsz/README.html).
This investigation itself runs no resizer and makes no geometry or constraint
change. It is not evidence of timing, LVS, antenna or full PHY closure.
