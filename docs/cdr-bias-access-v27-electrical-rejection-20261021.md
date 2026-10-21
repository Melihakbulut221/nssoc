# Actual v27 loaded full-wave rejection

Run39548690293 completed all original34.25ns/256bit captures with1104columns and113475rows per nominal case. The original maximum integration step remained0.3125ps; native warning diagnostics were empty. Both nominal cases were rejected. Existing100mV samples at0.3/0.6/0.9UI and37.5ps clock-to-valid gates were not relaxed.

Shortening only the8 BP/BN physical access resistors cleared the previously observed HBT VCE failures: every original device gate now passes. However the current candidate has substantial functional regression at C/D, so it cannot be accepted.

| Original gate | Early data | Late data |
|---|---:|---:|
| A below100mV /765 |97|112|
| B below100mV /765 |68|64|
| C wrong sign /765 |387|386|
| D wrong sign /765 |362|369|
| Phase mean |+104.674mV (wrong sign)|+108.745mV|
| VI mean |+234.608uA (wrong sign)|+239.785uA|

The upstream interface observations show C data and both select differential signals fail to cross zero in these complete native captures. This is a measured symptom, not yet a proven root cause. Reusing the physical master/slave graph and all original terminal probes, the new cloud diagnosis will locate the loss of steering and input transfer without rerunning or modifying the simulation. It independently reconstructs all120HBT bounds and all4 sampler checks from the retained raw data. A successful diagnosis is not electrical acceptance, closed-loop CDR, PVT, full PHY or mainchip closure.
