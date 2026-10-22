# v31 fresh MIM-aware parasitic validation

The v31 parent contains the physically verified follower pull-down change (four actual rppd resistors, length 4.5 to 2.25 um). Extraction run 39720055542 passed all four stages. Capture run 39720419606 measured 17,918 resistors, 12,850 wire capacitors, seven native MIM devices, 938 terminal points and 111 physical components. Those are fresh measurements, not reused v30 parasitics.

The cloud validation binds every upstream immutable summary and manifest by SHA256. It retains the v30 raw wire conservation audit, its 13 wire fault controls, nine intrinsic MIM controls and 19 composition controls. The seven independently matched intrinsic MIM cards must appear exactly once; every exported R/C token survives composition. The new source checker chains both the old validator and v31 capture validator, and verifies the exact namespace/provenance-only source delta.

Passing this workflow establishes model assembly only. Loaded waveforms, closed-loop CDR, full serial PHY and final mainchip timing remain open. Original stimulus, clocks, loads, device-safety limits and electrical acceptance thresholds are unchanged. All execution and evidence storage are on GitHub; no local project artifacts are required.
