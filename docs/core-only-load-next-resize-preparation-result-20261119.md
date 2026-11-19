# Two remaining slew-driver resize preparation — 2026-11-19

Preparation run: https://github.com/Melihakbulut221/nssoc/actions/runs/44505868283
Source head: `2f8f9bbde7acaea4208e4f2f23c8b5ee073a48cf`; attempt 1 succeeded.
Artifact 14518854658 SHA256 `243b14e961d165d81124ec57e503af59e6e6bbf2e6a5398180c013ae6dc0623d`; all 17 output hashes verified independently in memory.

Resized 61007 nor3_1 to nor3_2 and 63722 a21oi_1 to a21oi_2. Placement moved only these two cells (1.92 and 5.7 microns). 106656 instances retained. Connections, all other cell geometries, diode cells, power geometry, ports and die preserved. Four positive supply-terminal contacts passed, including synthetic negative tests and native rail-removal detection.

The preparation preserves 103082 DEF records (including two supplies) and all 2113 clock nets. Eight incident signal nets require rerouting: net2151, net2774, nssoc_sta_n_18115, nssoc_sta_n_28565, nssoc_sta_n_60087, nssoc_sta_n_60783, nssoc_sta_n_62749, nssoc_sta_n_63198.
Candidate ODB: `756fdc34ff3710eaf3341548c9c06815866d76ce5215c60e87c511eefddd6286`.

The next isolated experiment routes only those eight nets, fixes encoded paths of all other routed nets during DRT, restores their route status, checks exact unaffected DEF records, clock routes, NDR assignments/rules, connectivity, geometry, DRC and antenna. It must pass before fresh RC and all-corner STA. No timing benefit or production closure is claimed. 50 MHz and derating remain unchanged. Package/PCB and external devices remain unselected; external I/O signoff is open.
