# Rejected XOR input-load trial — 14 November 2026

[Simulation 43603972722](https://github.com/Melihakbulut221/nssoc/actions/runs/43603972722) changed only 24 XOR input HBT multiplicities from `nx=2` to `nx=1` relative to the previous select-bias trial. The C sampler and select bias stayed fixed. Existing wire RC was retained for this circuit experiment; it is not a new layout or a recovered-clock PHY simulation.

The simulator completed in 7,004.41 seconds, but electrical acceptance failed. X still has 385 wrong-sign samples and 717 samples below 100 mV out of 765. Y has one wrong-sign sample and 588 below 100 mV. Sampler A/C/D still have 65/148/96 weak samples; B passes. Reducing this load did not resolve the earlier failure.

[Read-only waveform diagnosis](https://github.com/Melihakbulut221/nssoc/actions/runs/43615016719) reproduced every original sampled gate. The two newly failing HBTs, XD0292 and XD0293, retain `nx=6`. Their active minimum VCE is 0.380924 V and 0.379038 V at about 5.83 ns, below the unchanged 0.4 V gate. Their maximum voltage and per-emitter current limits pass. These are active headroom failures, not startup excursions or current-density failures.

At 0.75 UI, the A sampler has the correct sign for transition groups, while the downstream data interface remains delayed or wrong. Median sampler/interface values are -0.2357/+0.0561 V for 01 and +0.2168/-0.0148 V for 10. Smaller XOR input devices therefore do not establish a fix for the upstream buffer path.

The next investigation should examine actual sampler-to-buffer settling, loading and the relationship between physical clock edges and observation windows before another sizing sweep. The bench clock changes again half a UI after its rising edge, while XOR observations occur 0.6, 0.75 and 0.9 UI after that edge. Whether the physical retiming topology supports those expected-bit windows must be checked; this observation alone is not proof that the checker is wrong. No threshold or expected-bit rule has been changed.

The trial is rejected. The prior nx2 circuit also remains unaccepted. Raw waveforms and native models stay in cloud artifacts; source/archive bindings and exact failed-device extrema are recorded in [the receipt](evidence/cdr-xor1-rejected-20261114.json). Full serial PHY integration remains open.

## Clock-window question resolved by actual input binding

[Native input tracing](https://github.com/Melihakbulut221/nssoc/actions/runs/43617454925) follows only the actual divider resistors from each buffer transistor base, stopping at sampler outputs and supplies. Both XOR selector pairs resolve to **D**, not raw B: `s0p/s1p` to `dqn` through XD0386 and `s0n/s1n` to `dqp` through XD0384. The D sample preserves the expected previous-bit sign across the late observation window. B switching there is therefore not grounds to alter the checker. All original expected-bit and acceptance rules remain unchanged.

The same audit observes 32 physical clock-connected HBT bases and expands all 50 passive `gp_*` subcircuits. It inventories 18,476 explicit capacitors and 28,984 numeric wire resistors. Incident explicit capacitance is approximately 0.567 pF at `adp`, 0.595 pF at `adn`, and 0.235 pF at `s0p`. These totals include coupling and exclude device intrinsic capacitance; they are not effective grounded loads or qualified RF extraction. The next investigation should bind the dominant capacitances to actual geometry and extraction assumptions before modifying the buffer/layout. Further blind XOR-device shrinking is not supported by these results.

[Detailed receipt](evidence/cdr-buffer-loading-and-retimed-selector-20261114.json) retains clock observations, passive load inventory and direct sampler binding. This diagnosis does not accept the failed circuit.

## Native capacitor provenance

Read-only run [43619048065](https://github.com/Melihakbulut221/nssoc/actions/runs/43619048065) authenticated the original metal extraction archive and located the dominant loads in Magic's native records. `T382_rppd_2.n0` carries 131020.2109375 aF and `T383_rppd_2.n0` 146790.359375 aF, corresponding to composed C8237/C8243. The original conductor aliases include each buffer collector and its six XOR input bases. Distributed resistance branches are retained. These capacitances were not introduced by the latest transistor-multiplicity trial.

The next physical investigation is the driver-to-load geometry and compact placement/routing of this interface. Native-record agreement does not qualify RF parasitic distribution, substrate treatment, PVT, or the layout corresponding to changed device parameters. All electrical gates remain unchanged and the candidate remains rejected. See `docs/evidence/cdr-native-cap-records-20261114.json` for source/artifact hashes and bounded native records.

## Measured physical span and layout direction

[43619538391](https://github.com/Melihakbulut221/nssoc/actions/runs/43619538391) authenticated the exact native GDS and terminal-anchor archive; KLayout read back DBU=0.001um and top bounds 2316.6 x 4715.48um. Source geometry remained unchanged.

| Conductor | Driver | XOR input distance from driver (Manhattan lower bound) |
|---|---|---|
| adp / T382_rppd_2 | T275_C | 1474.62–1804.62um |
| adn / T383_rppd_2 | T273_C | 1594.62–2044.62um |
| s0p / T397_rppd_2 | T282_C | 695.95–725.95um |
| s0n / T398_rppd_2 | T281_C | 605.95–665.95um |

The two data conductors each span 1322.77um vertically. This is a concrete physical-placement concern behind investigating the measured load; it does not by itself prove timing causality or predict a repaired waveform. Merely adding a parallel shortcut retains the old conductor capacitance. The next candidate must consider compact macro placement and coherent rerouting, including the resulting upstream sampler/divider connections, while preserving all device identities and circuit topology. Inspect the actual current macro boundaries before changing transforms. Fresh native DRC/deep+flat LVS, regenerated RC, unchanged loaded electrical gates, and subsequent full-PHY integration remain required.

Full coordinates and source hashes: `docs/evidence/cdr-buffer-physical-spans-20261114.json`.
