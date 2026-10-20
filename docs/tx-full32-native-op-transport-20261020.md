# Full32 raw-driver native OP command limit — 2026-10-20

Preparation39457421944 stopped before DUT simulation because the original save helper forbids a single wrdata command above10000arguments. All64physical drivers create more than10000observed native terminals. The failed run is retained. No probe may be dropped to make this pass.

The new transport keeps128-vector save commands and the unchanged full binary transient capture. Only the DC operating-point write is split into ordered chunks of at most512vectors. Every native chunk and exact printed decimal is preserved. Reconstruction checks all headers, column order, finite values, unique names, identical scale and exactly one data row. It copies the printed numbers into the original op.dat shape for the unchanged zero-source OP and device review; it does not recompute values or relax electrical limits.

Before preparing or running the DUT, the exact pinned simulator executes a10032-node DC control with distinct analytically known voltages. All10032values are checked; the first256 must match an original legal aggregate wrdata command exactly as printed decimals. Five corruptions—missing chunk, swapped header, truncated data, extra row and nonfinite value—must all fail. This is transport evidence, not a PHY simulation.

The ngspice manual documents wr_singlescale and wr_vecnames, which make chunk scale and vector identity explicit: https://ngspice.sourceforge.io/docs/ngspice-manual.pdf . The actual pinned native control remains the authority for this runtime.

Full DUT waveform, native MOS/HBT bounds and physical interface gates remain pending. FullPHY, closed-loop clocks and composite layout are still unaccepted. Cloud-only.
