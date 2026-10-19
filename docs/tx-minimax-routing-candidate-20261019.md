# All-leg minimax TX physical candidate — 2026-10-19

The measured p8_0/p8_7 data legs have522–546fF incident wire capacitance and approximately34ohm metal pair resistance, while p8_1/p8_6 have230–257fF and20–21.5ohm. The trunk256 full native waveform still has140wrong/164low output samples and24HBT violations. The next candidate addresses the signal routes.

The new planner reads every actual macro/port coordinate and all60 actual routed legs from the pinned strap6 physical report. It minimizes the maximum Manhattan centerline length across all legs, then minimizes total length with the first objective held. Macro rows snap to the original5nm grid. All16 leaf rows and the final row are fixed. Same-column macro order and at least600um origin separation remain required; actual leaf height is592.04um, so blindly compressing row pitch would overlap bodies. No native cell, transistor, resistor, timing, clock or reference-bit changes are allowed.

All31 macro X coordinates remain fixed. Actual output/input pin offsets, not macro centers, are used in the objective. Changed tracks are allocated by interval coloring with12um reuse separation and explicit exclusions around unchanged AVDD/SUB/AVSS rails. Every new route, including any longer upstream leg, is recorded. A shorter geometric path is not electrical acceptance.

The physical generator still performs the original560-rule DRC, unsimplified deep/flat1674-device LVS and original five injected geometry/reference faults. An independent native checker compares all three frozen child drawings, all31 physical placements and port translations, all60 actual parent TM1/TM2 routes, normalized full device references and three corruption controls. A source-delta guard binds the method to the prior generator and pins the two new helpers.

All native generation/controls execute in GitHub. Failed outcomes and complete CAD logs are published. Any physical pass must be followed by new intrinsic binding/RC extraction, original full256bit/34ns transient/fault checks, and PVT; no prior extracted RC can be reused for changed GDS. The full serial Gen3x4 PHY and mainchip timing remain OPEN.
