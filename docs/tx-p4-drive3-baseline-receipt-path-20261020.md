# TX p4-drive3 baseline receipt path correction — 2026-10-20

Cloud run 39452581487 completed the native master-substitution comparison, then both waveform jobs stopped in check_tx_p4_drive3_builder.py before ngspice was started. The checker named a nonexistent October 19 wire20 composition receipt; the actual wire20 receipt is dated October 20 and pins run 39407840528. This is an infrastructure rejection, not a measured waveform result.

Only that receipt filename and its exact source-delta manifest are corrected. The 1674-device native circuit, all RC, all 256 bits and three sample phases, device bounds, solver settings and physical clock assignments are unchanged. Original run and failure outputs remain available. The next cloud run must still pass every electrical gate before any acceptance claim.

Work is cloud-only. No source checkout, CAD process, waveform or layout artifact is stored in the local project folder.
