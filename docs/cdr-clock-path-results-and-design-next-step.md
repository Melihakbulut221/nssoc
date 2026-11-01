# Clock path diagnosis: measured result and design consequence

Read-only run41271280278 (source45286428f2d9a5dfcf6781ef04f1bb61cd20def8) completed successfully. Complete31-file proof: docs/evidence/cdr-clock-path-diagnose-41271280278. Native wave/archive stayed on GitHub.

The unchanged original reader and diagnostics reproduced all124 HBT metrics, all six stage metrics and1530 per-bit settling values, plus phase/VI. The new analysis retained all32 physical clock devices/eight shared emitter groups, four cp/cn terminal-pair combinations per group, both clock directions and255bits. All local crossing windows were unique.

Measured internal clock delay is relative to the already-loaded cp/cn boundary ports, not the ideal source. Representative pair extrema range from1.9544750519272536ps (B preceding group$318) to4.063760328786802ps (C output group$683). Therefore this result alone must not be used to claim that the entire clock path consumes only2–4ps.

The first rising edge demonstrates the distinction:
- nominal edge2.1875e-9s;
- actual loaded external crossing2.1985014172157795e-9s;
- A output clock pair101/97 crossing2.2017799491419757e-9s;
- original A deadline2.225e-9s;
- original A bit1 settling delay44.21874999999147ps relative to nominal;
- recorded settling-minus-local-clock29.93880085801587ps;
- signed A margin at the unchanged deadline0.03454877699928918V.

These are one-bit examples, not whole-run extrema. The full result retains every external edge and every original sampler bit for a complete cloud-only aggregation. Stable bits can already be valid before a clock edge and thus have negative settling-minus-local-clock; those values are not negative physical cell delays and must not be discarded or interpreted as such. Separate toggling/stable cases transparently if useful, without dropping any gate checks.

Native topology links are A:$485(output)/$482(preceding), B:$321/$318, C:$683/$680, D:$133/$149. Original testbench includes10ohm source resistances on cp/cn and unchanged150fF loads at sampler observation points. Those are part of the qualified workload; lowering source resistance, dropping output loads or shifting deadlines is not a demonstrated repair.

Next design work must consider the loaded external clock path and internal regeneration/loaded data path together, while resolving the separate coupled headroom failure. A physical clock-buffer or output-buffer topology would require real new devices/routing, complete device/vector coverage, unchanged functional/stress gates and fresh PEX. No such topology has yet been implemented or accepted. The prior four-shunt candidate remains rejected. Full PHY, routed mainchip and final setup/hold remain open.
