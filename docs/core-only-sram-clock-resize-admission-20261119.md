# SRAM clock driver physical preparation verified

Run 44432691473/head e5536575eb03f3c6ab4bc61b045d243a265fb55e; artifact 14487078971 SHA256 174162f2f8c55679aece9a67de73803fb32b45bd57c0e501b7d166eac6960ac0. All 17 outputs verified. Candidate ODB SHA256 a9e48d0c9f53e2ec3ac03fa35913b209bc0008717cf7b754b42c5b613734aab4.

Exactly one driver, clkbuf_1_0_0_clk_i, changed from buf_8 to buf_16 and moved 13.38 um during legalization. All other instances, terminal connections, antenna cells and special wiring were preserved. Both resized supply terminals passed positive-area native rail contacts. All 103083 unaffected DEF net records matched exactly. Only delaynet_17_clk_i and clknet_1_0_0_clk_i were cleared for rerouting.

The next experiment routes those two nets and rejects any changes in all other non-supply routed nets. It measures antenna and router DRC, then requires fresh extracted-RC timing in all three corners. Preparation is not a timing result. No constraint or library limit was relaxed.
