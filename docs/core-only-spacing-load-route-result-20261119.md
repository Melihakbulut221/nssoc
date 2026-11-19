# Load-isolation route: physical checks passed, fresh timing required — 2026-11-19

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44498843994 succeeded, attempt 1, head 0cf8bef5d231e5df8b0357bf5415aabf15f0b6c4.
Artifact 14517174354, SHA256 6f644670433b0442724d92b94ff50ae804c23a7cbb26b2353495d40ebd913162; all 50 output hashes verified.
Routed ODB: 8bd5334ca987ad52d5987b776587773d801188c9f83119d102cfd63a348d00c8.

DRT violations reached zero at iteration 3. Antenna nets/pins are zero. Independent native geometry reports zero inter-net contacts, no disconnected geometry, no unwired multi-terminal nets and no missing terminal geometry; native removal and synthetic controls passed. The previously measured contact with nssoc_sta_n_55301 is removed.

All 106656 instance identities and terminal connections are preserved. The other 103086 non-power nets and every one of the 2113 clocks are unchanged. Encoded FIXED and restored ROUTED checks cover 102970 paths. Existing NDR assignments and layer rules are preserved.

The next workflow exports DEF and Verilog from this exact routed ODB, verifies the cumulative 1400 added antenna diodes (1398 previous plus ANTENNA_2567/2568), verifies the three new identity buffers and their preparation/power evidence, extracts fresh nominal RC and measures slow/typical/fast timing. Native instance admission is updated to 106656 only for the new candidate. Clock period 20 ns and derating remain unchanged.

Passing these route checks is not final timing, transistor LVS, foundry DRC, qualified min/max RC, full chip integration or manufacturing approval. No fresh electrical/timing result exists yet for this candidate.
