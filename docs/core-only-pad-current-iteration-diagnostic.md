# Pad current diagnostic continuation: iteration limits

The package, PCB, attached devices and external interface speeds are not selected (user confirmation). External I/O timing and load signoff remain open. Internal routing and timing work continues independently.

Run 44367854354 failed for all 0/1/10 ohm fixture variants. The 0 and 1 ohm captures stopped near 22.7529 ns; 10 ohm near 22.7531 ns. Native Gear order 2 was confirmed. None reached the mandatory 50 ns capture. No result closes the pad slew violations.

This diagnostic keeps the ideal 1.5 V clamp, pinned schematic/models, supplies, temperature, Gear2, 5 ps step, DC operating point and default error tolerances. Only the transient Newton iteration ceiling changes from 10 to 100 or 1000. Each ceiling must be confirmed in the native post-transient options readback. Both data states and enabled/disabled controls must complete. Diagnostics and truncated captures remain fatal. A successful run alone would still require step convergence, physical parasitics and Liberty/model review; it is not production approval.

Core detailed route 44337630426 remains independently running and is not cancelled or replaced by this diagnostic. Preserve its exact head 19924a826cfca054f30f19cdde091fbe6c744960. After admission use the staged post-ECO extraction branch.
