# Common setup-driver selected routing — 2026-11-19

Preparation run 44451541789 at 54f69c44d1155216d7309873f97aec09a4c48462 succeeded. Route admission authenticates artifact 14495583524 SHA256 c15fe2a7fbeac097c782c716191d9e946547e900c6ca922e21afff743ed61fd2 and every manifest output before consuming the candidate.

The two equivalent-function master swaps are nssoc_sta_i_2496 nor2_1 -> nor2_2 and fanout2484 buf_1 -> buf_4. No other cells are changed. Re-route exactly nssoc_sta_n_97068, nssoc_sta_n_97069, nssoc_sta_n_11183, nssoc_sta_n_11352 and net2484. All other native wired paths are encoded FIXED for detailed routing, verified by dbWireDecoder, then restored to ROUTED with per-record equality checks. All 2113 clock records and 103080 unselected non-power records must remain identical. Full cell, terminal, special-wire, port and die identity checks remain mandatory.

Native route DRC zero is insufficient: independent same-layer short and connectivity geometry checks, plus antenna checks, must pass. If a fixed neighbor conflict appears, reject and investigate the specific geometry rather than accepting it or rerouting clocks. Fresh RC and all-corner timing remain required; this is not timing closure or production signoff. The retained 50 MHz / 5 percent constraints are unchanged. External package/PCB/devices remain unselected.
