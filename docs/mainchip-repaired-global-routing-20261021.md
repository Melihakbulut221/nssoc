# Fresh global routing after native repair

Deep handoff 39678505610 passed with 153130 instances and fresh ODB 22a6238e7786b75a715ac69ef06c0dc3ec17e590260d62ba869732e0f1d35551. Its source-bound repair proof, stale-data-wire removal, actual corruption controls and fixed-clock proof remain mandatory.

The native repair's placement estimates improved setup WNS from -5.641 to -3.874 ns and TNS from -25188.7 to -18247.5 ns compared with the earlier 80-iteration candidate. The deep optimizer stopped at iteration 1200 under its own progress logic despite the 5000 upper budget. It still reported 8006 setup endpoints and -0.469 ns hold WNS; these estimates are not routed timing.

The new cloud flow inherits the exact native fresh-fanout routing script and checks its SHA-256 dcfb68741ea369b67c9dcd551c8d7b4aca4e7387ec999568cefa3a68c13f684e before use. It preserves its entire preparation and global routing prefix, then writes views. The native DRT body and postroute stages are deferred to a separate resumable process; no completed-detail-route result is claimed here. The original signal/clock layers, 200 congestion iterations and layer adjustment settings are retained. No allow-congestion option is added.

The controller revalidates the original hermetic PDK/runtime/configuration package, unchanged 20/4/8/8 ns clocks and 5 percent derating, exact handoff digests and native executable version. Global routing must complete successfully; a separate native ODB readback must match physical DEF exactly except GCELLGRID, including all 153130 cells and twenty SRAMs. Native fixed-clock proof and real corruption rejections are additional gates.

Next: source-bound resumable detailed routing, then new antenna/connectivity/RC and three-corner STA on the resulting wires. Global guides do not demonstrate setup/hold closure, full serial PHY or production readiness. Local project remains empty.
