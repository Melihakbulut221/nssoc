# Clear persisted native layer capacity reductions

Run 39427183963 failed GRT-0116 with exactly the same eight overflow edges and
17,961,357 um global wire length as the preceding 20% trial. Its archived native
Tcl did contain wildcard adjustment 0.0, but the actual routing resource table
still showed 20.74–41.24% reduction and GRT-0704 still named the 20% setting.
Thus this was not evidence that a true zero-per-layer trial failed.

OpenROAD distinguishes the global adjustment from per-layer values:
https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/grt/src/GlobalRouter.tcl
https://github.com/The-OpenROAD-Project/OpenROAD/blob/master/src/grt/src/GlobalRouter.cpp
The native ODB layer field retains its own setting. The revised flow explicitly
sets each allowed signal layer to zero and records native getLayerAdjustment
before and after, refusing to route if any readback is nonzero. This is tested
on the pinned native runtime, not inferred from the source text alone.

No track geometry, blockage, fixed clock route, instance placement, circuit,
timing target, DRC or antenna gate changes. No negative capacity and no
allow_congestion option. Effective resource counts can still be reduced by
actual obstructions. Full detailed routing, fresh extracted RC and original
three-corner setup/hold/electrical checks remain mandatory.
