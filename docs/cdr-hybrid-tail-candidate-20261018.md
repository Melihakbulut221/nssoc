# Native hybrid-tail sampler candidate

The full left-output CDR failed both original loaded phases with14 HBT headroom violations. Its retimed input signal remains weak. This candidate addresses one circuit cause without claiming to solve the complete data path: replace the sampler reference HBT and two latch tail HBTs with native SG13 LV NMOS references/tails. Keep every switching/latching HBT and all12 native resistors unchanged. ReferenceW8um/L0.3um and two tailW32um/L0.3um are fixed at4:1; ng1 throughout. No parameter is chosen from observed pass/fail tuning. The original all-HBT circuit remains intact as baseline.

This is an initial schematic feasibility test, not a layout fix. Use original256 bits,8GHz clock1.29V common mode,10ohm data/clock source impedances,150fF/output,34.25ns/.3125ps and original data/margin/timing gates at nominal/hot-low/cold-high plus swapped-output/clock-stop negatives. Preserve original0.4–1.6V HBT VCE,1V VBE and3mA/emitter limits on every remaining HBT. Native MOS drain currents must maintain the original0.5mA minimum tail current; all MOS VDS/VGS/VGD/VDB/VSB magnitudes must remain below the existing1.32V LV screen. Runtime/models remain hash-pinned and zero-source OP/readbacks mandatory.

The exact source and controller deltas are independently guarded. Native PSP model instance/probe semantics follow the pinned [IHP SG13 LV model](https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.tech/ngspice/models/sg13g2_moslv_mod.lib) and [IHP native drain-current example](https://github.com/IHP-GmbH/IHP-Open-PDK/issues/360). The restored PSP binaries must match the existing model manifest.

No GDS/LVS/RC exists for this candidate yet. A schematic pass is only a prerequisite to actual primitive layout, native DRC/LVS and a fresh complete PD model under its original loaded tests. Full-loop/PVT/convergence/body/RF and serial PHY/mainchip acceptance remain open. Do not reuse all-HBT physical evidence as proof of this changed circuit.


## Verified native schematic result

Run39104163004/source0be3c44ebcb97d145774f80788401f4d998a1f1d passed three original positive cases and both actual fault detections. Nominal/hot_low/cold_high margins183.632/173.642/180.392mV, clock-to-valid20.469/23.281/18.594ps, each768 samples and zero data failures. All12HBT/3MOS gates pass. Full immutable reports/hashes: `docs/evidence/cdr-hybrid-tail-schematic-pass-20261018.json`. This does not qualify PVT, physical geometry, RC, recovered-clock CDR or full PHY. Real hybrid layout and its independent native physical proof are next; existing all-HBT sampler GDS is not this circuit.
