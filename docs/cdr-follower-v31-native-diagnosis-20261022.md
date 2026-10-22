# CDR v31 rejected full capture diagnosis

The full early/late native captures in run 39723936059 remain rejected. All 256 input bits, 1104 original waveform columns and original timing, loading and device gates remain in force.

This workflow reuses those immutable captures. It reconstructs actual master/slave latch graphs, reads every physical parallel clock selector and measures the real retimer follower base/emitter voltages and currents. It reproduces both original HBT failures (xd0105/xd0106), all original sampler failures and full capture identity before publishing observations.

The v30 diagnostic is frozen. An exact source-delta checker limits the v31 adaptation to source identities and the actual observed two-device failure set. Passing this diagnostic is not electrical acceptance, a recovered-clock test, complete PHY qualification or chip timing closure.

All execution and retained artifacts are GitHub-hosted.
