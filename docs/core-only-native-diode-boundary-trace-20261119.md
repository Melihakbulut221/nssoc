# Native diode boundary trace — 2026-11-19

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44411509216 (attempt 1) at `680e2ce19b59994c5e8c43848ac16ca07c899d32` reproduced the stock failure and captured 457 diagnostic rows without changing device equations, model parameters, fixture or tolerances. Artifact `14478435270`, SHA256 `dbf49c15b50f47b35ddd5a8201e584a558e158b69b2d45c0bc265b0530e0f492`; all 31 output hashes verified independently.

The failed endpoint remains 21.3261685 ns. There are 15 forward-region and 442 reverse-region evaluations near the -3*n*k*T/q boundary, -0.10385606953280702 V. At the nearest forward evaluation, charge is approximately -3.19263e-17 C and capacitance 2.98938e-16 F. Reverse-side evaluations have approximately -2.971789e-16 C and 4.570308e-16 F. This discontinuity is observed evidence, not yet an attribution to a specific constitutive term. Integrated current and conductance include timestep-dependent companion terms and must not be interpreted as DC values. Minimum timestep is 1e-23 s; the solver still aborts. No production runtime or timing model was replaced.

The next experiment adds bounded logging of DC current/conductance and depletion/diffusion charge and capacitance before integration, retaining the same equations and original-failure comparison. Neither experiment constitutes pad timing closure.
