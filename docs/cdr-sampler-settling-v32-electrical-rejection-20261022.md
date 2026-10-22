# V32 measured electrical rejection

The complete nominal early and late captures in run [39743054879](https://github.com/Melihakbulut221/nssoc/actions/runs/39743054879) retain all 113475 rows and 1104 columns, the original 256 bits, 150 fF sampler load, 50 fF XOR load, 37.5 ps output deadline and original electrical gates.

Both nominal device checks now pass. Neither data nor phase acceptance passes. The resistor changes therefore fixed the observed nominal transistor headroom failure, but did not fix retiming.

| Case | A maximum delay | B | C | D | C wrong-sign samples | D wrong-sign samples |
|---|---:|---:|---:|---:|---:|---:|
| Early | 44.15625 ps | 41.40625 ps | 51.09375 ps | 54.53125 ps | 40 | 64 |
| Late | 44.53125 ps | 40.15625 ps | 49.84375 ps | 53.59375 ps | 32 | 64 |

C and D became worse than v31; retain this rejected experiment rather than calling it a settling improvement. Both phase averages remain below the unchanged 30 mV magnitude gate. Early VI magnitude is 48.9664 uA and fails 50 uA; late 54.5102 uA passes that individual gate.

The clock-stopped and VI-bias-off cases detected their faults. They do not accept either nominal capture. The next cloud diagnostic reproduces every original HBT and sampler check, then measures native master/slave input, clock selection and output behavior in these exact waveforms. It does not change the stimulus, phase, loads or thresholds.

## Other cloud work

PLL metadata-reconciliation controls39750435996 passed; exact native continuation39750949326 is running. Mainchip detailed-route continuation39738186533 is running. Transmitter diagnosis39748605114 reproduced all 604 HBT checks and all 85 failures; the output device's elevated emitter/return voltage needs physical routing analysis before a repair claim. None of these diagnostic or storage-control passes closes full serial PHY or final chip timing.
