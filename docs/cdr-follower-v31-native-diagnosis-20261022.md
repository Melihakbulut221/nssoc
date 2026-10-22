# CDR v31 full native diagnosis

Run [39731416566](https://github.com/Melihakbulut221/nssoc/actions/runs/39731416566) completed both early and late diagnosis jobs. Each replayed the original 120 HBT measurements and all four sampler checks from its full original waveform, then reconstructed the physical latch topology. The unchanged electrical tests still reject v31. Diagnostic success is not PHY acceptance.

## Measured results

- The failed devices xd0105 and xd0106 are the **C sampler master track selectors**, identified by actual native shared-emitter and collector topology. Their minimum active VCE is about 0.379–0.382 V against the unchanged 0.4 V gate.
- In the late capture, both real emitter followers remain conducting: neither has nonpositive collector current or VBE below 0.5 V during the active interval. The earlier follower cutoff mechanism is absent in this capture. This does not prove adequate retiming.
- In A and B, all 255 slave-input samples at the expected capture edge exceed the internal 100 mV diagnostic marker, yet the original 0.3 UI output samples still fail (129 A samples, 91 B samples). Their observed worst clock-to-valid delays remain 44.53 ps and 40.16 ps against 37.5 ps.
- C and D also have weak or late master input/output observations. At the expected edge D has 64 wrong-sign master outputs; at 0.3 UI, C and D retain 20 and 64 wrong-sign slave outputs respectively.
- Physical clock-base crossing medians are about 2.05–3.75 ps behind the matching external clock crossings across all retained selector pairs. Median slave track-minus-hold current crossings are about 12.64–14.29 ps after the expected edge. These are observed statistics, not a proof of a single delay mechanism.
- No simultaneous positive master/slave track-minus-hold current was observed for A/C/D; B had six samples with at most 3.75 ps total observed overlap. No new acceptance threshold is inferred from this diagnostic.

## Next design work

Separate clock-selection and slave-settling behavior from the C/D input common-mode and drive problem. A new candidate must improve the original output deadline and amplitude while removing the C-master headroom violations. Merely increasing follower current, moving the sampling phase, reducing the 150 fF collector load, or marking internal 100 mV observations as acceptance would not close this failure.

Any parameter screening remains unqualified until its actual native PCell geometry, parent DRC/LVS, fresh RC extraction and the original full loaded early/late and fault cases are rerun. No replacement geometry or nominal acceptance is claimed by this document.

All full source waveforms remain in their immutable original releases. The new diagnosis summaries and parts are pinned in `docs/evidence/cdr-follower-v31-native-diagnosis-pass-20261022.json`.
