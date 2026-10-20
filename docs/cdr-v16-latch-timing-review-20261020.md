# Diagnose current physical CDR latch transfer before selecting another repair

V16 is the current physically extracted484-device CDR, with17674 metal resistors and12709 capacitors. Both original early/late full waveforms rejected sampling while passing device limits and solver diagnostics. The v17 divider sensitivity experiment worsened C/D errors and is not adopted.

This read-only cloud analysis binds the existing latch-timing method to the exact v16 fullwave and geometry receipts. It first reproduces all116 original HBT checks and all4 original sampler checks from the complete stored raw data. Native transistor ownership and shared-emitter connections identify each actual master/slave data pair, hold pair and parallel selector pair. All three graph corruptions per sampler remain required.

The report retains every physical clock-base combination and samples actual input/output voltages and track/hold collector currents at fixed offsets around original capture edges. Nearest-edge differences are descriptive, not claimed propagation delay or retiming. Internal100mV annotations are diagnostic markers; no new acceptance gate or relaxed external output limit is introduced.

This is intended to distinguish insufficient incoming data margin from latch transfer/clock overlap before a physical or intrinsic circuit repair. It changes no waveform, data oracle, sample phase, load, model or timing criterion. Failed nominal results remain rejected.

Independent cloud runs at publication: wholePLL39370629792, mainchip39373842033, TXg23439372036289 and TXg234+physicalfinalbridge39376417214. All native computation and artifacts stay in GitHub; local project remains empty.

## Verified result

[Cloud run39376994817](https://github.com/Melihakbulut221/nssoc/actions/runs/39376994817) completed both early and late analyses. The complete original116 HBT and4 sampler decisions were reproduced; the original electrical rejection remains in force. The companion [evidence receipt](evidence/cdr-v16-latch-timing-result-20261020.json) pins all summary, manifest and archive assets and preserves the original measured gates and selected fixed-phase diagnostics.

| Case | Sampler | Wrong sign /765 | Below100mV /765 | Maximum clock-to-valid |
| --- | --- | ---: | ---: | ---: |
| early | A |77|129|52.03125ps|
| early | B |129|129|52.65625ps|
| early | C |189|206|118.90625ps|
| early | D |339|345|118.90625ps|
| late | A |97|129|52.96875ps|
| late | B |0|128|45.46875ps|
| late | C |188|210|118.90625ps|
| late | D |310|330|118.90625ps|

At the unchanged+0.3UI output sample, A/B slave-input differential voltages have the expected sign and exceed100mV, while their slave outputs remain late or weak. At+0.9UI their outputs pass the100mV diagnostic marker. This later observation is not substituted for any original sample.

C/D additionally receive weak master-input data: all255 inspected samples at+0.3UI are below the internal100mV diagnostic marker. D has71 wrong-sign input samples early and48 late. Thus merely fixing A/B output timing cannot be assumed sufficient. No sampled simultaneous positive master/slave track-minus-hold collector currents were observed; this is not proof that all possible races are absent.

The existing physical macro order places the B source before A, D, C and the A-to-C filter; the B-to-D filter is above B. This causes long source/filter/consumer routes. Next physical work should compare fully regenerated source/filter/consumer placements using the unchanged circuit and child geometry, then run native DRC/LVS, fresh distributed extraction and the original full loaded early/late tests. A shorter geometric span alone must not be reported as an electrical repair. The previously rejected v17 divider experiment is not adopted.

All evidence is cloud-resident. The local project directory was rechecked empty. Mainchip short-clock routing, PLL full acquisition and both full TX comparisons are still pending; no full PHY, routed-mainchip timing or manufacturing acceptance is claimed.
