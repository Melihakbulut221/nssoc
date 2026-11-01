# HBT emitter-count load trial: rejected

Actual native run41299745896/source12f3e0f3bf7010289dc0f993ac71dbfa55cc19e4 completed simulation in1059.425s with engine return0 and no numerical diagnostics. Original device and VI gates pass, all six data/timing stages fail. Phase20.883396mV fails the unchanged30mV requirement and is worse than the12-divider parent's29.329406mV. X/Y wrong-sign samples increased to420/34. This40-HBT Nx reduction is rejected; no regenerated layout or freshRC acceptance follows from it.

The complete113file evidence is retained under docs/evidence/hbt-load-native-terminal-41299745896; native waveforms/model/runtime remain on release430521829. Keep the actual per-emitter current binding, source integrity and original device/data/phase gates. Future electrical repair must address the observed latch/buffer timing with actual waveform/current evidence. Do not silently retain this rejected circuit or increase unsupported single-MOS widths.
