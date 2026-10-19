# Parent AVDD v13: nominal early rejection and native diagnosis

Run [39276673160](https://github.com/Melihakbulut221/nssoc/actions/runs/39276673160), job118145370108, completed the actual 484-device,16010R11677C full capture. Native exit0, no numerical diagnostics, sources unchanged. The 34.25ns capture retains113475rows and1108columns. The original electrical screen rejected data and phase behavior; this is not CDR or PHY acceptance.

Device safety now passes in this early-offset nominal case. HBT129/147 minimum active VCE is0.4105773/0.4143585V, above the unchanged0.4V gate; all46MOS pass their original limits. This does not establish PVT or late-offset safety.

At the unchanged three phases, sampler A/B/C/D still show77/129/198/325 wrong-sign samples out of765each. Comparators X/Y show135/364 wrong-sign samples. Phase average is0.0189025V against the original0.03V gate. Mean signed VI current is35.1745uA against the original50uA gate. These failures remain recorded unchanged.

The new read-only cloud review restores the hash-pinned original raw capture, model and native planes; it reproduces the original sampler metrics and all HBT voltage/current metrics. It examines native master/slave inputs, actual local clock phases, supply and collector wire drops and conductor inventories. The only source adaptations are the new source binding/model counts/namespace and the now-empty HBT failure set. All waveform times, voltage thresholds, limits and graph methods remain unchanged. Shortest resistor paths and incident capacitance are diagnostic inventories, not effective RC or delay estimates.

## Late-offset nominal capture and disabled-VI control

The late capture from job118145370034 has native exit0, no diagnostics and unchanged sources. Device safety passes with minimum active HBT VCE0.4117509V. Phase average0.03980685V and signed VI current87.9278uA pass the original phase/current gates. Data acceptance still fails: A/B/C/D wrong-sign samples91/0/194/308, and below100mV samples129/128/238/331. Even sampler B with no wrong-sign samples fails its voltage and latency requirements. The overall capture remains rejected.

The same source-pinned native diagnosis now runs on the late capture. The already queued early review39282864029 remains intact; this new workflow revision selects only nominal_late to avoid duplicating the early analysis.

The disabled-VI fault job118145369918 is detected with mean signed VI current0.224093uA and bias_passed=false. Its green job denotes successful fault detection, not a working nominal CDR. Both original failed nominal captures and both detected faults remain preserved in cloud releases.
