# Actual 1 us PLL timestep refinement result

Run 39078674197 completed the exact native process resumed from run 39043210978's second checkpoint. The original raw prefix is unchanged. The full zero-to-1-us capture contains 6401211 complete rows, no trailing bytes, and a verified maximum integration step of approximately 0.15625 ps. Native startup readback confirmed all 102 HBT OFF flags and zero-source operating point; KLU options and diagnostics checks passed. No cold restart was substituted.

The original acceptance gate still fails. In the fixed 800–900 ns window, feedback frequency is 100013538.00262025 Hz (135.380026 ppm error), above the unchanged 100 ppm limit. In 900–1000 ns it is 100008984.9543807 Hz (89.849544 ppm). Phase ranges are 12.182553 ps and 8.085732 ps, respectively; both are below 50 ps and both windows have no cycle slip. Later overlapping windows that pass do not replace the fixed final two-window requirement.

The preceding coarser-step failure is preserved separately. Refinement does not close acquisition; no identical rerun is launched. The 34 selected voltage probes do not establish full-device safety, so that remains unaccepted. This capture also does not qualify PVT, substrate/RF extraction, CDR control-interface integration, x4 operation or mainchip timing.

The existing seven-geometry/26-device PLL MIM mask study passed only local 1-um-enclosure windows. It must be extended to actual complete clock macro/parent RC, with native identities, reference planes and raw-capacitance conservation, before adopting a corrected clock RC model. No capacitance is to be scaled or subtracted heuristically. The new CDR v2 model is already undergoing loaded transistor simulation independently.
