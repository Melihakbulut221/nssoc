# Actual v28 loaded full-wave rejection

Run39562531785 completed both nominal34.25ns/256-bit/1104-column captures with the unchanged0.3125ps maximum integration step. Native simulation completed without warnings. Both nominal cases failed the original electrical gates; clock-stopped and VI-bias-off controls detected their intended faults. Control detection is not nominal device acceptance.

| Measured gate | Early | Late |
|---|---:|---:|
| A wrong sign /765 |0|0|
| B wrong sign /765 |0|0|
| C wrong sign /765 |14|1|
| D wrong sign /765 |74|64|
| Phase mean |−12.902mV|+16.682mV|
| VI current mean |−39.995uA|+48.910uA|
| Worst original clock-to-valid |59.219ps|54.844ps|

The input resistor geometry change substantially reduced C/D polarity errors relative to v27, but the unchanged100mV and37.5ps output gates and30mV/50uA phase/current gates still fail. HBT xd0105/xd0106 also fall below the original0.4V VCE floor (about0.389/0.391V in late capture). No threshold has been relaxed.

The new cloud-only diagnosis reconstructs actual master/slave topology, every physical selector combination, all120 HBT bounds and all4 sampler checks from the saved native waves. It uses the exact v28 GDS-derived device locations and actual17674R12694C model. A successful diagnosis does not accept the circuit. Select the next geometry change from measured loading/steering/headroom evidence; do not replace real drive by ideal waveforms. Full closed-loop CDR, serial PHY and mainchip timing remain open.
