# Lower-metal spacing candidate — 2026-11-19

## Measured rejection
Run https://github.com/Melihakbulut221/nssoc/actions/runs/44471950240 at `1a6ba054e3a17179ff3b0099e1c5a2b7d3e2b0eb`, attempt 1, failed antenna admission. Artifact 14506240399 has SHA256 `05bc324883ba6613a33805d26a56bad4ecae4f54af716ba8ca51536f056744b5`.

Native route DRC: 0. Independent native geometry: 0 cross-net contacts and no disconnected signal geometry. 103067 unselected net records and 2113 clock records unchanged. However `nssoc_sta_n_56323`, sink `nssoc_sta_i_55608/B`, has TopMetal1 cumulative antenna ratio 212.86 against 200.00. This candidate remains rejected and is not a replacement for the measured baseline. No fresh timing closure is claimed.

## Next controlled experiment
Retain the same three resized cells, 18 reroutable signal nets, four aggressor assignments and all route-preservation checks. Apply 2x spacing only on Metal2–Metal5, with explicit default spacing on Metal1 and both top metals and default widths everywhere. Hypothesis: avoiding expanded top-metal spacing may reduce detours that contributed to antenna area. This is not an established cause or result. Re-run native DRC, antenna and independent geometry; require all to pass before fresh extraction/STA. No antenna thresholds, SDC, library limits or signoff criteria are relaxed. The cloud preflight verifies every output hash of the rejected predecessor before execution.

## External interface boundary
The user confirmed package, PCB and attached devices are not selected. External I/O timing remains unqualified. Do not invent QSPI part, board delays, loads or operating rates. Continue internal implementation with this limitation recorded; package/board selections and actual external timing budgets are required for final signoff.

PCIe and Ethernet remain excluded from the approved reduced scope. Manufacturing approval is not complete.
