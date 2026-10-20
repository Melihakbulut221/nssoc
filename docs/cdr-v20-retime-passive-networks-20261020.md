# V20 native latch evidence and next physical path measurement

Both native latch diagnostics in run39430120656 passed reproduction of all116 HBT checks and all4 sampler checks from the original rejected captures. They locate two distinct problems:
- At +0.3UI, A/B slave inputs have the correct sign and at least165mV, but their slave outputs still violate the original100mV/settling gate.
- At +0.3UI, C/D master inputs have small signed margins (early minimum C2.3mV, D-0.2mV; late C4.0mV, D3.4mV). All255 observations per sampler remain below the internal100mV diagnostic marker. This internal marker is not an acceptance requirement.

The earlier v16 passive diagnosis found substantial distributed conductor capacitance, and its v17 intrinsic-divider rebalance worsened C/D. Do not repeat that rejected hypothesis as a proven fix. The new cloud measurement restores the actual v20 composed wire graph and physical native devices, and measures collector/filter/base metal paths separately from intrinsic rppd/MIM elements. It retains the original topology mutations, KCL checks and passive solver controls; it does not infer transient timing from a scalar RC product.

Use current geometry-bound R/C and latch observations to choose routing/placement or drive repair, then rerun complete physical/extracted electrical gates. All current nominal captures remain rejected; no fullPHY or closed-loop claim is made.
