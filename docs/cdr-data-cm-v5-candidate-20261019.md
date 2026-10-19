# Physical CDR data-buffer common-mode candidate

All CAD, waveform processing and native verification run on GitHub-hosted runners.
The local project directory is empty; the verified migration receipt is in release
cloud-migration-final-checkout-20261013.

The collector-v8 native path review (run39202786678) reproduced the rejected
nominal early and late loaded waveforms without changing samples or thresholds.
This diagnostic success is not electrical acceptance. Both nominal cases still
fail sampler-data and HBT operating-window checks.

Late XD129 reaches VCE0.384447V at19.64328125ns, with base1.778396V and
emitter1.330945V. The shared-emitter XOR data stage has insufficient headroom.
Collector-wire widening alone did not close sampling or device gates.

This candidate increases only the data buffer native rppd header length from
2.0um to2.4um at unchanged8um width. The four HBT sizes, two load resistors,
substrate contacts, terminals, routing construction and select-buffer source
remain unchanged. Lower data-buffer common mode is a design hypothesis, not a
measured improvement. No supply, clock, input waveform or acceptance threshold is
changed to compensate.

The new workflow first checks exact source deltas, regenerates actual PCell
geometry and runs the same560-rule DRC, deep/flat14-device transistor LVS and
five original fault controls. An additional LVS fault deliberately supplies the
old2um header reference; accepting that mismatch fails the campaign.

Pending: native leaf results, two-leaf replacement in the484-device parent,
fresh parent DRC/LVS, native terminal planes, binding and wire RC, full MIM
composition, and the same loaded256-bit early/late and fault waveforms.
No standalone idealized-buffer transient can substitute for those checks.
Sampling errors, TX32-tree electrical failures, closed-loop CDR, complete PHY,
mainchip integration and final timing remain open.
