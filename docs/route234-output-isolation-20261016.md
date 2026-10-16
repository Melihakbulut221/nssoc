# Five output buffers for unavailable drive strengths

The actual234 routed source and all-endpoint sizing screen38917800540 found
five requested stronger gates absent from the source library: nand4_2,
two nand3_2 and two a22oi_2. Their existing weak output gates each drive one
long loaded net. Prior source146 paths identify the nand4 stage at approximately
3.116ns slow delay and0.212pF load; those values are historical diagnosis,
not a claim about the currently running nine-size candidate.

This cloud experiment inserts five actual sg13g2_buf_4 cells near those exact
five source234 output pins. It preserves all114025 original cell locations,
orientations, masters, every existing sink and all PG geometry/NDR/boundary.
Only each selected driver's output moves to its new local input net, and the
buffer drives the original net. Native detailed placement may move only these
five added buffers, within50um per axis, with final input Manhattan distance
at most100um. All new PG terminals connect to the corresponding source driver's
actual power nets. Exact net membership and wholechip restricted Liberty logic
must agree; real buffer-input disconnection and an actual output inversion
must fail. No timing exceptions or RTL behavior are changed.

The original five detailed routes are explicitly invalidated because their
driver terminal changed. This proposed database is therefore UNROUTED and is
never backannotated with stale SPEF. A placement/logic pass only proves this
alternative can be implemented. It does not prove improved setup, safe hold,
antenna closure, DRC/LVS or PHY acceptance. The five drivers' all-reachable
source234 hold margins are preserved from the source-bound screen; they are
not substituted for post-change timing.

The active nine-size physical run38925935829 remains intact. Before combining
these buffers with it, inspect its actual result, rebind the new source database,
repeat topology/placement/logic proofs, reroute/reextract and check all22544
endpoints/135264corner-delay rows plus independent geometry/annotation.
