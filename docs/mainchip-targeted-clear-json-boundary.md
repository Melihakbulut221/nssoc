# Preserve exact snapshot representation at the targeted wire-clear boundary

Actual route41266854050 failed before detailed_route, at the strict unchanged-master check after removing828 owned wires. Its fixed ODB and fixed snapshot matched their original byte pins; the process used about1.5GiB RSS with over13GiB available. Cleanup retained all1691 source clock/fixed records and complete native output.

Cloud readback41269689818 authenticated every member of the872464089-byte original archive, read both complete snapshots and passed the unchanged strict clear_delta across the whole design. Serialized master geometry was exactly equal. Replacing one saved box list with an equal Python tuple reproduced the same unchanged-snapshot-masters exception. The witness is SRAM master RM_IHPSG13_1P_2048x64_c2_bm_bist, A_ADDR[0], Metal2 box(388440,0,388700,260).

The native adapter now reloads its just-saved after snapshot before comparing it with the already-loaded before snapshot. It frees the in-memory snapshot before reading the saved one. The strict master, instance, protected-net, PG, net-identity and routing-scope predicates are unchanged. No geometry expectation was removed or normalized away.

The existing15-test scope suite now includes the actual reader regression: tuple/list representation passes after serialization, but a changed coordinate, missing pin or changed unowned wire still fails. All original source/host/stale/bulk/saved-diode tests remain required before a new independently reserved actual route attempt. The failed native attempt and readback proof remain preserved. This fix is not routed-layout, timing or PHY acceptance.
