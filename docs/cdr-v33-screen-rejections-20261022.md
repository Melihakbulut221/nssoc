# V33 full-screen rejection
All six original-length native runs completed and were rejected by the unchanged electrical gates. All120HBT/MOS device checks passed, but all four samplers still failed their original100mV/37.5ps acceptance and all six phase detector checks failed. C/D retained wrong-sign samples. The full113,475-row1104-column captures and failures are retained in immutable cloud releases.

Restoring slave bleeds alone (bleed12) did not solve C/D capture. Reducing sampler collector loads to2.0 or1.6um improved some A/B margins, but did not solve C/D; load16 produced approximately118.9ps worst clock-to-valid in C and, in the late case, D. These are failed exploratory intrinsic screens with frozen v32 wire RC, not physically accepted variants. No threshold, clock phase, output load or sampling window was relaxed.

The next CDR step is native master/slave and clock-transfer diagnosis against these exact full waveforms. Do not invest a new physical layout in any of these unaccepted candidates solely because transistor headroom passed. The detailed per-case receipt records all sampler, phase, VI and capture evidence.
