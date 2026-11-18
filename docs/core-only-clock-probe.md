# Native CTS8 connectivity probe

This read-only native OpenROAD job restores the verified CTS8 producer44246559242 and its authenticated mapping/placement inputs, including reconstructing and hash-checking the exact config-cts8.json. It checks every473 archived output and nine fresh corner metrics before reading the final database. No CTS or mapping is rerun.

It reports the exact16 loads of clkbuf_0_clk_bus/X and the driver/load network of SRAM bank2 A_MEN, plus native database-editing command availability. This information is required to choose and guard a balanced clock split and electrical driver repair without inventing connectivity or changing STA acceptance. A full slow-corner read-only STA accompanies the connectivity probe. Probe completion is not ECO completion, routing, timing closure, or signoff.

Independent routed-repair run44252197610 continues on its original source. Do not cancel or replace it. Native boot44239816779 also remains live. PCIe/Ethernet remain excluded; all other product gates remain required.
