# Cloud progress: exact mainchip dependencies and full-column PLL

The mainchip dependency package passed on run 39635867954. It contains 5,030 original input files (1,173,231,506 bytes), the separately bound runtime SDC, the unchanged candidate ODB/netlist/SDC, original raw and complete resolved configuration, and independently verified files from five SHA256-pinned upstream PDK archives. This repairs the prior packaging failure; it is not routed timing acceptance.

The same whole845 physical PLL process advanced from 724.593593750 ns to 820.364372710 ns on run 39602655093. All 5,106 original columns remain. The checkpoint preserves 2,626,323 complete rows plus the actual partial row. The old payload and protected inputs remained unchanged. Native execution ran for 1,800 host seconds, then saved for the next hosted stage. Full1us capture and original final-window acquisition/device-safety checks remain open.

The measured shared filesystem had 21,102,059,520 bytes free at checkpoint, with the original 12GiB native reserve still enforced. Full remaining capacity is not proven. The next stage must retain the same disk guards and preserve the process if capacity becomes insufficient. No vector, timestep, solver, gate or waveform byte may be discarded.

The next PLL descriptor is in the receipt. Mainchip ninth continuation 39631640578 and power128 TX continuations 39630182787/39630188922 remain independent live jobs. Do not cold-restart or fork them.
