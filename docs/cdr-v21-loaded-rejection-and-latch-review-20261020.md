# V21 full CDR result: improved transfer, still rejected

All four cases of native run39444824145 completed. Both normal cases returned0
without solver diagnostics and kept all116HBT/46MOS device limits, but failed the
original loaded sampling and phase requirements. Both actual clock-stopped and
V/I-disabled faults were detected. Their successful fault jobs are not nominal
operation evidence.

In the late case, C wrong-sign samples fell182→115 and D291→252 out of765 each
against the retained v20 result. A/B still have129/64 samples below100mV.
The phase average fell0.0333913→0.0238876V, changing that gate from pass to fail.
The early case has C113/D283 wrong signs; A/B have129 low-margin samples each.
The V/I gate fails early and passes late. The candidate remains electrically
rejected; a shorter physical route alone did not close the sampler chain.

The cloud-only latch review restores both exact immutable raw captures, their
fresh composition and physical terminal evidence. It first reproduces every
original sampler result, then reconstructs master/slave data and hold banks from
native connectivity. Every physical parallel selector-base combination remains
included. Diagnostic interpolation locates edges only; it cannot change the
original fixed sampling verdict or imply a recovered clock.

The exact source delta changes only v21 provenance, identity and the measured
capacitor count12704. No new simulation, sample-phase fitting, signal regeneration
or relaxed threshold is introduced. Raw waveforms stay in their original cloud
releases. Full serial PHY, closed-loop CDR and mainchip timing remain open.
