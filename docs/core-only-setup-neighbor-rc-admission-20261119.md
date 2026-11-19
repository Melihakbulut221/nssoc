# Clean setup-neighbor route and fresh RC admission — 2026-11-19

Run 44455684595, head b32fce23eb5cb79a1e9d9dbafcd023d6f4663e7d, attempt 1 succeeded. Artifact 14498857997 SHA256 4fd98ad9602a568e83027c0ef30451bddfedaff0035ee304c54efaf3621b2001; all 45 outputs verified. Routed ODB f381bd8d9e79ca38918d4bbda5c4014959a0e6966ac9a130d4ea9274d6a5192e.

The prior Metal2 short between nssoc_sta_n_11352 and nssoc_sta_n_97099 is absent. Native DRC reached zero at iteration 3; antenna nets/pins zero. Independent wire/via/LEF-terminal geometry reports zero inter-net contacts, disconnected signal nets, unwired multi-terminal nets and missing terminal geometry; all negative controls pass. Exact identity holds for 106650 instances. All 2113 clock records and 103079 unselected non-power records remain unchanged. 102963 wired nets passed encoded FIXED and restored ROUTED checks. This is not full GDS transistor LVS or foundry signoff.

Next run authenticates this route and both the two-driver resize and earlier clock/data/antenna lineage. It exports fresh Verilog and DEF from this ODB, preserves original SDC (20 ns / 50 MHz, 5 percent derating), and performs nominal RC extraction plus slow/typical/fast STA. The instance/name audit expects 106650, identical to this physical source. Existing antenna inventory remains 1397 added diodes. Previous 19 setup / zero hold results belong to the earlier combined route and are not results for this candidate.

Electrical slew/fanout/capacitance issues, qualified RC corners, external I/O timing, full SRAM characterization, transistor LVS, foundry DRC, DFT/PDN/package and manufacturer approval remain separate requirements. PCIe and Ethernet remain outside the approved scope.
