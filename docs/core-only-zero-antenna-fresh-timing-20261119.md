# Fresh nominal RC timing: zero-antenna routed core

Evidence run: https://github.com/Melihakbulut221/nssoc/actions/runs/44396480600 (attempt 1, success).
Source commit: 35697a797feab75754dd73e52505671fd1ddcddb.
Artifact 14470687470, SHA256 f357f6d4982f38a539b6ce5b550bfc89e81cb67c672501efdfeb0c3e247be5db. All 128 output hashes independently verified.
Routed ODB 4a618b8c1bad70988890ae099ca8d94c37495bc8fd56a9b6d38c64303b81bbf4.
Fresh netlist 2c5c94ab412759d733faa60db7815112e93d699dd7b669ca8334135630a225f5.
Nominal SPEF c20ef99a3c5e78bd6bec419a8da89e9fdf88f7671ac20caa6494abd940740185.
All 832 added antenna diodes exported with exact signal connections, no missing/duplicate cells.

| Corner | Setup count | Setup WS ns | Hold count | Hold WS ns | Slew | Fanout | Cap |
|---|---:|---:|---:|---:|---:|---:|---:|
| Slow 1.08V 125C | 69 | -0.870328 | 0 | 0.440273 | 519 | 126 | 47 |
| Typical 1.20V 25C | 0 | 6.864777 | 0 | 0.180587 | 2 | 126 | 51 |
| Fast 1.32V -40C | 0 | 10.342856 | 0 | 0.033758 | 0 | 126 | 56 |

50 MHz, 20 ns and 5 percent derate are unchanged. This is nominal extracted RC, NOT qualified min/max RC or full-chip signoff. All 1403 unannotated drivers were classified: 1288 disconnected outputs and 115 connected with no sink. No loaded unannotated driver was found; this is not blanket coverage acceptance.

## Source-bound targeted ECO diagnosis

The slow-corner violator_list.rpt lists 69 violating register-to-register paths, all from nssoc_sta_i_77897/Q or nssoc_sta_i_77912/Q. Worst endpoint nssoc_sta_i_78563/D has -0.870328 ns slack. Its max.rpt includes:

- nssoc_sta_i_2496/Y (nor2_1): 1.214957 ns slew, 1.047554 ns cell delay.
- nssoc_sta_i_3421/Y (xnor2_1): 1.030920 ns slew, 0.898038 ns cell delay.
- fanout677/X (buf_1): 0.852229 ns slew, 0.928345 ns cell delay, cap 0.134655 in report units.
- fanout657/X (buf_1): 0.568426 ns slew, 0.552747 ns cell delay.
- fanout644/X (buf_1): 0.726911 ns slew, 0.728221 ns cell delay.
- nssoc_sta_i_15033/Y (o21ai_1): 1.228134 ns slew, 1.028035 ns cell delay.
- nssoc_sta_i_15034/Y (a21oi_1): 2.999910 ns slew, 2.865788 ns cell delay, cap 0.233795 in report units.
- fanout541/X (buf_1): 1.293907 ns slew, 1.123320 ns cell delay.

These are diagnosis targets, not accepted replacements. First evaluate library-valid resizing/load splitting on the shared data paths, checking both early and late timing. Preserve logic function, all antenna protection, PG connectivity and fixed macros/clock tree. Do not resize blindly: larger input capacitance can worsen upstream gates and 33.8 ps fast hold margin is small. Each physical candidate requires legality, rerouting, zero-DRC/antenna checks and fresh RC/three-corner STA; unchanged SPEF cannot validate a changed route. Do not use constraints or Liberty edits to hide failures.

Remaining independent blockers include pad disable slew/model diagnosis, full cell/SRAM transistor LVS, qualified RC corners/SRAM models, hierarchical chip timing and signoff, external package/PCB/device budgets, PDN/IR/EM/ESD and manufacturer approval. PCIe and Ethernet remain outside the approved reduced scope.
