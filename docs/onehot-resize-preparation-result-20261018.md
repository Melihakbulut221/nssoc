# Native measured driver resizing passed preparation

[Run 39160200022](https://github.com/Melihakbulut221/nssoc/actions/runs/39160200022), source `9eb5f112210e144d8d8b58b46725ea569913ebcf`, passed actual OpenROAD sizing, legal placement and native logic proof. Fifty existing slow-path positive buffers were resized to buf8/buf16 according to measured capacitance. All 146728 instances and net memberships remain; other-cell master/position/orientation, PG, ports and NDRs are unchanged. Thirty-six targets changed orientation to match their new actual row. Their row, site and bounding box were verified after native check_placement.

The native equation proof retained 102646 non-buffer cells and contracted the same 34348 positive buffers on each side. Macro/state and control tests passed within the documented proof scope. Deliberately inverting an actual resized driver was rejected. This is not transistor LVS, SRAM interior proof or timing acceptance.

Candidate ODB SHA256: `3112f7db61f5f439f1827ac9a947c29b567086a0a1f4bb85bc8bd811ffa1626c`.
Candidate netlist SHA256: `51ed3101e6ce27b128c1fd55655334accd156535aae566b07f2795354b4b0a70`.

Every old signal route, guide and inherited SPEF/metric has been discarded. Fresh full routing, antenna/connectivity checks, RC and three-corner STA are the next required gates. Original frequencies, uncertainty, derating and acceptance thresholds remain unchanged. Previous failed runs are preserved.
