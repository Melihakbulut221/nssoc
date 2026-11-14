# Rejected XOR input-load trial — 14 November 2026

[Simulation 43603972722](https://github.com/Melihakbulut221/nssoc/actions/runs/43603972722) changed only 24 XOR input HBT multiplicities from `nx=2` to `nx=1` relative to the previous select-bias trial. The C sampler and select bias stayed fixed. Existing wire RC was retained for this circuit experiment; it is not a new layout or a recovered-clock PHY simulation.

The simulator completed in 7,004.41 seconds, but electrical acceptance failed. X still has 385 wrong-sign samples and 717 samples below 100 mV out of 765. Y has one wrong-sign sample and 588 below 100 mV. Sampler A/C/D still have 65/148/96 weak samples; B passes. Reducing this load did not resolve the earlier failure.

[Read-only waveform diagnosis](https://github.com/Melihakbulut221/nssoc/actions/runs/43615016719) reproduced every original sampled gate. The two newly failing HBTs, XD0292 and XD0293, retain `nx=6`. Their active minimum VCE is 0.380924 V and 0.379038 V at about 5.83 ns, below the unchanged 0.4 V gate. Their maximum voltage and per-emitter current limits pass. These are active headroom failures, not startup excursions or current-density failures.

At 0.75 UI, the A sampler has the correct sign for transition groups, while the downstream data interface remains delayed or wrong. Median sampler/interface values are -0.2357/+0.0561 V for 01 and +0.2168/-0.0148 V for 10. Smaller XOR input devices therefore do not establish a fix for the upstream buffer path.

The next investigation should examine actual sampler-to-buffer settling, loading and the relationship between physical clock edges and observation windows before another sizing sweep. The bench clock changes again half a UI after its rising edge, while XOR observations occur 0.6, 0.75 and 0.9 UI after that edge. Whether the physical retiming topology supports those expected-bit windows must be checked; this observation alone is not proof that the checker is wrong. No threshold or expected-bit rule has been changed.

The trial is rejected. The prior nx2 circuit also remains unaccepted. Raw waveforms and native models stay in cloud artifacts; source/archive bindings and exact failed-device extrema are recorded in [the receipt](evidence/cdr-xor1-rejected-20261114.json). Full serial PHY integration remains open.
