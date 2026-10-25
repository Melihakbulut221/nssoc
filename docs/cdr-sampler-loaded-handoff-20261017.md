# Native sampler results and loaded-comparator handoff, 2026-10-17

Run39051016629/source1955966b passes the clean native sampler screen at nominal, hot/low and cold/high. Actual swapped-output and stopped-clock faults fail the fixed source-bit check as intended. The unchanged15HBT/12R/41emitter source now has observed zero-source operating point, all15native OFF readbacks and no native numerical diagnostics in these five captures. This is a standalone schematic result, not physical sampler or recovered-clock acceptance.

| Case | Minimum margin mV | Wrong of768 | Maximum clock-to-valid ps | Active output commonmode min,max V |
|---|---:|---:|---:|---|
|nominal|146.815152|0|23.281250|2.405106,2.425144|
|hot_low|147.554400|0|25.468750|2.273828,2.292599|
|cold_high|135.627851|0|21.718750|2.535373,2.556557|
|swap_output|-181.080625|768|118.906250|2.405106,2.425144|
|clock_stopped|-177.873012|381|118.906250|2.408272,2.413215|

The normal cases meet0.4Vminimum activeVCE,1.6Vmaximum absoluteVCE,1Vmaximum absoluteVBE,3mA/emitter,0.5mAminimum tail current and37.5psclock-to-valid. All256bits and three fixed held-output phases are covered, including the final bit, with a34.25ns trajectory and0.3125psmaximum step. The old127bit/node-set experiment is not substituted for these new captures.

The measured sampler common mode is incompatible with directly assuming the XOR bench's2.0Vdata and1.3Vselect source conditions. The next required experiment is a connected sampled-comparator candidate: two actual samplers with independent fixed PRBS inputs and one actual fresh-wire XOR, including native level-shift resistors and loading on both sampler outputs. It is an integration prerequisite for a multi-edge phase detector, not a replacement for it.

A proposed passive starting point (not yet simulated/accepted) is seriesL1.8/W1 and shuntL10.8/W1 on each data-domain leg; seriesL3.0/W1 and shuntL4.3/W1 on each select-domain leg. These nominal ratios must be solved with the actual sampler, XOR input base currents, resistor self-heating and every native RC element. Do not assign ideal voltage gains, force common modes or reuse an unloaded waveform. Any candidate needs all-device limits and a fixed original source-bit comparison. The source samplers and both different input common modes must remain explicit in the result. If rejected, preserve actual loaded voltages and repair the interface; no fullCDR claim follows from a sampled comparison passing.

Actual early/late sample alignment, deadzone/polarity, native V/I feedback, oscillator acquisition with frequency offsets and missing transitions, noise/jitter/BER, fullPVT, physical sampler/levelconversion routing and x4mainchip integration remain open. The complete reports and immutable raw archive hashes are in docs/evidence/cdr-sampler-native-pass-20261017.json.
