# TX input-driver physical integration prerequisite — 16 October 2026

The full 32-stream schematic currently uses `tx_cmos_hv_resistive_input_v7.inc`; it is not a routed input-driver macro. Each instance contains the real IHP `sg13g2_buf_16`, four HV NMOS devices (`w=10u`, `l=.45u`, `ng=10`) and four native poly resistors. Its six external ports and separate supply/substrate connections must survive physical implementation.

The native `nmosHV` PCell generates all fingers but exports pin shapes for only the first source, drain and gate. Reusing the single-finger pump router would leave other fingers unconnected. The new `tx-driver-geometry-cloud` experiment therefore measures the actual active/poly intersections and all diffusion contacts for both ng=1 and ng=10. It checks total width, gate length and physical contact order, and preserves the generated GDS. It also retrieves the exact pinned PDK buf16 GDS/CDL/SPICE/LEF and retains original widths, finger counts and junction parameters. No finger substitution or schematic parameter rewrite is allowed.

The output records the contacts that the actual driver router must connect. This inventory is a prerequisite, not routed-driver, DRC, LVS, extracted electrical or PHY acceptance. Next: implement every finger connection and explicit bulk/well access, compare against the original circuit with native transistor LVS and fault controls, run DRC, then extract interconnect and repeat the unchanged electrical measurements. Four-lane CDR/clock, full serializer wiring and mainchip integration remain open.

All generation and inspection runs on GitHub-hosted runners. Native logs, failed assertions and source hashes are published as release evidence, with an artifact fallback. The local workspace remains empty.


## Native inventory result

Run 38863174519 passed the geometry inventory. Each actual ng=10 PCell contains ten 1um-wide, 0.45um-long active/poly intersections and eleven diffusion contact columns. Six source columns, five drain columns and all ten gates must be connected for each of the four HV devices. Native pin geometry labels only the first source, drain and gate, confirming that the single-finger pump router cannot be reused unchanged.

The original buf16 GDS and four transistor SPICE/CDL rows were retained, including widths 4.44/6.72/11.84/17.92um and ng=6/6/16/16. No device was substituted. Release `cloud-results-38863174519-1-tx-driver-geometry` preserves the specimen GDS and source inventory; summary SHA256 `9b83b5376a1c2768e2fc2c1aeefbcde12378757cbcd46c11ec198e20fa46cee2`. Failed run 38862708273 remains preserved: its label-report code called an unavailable KLayout API. The corrected code records both original transforms separately without changing geometry checks.

**Next physical work remains required:** route all fingers, preserve the original buf16 cell, add explicit body/well access and all four resistors, then demonstrate native DRC/LVS with missing-finger/open/short/width faults before extracting and simulating the complete driver. Neither this inventory nor the existing schematic tree proves those tasks complete.
