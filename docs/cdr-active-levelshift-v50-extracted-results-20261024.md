# v50 upper-metal electrical result: improved but rejected

Actual run40037560023 retains every67column/110385row/full34.25ns waveform. All three ordinary corners passed transistor safety, zero-source operating point, both native OFF flags and unchanged solver checks. Both injected faults were detected.

| Case | CM minimum (V) | Minimum sampled signed output (mV) | Maximum valid delay (ps) | Original result |
| --- | --- | --- | --- | --- |
| Nominal |1.861655|44.621|57.031|Signal failed; CM passed|
| Hot-low |1.747817|31.918|66.094|Signal and CM failed|
| Cold-high |1.970139|56.754|51.406|Signal failed; CM passed|

Requirements remain100mV,37.5ps and1.8–2.15V. Compared with the original v49 extracted nominal1.633534V/29.181mV/62.344ps, the new metal routing recovered common mode substantially but did not close signal delay. Do not label this a passing component or full PHY.

The separate losses workflow reads the exact saved wave, measures every physical R loss/path and additionally compares external input, actual HBT base pair, actual collector pair and external output. Source bits are SHA-verified; there is no Boolean reconstruction of internal nodes. Public output metrics must reproduce the original rejected report. Use stage-specific measured delay and remaining hot-low CM deficit to select the next geometry/topology repair. All old failures remain available.
