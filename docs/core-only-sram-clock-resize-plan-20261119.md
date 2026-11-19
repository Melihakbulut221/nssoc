# SRAM clock driver resize experiment

Native inventory run 44432082008/head 393ad5dabb3e8cacb8bb053e47b641bda684d730, artifact 14487237606 SHA256 22309e7a60ff32c87f0cda2afad5b178e7803332f5be7fb88b6eff1e1dbbbd14 and all three outputs were verified.

All four SRAM A_CLK terminals are driven by clkbuf_1_0_0_clk_i, sg13g2_buf_8, via clknet_1_0_0_clk_i. The net also has clkload0 and three antenna diodes. Its immediate upstream driver delaybuf_17_clk_i is already buf_16. The actual-RC fast hold path has SRAM clock slew 0.941342 ns and worst hold slack -0.429732 ns. This motivates testing a stronger leaf driver, not relaxing constraints.

Change only clkbuf_1_0_0_clk_i from buf_8 (6.24 um width) to buf_16 (12 um), both 3.78 um high. Freeze all other cell locations; maximum legalizer displacement 100 um. Prove identical logic function, pin set and terminal connections. Invalidate only delaynet_17_clk_i and clknet_1_0_0_clk_i. Compare every other DEF net record exactly and verify both resized power terminals geometrically.

Preparation is not timing closure. Earlier capture clock and larger upstream pin capacitance can change both SRAM-input setup and SRAM-output hold; all corners and path directions require fresh routed-RC measurements, as do antenna, DRC and connectivity checks. The candidate starts from the antenna-clean six-resize core and is separate from the running two-buffer data experiment. Period 20 ns and derating 5% are unchanged.
