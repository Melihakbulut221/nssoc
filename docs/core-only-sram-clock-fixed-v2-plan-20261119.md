# SRAM clock hold repair: actual FIXED encoding

The earlier clock run 44435678929 is cancelled because its incremental DEF importer skipped NETS. Run 44437146454 proved actual FIXED decoder types on 102965 data-candidate nets, including positive and negative native controls. That run also exposed terminal-list reordering; the latest implementation compares terminal multisets and exact route/property suffix tokens during status conversion, then retains the independent final identity, exact DEF, and physical geometry guards.

Apply that implementation to the previously admitted single buf8-to-buf16 SRAM clock candidate (run 44432691473). Only delaynet_17_clk_i and clknet_1_0_0_clk_i are permitted to reroute. All other cells and routes remain subject to guards. Native DRC, antenna checks and fresh RC all-corner timing are required before acceptance; no hold fix is assumed. 50 MHz and 5% derating remain unchanged. This isolated experiment is separate from the data-buffer candidate.
