# v30 electrical rejection and unchanged-waveform diagnosis

The complete 34.25 ns / 256-bit / 1104-column waveforms reject both nominal v30 cases. All transistor limits passed, but all four samplers and the phase response did not. The two original fault cases were detected. Physical DRC/LVS acceptance does not establish electrical acceptance.

The lower input resistance candidate worsened downstream sampling. Early C/D have 96/257 wrong-sign samples, versus v29 9/96; late C/D have 96/234, versus v29 0/74. Maximum early C/D delays are about 118.906 ps against the unchanged 37.5 ps target. No data, clock, load, test window, threshold, or safety limit was relaxed.

The new cloud diagnosis restores only the exact v30 complete waveform, composition, native planes and physical device locations. It reproduces all 120 HBT checks and four original output sample checks, reconstructs actual master/slave transistor ownership, measures internal transfer and selector current timing, and keeps all parallel device combinations. Its source delta changes only namespace, evidence identities, actual RC counts and the observed zero HBT violations. It does not change measurement equations or claim PHY closure.

Use these results to distinguish an upstream input timing failure, master/slave propagation failure or clock steering issue before the next geometry change. Any subsequent geometry change requires new DRC/LVS and native parasitic extraction. The active mainchip/TX calculations continue independently on GitHub.
