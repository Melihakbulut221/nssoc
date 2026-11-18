# Routed-core repair continuation

Global-route producer [44245993247](https://github.com/Melihakbulut221/nssoc/actions/runs/44245993247), source e37b67f0e8c82425a8951c2f978ed2ced10a830c completed successfully. Native artifact14402132298 SHA256 a2895b63e902f7b3e5fc1c220ec091ed1335ad166ccd6bed1d82ce70f412be11 was independently verified, including all105 inner outputs, three fresh metric files and actual CORE_ONLY_GLOBAL_ROUTES_VERIFIED markers in each STA process. This was routing execution, not timing acceptance.

| Corner | Setup count / worst ns | Hold count / worst ns | Slew | Cap | Fanout |
|---|---|---|---:|---:|---:|
| slow |1103 / -3.81095|0 / +0.483955|127|79|748|
| typical |0 / +4.68578|0 / +0.180187|2|81|748|
| fast |0 / +8.1723|2 / -0.0586839|2|83|748|

The slow worst path starts in NPU node0 LIF ev_axon_r[1] and crosses small fanout buffers and mux/XNOR logic. Global-route parasitics reopen placement timing and electrical violations. Neither 20 ns nor 5 percent derate is relaxed.

The new runner authenticates/restores mapping, placement, postCTS and global-route evidence. It uses native RepairDesignPostGRT then bounded ResizerTimingPostGRT, forcing post-repair global routing to remain enabled. Each phase ends with three separate guarded route-STA processes, never placement fallback or inherited metrics. It records fanout as well as setup/hold/slew/cap. Native artifacts persist on failure. Detailed routing/extraction and whole-chip signoff remain independent. The CTS8 topology candidate and native boot continue independently; this repair does not supersede them until measured.

The complementary interface-profile run44247358676 uses source97ffca0ad84ab2bf103f6647e0a11ea4008fb7d4 and must cover the union of14 tests, including six full-profile SpaceWire/CAN cases. Retained regression44246945276 passed inventory negative-control step but actual suites remained running at this checkpoint.
