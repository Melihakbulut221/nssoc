# Resized core pin-level regression review — 2026-11-19

Comparison source: https://github.com/Melihakbulut221/nssoc/actions/runs/44530797223
Head ca3858b4ed8be455acab8103fb278f90eb38bafa. Artifact 14534485221, SHA256 ee1d29007f07d60119aa7aeb9f62996162aff9424828fea44f509adf3895a857. All 126 output hashes verified.

Slow-corner slew: 10 removed pins and 2 added pins, net reduction 480 -> 472. Removed: ANTENNA_1405/A, fanout935/A, nssoc_sta_i_61007/Y, nssoc_sta_i_61075/B, nssoc_sta_i_63722/Y, nssoc_sta_i_63729/A2, nssoc_sta_i_64072/B2, nssoc_sta_i_64165/B, nssoc_sta_i_65944/A2, nssoc_sta_i_66027/A2.

Added: nssoc_sta_i_65080/Y (2.531092 ns), nssoc_sta_i_65081/B2 (2.531452 ns), both against 2.507400 ns limit.

New fanout violating pin in all three corners: nssoc_sta_i_61007/Y, 10 against limit 8. The source inventory has two functional sinks plus eight newly added antenna diodes; confirm from current native ODB before proposing a fanout/antenna change. Do not waive diode loads or delete antenna protection based on timing alone.

Worst remaining slow driver is nssoc_sta_i_8624/Y at 3.495598 ns; nssoc_sta_i_8545/Y is 3.403015 ns. Native inventory of these drivers, both new slew pins, 61007 and 56298 is next. No closure claimed. Reported aggregate fanout counts are 211; the simple pin-row comparison parses 131 five-column rows, so that parser is not a complete fanout census.
