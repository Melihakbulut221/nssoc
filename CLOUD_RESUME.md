# Cloud continuation — checkpoint v193

Updated: 2026-10-31T20:18:46.113018+00:00

The latest user instruction is cloud-only. Every test, simulation, CAD tool and native numerical analysis runs on GitHub. Local source authoring, static review and derived API text coordination use RAM only. Never acquire native project archives, models/SPICE, ODB/GDS, raw waves or native-frame gzip locally, even in RAM. The workspace and project temporary prefixes are empty; no local CAD processes. Preserve unrelated user files and original attachments.

## VI experiment completed; electrical closure remains open

[41235814518](https://github.com/Melihakbulut221/nssoc/actions/runs/41235814518), exact source 2ee31206416e6c8b1fe1bb19078fa815038f2644, completed all four jobs successfully. The original VI bias-off operating point and loaded transient ran from 19:52:05 to 20:08:04 UTC, return code zero, no backend diagnostics or terminal errors. Native data remain exclusively in releases 430148450 and 430148486. Root independently authenticated the 1,570,432-byte derived result, SHA 98ac478eb6ca175c9b403352030eb8dedb2a141025d975a9637b2337d36c775e.

The disabled tail currents measured -16.915247 nA and 104.733566 nA, compared with 251.980851 and 248.442788 microamperes in the matching nominal_late baseline. This specifically confirms the intended bias disable. The frozen generic fault predicate can also pass because data or VI already fails; it does not prove sensitivity against a healthy nominal baseline. Nominal device, data and phase gates remain rejected. The nine completed original cases were not rerun.

The exact current contract is 977 node-voltage vectors, 124 HBT collector-current vectors and 50 MOS drain-current vectors, totaling 1,151. The HBT limit is max(abs(Ic))/emitter_count < 3 mA. Earlier loose “Ie” terminology is superseded: raw emitter Ie and base Ib were not saved or qualified.

Matching nominal_late has four HBT minimum-VCE failures: T061 0.341252 V, T062 0.342447 V, T115 0.377900 V, T116 0.379080 V, against 0.4 V. These negative-clock hold-steering devices connect to the two eight-drain access clusters targeted by the physical candidate. Lower access resistance is a hypothesis to test, not a demonstrated remedy. Full sampler/XOR timing and voltage-margin failures also remain open.

## Physical checker dependencies closed; reuse existing generated layout

Original [41235314835](https://github.com/Melihakbulut221/nssoc/actions/runs/41235314835), source db7077a9495229ef444d1155aed687cfe374f9ae, generated eight Via2 cuts and eight Metal3 branches in 119.792 seconds, with exact structural reversal. Its GDS is 998,644 bytes, SHA 42ed5bcd567518786b718248947771172e9f5cc419d0aaa8fc8c49d8cfa4e876, cloud release 430145282. The frozen checker then failed at import on a missing SPICE dependency; DRC/LVS never executed. Preserve that failure and all 99 native outputs.

Complete source closure 1c3e1d5c03264647ebeb46881c3af421474b04ee passed hosted [41237175898](https://github.com/Melihakbulut221/nssoc/actions/runs/41237175898). The unchanged generated checker is 15,411 bytes, SHA 3ef6c47117a5467acc37ee4ea87af979a75e9be671cbf0a5153307974d082d66. Its closure includes nine imported and three additionally hashed Python files, seven SPICE files, two locks and 98 runtime decks. The actual import-to-first-command fixture passed seven missing-import, four missing-runtime and six external-effect/write controls, with 118 source reads. No native DRC/LVS ran in these controls. Root and both peer reviews passed.

fresh_rc_next_audit prepares a physical-only reuse adapter. Restore all 99 authenticated producer members at their original absolute runner path, retain result.json and all 20 input hashes unchanged, and copy the four layout files byte-identically to a separate recheck output. Keep the frozen validate_physical implementation, all 560 DRC rules, deep/flat 500-device LVS and 13 fault controls. Do not regenerate geometry. Own-source controls, full proof, review and a new independent empty exact-source destination must precede actual execution. Fresh RC and matching nominal_late simulation follow only after physical qualification.

## Mainchip readonly observation

The one actual observation [41236517605](https://github.com/Melihakbulut221/nssoc/actions/runs/41236517605), source 65e620dc413389fffaa8389e4abdfc17cfbf4ecf, is owned by mainchip_next_timing_audit. Root reserved public release 430152907 independently. Its 40 source controls and full-log prerequisite passed. Track the same execution to terminal and preserve complete command, supervisor, native and failure evidence. Do not duplicate or infer a phase from a redirected, opaque worker step.

The observer authenticates all 735 archive members, four selected inputs and the qualified analysis. It uses the exact frozen OpenDB runtime in the network-none 12 GiB container with 10 GiB process-group RSS and 2 GiB host-available guards. The readonly phase limit is 1,200 seconds. Observe all 434 Metal2 short markers and counterparts, exact DBU, complete transformed pins/vias/wires and independent terminal census.

The saved stale-wire-cleared.odb is preroute input and lacks iteration 10 mutable routes. Intersections are obstacle evidence, not a complete physical root-cause proof. Original route 41211382427 hit the 10 GiB RSS guard and produced no routed checkpoint. Preserve all 1,691 clock/fixed nets and use the observation to select a justified bounded routing change. Rerouting is not yet authorized by this observer.

## Acceptance and continuation

Full serial Gen3 x4 PHY, PLL/SERDES/TS/EQ/LTSSM, physical CDC and soc_top serial integration, final routing/setup/hold, RC min/max and production approval remain open. Keep UI 125 ps, sampler 100 mV/37.5 ps, XOR 100 mV/75 ps, HBT minimum VCE 0.4 V, maximum absolute VCE 1.6 V and VBE 1 V, actual Ic/emitter limit 3 mA, and PLL 62.5 ps. STA clocks remain 20/4/8/8 ns plus five percent, three PVT corners and zero setup/hold/slew/capacitance/fanout violations.

Monitor v193 tracks 505 handles every eight hours, read-only with automatic_native_dispatch=false. Earlier HTTP 502 is not claimed fixed. Use [skip ci], nonforce compare-and-swap updates and scoped Git trees.

Detailed state: docs/evidence/cloud-active-checkpoint-20261024.json
Immutable receipt: docs/evidence/cloud-collector-recipes-20261029/cloud-vi-terminal-physical-reuse-v193.json
