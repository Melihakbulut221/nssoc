# Eight-sink clock-tree candidate

The authenticated postCTS electrical diagnosis records 748 fanout violations, all on pins named as clock buffers, with loads up to 17 against an unchanged limit of 8. The old prepared config did not explicitly set CTS clustering sizes.

This candidate restarts the authenticated detailed-placement state before CTS from placement producer 44239812957. It changes only CTS_SINK_CLUSTERING_ENABLE=true, CTS_SINK_CLUSTERING_SIZE=8, CTS_MACRO_CLUSTERING_SIZE=8. These are native LibreLane 3.0.5 topology parameters passed to OpenROAD clock_tree_synthesis; timing constraints and fanout limits are unchanged. Upstream source and artifact hashes must match before use. Explicit unexpected prior CTS settings are rejected rather than overwritten.

It builds a fresh tree, measures three corners, performs propagated-clock electrical and timing repair, and measures three corners after each phase. Clock checks retain one clk_i at 20 ns with 5 percent derate. Fresh fanout metrics are mandatory alongside setup/hold/slew/cap. Native artifact and summary are retained independently of success. Eight sinks per cluster is a candidate remedy, not proof that internal branches meet fanout or that timing remains closed.

Baseline global-route run 44245993247 continues independently. This candidate does not replace its evidence. Any candidate selected later needs its own routed/extracted timing, DRC/LVS, boot and padframe/production qualification.

## Verified trial result

Run44246559242/source67e18d0c5ffec9db966d8733b5e5971d2422047c completed. Native14402843316 SHA256 3378e8d44bf485cf28dde3e91389629d5de877e5aae7f59c6cf12daac3233bdc was independently checked, all473 inner output hashes and nine fresh corner metric files. Final setup/hold counts are zero in all three placement-estimated corners. Slow setup worst+1.31206ns; fast hold worst+0.0371873ns. Cap violations zero. Fanout reduced748 to1, but not closed: clkbuf_0_clk_bus/X drives16 against limit8. The remaining SRAM b2/A_MEN slew is0.769460ns versus0.595200ns slow and0.477503 versus0.476000 typical; fast slew count0. Full evidence: evidence/core-only-cts8-20261118.json.

Next engineering candidate: split the specific16-load bus-clock branch into balanced buffered groups with fanout<=8, preserving all endpoints, clocks and budgets, then re-legalize and remeasure all corners. Inspect the remaining A_MEN driver before deciding its targeted electrical ECO. Do not assume another leaf-cluster-size sweep repairs the internal clock root. No such targeted ECO has been executed yet. CTS8 routing remains pending; baseline postGRT repair44247595292 continues independently.
