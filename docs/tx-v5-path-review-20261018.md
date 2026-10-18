# TX v5 full-wire path review

The original 34 ns full-wire capture failed with 227/768 wrong-sign output samples. The new cloud review restores that exact binary capture, contract and operating point and replays the unchanged original evaluator. It requires exact equality with all original signal, interface, transistor and capture reports before producing diagnostics.

The derived report localizes each failed physical input group at the original bits and phases, including all nine combinations of parallel positive/negative input terminals. It maps all eight failed HBTs to their actual collector/base/emitter/substrate voltages and lists the common-mode and swing at every physical input group. All 604 native HBT terminal voltage summaries remain available. No new transient is run, and no PHY acceptance is implied.

The waveform remains in its original GitHub Release. Only derived summaries are published by `tx-v5-path-review-cloud`; no local checkout or simulation artifact is written.
