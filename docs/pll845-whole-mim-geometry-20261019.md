# Full PLL845 geometry for MIM-aware distributed extraction
The original C8 half-step waveform still fails the unchanged800–900ns100ppm gate. The prior seven-geometry/26-device MIM study covered only clipped windows, so it cannot correct the complete PLL model.

This cloud job uses the actual LVS/DRC-passed C8/divider-v2 parent from39005910789 at33ba6065f92dd84df10569862bac6c3ba9e14aa8. Exact GDS SHA256:79b2f5869f620cb5d6ce57756bab18f6ef10743aee953fb9c140202a6b225cdc.
It exports every actual parent and child metal/via polygon, verifies each conductor against unsimplified native LVS, and compares the complete845-device census to the frozen native SPICE export. The original conductor ownership, coverage and split guards are retained.

All26actual MIM masks are associated with native device terminal shapes and exact dimensions. Both plate references bind to real native metal components; bottom references must be outside intrinsic masks. Five faults exercise missing/changed physical masks, swapped plate ownership, an off-geometry reference and missing device identity. Export/readback retains the entire metal/via drawing and both MIM-mask layers without clipping windows.

This stage prepares the full physical model. It does not claim complete intrinsic-terminal anchors, fresh distributed RC, RF/substrate qualification, PLL acquisition, full PHY or mainchip acceptance. Next bind every remaining native intrinsic terminal and extract/audit the complete MIM-aware parent before composing and running the original acquisition gates. No capacitance scaling, altered window or ideal-wire substitution is introduced.

CDR39320016317, TX39308903140 and mainchip39293720171 remain separate live jobs. All CAD, artifacts and evidence stay on GitHub; no local checkout or build outputs.
