# V22 actual early and late waveform diagnosis

Both nominal fullwave cases in run39458941860 were rejected by unchanged sampling and phase gates; native device gates passed. The clock-stopped and VI-bias-off actual faults were detected. Early A/B/C/D wrong-sign counts are0/0/115/253; below100mV counts129/129/128/260. Early phase average6.871mV fails the signed30mV requirement. Late results and full waveform receipt remain preserved separately.

The v22 latch review reuses the exact v21 diagnostic, changing only immutable run/source/model-count bindings. Its source-delta manifest proves the waveform reader, transistor gate reproduction, original sampler reconstruction, complete parallel selector pairing and master/slave graph checks remain byte-identical outside those bindings. It reads original full raw captures from their cloud releases; no new simulation or decimation.

The review must reproduce both original rejected sampler results and every116-HBT device measurement before interpreting physical master/slave data voltages and selector-current windows. This locates whether remaining delay is in input transport, track/hold steering or regeneration. Diagnostic success is not acceptance of the failed design. Fresh real geometry and RC remain mandatory for a subsequent candidate.
