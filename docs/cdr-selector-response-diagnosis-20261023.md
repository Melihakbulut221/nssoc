# Actual CDR selector response diagnosis — 2026-10-23

The prior full-capture selector observation passed in run 39943530320 at
79cfd435e4f38a04d91f136db311587bd62881ce. The immutable compact observations
are pinned in the adjacent evidence receipt. This is a diagnostic pass:
the original data/phase rejection and all 120 HBT/4 sampler results remain.

C/D master track selectors show greater positive base-to-collector voltage
than A in the measured original captures. This alone does not establish
stored charge as the cause of settling failure. The rejected v42 slave-area
experiment remains rejected.

The next observation compares each actual track/hold selector pair's base
voltage, base-emitter voltage and collector-current differential crossings.
For each original edge it retains counts in the unchanged +/-0.45 UI window.
Only exactly one crossing of each signal yields a response triplet; missing
or ambiguous triplets remain explicitly unresolved. All eight physical
pairs per stage are retained. No signal is regenerated or realigned.

Synthetic cloud controls exercise known base-to-VBE and VBE-to-current
offsets in both latch directions, non-finite inputs, time/order/window errors,
and missing/ambiguous crossings. Original full-record checks still run.
These response differences identify candidate circuit mechanisms; they are
not causal proof, a new electrical gate, or PHY acceptance.

All execution and retained waveform evidence stay in GitHub. Mainchip route
39932664501, PLL recovery 39941648965 and TX 39939103488/39939107708 are
existing live native processes and must not be duplicated or cold-started.


## Observed result

Run 39945517007 passed both phases and controls. Every one of the 32
physical pairs per phase yielded 255 unique triplets, with no unresolved
windows. The receipt records exact assets and all per-stage summaries.

Pair median base-to-collector-current delays are approximately 0.476–0.685 ps.
The actual C master base crossings occur approximately 14.03–14.09 ps after
the original expected edge; collector-current crossings occur approximately
14.53–14.72 ps after it. Direct pair matching therefore does not support
attributing the earlier approximately 10 ps difference between two separate
clock/steering observations to selector intrinsic response. Those earlier
observations used different measurement points or reference associations.

Next inspect the exact graph from original clock sources through the
physical local clock nodes to selector base terminals. Match directions and
original edge indices before distinguishing interconnect/loading from
reference-definition differences. Only then select an internal clock-path
or physical correction; do not shift external clocks or acceptance windows.
The original data/phase failure remains open.
