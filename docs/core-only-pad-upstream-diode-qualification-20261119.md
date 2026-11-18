# Full schematic pad current qualification with official diode model — 2026-11-19

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44415400942, attempt 1, source `cf084687f9a84b9a4b2ccfacbaf6b1ee450e3915`, artifact `14477989668`, SHA256 `a681ba012822eeca4d552acdc506d1fe3eb80e781f88ebe78068c75f7d880e7d`. All 79 output hashes were independently verified after completion.

## Scope and native controls

Full transistor schematic of `sg13g2_IOPadInOut4mA`, 125 C, slow MOS/resistor/diode corner, 1.08 V core / 3.0 V I/O, ideal pad clamp at 1.5 V, data 0 or 1.08 V, enable released over 120 ps at 20 ns. Six cases: each data value with turnoff, permanently enabled and permanently disabled. Native KLU/Gear2/ITL4=100 readbacks pass, maximum timestep 1 ps, no forced initial conditions or relaxed tolerances.

The complete official diode library at IHP commit `013bb30bb7c8f9d3c85173378597ac992ef7a272`, SHA256 `e6211bd0318122fbeb707498ede893223c332098cbb21c441b28b9d8c365e83d`, replaces only the diagnostic model copy. Original pinned MOS/resistor models, pad SPICE and OSDI inputs stay hash-bound. The production PDK and Liberty are unchanged.

## Results

All six waveforms complete 50 ns with finite, strictly increasing sample times, and no warnings/errors/abort diagnostics. Turnoff cases have 50,014 rows; static cases 50,008.

| Data | Enabled current | Post-disable current | First crossing below 1% of enabled current after enable midpoint |
| --- | ---: | ---: | ---: |
| 0 | -2.13127375 mA | +0.267314467 nA | 1.5605 ns |
| 1 | +2.08507141 mA | +0.267314455 nA | 1.8705 ns |

The enabled controls retain their currents; disabled controls agree with the post-turnoff leakage. Previously failing low-drive turnoff now completes with the official model correction. No custom simulator patch was needed.

## Remaining gates

This closes the six-case schematic current-capture convergence blocker at this corner. It does not establish extracted pad behavior, a complete Liberty characterization, maximum-slew compliance, ESD/IR/EM, or production signoff. The one-percent current crossing is not a Liberty voltage transition measurement and must not be substituted for one. Next: compare native current turnoff and proper Liberty three-state arc semantics, characterize required loads/input slews and PVT with the supported model revision, and qualify the physical pad before promoting dependent timing results. Main core detailed-route run `44402072903` remains separate and pending at this report.
