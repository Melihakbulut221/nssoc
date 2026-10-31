# Current loaded CDR sampling witnesses

This source-only helper explains the existing nominal captures without rerunning a simulator or changing the original gates. It reproduces every sampler/comparator scalar and per-bit settling delay exactly before returning observations. All 4,590 interpolated sample queries are separate from native row IDs, timestamps and voltages. The 1,530 settling windows retain every bad native row, including disjoint regressions; the original added time step is explicit.

The caller must independently authenticate the complete producer case, native capture, original report, current terminal/plane binding and source. This helper is not that admission boundary. Witness vector names come from that authenticated binding. No dynamic KCL, causal mechanism, closed-loop operation, electrical acceptance or physical acceptance is claimed.

Six hosted test methods cover a known constant signal, a zero interpolated margin between two nonzero native values, rejected scalar/delay changes, invalid capture/expected data, and simulator/partial-capture failures. They have not yet been executed. No local numerical test or native archive acquisition is authorized.
