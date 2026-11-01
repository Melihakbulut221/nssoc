# Original waveform diagnosis

Run [41263882381](https://github.com/Melihakbulut221/nssoc/actions/runs/41263882381) at immutable source `580db114a842353df8b3ae6be32b8ab8294887bd` completed successfully on GitHub. This is read-only analysis of the previously retained native waveform, not a new simulation or electrical acceptance.

All four archive parts and 113 members were checked on the runner. The frozen original reader reproduced the complete capture, all 124 HBT measurements, all six stages and 1,530 per-bit delays, and original phase/VI results. Seven source controls passed. Complete actual proof: `docs/evidence/cdr-via2-m3-wave-diagnostic-terminal-41263882381` at `5803aaedcb8eba6b9a894e9bf6eeae2384508df5` (28 files); source-control proof at `808c96091a93bc4b277427a20117b474e03352a4` (15 files).

| Device | Worst time, ns | Collector V | Base V | Emitter V | VCE V | Ic per emitter, mA |
|---|---:|---:|---:|---:|---:|---:|
| T061 | 20.81328125 | 0.851712 | 1.424403 | 0.511010 | 0.340702 | 1.581518 |
| T062 | 20.81328125 | 0.852607 | 1.424472 | 0.510688 | 0.341919 | 1.588930 |
| T115 | 18.18609375 | 0.888460 | 1.428418 | 0.512216 | 0.376244 | 1.598209 |
| T116 | 18.18609375 | 0.889318 | 1.428412 | 0.511874 | 0.377445 | 1.605001 |

All four fail the unchanged 0.4 V minimum active VCE. The complete result retains simultaneous clock/data/bias voltages, every below-gate interval and all under-margin stage samples. Phase remains 13.980168 mV against 30 mV; VI current remains 42.611702 uA against 50 uA. Correlated values are diagnostic evidence, not proof of a corrective circuit edit.

Next: map the exact original connectivity to these observed nodes on a cloud runner, then qualify a concrete circuit/layout correction. Do not change stimulus or acceptance limits, assume a sampling-oracle defect without topology evidence, or rerun identical native work.

Native archives, models and waveforms remain exclusively in the cloud. Full serial PHY, final mainchip routing and setup/hold closure remain open.
