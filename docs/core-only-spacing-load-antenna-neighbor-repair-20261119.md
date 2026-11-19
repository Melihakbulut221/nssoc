# Antenna-clean load route rejected for neighbor contact — 2026-11-19

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44495727137 failed independent geometry verification, head e9c44f26e4d2eee8f0f41a8ddffc7fc914074bd7, attempt 1.
Artifact 14516206242, SHA256 1bd5f3f358aee5c976b96b3c77053a7415a455b91d1d81b38bfa245d357f0678. All 50 output hashes verified.
Routed ODB: c5236f72fc54ce6860e10a50c83bd6c36c8dad519cf43ddc5e4be2594c043ea1.

DRT reported zero violations at iteration 23. Antenna net/pin violations are now zero, and antenna.rpt is empty. All 106656 instance identities and terminal connections passed preservation, as did 103087 unselected non-power nets and all 2113 clocks; 102971 encoded fixed paths were checked before routing and restored afterward.

Nevertheless independent native geometry found three Metal2 contacts between nssoc_slewiso_1_net and nssoc_sta_n_55301 near x=2969.76 um, y=984.48 um. No disconnected signal geometry, unwired multi-terminal nets or missing terminal geometry were reported. The three contacts are sufficient to reject this candidate: native DRT zero is not complete physical clearance.

The next candidate restarts from the verified preparation run 44494801363 (ODB 44e5b8fe6d989394000395ca7449744007dc812710149bc856efaa6172aad9d4), adding only nssoc_sta_n_55301 to the allowed route set. Route preservation must cover the other 103086 non-power nets and all clocks. The insertion audit still uses the stricter one-net allowance. All identity, power, NDR, DRC, antenna and independent geometry checks remain mandatory. Timing constraints and derating are unchanged. Fresh RC/timing and production signoff remain open.
