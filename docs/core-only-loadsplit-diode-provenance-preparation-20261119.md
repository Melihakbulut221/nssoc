# Load-split diode provenance preparation — 2026-11-19

The 21-buffer preparation moves 44 antenna diode signal terminals. The new helper admits only the explicit per-cell source/destination map. All moved diodes must exist in the cumulative inventory; missing inventory fails closed. It preserves input evidence, power terminals, and unrelated cells. Export verification checks each moved diode, including missing, duplicate, or stale connections.

The cloud test exercises synthetic invalid evidence. It does not admit the running route, prove actual inventory coverage, or establish timing/production signoff. The actual preparation audit and fresh netlist must subsequently pass this helper, together with route geometry, antenna, power, identity and preservation gates.

Source baseline: `d800be2ea61e39adef89e58c075591d77f71773e`. Running physical route: https://github.com/Melihakbulut221/nssoc/actions/runs/44562378599. This separate test does not modify or restart that run.
