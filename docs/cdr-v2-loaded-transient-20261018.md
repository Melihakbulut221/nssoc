# Loaded native CDR v2 screen

The physical v2 layout has a newly audited MIM-aware model: 394 native devices, 8956 resistors and 7079 capacitors. Composition run 39081620727 preserved every wire token, matched all eleven extracted MIM devices to the native model binding, emitted each intrinsic MIM once, and rejected all 15 composition corruptions. Model SHA256: 96ddeb52f12e3efc40046b228cb5b3d45cb4af3e7776e5f338eaa65421fc3f2d.

The cloud screen runs nominal early and late phases, plus stopped-clock and VI-bias-off faults. The original 256-bit stimulus, 0.3125 ps step, zero-source operating-point check, native KLU readback, 122 actual HBT OFF flags, sampler/comparator timing and 100 mV margins, signed phase/VI gates and all device current/voltage bounds remain unchanged. Sampler loads remain 150 fF at their actual data-pair collectors; XOR ports retain 50 fF. No resistance or capacitance is scaled.

Native IDs, reference planes and model are all from v2. The plane proof is restored and its layout-result hash must equal the layout used by the device binding. The negative plane control now substitutes the actual opposite output identity instead of a v1 hardcoded node name, and requires a real change before checking rejection.

This is an externally clocked phase-detector screen, not recovered-clock acquisition. All full captures and failed results are retained. PVT, timestep convergence, real PLL/CDR control-voltage integration, complete serial data paths, x4 behavior, routed mainchip and final signoff remain required.
