# CDR input and retime resistor width sensitivity — 2026-10-19

This is a cloud-only circuit-sizing diagnosis, **not a new physical candidate or
a CDR/PHY pass**. The existing physically verified input-drive v10 layout remains
unchanged. Its full-wave nominal early/late cases failed the original data gates.

The fixed-phase review found the A/B output correct at 0.6/0.9 UI, but failing
the required 0.3 UI point. C/D retiming remains late at several phases. Compare
intrinsic widths 8 and 16 um against the prior 4 um for exactly 24 native rppd
instances: 16 sampler input-divider resistors and 8 retime-divider resistors.
Lengths, device terminals, all other primitive parameters, all 15482 explicit
wire resistors and 11527 capacitors remain fixed. The goal is to choose whether
lower divider impedance warrants a real new layout; extra loading may worsen
the result and will be reported.

**Limitation:** changing intrinsic resistor width invalidates correspondence to
the original geometry. Frozen wire RC is intentional for this diagnostic and is
not a valid extraction of the proposed changed layout. Even a nominal gate pass
requires new PCells, layout, DRC, LVS, full RC extraction, full waves and corners.
The experiment must not be used as signoff, a recovered-clock loop, or a routed
mainchip PHY.

Both early/late 256-bit PRBS tests retain the original 34.25 ns run, maximum time
step, all fixed sample phases, source impedance, loads, output thresholds,
phase/VI gates and all 116 HBT/46 MOS voltage/current gates. No clock shift or
source-bit replacement is allowed. Full results and failures publish to GitHub
release assets. The baseline source-delta chain and six parameter/input fault
controls run in cloud before the transient.

The two TX physical candidates and mainchip route continue independently:
- Strap6 wave: run39221063981.
- Trunk256 wave: run39226121734.
- Mainchip native resize route: run39202263552.

All CAD execution, simulation captures and result archives stay in GitHub cloud.
The local NSSOC workspace remains empty.
