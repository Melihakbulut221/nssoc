# Recheck completed native route without restarting CAD

Run39373842033 completed native routing, antenna repair, extraction and three-corner STA with native returncode0. Its original final audit failed on the literal prior-stage count150419 before comparing the saved ODBs. The failure and its original artifacts remain immutable.

The native reports record0 routing DRC markers,0 critical disconnected pins and2 final antenna nets/pins. Those remaining violations are not waived. The exact routed ODB is bde963927da325e3f66c1c62d6f78f5db4c60b1344670ebabd04d3339c1a5850. The exact pre-route transferred-clock ODB is c13a87d9127193482c96708e2f7bbdce8d83636fe4800876d9dbc14e89c6b23e.

This read-only cloud job restores both hash-pinned databases. The original complete before/after comparison and four faults remain byte-identical. The old count literal is replaced by the two exact ODB SHA256 assertions; every before-state cell, master, location, orientation, port, net and pin connection must still be retained, and only native antenna diodes may be added. A real topology or fixed-route change still fails. The original checker remains unchanged.

The same saved source also contains full routed STA and native SPEF/script proofs. The new report exposes those measurements even if topology validation rejects, marking them as diagnostic and retaining the rejection. It does not reroute, alter constraints, rewrite metrics, waive antenna violations or assert LVS/manufacturing/final timing closure.
