# Cut10j measured Ethernet driver repair

Experimental candidate; no acceptance claim. Source route is artifact 14068260482,
SHA256 cf6a83685c33cdf4083786f0ab136ef1ea2666b44476521228aed5eed73d0855,
built from ecef9ad7cc9cd38c40b37b2109c2c976c53d1e4b. Baseline routed STA run
43492086181 reports slow setup 1233 / -2.134266 ns and fast hold 94 / -0.184995 ns.

The slow Ethernet receive MBIST background path to SRAM bank4 A_DIN[14]
contains place28029 (buf2, 0.462680 pF, 1.043456 ns cell delay) followed by
fanout67050 (buf1, 0.780456 pF, 2.932087 ns cell delay, 4.842957 ns output slew).
Path slack is -1.607208 ns. Trial replaces precisely these two buffers with buf16;
source masters and complete pin/net connectivity are checked before/after.
This is a targeted physical hypothesis, not a claim to solve CLINT/PCIe timing.

Legalization invalidates wires: all signal/clock detailed wires and guides are
removed, power wires retained, then native GRT/DRT runs again. The same three
PVT corners, original 20/4/8/8 ns clocks and derate guards remain. Fresh nominal
RCX conservation and propagated standalone STA determine the result. Nominal
RC is not qualified RCmin/max. New layout needs physical and logic validation;
master-name/connectivity checks are not a substitute for full equivalence/LVS.
Native data stays in GitHub artifacts; only derived reports are collected locally
in memory. Current branch RTL fixes are not automatically covered by this old
source-bound physical experiment.
