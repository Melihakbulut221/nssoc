# Fresh RC and three-corner STA on the current main-chip route

Run42047826928 (`analysis/mainchip-sta`, `scripts/mainchip_sta_measure.py`) measured the routed database of run42001907194 (artifact 13423006669, full `check_drc` 44). It is a measurement, not the qualified post-route wrapper, and accepts nothing.

## Inputs and bindings

- The routed database was exported with the routing engine itself (OpenROAD dcf36133): 154480 instances, 143820 nets, 354 ports.
- `write_verilog -include_pwr_gnd` of that database is byte-identical to the qualified handoff export of run41789053844 (`handoff-candidate.v`, SHA-256 45dab536...). The timing netlist is therefore the same design whose instance and boundary connectivity the handoff proved.
- PDK (c4b8b4e5...), configuration, SDC (19fdfb6d...) and macro views come unchanged from the verified post-route input package of run39635867954, which is restored file by file against its contract hashes.
- RC: the repository's `AuditedRCX` in LibreLane 3.0.5 (IHP_rcx_patterns.rules, SHA-256 ffda02d5..., nominal only). The SPEF audit passes: 3182554 coupling entries, 0 inconsistent nets.
- STA: the repository's `AuditedRoutedSTA` (standalone OpenSTA, derate guard, original clocks 20/4/8/8 ns, every clock propagated, `unpropagated.rpt` empty in all corners).

The LibreLane AppImage does not start on the ubuntu-24.04 hosted image (`cannot write uid_map`). The job therefore runs on ubuntu-22.04, as the earlier post-route jobs did.

## Result

| Corner | Setup WNS | Setup violations | Hold WNS | Hold violations | Max cap | Max slew | Max fanout |
|---|---:|---:|---:|---:|---:|---:|---:|
| nom_slow_1p08V_125C | -14.038 ns | 9652 | -0.487 ns | 5 | 581 | 1839 | 1350 |
| nom_typ_1p20V_25C | -5.390 ns | 6177 | -0.405 ns | 12 | 593 | 48 | 1350 |
| nom_fast_1p32V_m40C | -2.624 ns | 2025 | -0.343 ns | 18 | 607 | 22 | 1350 |

3749 nets are unannotated in every corner, and 0 remain after LibreLane's filter. The earlier 153130-instance repair-deep route (run39904823953) measured -15.52 / -5.73 / -2.58 ns setup WNS and 9683 slow-corner setup violations. The current route is therefore in the same state, and no setup/hold gate is closed.

## Where the slow-corner setup time goes

All 737 worst `clk_i` paths in the first 20 MB of `max.rpt` start at one Ibex register-file flop (`u_ibex.gen_regfile_ff.register_file_i.g_plain_rf.g_rf_flops[11].rf_reg_q[24]`). They pass through operand compare logic and an adder carry chain to arrive at about 34 ns against the 20 ns period. The delay is dominated by heavily loaded single-drive cells:

- `fanout37385` is an `sg13g2_buf_1` driving 8 loads (0.27 pF): 1.69 ns slew, 1.41 ns delay.
- An `sg13g2_nor4_1` reaches 2.50 ns slew and 2.11 ns delay.
- An `sg13g2_nand4_1` drives 0.18 pF: 3.23 ns slew, 3.01 ns delay.
- A second `sg13g2_nor4_1` takes 1.72 ns, and an `sg13g2_o21ai_1` takes 1.07 ns.

The clock tree inserts 2.7 ns of latency through the Ibex clock gate, and that latency is common to launch and capture.

In the typical and fast corners the worst paths are `pcie_clk_i` (4 ns) paths from top-level input ports (-5.39 ns typical, -2.62 ns fast) and `pcie_clk_i` register paths around -3.3 ns typical. The hold violations are a few `pcie_clk_i` flops, two reset-recovery (asynchronous) endpoints and two Ethernet MAC paths. All are below 0.5 ns.

The slew and capacitance counts, together with the single-drive cells on the critical path, show that the post-CTS and post-GRT setup repair stopped well short of convergence. The interface flow caps those searches at 100 iterations, so cell sizing and buffering are the first lever. Whether sizing alone can reach 20 ns at the slow corner is the next measurement.
