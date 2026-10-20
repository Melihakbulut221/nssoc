# TX group234 plus physical final bridge: rejected full-wave comparison

Native run39376417214 at7c4591087991dadb503396935cf79eef7e94168c finished the
original34ns no-fault capture with returncode0, no solver diagnostic,76784 rows
and3008 columns. The bridge is the actual independently verified two-device
differential resistor/contact model, with its wire parasitics and finite body
contact. All original256bits, three sampling phases and device gates remain.

| Metric | Group234 without bridge | Group234 with bridge |
| --- | --- | --- |
| Wrong-sign output samples /768 | 83 | 87 |
| Output samples below100mV | 104 | 107 |
| Worst final selector active VCE | 0.356462V | 0.392282V |
| Worst final tail active VCE | 0.379985V | 0.380794V |
| Failed HBTs /604 | 6 | 6 |
| Failed MOS /512 | 0 | 0 |

The original0.4V device minimum still fails for all four final selectors and
both final tails. Upstream level4 still has153 wrong-sign interface samples
and2268 below150mV; level8 still has45 below150mV. Final input-interface
wrong-sign count remains567. Each aggregate interface covers6912 samples.

The actual bridge improves selector headroom but worsens final output errors.
It is not accepted and does not establish PHY functionality. Preserve both
candidate captures. Continue with the exact-capture path review39399643386 to
localize data arrival and device voltage failures before another circuit
change; do not lower the0.4V or signal thresholds or fit an output latency.
The swap-leaf-select fault job passed by detecting the injected fault, not
by showing correct nominal operation.
