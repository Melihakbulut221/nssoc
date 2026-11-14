# Retry write-enable buffer repair — 2026-11-14

The prior routed slow-corner critical path starts at `u_pcie.flow.packets.retry.write_valid`. Its `place31551` buffer (`sg13g2_buf_1`) drives 0.299358 pF with 1.540707 ns output slew and contributes 1.204865 ns delay. The whole path has -0.799543 ns setup slack at the original 4 ns PCIe clock. There are no hold-delay cells on this path. Source: run 43579643337, artifact 14111793410, `nom_slow_1p08V_125C/max.head.rpt`.

The isolated candidate replaces that buffer with `sg13g2_buf_4`. Native legalization moves only the selected instance 1.92 µm left on the same row and changes its orientation from R180 to MX. A fresh native placement check passes. All other 159,933 instance masters, positions, orientations and placement statuses remain unchanged; every net connection and all 354 top ports match. See the [placement receipt](evidence/retry-driver-buf4-placement-20261114.json).

The actual fast, typical and slow Liberty files are bound by hash to the frozen implementation input package. Yosys imports their Boolean functions and proves `buf_1` equivalent to `buf_4` for all inputs in each corner. Substitution by an inverter produces a proof failure in each corner. All three positive cases and three negative controls pass in [run 43611046213](https://github.com/Melihakbulut221/nssoc/actions/runs/43611046213); the [receipt](evidence/retry-buffer-liberty-equivalence-20261114.json) retains file and log hashes. This proves Boolean equivalence, not delay equivalence.

[Run 43610680141](https://github.com/Melihakbulut221/nssoc/actions/runs/43610680141) reroutes the candidate and then extracts RC and measures setup, hold, capacitance, slew and fanout at all three original corners. The original independent netlists receive exactly one reversible buffer-master replacement so their reference agrees with the sized layout. Clock constraints and all acceptance thresholds remain unchanged.

The candidate is not yet accepted as a routed or timing-closed design. A larger buffer can increase its predecessor's load and worsen short-path hold. New geometry must receive fresh routing, extraction, DRC, antenna and LVS verification. The old chip LVS pass and this local function proof do not establish those results or complete serial PCIe PHY integration.

## Subsequent baseline measurement

The diode-legalized baseline finished extraction and STA in run 43591198141. It still fails acceptance: slow setup 539 endpoints, worst -1.074318 ns; typical hold 8 endpoints, worst -0.033812 ns; fast hold 115 endpoints, worst -0.110755 ns. Router DRC remains zero, but antenna violations remain at 377 nets / 424 pins. Capacitance, slew and fanout violations are also nonzero. See the [full measurement receipt](evidence/diode-legalized-routed-sta-20261114.json).

The new worst write-enable branch includes a `nand3_1` with 1.356738 ns delay and `place31537` (`buf_1`) with 0.977058 ns delay. It differs from the earlier `place31551` branch targeted by the running experiment. That experiment remains useful as an isolated comparison, but cannot be assumed to close the distributed decoder/load problem. A registered partial write-address decode is a possible next candidate; it has not been implemented or qualified.
