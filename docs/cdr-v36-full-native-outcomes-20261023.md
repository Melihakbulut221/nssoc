# Complete v36 native outcomes

All four native runs in39850649751 completed the full34.25ns with113475 rows/1104 columns, exit0, no numerical diagnostics and unchanged protected inputs. Every original device gate passed. All four whole candidates were rejected: original data and phase/V-I gates remain false. The B sampler individually passed all four; A/C/D did not.

| Variant | Case | A minimum / worst valid delay | B minimum / worst valid delay | C wrong-sign samples | D wrong-sign samples |
| --- | --- | --- | --- | --- | --- |
| slave_drive15_load12 | early |92.34mV /38.28ps|110.96mV /37.03ps|3|30|
| slave_drive15_load12 | late |89.48mV /38.59ps|131.21mV /35.16ps|0|17|
| slave_drive15_load10 | early |101.42mV /37.66ps|120.63mV /36.09ps|9|4|
| slave_drive15_load10 | late |98.27mV /37.97ps|141.07mV /34.22ps|0|1|

The original A/B/C/D requirement remains100mV and37.5ps, on every original sample and clock-to-valid predicate. The load10 early A case misses the conservative delay predicate by about0.156ps; its positive aperture samples do not override that failure. This is not a qualified timestep convergence result.

The v37 C/D input-bias width experiment remains valid as a separate full-circuit test on the load12 parent, but that parent is now known rejected. Do not promote it as a validated baseline. Its two input-impedance choices keep the nominal resistor geometry ratio; actual common mode/headroom/gain and all A/B/C/D/phase/device results must be measured.

The load10 native data-hold HBT maximum current per emitter reaches about1.780mA at Nx6. Smaller data/hold emitter area is a potential next way to reduce master/slave input capacitance; rescaling the old current is only a planning estimate, never proof of current density or headroom in a modified circuit. Any such candidate must undergo new complete native gates and ultimately actual GDS/DRC/LVS/fresh RC/PVT/full-loop verification.
