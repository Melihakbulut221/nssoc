# TX v5 full-wire path review

The original 34 ns full-wire capture failed with 227/768 wrong-sign output samples. The new cloud review restores that exact binary capture, contract and operating point and replays the unchanged original evaluator. It requires exact equality with all original signal, interface, transistor and capture reports before producing diagnostics.

The derived report localizes each failed physical input group at the original bits and phases, including all nine combinations of parallel positive/negative input terminals. It maps all eight failed HBTs to their actual collector/base/emitter/substrate voltages and lists the common-mode and swing at every physical input group. All 604 native HBT terminal voltage summaries remain available. No new transient is run, and no PHY acceptance is implied.

The waveform remains in its original GitHub Release. Only derived summaries are published by `tx-v5-path-review-cloud`; no local checkout or simulation artifact is written.

## Result

Run39084981409 reproduced every original evaluator output exactly. All four level_4 input groups fail: p4_0 has45 wrong-sign samples, p4_1 has90, p4_2 has189 and p4_3 has162, including all nine physical terminal combinations. Final inputs a/b have892/923 wrong samples. All level_8 groups retain positive margins. The original full serial output still has227/768 wrong samples.

The failed native devices xd0114/xd0115 have emitter means approximately0.1722V above external return and minimum VCE0.29445/0.29306V. Devices xd0109–xd0112 and xd0515/xd0521 also retain their headroom failures. These terminal values localize the actual failure; they do not yet prove that reducing return resistance alone restores the original bit stream. Next bind these device identities to the actual v5 physical hierarchy and inspect its return conductors before geometry repair. The complete native waveform remains unchanged in its original release.
