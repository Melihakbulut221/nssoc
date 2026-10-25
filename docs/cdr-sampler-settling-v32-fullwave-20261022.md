# v32 full loaded native electrical tests

Run original nominal early/late, stopped-clock and disabled-VI-bias cases only after exact fresh v32 audit/composition39742448854 succeeds. No test waveform, device or electrical acceptance gate is relaxed. All476 native devices,17918R,12850C,1104 waveform columns and the full256-bit transient remain included.

The v32 physical sampler changes target headroom and settling. These full tests must measure whether those changes actually help; physical/capture success alone establishes no such improvement. The prior v31 failures remain retained.

Passing these externally clocked loaded cases would still leave recovered-clock closed-loop, PVT, complete serial x4 PHY and mainchip final timing open.
