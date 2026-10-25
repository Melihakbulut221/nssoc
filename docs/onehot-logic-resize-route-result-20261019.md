# Measured logic-resize route result — 2026-10-19

Run39202263552 completed routing, fresh native RC and original three-corner STA.
It is **not timing closure**. Native routing DRC and critical disconnected pins
are0;32 antenna nets remain. All original clocks/derates and source/topology
proofs were retained. Full source report and immutable asset hashes are in
[evidence](evidence/onehot-logic-resize-route-result-20261019.json).

| Corner | Setup count | Worst setup ns | Hold count | Worst hold ns | Slew count | Cap count |
|---|---:|---:|---:|---:|---:|---:|
| slow1.08V125C |9708|-20.186431|4|-0.460968|4060|819|
| typ1.20V25C |7864|-8.403845|9|-0.399642|737|826|
| fast1.32V-40C |3808|-4.732550|21|-0.350979|211|843|

Compared with the prior routed candidate, slow worst setup and hold counts
improved, but typical/fast worst setup and several electrical counts regressed.
The32 resized cells do not establish an acceptable final candidate. Existing
failed results remain preserved. The next cloud job reads the exact saved
native max/min/check/clock reports, compares original metrics, and exposes the
new limiting paths before any further physical ECO. It does not reroute or
change constraints. Full transistor LVS/RF/body PEX/signoff are separate proofs.
