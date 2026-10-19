# Sampler MOS source midpoint access candidate

The actual CDR supply-to-layout review39295620005 mapped91selectedAVDD/AVSSwire resistors without unresolved points. R15966 is a33.6787ohm extracted source-access edge ending at T001_S inside sampler sb. The native source point is Metal1 near the middle of a36um MOS source strip; the original escape contacts the strip near its bottom. Equivalent long source accesses recur in the four samplers. These values are extracted wire edges, not effective circuit resistance or inferred source currents.

The candidate retains the exact passed parent AVDD-bypass GDS, all484devices, all child placements and the byte-identical reference and LEF. For each of the36sampler MOS sources, a native1column/16rowMetal1-to-Metal3 via array is added at the actual source-strip midpoint. A1.2umMetal3bridge joins the existing source escape column through a native8columnMetal3-to-Metal4array. The source midpoint and existing column are each probed on the original wire L2N to verify AVSSownership before drawing.

No gate/diffusion or device parameters are changed. All original geometry must survive; only nativeMetal1–Metal4andVia1–Via3additions are allowed. Serialized GDS is rechecked against the original plus the declared overlay, with actual bridge-cut, via-removal and unrelated-gate-geometry controls.

The unchanged native560categoryDRC and deep/flat484deviceLVS suite, including original physical/reference negative controls, determines whether the candidate is physically valid. Passing physical checks still requires fresh native RC, MIM-aware composition and the original full loaded data/phase/device gates before electrical adoption. No CDR/PLL lock, full serialPHY, mainchip routing or timing closure is implied.

All execution and retained evidence are cloud-only.
