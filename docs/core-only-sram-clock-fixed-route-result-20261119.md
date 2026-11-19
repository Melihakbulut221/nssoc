# SRAM clock fixed-route result and actual-RC follow-up

Run 44438114279 at 2f0e5e8b1fa7352b93ae19796fd741a4ef1f52f6 completed successfully on attempt 1. Artifact 14490194336 SHA256 eaa8647f9269c317488cc1fb488ae12402d9ea637dcb5a040dea27779298903a and all 45 outputs were independently verified.

The final restored-status ODB is a2d85760fec57ea28ea10a192c27528326b9fb48aa5c4a682367c08fdacca9ba. Native DRC is zero. All 103081 unselected DEF net records (including 2111 clock nets) are unchanged. Native encoded FIXED/ROUTED controls pass for 102965 nets. Exact identity/connectivity/PG and visible geometry checks pass. These checks do not establish transistor LVS or foundry signoff.

One antenna net/pin remains. The next extraction is explicitly diagnostic, not production acceptance. It measures whether the isolated buf8-to-buf16 clock driver improves the 52 fast-corner and four typical-corner hold violations from clean baseline run 44430367099, and whether it worsens slow setup (baseline 59 paths, -0.74034647175 ns). Full all-corner results must be examined before combining with data-path changes. Any later antenna repair requires fresh extraction again. Clock remains 20 ns and derating 5 percent; nominal RC is not qualified RC min/max.
