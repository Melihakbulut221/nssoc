# Diagnose current physical CDR latch transfer before selecting another repair

V16 is the current physically extracted484-device CDR, with17674 metal resistors and12709 capacitors. Both original early/late full waveforms rejected sampling while passing device limits and solver diagnostics. The v17 divider sensitivity experiment worsened C/D errors and is not adopted.

This read-only cloud analysis binds the existing latch-timing method to the exact v16 fullwave and geometry receipts. It first reproduces all116 original HBT checks and all4 original sampler checks from the complete stored raw data. Native transistor ownership and shared-emitter connections identify each actual master/slave data pair, hold pair and parallel selector pair. All three graph corruptions per sampler remain required.

The report retains every physical clock-base combination and samples actual input/output voltages and track/hold collector currents at fixed offsets around original capture edges. Nearest-edge differences are descriptive, not claimed propagation delay or retiming. Internal100mV annotations are diagnostic markers; no new acceptance gate or relaxed external output limit is introduced.

This is intended to distinguish insufficient incoming data margin from latch transfer/clock overlap before a physical or intrinsic circuit repair. It changes no waveform, data oracle, sample phase, load, model or timing criterion. Failed nominal results remain rejected.

Independent cloud runs at publication: wholePLL39370629792, mainchip39373842033, TXg23439372036289 and TXg234+physicalfinalbridge39376417214. All native computation and artifacts stay in GitHub; local project remains empty.
