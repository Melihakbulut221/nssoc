# Final differential clock bridge: native model extraction

The physical bridge candidate from run39373038910 has zero markers across all560 DRC categories, deep/flat native two-device LVS, and six rejected physical/reference faults. It is one rppd (W6um/L1.2um) plus one substrate tap (A4um²/P8um). GDS SHA256: e02f760468950f7e095a3db511081c166ffe931dde3281b1ed1ec6802182fca3.

The new cloud job exports real device terminal shapes from both LVS databases. Its three public ports are resolved by probing actual metal5 geometry; its private body is derived from native rppd_sub, and the tap WELL must connect to that same body. No public port may alias it. Deep and flat semantic devices must agree despite differing native IDs.

The intrinsic model preserves rppd dimensions, end correction, multiplicity, self heating and named terminal order. It uses the pinned PDK finite tap-contact equation and explicit sub/BULK terminals. Twenty binding corruptions across both extraction modes and ten actual model-text corruptions must be rejected.

This step is not an electrical pass. Next: extract actual wire terminal anchors and RC, compose the bridge with the original full32 TX clock sources and 25ohm source resistors unchanged, and run all original waveform/device gates. Intermacro routing, assembled layout, qualified PEX/substrate, PVT and full PHY acceptance remain open.

Live independent jobs at publication: mainchip39373842033; full-terminal PLL39370629792; TX group2/3/4 experiment39372036289. All execution and retained results are cloud-only.
