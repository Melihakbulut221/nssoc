# Native clock evidence and local-bus CDR full waves — 2026-10-19

All computation and immutable captures remain in GitHub; the local project directory stays empty. Full serial Gen3 x4, recovered-clock operation, routed mainchip and final setup/hold remain OPEN.

## CDR original full-wave gates

[Run39252773409](https://github.com/Melihakbulut221/nssoc/actions/runs/39252773409) completed all four native cases. Original256bits/34.25ns/150fF sampler load/50fF XOR load/.3125ps maximum step and device limits remain unchanged. All four native executions returned0 with no reported diagnostics and unchanged sources. Both nominal cases are electrically REJECTED. The two injected faults were detected; their workflow success is not nominal acceptance.

| Case | Wrong sampler samples | Below100mV | Phase average(V) | Phase gate | VI current(uA) | VI gate |
|---|---:|---:|---:|---|---:|---|
| nominal_early | 725 | 837 | 0.018162689 | False | 33.499563 | False |
| nominal_late | 595 | 822 | 0.039418422 | True | 87.469896 | True |

Compared with folded v11: early wrong885→725/low1148→837; late wrong745→595/low970→822. Improvement is insufficient. Both local-bus cases violate the unchanged0.4V minimumVCE at xd0129 and xd0147; their exact minima remain in the full receipts. Local-bus DRC/LVS and RC/composition passes do not close these electrical failures. CDR remains externally clocked, with no qualified RF/body PEX or fullPHY acceptance.

## Actual TX clocks and next repair decision

[Run39254883221](https://github.com/Melihakbulut221/nssoc/actions/runs/39254883221) exposes all native clock details from independently reproduced strap6 waveform review. All31 clocks mapped to124 actual selector bases through the unchanged116611R model. No unmatched native or public clock edges were observed.

Across the diagnostic same-polarity matches the edge-bracket envelope is [-0.358158674,1.112115227]ps. This is an event association, not causal propagation proof or a timing acceptance gate. The result does not support blaming a large clock-wire delay for the140wrong/164low output samples and24HBT failures. Data-stage loading and bias headroom need direct analysis.

The new tx-strap6-data-network-review-cloud job restores the existing native wire model/contract, maps all124 data legs and372 native bases, records real output-series resistor boundaries, separately measures wire capacitance at outputs and receiving bases, and solves passive metal-network pair resistance with KCL checks. It keeps nonlinear native resistor cards and intrinsic device models unchanged and does not use sumR*C as a delay estimate. Solver controls cover series, parallel, loop, changed/removed branches and invalid/disconnected networks. No SPICE rerun, waveform resampling, source-bit edit or relaxed gate. Use measured per-stage load/asymmetry to select the next physical repair; qualify any changed layout with fresh DRC/LVS/RC and original full-wave gates.

Strap6 and trunk256 swap-leaf injected faults both completed and were detected. Trunk256 nominal and mainchip39-buffer route were still running at the last API check; preserve healthy runs. Neither fault pass closes nominal PHY or timing.
