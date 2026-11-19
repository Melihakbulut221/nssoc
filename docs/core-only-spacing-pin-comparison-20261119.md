# Spacing ECO pin-level comparison — 2026-11-19

Verified report bundle run https://github.com/Melihakbulut221/nssoc/actions/runs/44483545915 at `19371c36bb24e3cad037c2c9f836fc6cf0467b3a`, attempt 1. Artifact 14509217737 SHA256 `8935fd6f0c03acac0ddcdcc1f0ea5ed0f0724a658e8696a113a973296c725313`; 189 report/output hashes checked. Sources: baseline 44459123476, resize 44468611583, spacing-plus-diode 44482078997.

Slow slew pin sets: 502 -> 507 -> 495. Comparing resize to spacing, all 13 regression pins disappeared: ANTENNA_185/A, ANTENNA_186/A, ANTENNA_187/A, ANTENNA_188/A, ANTENNA_2127/A, nssoc_sta_i_53399/Y, nssoc_sta_i_53400/B, nssoc_sta_i_54480/Y, nssoc_sta_i_54488/A2, nssoc_sta_i_57716/A1, nssoc_sta_i_57755/Y, nssoc_sta_i_57756/D, nssoc_sta_i_57928/B2. One new pin appeared: nssoc_sta_i_57622/A_N. Against the original baseline, eight removed pins remain removed and this one pin is the only addition.

Typical slew 4 -> 0 -> 0; fast slew 0 throughout. Slow capacitance pin sets are identical (52). Typical capacitance 54 -> 55 -> 54 and fast 60 -> 61 -> 60: fanout4850/X is no longer violating. Fanout pin sets are identical at 210 in all corners. Rows with omitted fanout slack were retained; counts agree with metrics.

Worst remaining slow driver outputs include nssoc_sta_i_8457/Y (3.671868 ns), 52826/Y (3.637674), 63807/Y (3.572289), 8624/Y (3.562521), 8545/Y (3.523937), and 61007/Y (3.452245), against 2.507400 ns. The next read-only native inventory binds the measured 106651-instance ODB and includes these drivers, 63722/56298 and the new 57622 input violation. Inspect actual fanout, load locations and available masters before selecting load isolation or logic restructuring. Do not assume an unavailable o21ai drive variant exists.

This comparison is diagnostic evidence, not electrical or production closure. Setup/hold remain zero only under the measured nominal-RC corners; slew, fanout, capacitance and broader signoff remain open.
