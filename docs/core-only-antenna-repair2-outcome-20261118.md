# Second antenna repair outcome — 2026-11-18

[44388764024](https://github.com/Melihakbulut221/nssoc/actions/runs/44388764024), head 9eda08b7e6a8dc2dc79807245ba3a637630e8db8, failed the zero-antenna gate after native routing returned 0. Artifact 14468701486 SHA-256 2bd46705a4ab1c9a0a49edacdbad7955cbc8e94e0eb1bbde5d1d9d4eea9c53a8 and every declared output hash verified.

29 additional SIGNAL-net antenna diodes were inserted, for 106080 total instances (829 added across the two rounds). All existing instance geometry/status/masters and terminal connections were preserved. All 58 new supply terminals have verified local same-net rail contact, with no wrong-supply contacts. The new insertion ODB SHA-256 is 857de2e2918128b5bbf6fa3932c008a165c5375c6f954c9904ecaf4c977adad6.

Routed ODB SHA-256: 761ee985d5180b9d4e206eb1bb970d7b3939c0875cc6ac00a1c1caf12be4a4df. Native DRC=0; antenna violating nets=2 and pins=2 (previous round 17/19; original 363/399). Exact identity was preserved during rerouting. The visible wire/via/LEF audit reported zero disconnected signal nets, unwired multi-terminal nets, missing terminal geometry and inter-net contacts, with negative controls passing. Native routing took approximately 6m56s; the complete job also includes download, insertion and independent geometry audits.

Third repair source is staged/dispatched under cloud-core-antenna-repair3-20261118. It admits only the above exact failed-but-measured candidate, keeps all original identity and local-power checks, and retains the same 10% antenna-repair planning margin. That margin does not relax foundry antenna rules or timing constraints; final acceptance still requires zero native DRC and zero antenna violations. Do not use this 2-net candidate as a successful extraction source. Old extraction-v4 still binds the first failed route and is superseded pending a new successful-route admission.

Full chip GDS/transistor LVS, extracted timing, qualified RC and production approval remain open. The separate native diode derivative experiment is 44391317766/head d70786a5925f585719fa3f7fedcf6fbd36ef97cc and was still active at this checkpoint.
