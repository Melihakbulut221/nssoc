# Data/hold Nx4: rejected native waves and read-only latch diagnosis

Both original nominal cases in run39426217320 are rejected. Native simulation completed34.25ns /256bits with all1,108 columns and no startup diagnostics. All116 HBT/46 MOS safety gates passed, but sampler and early phase gates did not.

Each sampler has765 original output comparisons. Early wrong-sign/below100mV counts are A0/95, B32/129, C184/202, D313/331. Late counts are A0/109, B0/65, C182/200, D291/328. These remain failures. Compared with v19, reducing data/hold size helped some samples but did not close the loaded circuit.

The new read-only cloud diagnostic restores both exact immutable raw files and new physical geometry, reproduces every original HBT and sampler check, then measures actual master/slave input/output voltages and track/hold currents. All physical parallel selector pairs and original graph-fault controls remain. It asserts the actual new Nx4 data/hold devices; no waveform, load, phase or acceptance threshold changes.

Internal100mV markers and nearest crossings are diagnostic only. Follow the measured root cause into a new physical candidate; do not accept this rejected model, use ideal regenerated internal data, or claim closed-loop/fullPHY behavior.
