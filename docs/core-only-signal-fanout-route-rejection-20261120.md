# Signal fanout route rejected — 2026-11-20

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44573258297
completed with failure. It was not cancelled or timed out. Detailed routing
completed in 3h55m41s, with zero native DRC violations at iteration 30.
Independent native geometry checks found 680 inter-net shape contacts; no
unwired multi-terminal nets, disconnected signal nets, or terminals without
geometry were reported. Antenna checking found 13 nets / 17 pins violating.
Zero router DRC therefore does not establish physical acceptance.

Archive 14574906878, SHA256
49146cfdc855dcecc16424a8875ff02ba59fe5874e58a990f450e8cc5e0074f1,
and all 45 inner output hashes were independently verified. Routed ODB SHA256:
aa14215aceb062d14e6a39eb576e369a37ff31f7157762caaea47e78f7f603e7.
Identity checks preserved 107106 instances / 103530 nets and terminal
connectivity. The 102910 unselected nonpower records and 2113 clocks were
preserved. 102794 fixed wires were restored to ROUTED status.

Complete contact counts and actual violating antenna pin/layer records are
stored in [the diagnostic evidence](evidence/core-only-signal-fanout-route-rejection-20261120.json).
The geometry example list is truncated to 100 entries by the producer; use the
complete contact_counts-derived list, not only examples, to select neighbors.

Next: derive the involved unselected signal nets from the authenticated full
contact list; check that no clock net is silently released. Adapt the established
neighbor-release route procedure from the original prepared candidate, keeping
unaffected wires and cell placements protected. Revalidate contacts and antennas
before fresh extraction. Antenna protection may require a subsequent measured
diode repair; do not remove or waive the current 13/17 violations. New diodes
must be included in load counts and postrepair STA.

This rejected route is not admissible as a fresh-RC signoff source. No timing
improvement is established for the 413-buffer experiment. The prior completed
nominal-RC result remains the timing baseline. Qualified RC corners, SRAM and
whole-chip production validation remain open.
