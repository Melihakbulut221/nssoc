# Native routed data-net geometry — 2026-10-19

[Run39241091888](https://github.com/Melihakbulut221/nssoc/actions/runs/39241091888)
passed on sourceaf374dc465d190c0bce30b65a46ea22a76283ce5. It read the exact
148832-instance routed database (147858 retained cells plus974 route-added antenna diodes) of run39202263552 and all three original
maximum-path reports. Native pin-key uniqueness, INPUT sink role, exact
reported fanout and unchanged-source byte checks passed for39 selected nets.
Alias-proxy controls ensure the driver is not counted as a sink.

| Native driver suffix | Master | Total routed wire (um) | Driver-to-sink Manhattan (um) | Actual sinks |
|---|---|---:|---:|---:|
|1834059|nand4_1|2375.000|290.505|1|
|1824966|o21ai_1|2073.740|979.113|1|

The first is on the worst typical/fast PCIe output path; the second is on the
worst slow path. Their measured native loads/delays are preserved with every
corner witness in the full receipt. Total routed wire length is not a measured
individual RC branch delay. The geometry establishes long routed connections;
it does not alone identify obstacles, congestion or the best buffer site.

Next repair: inspect the available legal sites/route obstacles around those
drivers and evaluate positive buffering to isolate weak gates from heavy
wire loads, or a shorter route where physically legal. Keep all original
clock constraints and native logic proofs. Any candidate still requires new
routing, extraction, three-corner setup/hold and electrical checks, antenna
checks and full-chip verification. No layout or gate was changed by this run.

The first diagnostic39240031550 is retained as rejected because Python proxy
comparison added the driver to the sink list. The second39240623218 failed
because the pinned dbITerm binding lacks getId(). The accepted diagnostic
uses the already verified native(instance name,MTerm name) pair and proves
its uniqueness. It supersedes those diagnostic reports, not the timing result.

All work and published evidence are cloud-only. This is not PHY/timing signoff.
