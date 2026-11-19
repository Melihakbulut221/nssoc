# Two-buffer critical load isolation candidate

Native inventory run 44424914697, head d3530f50f723406ffa59eef5833a50f76289b3b0, artifact 14482879232, SHA256 3ee10154099aba8197c9c3ae45ed3a9a509055b97f14df54018cc7cb5cf418e8 verifies no antenna diodes on either common critical net.

For nssoc_sta_i_2657/Y (nand3_1), keep nearby critical nssoc_sta_i_11771/C directly connected; isolate distant nssoc_sta_i_11769/C and nssoc_sta_i_2658/B behind a buf_4 placed near the source. For nssoc_sta_i_11771/Y (nor3_2), drive its eight remote logic inputs through a buf_8 near the source. Exact sink lists are asserted against native ODB. This reduces load presented to slow compound gates without changing Boolean logic.

Source is the authenticated first repaired route with 106617 instances and 15 antenna-violating nets, deliberately separate from the ongoing second antenna repair. Keep every original cell position, type, orientation, net type and power geometry fixed. Prove original terminal connectivity after collapsing the two verified identity buffers; check legalization, bounded displacement and positive-area physical supply contacts. This is a candidate, not timing closure. Subsequent routing, antenna repair, actual RC and hold/setup checks remain mandatory; do not merge it into the clean-route branch without validating its exact lineage.
