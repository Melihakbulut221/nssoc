# Original-clock candidate: setup and hold zero in global-route estimates

Run **44254614637**, source **609a6568e1d793eff18885d0d20f5b43b90e7be4**, completed successfully. Independent inspection verified every archived output hash and six fresh corner metric files, including their reported values. All three final STA logs confirm global routes and contain no EST-0026 warnings. See `docs/evidence/core-only-route-refine200-20261118.json`.

Final timing: slow setup 0, worst slack +0.0195897 ns; typical setup 0, +5.41767 ns; fast setup 0, +8.56396 ns. Hold violations are zero in all three corners; worst hold slack is +0.503234 / +0.218151 / +0.0395028 ns (slow/typical/fast). The slow setup count fell from 41 to 0. Electrical violations remain: slew 12/0/0, capacitance 2/2/2, fanout 748/748/748.

This is the ORIGINAL clock topology, not the separate zero-fanout clock-split topology. Do not combine its timing with the other candidate's fanout result. Constraints remain 20 ns and 5% derate. Parasitics are global-route estimates; narrow positive margins do not establish detailed-route timing closure. Acceptance and final timing remain false. Detailed routing, qualified extraction, electrical closure, post-ECO equivalence and full physical/product signoff remain required.

The zero-fanout candidate's post-GRT repair is run **44256809783**, last observed in progress. Preserve it and compare its actual final fresh reports before selecting the next physical candidate. No duplicate or additional repair was dispatched for this result.
