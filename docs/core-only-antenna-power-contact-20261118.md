# Added antenna diode local power contact — 2026-11-18

Run [44383998997](https://github.com/Melihakbulut221/nssoc/actions/runs/44383998997), head 0afa898e2a05fdc00e2a4f38bb620faebd2d0046, completed successfully. Artifact 14465730398 SHA-256 6610d7e0094ba9359005f4c14ad0593b7611898ffa88fff27055e9c702fbde18 and all declared outputs verified.

All 1600 power/ground terminals on the 800 added diodes have positive-area LEF pin overlap with same-net native special-wire metal or via landing geometry. No wrong-supply contact was found. Source ODB 2147b6df67feac28691ca76defdd7d3cafd4df1c00a74c0043fcd55f47767750 remained unchanged. Six geometric fault controls passed. Removing the actual matching rail shape under ANTENNA_1169/VDD caused loss of contact as expected.

Scope: local diode-to-rail contact only. This does not establish full PDN connectivity, internal GDS connectivity, IR/EM, transistor LVS or foundry acceptance.

Reroute run 44383558280 remains active at this checkpoint. Fresh RC/three-corner STA is staged but not dispatched. Its admission requires successful exact routing evidence and the above power-contact proof, with route identity proving the pre-route database's placement and supply geometry were preserved. It exports a new netlist and DEF from the routed ODB, checks 106051 canonical instances, and preserves the existing 20 ns clock and 5% derate. It does not reuse old SPEF/SDF or inherited timing metrics. Nominal RC is not qualified RC min/max. Do not dispatch until the routing artifact is independently admitted.
