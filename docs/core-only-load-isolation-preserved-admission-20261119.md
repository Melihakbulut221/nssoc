# Preserved-route two-buffer candidate admitted to routing experiment

Run 44429837311/head 619af32fe137b8b462e2b914768582c32c3767e7 passed preparation. Artifact 14487100254 SHA256 8b093ce66665f3b4a52861dbe0835902e3a275e570e4e4960cf65892450c5c92 and all 16 outputs were verified. ODB SHA256 d0ff86380bdb3b5c37e47df89667e2aa25aa9a83f87239353242a1b94af1f2c4 contains 106619 instances. All 103081 unaffected non-supply DEF net records and existing geometry were preserved; both added buffer supply pairs passed contact checks.

Four nets require routing: nssoc_sta_n_11344, nssoc_sta_n_19589 and the two nssoc_loadiso output nets. The selected-net global routing API is present in pinned OpenROAD dcf36133a369abc8f3c5e5738cd4d82e4903c0e0. Native detailed routing may still change unaffected nets; exact post-stage DEF record comparisons reject that outcome rather than assuming preservation. Native identity and visible geometry remain separate checks.

This branch comes from antenna repair round one, with 15 antecedent antenna violations. It is distinct from the clean six-resize candidate. Routing measurement is not antenna, timing or production acceptance. Fresh extraction and all-corner STA remain mandatory.
