# TX row-lattice candidate after native private-net diagnosis

The cloud-only private-net review39263440258 binds all589 actual HBTs and
all378 intended nets. Actual extraction has376 clusters: p16_8p is shorted
to p8_0_qn, and p16_8n to p8_0_qp. No private opens were found.
The exact original native report and the missing-HBT/wrong-Nx/unbound-base
rejection controls are retained in the full evidence receipt.
This diagnostic is not a physical acceptance result.

Continuous-Y minimax movement placed horizontal parent conductors through
native cell conductors. The first p8_7 local correction fixed public shorts,
but left the private p8_0 shorts. The replacement uses integer row indices
with each macro's original residue modulo600um. Both minimax objectives
are solved over that lattice, with proven optimum required; timeouts fail.
All16 leaf rows and the final row remain fixed, along with every X position,
native child drawing/device card, clock and electrical acceptance threshold.
The native geometry checker also verifies each actual translation is an
integer multiple of600um. All60 routes are regenerated and length regressions
remain in the report. Row alignment is a candidate repair, not proof of LVS.

Required next: original560-rule DRC, deep/flat1674-device LVS and all physical
faults. Only after physical pass may fresh RC and the full original native
waveform gates run. Old RC is invalid for this changed geometry.
Full serial PHY and mainchip final timing remain open. All execution and
artifacts stay on GitHub; no local CAD or checkout.

## Exact-model solver failure and correction

The initial lattice run39264686080 stopped before CAD. Diagnostic39265239206
reproduced the exact31macro model with both HiGHS presolve settings.
First objective2326um was proven in both modes. The secondary objective
with the same2326.001um upper bound was declared infeasible with presolve,
but without presolve produced an optimum84266.4um total with zero MIP gap,
linear residual below5e-13, zero bound violations and integral row indices.
This is direct evidence of a solver presolve failure for this model.

The planner now disables presolve, with all original model coefficients,
row constraints and objective bounds unchanged. Every returned solution
is independently checked for all linear/bound/integrality constraints and
zero MIP gap. The actual31macro plan runs before downloading CAD runtime.
Final allocated route lengths can differ from the fixed-track optimization
objective; the plan reports both, and native physical/electrical gates remain
mandatory. No physical verification has passed from this diagnostic alone.
