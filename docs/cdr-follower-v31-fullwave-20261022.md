# v31 full original loaded waveform screen

Run 39721805172 passed the fresh native raw wire/MIM audit (13 wire and nine intrinsic fault controls) and exactly-once composition (19 controls). The new model has 476 native devices, 17,918 R and 12,850 C. It is not qualified full PEX or a closed-loop CDR.

The cloud workflow runs nominal early, nominal late, stopped-clock and disabled-VI-bias cases. The wrapper binds exact successful audit/composition release summaries, and validates fresh v31 planes against the v31 parent. The transient controller differs from v30 only by provenance namespace and composed model name. All original 256 bits, 34.25 ns duration, 8 GHz external clock, 1104-column capture, 150 fF sampler and 50 fF XOR loads, 37.5 ps sampler deadline, 100 mV sample margin, 30 mV phase gate, 50 uA VI gate and individual device-safety checks remain intact.

This is the first loaded validation of the shorter follower pull-down resistors in the full extracted parent. It may still fail, particularly at the unchanged A/B timing gates. Nominal acceptance must be read from actual complete reports; fault detection is a separate result. All native computation and immutable evidence publication run on GitHub-hosted runners. No local checkout or artifacts are required.
