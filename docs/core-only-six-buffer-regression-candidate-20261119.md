# Six-buffer regression repair candidate — 2026-11-19

Native inventory run 44531468179 / edadf0934c4554b708daa473e3a175b15d509ed2 succeeded. Artifact 14534930939 SHA256 1e14bf8a4f2cb3be0150dee5c14d52969aa261332f1937d66e5e222b23e19f43 verified. Source routed ODB 171fa1a8f80a9eff594c169519b2fc216ff12ffd7c2e4ef150964ee0af26a1bb, 106664 instances.

Candidate adds six buf_8 identity buffers: one each for drivers 8624, 8545, 56298 and 65080; two parallel branches for driver 61007. The latter branches each drive four existing antenna diodes and one functional sink (five loads), while the original driver drives two buffer inputs.

All original instances/geometry remain fixed. Existing ANTENNA_491, ANTENNA_500 and ANTENNA_2569..2576 are retained, with signal terminals reassigned to the appropriate buffer output. This deliberately changes ten diode signal nets: it is not an unchanged-antenna-connectivity claim. The audit must prove recovery of every original connection after collapsing identity buffers, exact assigned-sink completeness, explicit diode move inventory, all other DEF routes and 2113 clock routes unchanged, and local power contacts for six new cells.

Expected candidate: 106670 instances, six new nets, five original nets needing rerouting. No timing improvement or antenna protection is assumed until fresh routing, antenna checks, physical connectivity and RC/STA succeed. Future cumulative antenna inventory must apply the explicit diode move map before checking exported netlist connections.
