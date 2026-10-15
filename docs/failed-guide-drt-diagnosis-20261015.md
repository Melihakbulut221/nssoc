# Full-chip failed-guide physical diagnosis, 2026-10-15

The best retained global-route candidate, run38448901835, ended with132native overflow (Metal3:5, Metal4:20, Metal5:97, TopMetal1:6, TopMetal2:4). It remains rejected. Later clock-layer restrictions exhausted six hours and emitted native NDR downgrade warnings; they are not replayed here.

Run38788529905 tests whether detailed routing of the exact saved guide file can produce useful physical evidence. Native OpenDB preflight compares all113791cell identities/master/location/orientation/status, net pin connectivity, boundary pin geometry, die/units and each assigned NDR name/width/spacing/hard-spacing flag to the original pre-route database. Controls deliberately remove an NDR, disconnect a terminal and move a cell; each must be detected and then exactly restored. Saved guide entries must match native loaded guide counts for every named net. All original files are SHA256-bound.

Detailed routing uses the frozen LibreLane3.0.5/OpenROADdcf36133 runtime, original database technology and two threads. No new clock restrictions, capacity inflation, removed obstructions, endpoint omission or NDR weakening is introduced. Default native search/repair runs; DRC and guide coverage are retained along with completed ODB/DEF. Native logical/placement/NDR invariants are checked again afterward.

The upstream [detailed-router documentation](https://openroad.readthedocs.io/en/latest/main/src/drt/README.html) describes its pin-access, track-assignment and DRC stages. Actual supported options were verified against the [frozen Tcl implementation](https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/drt/src/TritonRoute.tcl), including default iteration handling and native DRV reporting. OpenDB rule fields were checked against the same revision's header, SHA256142810acc2b0495b10c988b59e4d450e54dc27b2569687391588bfe1fad78bda.

This experiment is diagnostic. The original global-route gate is still FAILED even if detailed routing returns successfully. Stored NDR declarations do not prove actual wire geometry, and wire objects do not prove connectivity. No adoption or full PHY claim is made. Independent connected-route checks, geometric width/spacing, full-chip DRC/LVS/antenna, qualified parasitic extraction and original all-corner setup/hold remain required. The serial analog PHY is also still incomplete.

All source edits, CAD, tests, archives and checkpoints stay on GitHub. The local workspace remains empty.
