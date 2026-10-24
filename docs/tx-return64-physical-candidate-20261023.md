# TX long-span return64 physical candidate, 2026-10-23

The complete return32 normal capture failed 85 HBT checks and 14 output samples. Its passive output-tail return remains 12.383116442 ohm; edge R139947 contributes 96.361849% of the unit-current energy. This is a physical routing target, not a reason to loosen the electrical gates.

The new generator adds 64 um metal only to output AVSS spans longer than 80 um, stopping the widened centreline sections 40 um before endpoints. It preserves the selected route's 6/32 um shapes, all original core/leaf primitives, supplies, native vias and external ports. The right vertical addition shifts left 18 um so its SUB-facing edge is unchanged from the prior 32 um metal shifted left 2 um. All collision checks remain enabled; a blocked candidate must fail.

The full-width return-open control is widened to sever the complete new64um section. The same 560 DRC categories, deep/flat unsimplified 8088-device LVS, exact165 external ports and all actual geometry/reference fault controls remain required. These are fresh physical checks, not reused return32 results.

No candidate has been electrically accepted. A physical pass requires fresh conductor extraction/composition and complete loaded native waveforms. This repair targets the output return only; it does not close the82 selector/2 final-stage-tail failures, CDR/PLL, serial Gen3x4 or mainchip integration.
