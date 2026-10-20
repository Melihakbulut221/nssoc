# Selector4 CDR full-wave outcome — rejected

Run[39400191012](https://github.com/Melihakbulut221/nssoc/actions/runs/39400191012)
at604b0fbf89e27619220422b41a068de0dfc144e4 completed both original34.25ns nominal
captures. Native returncode0, no simulator diagnostics, actual116HBT/46MOS
device gates pass. Neither nominal case passes the original loaded data gates.
The stopped-clock and bias-off jobs detect their injected faults independently.

| Case/stage | Wrong sign /765 | Below100mV /765 | Maximum clock-to-valid(ps) |
| --- | ---: | ---: | ---: |
| Early A | 0 | 113 | 46.40625 |
| Early B | 129 | 129 | 52.65625 |
| Early C | 186 | 208 | 118.90625 |
| Early D | 337 | 341 | 118.90625 |
| Late A | 0 | 129 | 47.96875 |
| Late B | 0 | 96 | 41.09375 |
| Late C | 188 | 214 | 118.90625 |
| Late D | 304 | 330 | 118.90625 |

The early phase-average16.27554mV fails the unchanged30mV minimum; late31.74229mV
passes that phase check but not the data check. Sampling remains at the original
0.3/0.6/0.9UI, with the150fF collector and50fF XOR loads unchanged.
The reported maximum settling time must not be substituted for the individual
phase/amplitude/bit gates.

Against v18, early A wrong-sign samples improve81→0 and late A97→0. Late B
low-margin samples improve128→96. Other stages remain materially deficient,
so reducing the actual32 clock-selector HBTs fromNx8 toNx4 is not closure.
All observations come from fresh native v19 geometry and audited wire/MIM
composition, never reused v18 RC or a modified source-bit oracle.

Continue separating remaining A/B clock steering and regeneration from C/D
input amplitude/arrival failures. Any further device-size or route change
requires new geometry, native DRC/deep+flat LVS, extraction and the same full
waveform gates. Do not tune phases, shorten the bit sequence, bypass the clock,
reduce loads, waive device bounds or declare an isolated-block pass as
closed-loop PHY completion.
