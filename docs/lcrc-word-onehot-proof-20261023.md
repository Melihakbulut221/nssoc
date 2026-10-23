# LCRC registered word cursor verification, 2026-10-23

[Run 39890538709](https://github.com/Melihakbulut221/nssoc/actions/runs/39890538709) passed at capacities 4, 5, 8 and 16. Respectively 347, 379, 486 and 761 equivalence points were proved with zero unproved points. Explicit clock/reset-event semantics and undefined memories remain enabled. The newly registered cursor relation is proved, never assumed.

Every capacity passed the arbitrary defined-memory read cut; wrong-word and byte-order mutations produced counterexamples. A frozen cursor failed the full sequential proof at every capacity (two unproved points), and failed both original default-capacity port tests.

At default capacity the original two port tests passed for baseline RTL, candidate RTL, baseline IHP mapped cells and candidate IHP mapped cells. The unchanged four reliable-packet integration cases also passed for both RTL variants. No tests were skipped. Both netlists contain only IHP cells: baseline 1799, candidate 1449. This cell-count reduction is not a routed timing result.

The canonical source is still unchanged. Exact mapped netlists and all original proof logs/counterexamples are retained in the run releases. Receipt: `docs/evidence/lcrc-word-onehot-proof-pass-20261023.json`.

The follow-up `lcrc-word-onehot-timing-cloud` reads those exact mapped files without remapping. It measures register-to-register paths at the pinned IHP typical/slow/fast corners, with the same 4 ns clock, 0.25 ns uncertainty, 1.05/0.95 late/early derates, 0.05 ns diagnostic slew and 0.01 pF diagnostic output load. Interconnect RC is zero and I/O delays are unconstrained; it is a controlled block comparison, not the routed mainchip environment. Candidate adoption requires reviewing these measurements; final closure requires a fresh physical implementation at the original chip constraints.


## Comparative tool correction
The first timing run39891422617 is retained as a tooling rejection: an obsolete Ubuntu OpenSTA could not parse the newer Yosys netlist, and default Verilog cell renaming invalidated JSON-based launch names. No resulting slack is accepted. The follow-up builds the pinned source following the [OpenSTA build instructions](https://github.com/The-OpenROAD-Project/OpenSTA/tree/f2b334cf92b75c4091cb521de4607b0cf54c7b1b), with pinned CUDD. A scalar-only rendering of the exact mapped JSON is re-read by native Yosys and compared for every cell type, parameter, pin and port; a deliberately corrupted D pin must be rejected. This is a spelling/interface correction, with no synthesis, sizing or timing-constraint change.
