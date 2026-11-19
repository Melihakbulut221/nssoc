# Load-split electrical pin delta — 2026-11-19

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44570529195 completed at `4753cbe3fc7b357bbefd14d6d2ee5d706fad8179`. Artifact 14552649545, SHA-256 `69e213a43b5117fbc7e5915c3983059808060fdaf6ed930e29b42cce50cfccc8`; three per-corner outputs verified. All pin inventories were checked against native violation counts.

Slow slew: 39 old violating pins removed, seven new violations added, net 456 to 424. New pins: `load_slew2983/A`, `max_cap11665/A`, `nssoc_sta_i_52788/Y`, `nssoc_sta_i_52789/B`, `nssoc_sta_i_57622/A_N`, `nssoc_sta_i_9021/Y`, `wire2982/A`. These remain explicit repair targets.

Fanout: three violating pins removed with none added, all corners 210 to 207. Capacitance: four pins removed in each corner; slow corner adds `fanout4411/X` (0.300978 pF against 0.3 pF), typical/fast add none.

Worst remaining slow slew is `nssoc_sta_i_54307/B` (input pin) at 3.225667 ns; associated driver `nssoc_sta_i_54306/Y` is 3.217954 ns. Next driver `nssoc_sta_i_59165/Y` is 3.131460 ns. Worst fanout is `nssoc_sta_i_78670/Q`, 19 against limit 8. Worst fast capacitance is SRAM `u_ram.g_ram_2048x64_ecc.u_b1/A_DOUT[12]`, 0.105566 pF against 0.064 pF.

Next: read-only native inventory of every remaining violation pin, its net, driver, loads and available cell masters. This supports broader repair planning and includes regressions; no exceptions or timing constraints are relaxed. SRAM output buffering is distinct from qualifying SRAM Liberty and transistor LVS.
