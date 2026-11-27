# First detailed route, native LVS input receipt

The stream-out for this completed interface-profile checkpoint used the DEF and powered Verilog exported from one OpenDB database. The root circuit is `soc_top`. This receipt covers the first detailed route. The newer banked-Ibex experiment requires its own stream and schematic.

| Input | SHA-256 |
|---|---|
| Routed ODB | `786b3109036a98ef1cef238f1742d1566c9c95166b91c263425fde6747ff7067` |
| DEF | `2f0bf6ed51099bc2b3be4d797a6c8d5cbaf76b49fabeef044cf7b3a320ae3d6d` |
| Powered Verilog | `241000a2bae24a0548c7eda14b5bbe436dfd8555a5714c021f9b48617df52a28` |
| Stream GDS | `c8c79effcea9c03349272051318c302ae32cb710872d15135021ecf2ca7e5d56` |
| OpenROAD top CDL | `58efab7ccf7486a70cc573b3857b996b960ba2a934cf52c74544fce4f10b5139` |
| Reference with reachable cell definitions | `c1cbfcd2b317e0838b09fa1e1bd871a693a21bc8067ed5609c4a2e5b13a7736c` |
| IHP native LVS deck | `5de8c4b60398f95d5a596b265dc4f723f2a208c908b71284770180dbe62bd234` |

OpenROAD revision `dcf36133a369abc8f3c5e5738cd4d82e4903c0e0` read the routed database and ran `write_cdl -include_fillers -masters $masters snapshot.cdl`. The master files were the standard-cell CDL and the RM_IHPSG13_2P_256x16_c2_bm_bist and RM_IHPSG13_1P_2048x64_c2_bm_bist CDL files at PDK revision `c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c`.

Recursive resolution from the exported top found 145 definitions including the top. Instance terminal counts matched formal terminal counts throughout. Both top views contained 101,118 instances and their per-master counts matched. This checks reference completeness. Connectivity still requires the GDS comparison and the explicit native report gate `make check-native-lvs LVS_DB=<report.lvsdb> LVS_TOP=soc_top`. The run uses deep extraction with a 1,200-second diagnostic bound. This input receipt records no passing LVS verdict.
