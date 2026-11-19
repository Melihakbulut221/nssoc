# Load-isolation pin comparison and next resize — 2026-11-19

Comparison run https://github.com/Melihakbulut221/nssoc/actions/runs/44505218018 succeeded, attempt 1, head 77fc421c447812bfd392a4d951b90dc397400329. Artifact 14519531109, SHA256 3ae3429f1b82b3731a1360fbc748ee9838d680b81b867e4fc421a226ea8e9102; all 126 outputs verified. Source reports are spacing run 44482078997 and load-isolation run 44502914675.

Slow slew violations: 495 to 480, exactly 15 removed and no new violated pins. Removed pins: load_slew2428/A, load_slew2431/A, nssoc_sta_i_52826/Y, nssoc_sta_i_52834/A2, nssoc_sta_i_57620/A1, nssoc_sta_i_63807/Y, nssoc_sta_i_63808/C, nssoc_sta_i_65288/A1, nssoc_sta_i_65678/A1, nssoc_sta_i_65697/D, nssoc_sta_i_65702/C, nssoc_sta_i_65898/C, nssoc_sta_i_66452/B2, nssoc_sta_i_8457/Y, wire2427/A. Typical/fast slew stay zero. Capacitance and fanout violated pin sets are identical in each corner.

## Next candidate
Two remaining drivers have stronger library equivalents: 61007/Y (nor3_1, actual slow slew 3.452245 ns) and 63722/Y (a21oi_1, 3.292414 ns), against 2.507400 ns limit. Resize them to nor3_2 and a21oi_2 respectively. The other worst drivers 8624/Y and 8545/Y are o21ai_1, with no stronger equivalent in the pinned library; they remain open for later load-isolation work.

Start from the exact physically clean ODB 8bd5334ca987ad52d5987b776587773d801188c9f83119d102cfd63a348d00c8. Verify Liberty function identity and pin identities, freeze all other cells, keep connections exact, bound displacement, derive precisely the incident signal nets from the native database, clear only those routes, and verify all remaining routes and all 2113 clocks. Require four supply contacts with negative controls. No clock, period or derating change.

This is a preparation experiment, not a measured improvement. It requires subsequent routing, DRC/antenna/independent geometry and fresh RC/three-corner STA. The 480 slew, 210 fanout and corner-dependent 52/54/60 capacitance violations remain the last measured counts; full production signoff remains open.
