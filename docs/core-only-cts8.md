# Eight-sink clock-tree candidate

The authenticated postCTS electrical diagnosis records 748 fanout violations, all on pins named as clock buffers, with loads up to 17 against an unchanged limit of 8. The old prepared config did not explicitly set CTS clustering sizes.

This candidate restarts the authenticated detailed-placement state before CTS from placement producer 44239812957. It changes only CTS_SINK_CLUSTERING_ENABLE=true, CTS_SINK_CLUSTERING_SIZE=8, CTS_MACRO_CLUSTERING_SIZE=8. These are native LibreLane 3.0.5 topology parameters passed to OpenROAD clock_tree_synthesis; timing constraints and fanout limits are unchanged. Upstream source and artifact hashes must match before use. Explicit unexpected prior CTS settings are rejected rather than overwritten.

It builds a fresh tree, measures three corners, performs propagated-clock electrical and timing repair, and measures three corners after each phase. Clock checks retain one clk_i at 20 ns with 5 percent derate. Fresh fanout metrics are mandatory alongside setup/hold/slew/cap. Native artifact and summary are retained independently of success. Eight sinks per cluster is a candidate remedy, not proof that internal branches meet fanout or that timing remains closed.

Baseline global-route run 44245993247 continues independently. This candidate does not replace its evidence. Any candidate selected later needs its own routed/extracted timing, DRC/LVS, boot and padframe/production qualification.
