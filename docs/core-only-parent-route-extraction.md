# Parent route extraction candidate

This runner restores the independently verified shell route from physical geometry run 44294471048 and extracts the actual parent-level wires using the pinned IHP nominal model and native OpenRCX. It checks SPEF capacitance conservation. It does not infer core-internal wires from a LEF abstract, invent core timing arcs, or claim min/max RC qualification. All production acceptance flags remain false.

Next: inspect native logs, audit SPEF net and terminal coverage against the exact ODB, and only then use the result in scope-limited shell timing diagnostics. Complete core routing, native extracted timing, routed boot, full GDS/LVS and foundry qualification remain required.
