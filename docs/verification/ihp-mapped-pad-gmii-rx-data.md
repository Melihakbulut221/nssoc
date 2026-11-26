# GMII receive data at the mapped SoC input

The [directed test](../../hw/soc/tb/tb_chip_mapped_gmii_rx_data.v) drives only the eight external GMII receive-data pads and samples the eight-bit input on the actual mapped soc_top. Four-state comparison rejects unknowns. The test applies all-zero and all-one backgrounds and walks one and zero across each lane, for 18 samples.

Replay the [mapped-core compilation command](ihp-mapped-pad-clock-replay.md) with top `-s tb_data` and test source `hw/soc/tb/tb_chip_mapped_gmii_rx_data.v`. Keep the same mapped core, status serializer, native pad and cell models, and four SRAM source files. Baseline simulation exited 0 and printed `PASS GMII RX eight input lanes`.

For the negative control, copy the wrapper and interchange the two unique `.p2c(eth_rxd_i[0])` and `.p2c(eth_rxd_i[1])` connections. Leave the external stimulus, core, model set and acceptance assertion unchanged. Both variants compiled successfully. The crossed variant exited 1 with `GMII RX input mismatch expected=01 observed=02`. The baseline run checks digital input direction and lane ordering up to the core port. Frame reception, PHY, pad electrical behavior and package connections require separate evidence.

The first-detail native LVS process ultimately logged SIGTERM at line 382 of the pinned deck and left a 38,132,510-byte extracted circuit without a comparison database. The native report gate rejected the missing database. The recorded timing pair has no final extracted comparison at this checkpoint. Sequential recovery started from the candidate's pre-STA state after confirming both former STA processes were gone.
