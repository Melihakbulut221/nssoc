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

## Sizing alone, with placement-estimated wires (run42051193750)

The same database, slow-corner libraries, physical SDC and propagated clocks were used with `set_wire_rc` on Metal2/Metal3 (signal) and Metal4/Metal5 (clock) and `estimate_parasitics -placement`, in the routing engine's OpenROAD (dcf36133). The sequence was `repair_design`, then an unbounded `repair_timing -setup -repair_tns 100`:

| Step | Setup WNS | Setup TNS | Max slew / cap / fanout |
|---|---:|---:|---:|
| before repair | -4.398 ns | -15091 ns | 0 / 0 / 1350 |
| after `repair_design` | -5.098 ns | -16574 ns | 0 / 0 / 1150 |
| after `repair_timing` (850 resized, 267 inserted, 33 removed, 246 pin swaps; "unable to repair all setup violations") | -4.270 ns | -12885 ns | - |

With estimated wires the worst `clk_i` endpoint is -3.21 ns, against -14.04 ns with the extracted SPEF. The remaining worst path is `pcie_clk_i` to the output port `pcie_tx_data_o[0]`: about 35 logic levels from a flop to the port, arriving at 7.22 ns against 2.95 ns required (4 ns period, 0.8 ns output delay, 0.25 ns uncertainty). Sizing cannot close that path; the output needs a register stage at the boundary.

## Routed wire length against pin half-perimeter (run42057290754)

Read-only on the same database (`scripts/mainchip_wire_detour.py`). Over 143706 routed signal and clock nets, the routed length is 13.95 m against 11.88 m of pin half-perimeter (ratio 1.17; per-net median 1.06, 90th percentile 1.40, 99th percentile 2.19). Routing detour is therefore not the cause.

The critical-path nets are long because of where their pins are placed:

| Net | Routed | Half-perimeter | Pins |
|---|---:|---:|---:|
| `net37385` (the `buf_1` fanout output) | 1116 um | 801 um | 9 |
| `$abc$1804206$new_n50559` (the `nand4_1` output) | 735 um | 734 um | 3 |
| `net2903` | 783 um | 785 um | 2 |
| `net2603` | 930 um | 848 um | 9 |

The die is 3326 x 2476 um. The extracted wire capacitance averages 2713.5 pF / 13.95 m = 0.19 fF/um, coupling included, which is higher than the placement estimate assumes. The 10 ns gap between the estimate and extracted timing on `clk_i` is therefore wire capacitance on long, placement-determined nets in the Ibex datapath.

Run42058017703 repeats the sizing probe with wire RC calibrated to that average (0.4 Ohm/um, 0.194 fF/um). The extracted results above would then point to the levers for a new implementation:

- Timing-driven placement or region constraints for the Ibex datapath.
- Registered PCIe boundary outputs.
- Setup repair calibrated to extracted wire capacitance, without the 100-iteration caps.

## Sizing with wire capacitance calibrated to the extraction (run42058017703)

This run repeats the same sizing probe with `set_wire_rc -resistance 0.0004 -capacitance 0.000194`. The capacitance, 0.194 fF/um, is the extracted average. The resistance, 0.4 Ohm/um, is lower than the PDK's LibreLane `LAYERS_RC` (Metal2 2.5, Metal3 1.5, Metal4/5 about 0.65 Ohm/um), so the wire delay here is optimistic. The `LAYERS_RC` capacitances (Metal2 0.169, Metal3 0.183, Metal4 0.166, Metal5 0.086 fF/um) agree with the extraction, so the flow's repair is not working from underestimated wire capacitance.

The job reached the 350-minute limit during `repair_timing` and was cancelled; its streamed log is kept.

| Step | Setup WNS | Setup TNS | Violating endpoints | Max slew / cap / fanout |
|---|---:|---:|---:|---:|
| before repair | -12.343 ns | -48494 ns | - | 1400 / 278 / 1350 |
| after `repair_design` | -12.606 ns | -48030 ns | - | 2 / 0 / 1150 |
| `repair_timing` iteration 130 (worst endpoint is a `clk_i` flop) | -9.258 ns | -41854 ns | 9467 | - |
| iteration 530 (worst endpoint now `pcie_tx_data_o[4]`) | -6.536 ns | -37176 ns | 9467 | - |
| iteration 2450, cancelled (worst `pcie_tx_data_o[2]`) | -6.311 ns | -31079 ns | 9467 | - |

With calibrated capacitance the estimate reproduces most of the extracted -14.04 ns. Unbounded sizing then lifts every `clk_i` path above -6.3 ns within about 500 iterations. The worst remaining paths are the PCIe output-port paths, which the register slices on `timing/pcie-boundary-skid` remove.

The 9467 violating endpoints and the slow TNS progress show that the remaining `clk_i` violations are spread out. Closing them takes a re-implementation with setup repair that is not capped at 100 iterations, plus placement that keeps the Ibex datapath local. This probe is not a candidate, and the cancelled run proves no closure.
