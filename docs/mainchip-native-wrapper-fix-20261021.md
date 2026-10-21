# Exact native parasitic-mode override diagnosis

Native run 39667104303 reported OpenROAD revision dcf36133a369abc8f3c5e5738cd4d82e4903c0e0.
It reproduced the six original routed slacks, then failed RSZ-0074 (3/4 loads)
after 19 reported setup resizes. The partial setup ODB/netlist is preserved.
The estimates in that attempt do not prove physical improvement.

At this exact upstream revision, Resizer.tcl repair_timing lines 345-348
forcibly sets detailed_routing whenever design_is_routed is true. This undoes
the prior explicit placement estimate and invokes makeBufferedNetGroute again.

The correction creates a separately named candidate-only procedure. At runtime
the entire native procedure body and argument list must match a frozen exact
upstream reference. Only the forced model-selection block is replaced with
explicit placement mode. The original repair_timing procedure remains untouched;
there is no replacement of design_is_routed, no disabled route check, and no
removed timing gate. Every argument parser, limit, constraint and native C++
setup/hold optimizer call is retained. Both actual runtime bodies are saved.

A changed-gate negative control must fail identity. Baseline SPEF measurements,
clock periods, uncertainty, derates, functional and physical proof requirements
remain unchanged. Estimated candidate timing is never final timing evidence.
Fresh routing, extraction and all-corner setup/hold checks remain mandatory.

Source: https://github.com/The-OpenROAD-Project/OpenROAD/blob/dcf36133a369abc8f3c5e5738cd4d82e4903c0e0/src/rsz/src/Resizer.tcl#L345
