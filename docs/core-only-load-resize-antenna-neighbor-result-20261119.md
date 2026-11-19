# Two-driver antenna neighbor route result — 2026-11-19

Run: https://github.com/Melihakbulut221/nssoc/actions/runs/44524545738
Source: c0ae24df469b3a3422b35c7ff9bcb99b38870b94
Artifact 14531207616; SHA256 3be91dc83fb3d6312ada57dbcb86dba41cf073099485b49591541ff693fd163b. All 52 output hashes verified.

The three-net repair completed with router DRC 0, antenna nets/pins 0/0, and native visible-geometry inter-net contacts 0. No disconnected signal geometry, unwired multi-terminal nets, or terminals without geometry. Native negative controls passed. 103085 unselected nonpower routes and all 2113 clock routes preserved; 102969 encoded fixed routes restored. Identity: 106664 instances, 103090 nets.

Routed ODB SHA256: 171fa1a8f80a9eff594c169519b2fc216ff12ffd7c2e4ef150964ee0af26a1bb.

Next extraction uses fresh Verilog/DEF from this ODB, retains provenance of all prior 1400 added diodes and two driver resizes, and includes eight new diodes (1408 total; 2816 checked diode power terminals). Timing constraints remain 20 ns / 50 MHz and 5% derating. Previous timing metrics are not results for this new candidate.

This is not foundry DRC, full transistor LVS, qualified RC min/max, full-chip signoff or manufacturing approval. Package/PCB and attached devices are not selected, as confirmed by the user; external I/O signoff remains open.
