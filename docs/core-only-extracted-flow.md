# Core-only detailed routing and extracted timing adapters

These adapters prepare the retained core for actual detailed routing and nominal OpenRCX/standalone OpenSTA. They do not launch a route or prove physical closure. The running zero-fanout repair is left unchanged.

`core_only_detailed_route_flow.py` retains the existing guarded propagated 20 ns / 5% derate detailed router, orphan-guide cleanup, antenna check and disconnected-pin report. `core_only_routed_extraction_flow.py` reuses pinned nominal OpenRCX rules and SPEF integrity checks, but replaces the obsolete four-clock requirement with exactly one propagated `clk_i` at 20 ns and 5% derate. It rejects the OpenROAD estimated-parasitics branch and requires standalone OpenSTA plus SPEF. Reporting-label correction does not change clock propagation. Missing or changed native Tcl anchors fail closed.

Qualification executes negative clock/derate/engine cases in Tcl and imports both flows in the pinned native runtime. This is guard and import qualification only. Actual routed database/SPEF execution, route connectivity, annotation completeness, RC min/max qualification, timing, electrical checks and manufacturing signoff are still required. Inherited nominal RC rules are not qualified min/max extraction. The SRAM fast model temperature remains a separate qualification issue.

Do not use legacy multi-clock extraction adapters unchanged for the core-only release. Do not merge legacy PCIe/Ethernet clock constraints back into this release.
