# Native OP control initialization repair — 2026-10-20

Run39458613068 connected all64raw drivers, then its native10032-node OP control completed but emitted: "Warning: can't find the initialization file spinit." The strict native-warning gate rejected it before any DUT simulation. The original capture is retained in the cloud archive SHA2560021decaca0e14b7294bf23c463e90ae5c645d7dc3495fbab95811228cad4af5 (66688511bytes).

The control now provides its own spinit containing set num_threads=1 and explicitly points SPICE_SCRIPTS to that directory, matching the existing native testbench initialization pattern. No warning text is ignored and the all-value, original aggregate comparison and five corruption controls are unchanged. This is a runtime repair, not an electrical pass. Full PHY/mainchip/timing remain open.
