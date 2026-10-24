# Require exact external pins in addition to native LVS

Run39465250247 fixed the original annotation problem: full native DRC has zero markers; deep and flat LVS both match all8074 devices, with163 correctly named external ports. Actual open/short/wrong-width/offgrid controls reject. The source is not accepted yet because the new extra-internal-port control unexpectedly passed the native comparer.

The actual fault GDS extracts164 public ports, withD0P extra, while the nominal GDS and reference both have exactly163 matching names. The native deck declares success for this single extra port. That result is preserved; it is not reclassified as a native rejection.

A separate mandatory exact-interface gate now compares the complete extracted top-subcircuit pin list against the original163-pin reference, disallowing missing, extra, duplicated, renamed or aliased names. Both positive deep/flat cases must pass this gate and every original native gate. The real164-pin fault must fail the independent interface gate; native circuit comparison success remains visible. Synthetic parser controls cover all five corruptions and case-insensitive SPICE names.

The generator, GDS geometry, reference, native DRC/LVS decks and original open/short/device/offgrid controls are unchanged. This strengthens the parent interface contract; it is not a waiver of a native mismatch. Fresh whole-parent RC and original complete electrical tests remain mandatory.
