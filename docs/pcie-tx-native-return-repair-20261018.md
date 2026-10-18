# TX native return repair — 2026-10-18

The full 32:1 serial transmitter remains rejected. Run 39112087217 completed the original 34 ns / 256-bit waveform with 181 wrong-sign samples, 220 samples below 100 mV and 24 HBT minimum-VCE failures. Its immutable waves and failures remain in GitHub releases. This work does not change those acceptance limits.

## Evidence used for this candidate

- Run 39130617772 mapped the 24 failed HBTs to native physical devices: six in final macro `f`, eighteen clock selectors in five `p8` macros.
- Run 39132058371 read all 77,618 native samples and reproduced all 604 original HBT metric records exactly. Final tail devices 114/115 have approximately 93 mV at their physical emitter terminals, although their native schematic emitter net is AVSS. Their minimum VCE is about 0.366/0.364 V. Clock selector failures and data-interface failures are separate remaining concerns.
- Run 39133064102 analyzed the actual 5,823-node / 9,140-resistor AVSS component. Its unit-current DC effective return resistance is 5.559999/5.573833 ohm at final emitter points T114_E/T115_E. KCL residual, resistor energy and reciprocal transfer checks passed. This is a static diagnostic, not a replacement transient model or a prediction of operating current.
- Run 39133346816 bound the limiting branches back to unchanged native extraction records. The common final branch R105585 is 1.4131 ohm between P_avss.n5354 and P_avss.n5353; the native coordinate records span the long final-column return trunk. The complete raw records, extraction scale and terminal anchors are retained in `docs/evidence/tx-v5-columns-native-return-coordinates-20261018.json`.

## Physical candidate

Keep all 31 macro placements, all 1,674 native devices, child drawings, signal wires and original topology. Change only the final-column AVSS trunk from 64 to 128 micrometres and move its centre 80 micrometres farther outward to leave clearance from the SUB trunk. Widen the existing final-emitter TopMetal1 strap from 4 to 12 micrometres, retaining its lower Metal2 emitter contacts; increase its top via array from 2 by 2 to 4 by 4. Other column trunks and the bottom return bus retain their original widths.

This is an unverified candidate. The cloud workflow must regenerate real GDS and pass the original native DRC, unsimplified device/port LVS and physical fault controls. Frozen-child and native-placement checks remain enabled. Native extracted RC, independent geometry-delta inspection and full loaded waveform gates must then be repeated. No resistor value is scaled and no waveform result is inferred from the DC diagnostic. A return repair alone is not evidence that level-4/final data timing or all selector headroom failures have closed.

All source changes, receipts and artifacts are cloud-only. The original failed design and its evidence remain available.
