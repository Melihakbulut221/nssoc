# Full native TX headroom diagnosis

Actual native topology mapping39747431826 places the85 retained HBT failures in82 mux selector devices,2 final-mux tail devices, and1 remaining parent/output HBT. None is among the372 physically identified data-base devices. Each of31 mux stages is12 data,4 selector,2 tail and1 diode-connected reference; all593 parent HBTs are bound. Seven identity/connectivity controls pass. Prior mapper schema/topology-assumption failures remain in releases39745840047 and39746830294.

The new diagnostic restores the original rejected full34ns waveform and all14182 columns. It uses the unchanged strict memory-mapped reader, reproduces all604 original HBT checks exactly, and records real terminal voltages/currents at worst VCE and across the active interval. Stage headroom windows are algebraic observations, not nonlinear bias sensitivity or acceptance.

The original interface gate is150mV signed margin and1.8–2.05V common mode. CMOS inputs violate the lower common-mode bound. The final/level4/level8 interface reports also fail signed-margin checks; their reported common-mode ranges are inside the bound. Do not mislabel their margin failures as excessive common mode.

No source waveform, native transistor, clock, threshold, row, column or load is changed. Use actual evidence to select physical repairs, then repeat complete extraction and electrical verification.
