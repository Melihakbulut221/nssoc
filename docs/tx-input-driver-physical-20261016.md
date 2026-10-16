# TX input-driver physical integration prerequisite — 16 October 2026

The full 32-stream schematic currently uses `tx_cmos_hv_resistive_input_v7.inc`; it is not a routed input-driver macro. Each instance contains the real IHP `sg13g2_buf_16`, four HV NMOS devices (`w=10u`, `l=.45u`, `ng=10`) and four native poly resistors. Its six external ports and separate supply/substrate connections must survive physical implementation.

The native `nmosHV` PCell generates all fingers but exports pin shapes for only the first source, drain and gate. Reusing the single-finger pump router would leave other fingers unconnected. The new `tx-driver-geometry-cloud` experiment therefore measures the actual active/poly intersections and all diffusion contacts for both ng=1 and ng=10. It checks total width, gate length and physical contact order, and preserves the generated GDS. It also retrieves the exact pinned PDK buf16 GDS/CDL/SPICE/LEF and retains original widths, finger counts and junction parameters. No finger substitution or schematic parameter rewrite is allowed.

The output records the contacts that the actual driver router must connect. This inventory is a prerequisite, not routed-driver, DRC, LVS, extracted electrical or PHY acceptance. Next: implement every finger connection and explicit bulk/well access, compare against the original circuit with native transistor LVS and fault controls, run DRC, then extract interconnect and repeat the unchanged electrical measurements. Four-lane CDR/clock, full serializer wiring and mainchip integration remain open.

All generation and inspection runs on GitHub-hosted runners. Native logs, failed assertions and source hashes are published as release evidence, with an artifact fallback. The local workspace remains empty.
