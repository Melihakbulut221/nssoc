# Slew-spacing antenna route passed — 2026-11-19

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44478446308 succeeded at `a7588cc2006d42dd8a30a7ea86b1e671c643830b`, attempt 1. Artifact 14507999805 SHA256 `228f4466bb34319c99b4354c0189c5e4c350b8ff781a381686dc90c87e5a361d`; all 50 output hashes verified.

Routed ODB SHA256 `a185d1494ffb265a9d07a08a4175704602ade02cf974ee8f9efbb923d22d098e`, 106651 instances and 103087 nets. Native DRC 0 at iteration 4; antenna violating nets/pins 0/0. Independent native wire/via/LEF-pin geometry: no cross-net contacts, disconnected signal nets, unwired multi-terminal nets or missing terminals. Negative geometry controls passed.

103084 unselected non-power net records and all 2113 clocks remain exact. 102968 other routed nets were verified encoded FIXED and restored to ROUTED. Inherited NDR assignments and layer width/spacing definitions were checked unchanged by the preservation script. All original instances and terminals from the diode preparation remain exact.

This closes the measured antenna regression of the spacing experiment under the native checker. It does not prove transistor LVS, foundry GDS DRC, qualified RC corners or production signoff. The added diode and spacing changes still require fresh timing measurement.

Next: export DEF and Verilog from this exact ODB, preserve the 20 ns SDC and all prior provenance, require 1398 cumulative added diodes including ANTENNA_2566, then extract nominal RC and measure slow/typical/fast setup/hold and electrical violations. Keep nominal setup/hold baseline and production-admission flags unchanged until measurement supports promotion.
