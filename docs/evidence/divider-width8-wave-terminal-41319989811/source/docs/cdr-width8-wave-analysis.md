# Width8 loaded sampler failure analysis

This read-only cloud analysis consumes the complete raw capture from run 41310192873, source 66fb47bb12eff45c83b3d2819d281f99960ac4cc, release 430594515. It preserves the original rejection: device, data and phase gates failed. The model and its retained wire RC are not modified; no simulator or fresh PEX is run.

All archive members are authenticated before selecting the complete raw, original measurements and topology. The existing six data measurements and phase integral are reproduced. Buffer/divider source-conditioned margins, native driver/consumer terminal values, and one-UI traces locate the failing paths.

The added device replay recomputes all original HBT, MOS, tail-current and MIM tables from full raw rows and compares them with the producer. It enforces unchanged HBT VCE/VBE/current, MOS voltage/polarity, per-device current, aggregate stage-current and capacitor limits. Actual offending HBT extrema include raw row, time, physical instance, Nx and terminal values. A successful diagnostic run means measurements were reproduced, not that a rejected device became acceptable.

The 34 existing parser/measurement controls remain, with 14 added device-limit controls. All native payloads and numerical analysis remain on GitHub. The local coordinator handles source/API-derived text only. Full PHY, recovered-clock closed loop, fresh physical layout/PEX and final chip timing remain unaccepted.
