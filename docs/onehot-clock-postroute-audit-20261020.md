# Recheck completed native route without restarting CAD

Run39373842033 completed native routing, antenna repair, extraction and three-corner STA with native returncode0. Its original final audit failed on the literal prior-stage count150419 before comparing the saved ODBs. The failure and its original artifacts remain immutable.

The native reports record0 routing DRC markers,0 critical disconnected pins and2 final antenna nets/pins. Those remaining violations are not waived. The exact routed ODB is bde963927da325e3f66c1c62d6f78f5db4c60b1344670ebabd04d3339c1a5850. The exact pre-route transferred-clock ODB is c13a87d9127193482c96708e2f7bbdce8d83636fe4800876d9dbc14e89c6b23e.

This read-only cloud job restores both hash-pinned databases. The original complete before/after comparison and four faults remain byte-identical. The old count literal is replaced by the two exact ODB SHA256 assertions; every before-state cell, master, location, orientation, port, net and pin connection must still be retained, and only native antenna diodes may be added. A real topology or fixed-route change still fails. The original checker remains unchanged.

The same saved source also contains full routed STA and native SPEF/script proofs. The new report exposes those measurements even if topology validation rejects, marking them as diagnostic and retaining the rejection. It does not reroute, alter constraints, rewrite metrics, waive antenna violations or assert LVS/manufacturing/final timing closure.

## Actual saved-output result

[Read-only audit39382009151](https://github.com/Melihakbulut221/nssoc/actions/runs/39382009151) passed complete topology/geometry conservation and all four faults. The actual transferred-clock input contains150996 instances, explaining why the previous-stage150419 literal was invalid. All150996 original cells, masters, locations, orientations, ports, nets, NDRs and pins survive. Only26 antenna diodes were added. The fixed clock's actual routed geometry also matches exactly.

The saved native result has0 routing DRC markers and0 critical disconnected pins, but2 final antenna nets/pins remain. The [full audit receipt](evidence/onehot-clock-postroute-audit-pass-20261020.json) preserves exact source ODBs, all proof hashes and the original measured timing.

| Corner | Setup violations | Hold/min violations | Setup WNS(ns) | Hold WNS(ns) | Slew | Cap | Fanout |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| slow |9660|3|-15.803526|-0.513282|3693|734|2146|
| typical |7027|10|-6.502469|-0.425369|450|749|2146|
| fast |3151|20|-3.161320|-0.362347|91|767|2146|

Relative to the preceding routed result39331918238, fast hold/min violations fell95→20, typical17→10, and slow remains3. Fast setup violations increased3107→3151; slow/typical remain9660/7027. Antenna nets fell16→2. This tradeoff is retained explicitly: the clock intervention is not complete timing closure, and the setup regression is not hidden. Full setup, remaining hold/removal checks, transition/capacitance/fanout and antenna closure remain work.

Next work should use these saved reports and databases to identify the remaining worst paths and two named antenna nets. The original failed wrapper run remains preserved; there is no need to repeat its completed CAD solely to fix the bookkeeping check.
