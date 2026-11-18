# Third antenna repair: routed core evidence

Run: https://github.com/Melihakbulut221/nssoc/actions/runs/44392013502
Source: bea6ce2b77b37f1d7260008aa35007cef91c7f73
Artifact: 14470750161; SHA256 649654de02cb1931abd888d8ffbb038f5cb743e89aa8dfe4a7ee484805fb8415.

The completed successful run and all 18 output hashes were independently verified from the artifact. Native OpenROAD routing DRC: 0. Antenna violating nets/pins: 0/0. The third round added three sg13g2_antennanp cells, for 106083 total instances and 832 diodes added across the three repair rounds. All original instance geometry, placement status, masters, terminal connections, net names/types and special-wire/port/die geometry were preserved. The six new power terminals have positive-area same-supply rail contact and no wrong-supply contact. Visible wire/via and LEF terminal geometry has no disconnected nets, unwired multi-terminal nets, missing terminal geometry, or inter-net contacts; negative controls passed.

Final routed ODB SHA256: 4a618b8c1bad70988890ae099ca8d94c37495bc8fd56a9b6d38c64303b81bbf4.
Inserted pre-route ODB SHA256: 6c20516966e38f3459bed517e1d8932fc3835980123b469f0d58b3e9bcb35e9b.

## Next admission and remaining gates

Bind fresh native netlist/DEF export and RC extraction to this exact artifact and ODB. Compose the 800 + 29 + 3 new-diode inventories and physical power-contact evidence from all rounds. Check all cumulative new diode connections in the fresh netlist. The earlier extraction-v4 staging targets the failed first reroute and MUST NOT be dispatched unchanged. Preserve 20 ns clocks and 5 percent derate; old SPEF/timing results do not establish this candidate's timing.

This establishes native core routing/antenna and visible geometry checks only. It is NOT foundry DRC, hidden cell/SRAM transistor LVS, qualified min/max RC, fresh post-route setup/hold or electrical closure, hierarchical pad/core signoff, global PDN/IR/EM, ESD, or manufacturer approval. External package/PCB/device timing remains unspecified by the user. PCIe and Ethernet remain outside the user-approved reduced scope. The diode DC branch diagnostic run 44392633722 is separate and was still live when this checkpoint was recorded.
