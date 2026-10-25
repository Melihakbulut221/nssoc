# CDR v22 retime-input routing — 2026-10-20

V21 remains electrically rejected. Native late waveform re-analysis reproduces the original checks: A and B have no wrong-sign samples but 129 and 64 below-100mV samples; C has 115 wrong and 130 below-100mV samples, D has 252 wrong and 277 below-100mV samples. At the capture edge the C master input is only 7.27mV minimum signed and D is -22.04mV. These diagnostic observations do not replace the original three sample phases.

The fresh passive measurement from run 39451162827 gives collector-to-filter incident wire capacitances C+/C-/D+/D- of 0.4674/0.5279/0.3426/0.3920pF, reduced from v20. The following filter-output-to-sampler networks still contain 0.2481/0.2571/0.2305/0.2382pF and 46.37/54.92/45.73/54.28ohm effective metal resistance to the sampler series-resistor terminal. These values are native-network measurements, not qualified foundry RF PEX.

The next physical candidate shortens cup, cun, dup and dun. The actual v21 GDS has eight long horizontal arms from x478.4–556.8um to x989.2um. The existing proven corridor planner moves their four vertical trunks toward the macros while checking actual flattened TM1 obstacles, including the already relocated v21 collector trunks and the AVDD rail. It preserves all 16 children, their placements, primitive parameters, public pins, schematic and LEF. Only twelve route rectangles and eight native via cuts may move; undeclared geometry changes are rejected.

A complete native 484-device DRC/deep+flat LVS and the original fault controls are mandatory. After that, fresh RC extraction, MIM binding and original loaded early/late/fault waveforms are still required. Shorter wire length is a hypothesis for faster transfer, not acceptance or a guarantee. No clock phase, sample time, voltage limit, device limit or solver criterion is relaxed.

Everything runs on GitHub-hosted workers. Local workspace remains empty.
