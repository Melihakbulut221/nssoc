# Follower v23 electrical result

Run 39479905700 completed both nominal cases as electrical failures. Clock-stopped and VI-bias-off fault cases passed. All original complete 256-bit waves, 150fF sampler loads, 50fF comparison loads, phase/data/current/headroom thresholds remain unchanged. This is not an accepted CDR or full PHY.

Late data sampler C improves from 117 wrong samples in v22 to 33 in v23, and D from 181 to 96, but they still fail. Late A/B maximum clock-to-valid are 44.219ps/39.531ps; C/D are 49.219ps/56.406ps, all above the original 37.5ps requirement. Phase output is +17.648mV late and -13.197mV early, below the required signed 30mV. Two HBTs fall below 0.4V active VCE (late minimum 0.393550V); these are retained as failures.

A new cloud-only read of the already archived native waves reconstructs actual master/slave topology and data/clock transfer for all four samplers. It must reproduce all 120 HBT measurements, including the two original headroom violations, and every original sampler result exactly. It identifies the physical owners of the violating HBTs. It changes no waveform, circuit, sampling phase, or acceptance gate, and is diagnosis only.
