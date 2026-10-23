# CDR v40 loaded selector diagnosis

All four v40 full native captures failed the original data/phase gates. Enlarging master selectors also violated VCE. Before proposing another electrical candidate, inspect their existing complete waveforms with the same measured collector-current, base-clock, follower common-mode, master/slave transfer and original bit-window equations used for v39.

This diagnostic uses immutable run39878490784 summaries, archives and full raw SHA256 identities. It reproduces all120 original HBT checks and all four original sampler checks, including every failed case. Master/slave selector areas are verified against each actual candidate's source graph. The all_select34 case is permitted to be *diagnosed* only if its original device failures reproduce exactly; no device failure is waived or converted to acceptance.

No new native simulation, stimulus, shortened window, resized transistor or physical implementation is introduced. The four v40 candidates remain rejected. Compare resulting clock-current steering, input/output transfer and headroom with v39follower_l18 before selecting the next candidate. Frozen17918R/12850C does not qualify fresh candidate geometry, PVT, closed-loop recovery or a complete Gen3x4 PHY.
