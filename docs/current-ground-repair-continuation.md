## Current continuation: route iteration20 verified; ground clearance diagnosis

All native CAD remains GitHub-only. Full serial Gen3x4 PHY, complete mainchip routing and final setup/hold are OPEN.

Actual original router reports authenticated in run41385020793: iterations5/10/15/20/25 contain561/267/159/140/298 violations. Iteration20 has89shorts and51metal-spacing violations; it is the lowest of the five retained reports, not proof of a completed route. Run41385939588 independently loaded, wrote and reloaded iteration20 and verified preservation of154480instances,143820nets,1691protected clocks and original828-net allowed changes, with zero absent owned wires. It did not run routing repair, restore original signal classes, verify diodePG, close timing or accept physical signoff. The original iteration25 verification remains valid, but iteration20 is the preferred qualified next repair input.

Ground reinforcement runs are preserved, including failures:41385188402 source-controls caught an ambiguous KLayout sizing overload; explicit three-argument sizing fixed it.41385545130 rejected all32ten-micron candidates;41386007875 admitted5of32centered five-micron candidates;41386421055 admitted18of32using centered/upper/lower added-only positions with identical guards. No candidate GDS was generated. Do not claim18of32as a passing repair. The remaining14need actual layout redesign.

Current diagnosis41387369679/source88babaeadcbf90ec8aff7d4fc7885a106c653a1e reports whole/original/added-only clearances using actual native geometry. It preserves every existing guard and reports exact overlap areas and foreign bboxes at1999/2000/2005/5000/5005nm. Three independent geometry controls distinguish an unchanged exact2000nm baseline gap from new spacing loss. Inspect the live outcome before further width proposals. No weaker acceptance or synthetic input substitution is authorized.

Snapshot20 first attempt41385528741 failed source authentication because a newly pinned document was missing from explicit sparse-checkout lists. Fixed source6ea1056a421a5ba7ebe6bba23d549d552d3e18bf passed standalone controls41385666865 and native41385939588. These failures remain recorded.

Electrical reference is still loaded41379770619: local ground rise0.324-0.331V, phase13.5867mV<30mV and HBT minimumVce0.3490/0.3463/0.3813/0.3801V<0.4V. Current accepted physical geometry remains four-shortcut GDS1c7d56173b350c067df5db468b4099d7c5b8681e891d027b700737566c2c3b94; no later failed proposal replaces it. Any new actual GDS needs full560DRC, deep/flatLVS13, exact canonical binding, fresh RC and unchanged loaded-wave acceptance.

Next: inspect actual baseline-vs-added ground collisions; redesign only from native evidence. For mainchip, classify140report20violations against native net identity and original scoped owners, then implement a bounded actual repair with protected-clock/material checks. Loading an ODB does not restore the internal detailed-router search state. Keep full original three-corner timing constraints and all physical acceptance gates. Monitor remains read-only every8hours; automatic_native_dispatch=false.

Observed runs at 2026-11-02T04:16:38.712752+00:00:
- 41385020793: completed/success
- 41385188402: completed/failure
- 41385545130: completed/failure
- 41385528741: completed/failure
- 41385666865: completed/success
- 41385939588: completed/success
- 41386007875: completed/failure
- 41386421055: completed/failure
- 41387369679: in_progress/None
