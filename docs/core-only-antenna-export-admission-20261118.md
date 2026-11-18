# Antenna netlist qualification and extraction continuation — 2026-11-18

## Verified native export

Native export run [44385801058](https://github.com/Melihakbulut221/nssoc/actions/runs/44385801058) at f35a79dec5bb998eb88de851d6be0c0808075cee passed. Artifact 14466022194 SHA-256 2e6196a75cfad112e7acdb775895e0fb1936615d92424b84160947a711a38de0; archive and all declared output hashes verified. All 800 added diodes are present, with no duplicate instances or signal-connection mismatches.

ODB SHA-256: 2147b6df67feac28691ca76defdd7d3cafd4df1c00a74c0043fcd55f47767750.
Native exported Verilog: 012c7ed722b8ea78d78a22b2130ff323f5e27fb7ec773d99acd09d98ad69f337.
Native exported DEF: 4f6e4f796ba77cee725722311e51fc1cd6d268674fa0653d9a8b82916fe4c39a.

The preceding failure 44384960280 was a checker error: two legal escaped Verilog identifiers were compared without decoding. The native exports are byte-identical before and after the checker fix. No design connectivity was altered to make this check pass.

## Indexed checker qualification

Run [44386791996](https://github.com/Melihakbulut221/nssoc/actions/runs/44386791996), head b43b152b120b4e38d698d8dcb184fb39faf91926, passed 12 parser/fault tests and the authenticated actual netlist/inventory comparison. Artifact 14466647393 SHA-256 ca08f30ce6e38d33436dbc5423c32a1412b1baa989c8aa43677e41e6db0fba46. The measured parse/check duration was 0.257309146 seconds; this is not the whole CI job duration. The checker indexes matching cells once instead of rescanning the entire file for each diode. All 800 signal connections matched, with zero missing/duplicate diodes.

## Exact next step

Continue watching reroute 44383558280/head b42104b780290a762ecf705e0741af846db8d43b. It was still active when this checkpoint was written. Do not launch another route merely because no terminal result is available.

Use immutable tag cloud-core-antenna-extraction-v4-20261118 for the next RC/STA job. It is staged, not dispatched. Authenticate the completed successful route and its output artifact digest before dispatching cloud-evidence-summary.yml with route_artifact_id and route_artifact_digest (including sha256: prefix). All earlier post-antenna extraction tags are superseded.

The v4 script retains exact route, power-contact and export-test admissions, exports fresh views from the routed ODB, rechecks the 800 added diode connections, requires 106051 valid instance names, clears inherited SPEF/SDF/lib/pnl/timing metrics and performs nominal extracted-RC STA in slow/typical/fast corners at the unchanged 20 ns clock and 5% derate. Fresh timing and annotation reports still need inspection. Qualified RC min/max, SRAM signoff, pad timing, full-chip LVS and production approval remain open.
