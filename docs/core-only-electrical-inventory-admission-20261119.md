# Electrical inventory report admission — 2026-11-19

Read-only inventory uses combined route 44446105491 and matching extracted STA 44448236669. The exact timing subset was collected in run 44452987978, artifact 14496057491, SHA256 18d5eb5a4d9e14f0c03302607a6374d9493bc4c129e48aa1880f93079ec289d0. All 63 subset outputs and 134 source outputs were verified. This precedes the two common setup-driver resizes; it does not measure their result.

Initial mapping run 44453346384 failed closed before native inventory: its parser counted only 130 of the 210 fanout violations in each corner. The report contains 80 additional rows with limit 8, actual 9 and `(VIOLATED)`, but a blank slack column. Preserve those rows with `slack: null` and `slack_printed: false`; do not fabricate reported slack. Malformed rows, missing numeric fields for other check types and count mismatches remain fatal. Expected counts stay slow 502 slew / 210 fanout / 52 capacitance, typical 4 / 210 / 54, fast 0 / 210 / 60.

Next map every pin to native nets, output drivers, functional input loads and antenna diode loads. Keep SRAM outputs, clocks and ordinary signal drivers distinct. Resizing does not by itself resolve excess fanout or a fixed macro output-capacitance limit; load splitting requires routed and all-corner verification. No constraints or violations are waived.
