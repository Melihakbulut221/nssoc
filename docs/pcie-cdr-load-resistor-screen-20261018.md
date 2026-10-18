# Exploratory sampler load-resistor geometry screen

Actual local-v5 loaded run39147266374 failed its nominal early/late gates. The saved-wave diagnosis39148394285 reproduced every failed sampler count and HBT minimum. Minimum HBT VCE improved from the power-v4 candidate's approximately0.17V to approximately0.30V, but remains below the unchanged0.40V bound.47 early and42 late HBT devices fail at least one original voltage/current gate; all46 MOS terminal-voltage checks pass. Sampler wrong-sign counts remain early113/305/363/393 and late166/128/366/380 out of765 samples each. VI phase/current gates fail. Neither clock-stopped nor VI-bias-off control is evidence of healthy operation; both detected their injected faults.

The16 sampler collector-load native rppd devices are32um wide and2.12um long. The next experiment reduces only their PDK compact-model length to1.6um or1.2um. Reducing their resistance may improve collector voltage headroom and transition time; this is a hypothesis, not an accepted correction. All other484-device model cards, all3250 wire resistors and3841 wire capacitances, node connections,11 MIM devices,256 PRBS bits, original sampling phases,150fF/50fF loads,8GHz external clock and every original acceptance threshold remain unchanged.

These four nominal early/late simulations use the previously extracted wiring. They are deliberately labeled exploratory circuit screens: the changed resistor geometry has NOT been generated in GDS, checked against DRC/LVS, or freshly extracted. A successful screen would select dimensions for new native layout and full repeated physical/RC/loaded verification; it cannot itself close CDR, PHY, or production acceptance. Failure artifacts and original captures stay in cloud releases. No fabricated internal waveform or fitted phase/latency is introduced.

## Actual outcomes and cloud recovery

Original run39149512255 completed native transients with return code0 and no simulator diagnostics, but all four candidates failed unchanged functional/device gates. Publication rejected dotted group names; all original files were retained as Actions artifacts. Run39150862130 recovered all four artifacts in hosted runners, verified their ZIP SHA256 and every report output hash, and published the original reports and waveforms without resimulation. No candidate layout or RC was regenerated for this parameter screen.

| Load length (um) | Phase | Wrong-sign a/b/c/d samples | Failing HBTs | Minimum VCE (V) |
|---|---|---|---|---|
| 1.2 | early | 109 / 297 / 348 / 384 | 37 | 0.315354 |
| 1.2 | late | 143 / 128 / 352 / 361 | 36 | 0.314210 |
| 1.6 | early | 113 / 303 / 356 / 389 | 45 | 0.306082 |
| 1.6 | late | 148 / 128 / 361 / 379 | 41 | 0.310690 |

The gate remains zero wrong-sign samples and active HBT VCE>=0.4V, along with every other original voltage/current/timing requirement. None of these screens is accepted. The measured native wire losses now motivate an actual upper-metal strap layout, keeping the original2.12um intrinsic loads.

Evidence: `docs/evidence/cdr-load-resistor-screen-rejections-20261018.json` pins recovered summaries, parts manifests, artifact provenance and compact failed checks. Full waveforms remain exclusively in cloud Releases.
