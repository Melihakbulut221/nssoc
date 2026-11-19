# Resize-neighbor route result and antenna repair — 2026-11-19

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44513619343 (head 0932f2f79408836e0180d5289a340b09b7c8f96d, attempt 1) was rejected solely at the zero-antenna gate after geometry passed.
Artifact 14525048985, SHA256 c5462d5eef29d68908c3fdb80c4ec1ae800f3ec7c3ddf9dbae315299fa09291d; all 47 outputs independently verified in memory.

All 32 prior inter-net metal contacts are removed. Native geometry reports zero contacts, zero disconnected signal geometry, zero unwired multi-terminal nets and zero missing terminals. Synthetic and actual route-removal negative controls passed. DRT reaches zero DRC at iteration 3. 103076 unaffected non-power records and all 2113 clocks remain exact. 106656 instances and 103090 nets remain unchanged. This is not full GDS or transistor LVS.

ODB SHA256 8569baaabaf2e1c027eb5c59a8872a9d1936dc2d40d6781f17c0e36fbf0eafe5.

Remaining antenna: one net nssoc_sta_n_60783, two sinks nssoc_sta_i_61075/B and fanout935/A. Metal5 ratios 289.88/296.35 and TopMetal1 304.13/310.60 exceed 200; the TopMetal2 checks pass. No waiver is applied.

Next preparation invokes native diode-only repair with 10 percent ratio margin on the admitted routed ODB, verifies that every new diode belongs only to 60783, checks legal placement, unchanged original geometry/connections, positive supply contact and negative controls, and preserves every other signal/clock route. Native repair may select one through four diodes; exact inventory, names and instance delta are recorded and checked. Rerouting, zero antenna/DRC, independent geometry, fresh RC and all-corner timing remain mandatory afterward. 50 MHz/5 percent derating are unchanged. No production approval is claimed.
