# CDR v39 actual follower and latch diagnosis

Four completed v39 trials changed retimer pull-down lengths to1.8/1.5um while retaining v37cdbias15's6um input bias resistors. All four native captures completed but failed the original data/phase gates. Fewer wrong signs alone does not prove a repaired data path.

This hosted analysis reads each original113475x1104 waveform and exactly reproduces all120 HBT checks and all four complete sampler results before additional observations. All76 declared primitive parameter changes must reverse to the original476-device contract with identical topology, native references and other parameters. It retains all17918R/12850C, original150fF/50fF loads,256bits and original8GHz clock/gates. There is no new SPICE run or wave replacement.

The existing qualified observation code measures real AC/BD follower collector-current distributions, base/emitter common mode and differential amplitudes, C/D input-divider terminal voltages, master/slave headroom, current-steering transitions and per-bit settling. Its equations and negative controls remain unchanged; only immutable capture bindings and report paths are adapted. Compare with the already completed v36/v37 observations39867076460, rather than rerunning their simulations.

These source-bound measurements distinguish an intended current increase from observed current and expose common-mode/headroom tradeoffs. They do not make a failed candidate acceptable or establish causation from correlations. All four raw captures and rejection results remain in cloud releases. No candidate geometry, new PEX, recovered clock, x4 or final timing acceptance is claimed.
