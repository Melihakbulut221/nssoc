# Current routed-chip candidate review

The complete cloud readback 40930102746 passed. Its 677 local material records and embedded technology are preserved in f9d2b1b1, tied to current serialized ODB 47d657f4. This review does not alter geometry or accept routing.

The immediate two-Via4 Metal4 bridge at x=947520 is rejected: it lies inside the SRAM Metal4 master obstruction. Shifting to x=949440 hits VPWR; x=952320 hits another SRAM obstruction. A direct TopMetal1 bridge overlaps the existing delay clock route. Two inspected lower escape routes also hit existing clock material. Full exact witnesses and coordinates are in the companion JSON.

These observations explain why a layer-name substitution or an unverified short detour is inadequate. No replacement route has been accepted. Continue with a bounded multilayer candidate using the authenticated all-layer census and actual spacing/enclosure/area/grid rules, enlarging the native readback window on GitHub if needed. Preserve net36993, all non-target material and the 1,691 original fixed/clock records. Any candidate still needs paired DEF import, serialized readback, full original-class DRC and original 20/4/8/8 ns plus 5% timing.

All calculation and native files remain on GitHub runners. This source-only review used existing derived JSON/text evidence; it ran no local CAD or tests.
