# Actual v49 extracted loaded result: rejected

Run40032180357 preserved all five full34.25ns captures:110385rows,67columns each, original0.3125ps maximum step, no native diagnostics, both HBT OFF flags and zero-source operating point verified. The three ordinary cases failed the original component signal and common-mode gates; all transistor safety gates passed. Both injected faults were detected. These fault detections do not make the ordinary design acceptable.

| Case | Output CM (V) | Minimum sampled signed margin (mV) | Worst valid delay (ps) |
| --- | --- | --- | --- |
| Nominal |1.633534–1.643263|29.181|62.344|
| Hot-low |1.542803–1.551192|17.808|72.344|
| Cold-high |1.719323–1.730225|39.573|56.406|

Unchanged requirements: CM1.8–2.15V; margin100mV; delay<=37.5ps. Full evidence is in docs/evidence/cdr-active-levelshift-v49-extracted-results-20261024.json and referenced GitHub Release archives. The failed wire model is retained unchanged.

The new losses workflow reads the original full captures and derives actual power/return/signal terminal voltage drops, native R paths, all53 resistor currents/losses, all93 capacitor values and body voltage. It does not rerun SPICE, collapse resistance, regenerate data, remove load, or claim a fix. Use its measured losses to revise physical routes and regenerate native DRC/LVS/RC before another acceptance test. Qualified RF/substrate extraction, parent integration, full serial PHY and final chip timing remain open.
