# Cloud continuation — checkpoint v194

Updated: 2026-10-31T20:46:44.824068+00:00

The latest user instruction is cloud-only. Every test, simulation, CAD tool and native numerical analysis runs on GitHub. Local source authoring, static review and derived API text coordination use RAM only. Never acquire native project archives, models/SPICE, ODB/GDS, raw waves or native-frame gzip locally, even in RAM. The workspace and project temporary prefixes are empty; no local CAD processes. Preserve unrelated user files and original attachments.

## VI experiment completed; electrical closure remains open

[41235814518](https://github.com/Melihakbulut221/nssoc/actions/runs/41235814518), exact source 2ee31206416e6c8b1fe1bb19078fa815038f2644, completed all four jobs successfully. The original VI bias-off operating point and loaded transient ran from 19:52:05 to 20:08:04 UTC, return code zero, no backend diagnostics or terminal errors. Native data remain exclusively in releases 430148450 and 430148486. Root independently authenticated the 1,570,432-byte derived result, SHA 98ac478eb6ca175c9b403352030eb8dedb2a141025d975a9637b2337d36c775e.

The disabled tail currents measured -16.915247 nA and 104.733566 nA, compared with 251.980851 and 248.442788 microamperes in the matching nominal_late baseline. This specifically confirms the intended bias disable. The frozen generic fault predicate can also pass because data or VI already fails; it does not prove sensitivity against a healthy nominal baseline. Nominal device, data and phase gates remain rejected. The nine completed original cases were not rerun.

The exact current contract is 977 node-voltage vectors, 124 HBT collector-current vectors and 50 MOS drain-current vectors, totaling 1,151. The HBT limit is max(abs(Ic))/emitter_count < 3 mA. Earlier loose “Ie” terminology is superseded: raw emitter Ie and base Ib were not saved or qualified.

Matching nominal_late has four HBT minimum-VCE failures: T061 0.341252 V, T062 0.342447 V, T115 0.377900 V, T116 0.379080 V, against 0.4 V. These negative-clock hold-steering devices connect to the two eight-drain access clusters targeted by the physical candidate. Lower access resistance is a hypothesis to test, not a demonstrated remedy. Full sampler/XOR timing and voltage-margin failures also remain open.

## Physical checker dependencies closed; reuse existing generated layout

Original [41235314835](https://github.com/Melihakbulut221/nssoc/actions/runs/41235314835), source db7077a9495229ef444d1155aed687cfe374f9ae, generated eight Via2 cuts and eight Metal3 branches in 119.792 seconds, with exact structural reversal. Its GDS is 998,644 bytes, SHA 42ed5bcd567518786b718248947771172e9f5cc419d0aaa8fc8c49d8cfa4e876, cloud release 430145282. The frozen checker then failed at import on a missing SPICE dependency; DRC/LVS never executed. Preserve that failure and all 99 native outputs.

Complete source closure 1c3e1d5c03264647ebeb46881c3af421474b04ee passed hosted [41237175898](https://github.com/Melihakbulut221/nssoc/actions/runs/41237175898). The unchanged generated checker is 15,411 bytes, SHA 3ef6c47117a5467acc37ee4ea87af979a75e9be671cbf0a5153307974d082d66. Its closure includes nine imported and three additionally hashed Python files, seven SPICE files, two locks and 98 runtime decks. The actual import-to-first-command fixture passed seven missing-import, four missing-runtime and six external-effect/write controls, with 118 source reads. No native DRC/LVS ran in these controls. Root and both peer reviews passed.

Actual physical-only recheck [41238994098](https://github.com/Melihakbulut221/nssoc/actions/runs/41238994098), source 0b1ec86b35f8cb98928a5687f007a7ccd676f620, completed all three jobs successfully. Full 560 DRC rules reported zero markers; deep and flat LVS matched 500 devices, and all 13 fault controls passed. The physical report is 86,874 bytes, SHA 82dd30f99bc7b7bd430e0f2ac94c5d026ef8ecb2085166778ab367a94f909d94. Root independently reserved empty public release 430168624 with its exact lightweight source tag at 20:30:09.107852 UTC. Same-run source controls and full-log prerequisite passed. The complete 172-member output archive remains exclusively in the cloud; all three full job logs, 120 native-derived records, 14 admission records and the complete 181-file terminal proof plus five-file independent reservation proof are preserved. No new geometry, RC or wave simulation ran, and electrical/full-PHY/timing acceptance remains false.

The adapter restores all 99 original members at their original absolute path, retains all 20 input hashes and result.json, and copies four layout files byte-identically to the new output. Production checker, admission, validation and publication methods remain unchanged. Full 560 DRC, deep/flat 500-device LVS and 13 fault controls are required; no new geometry, RC or waves. Root independently matched all 45 DRC and 53 LVS files to the actual prior runtime's 197-file manifest, so the source fixture's preparation step is not the only evidence of runtime availability.

Disabled source controls 41238328897 and activated source controls 41238703809 passed, with complete 35-file and 37-file proofs. An activation fixture assumption was caught before actual execution and corrected to use an explicitly disabled copy plus a refusal for the real source-control job under enabled configuration.

## Candidate view for fresh extraction: source controls only

Source 6f0dd8af1c026acfd1345bd9f01bae93329c2769 on codex/cdr-via2-m3-fresh-rc-source-v1 passed [41239363169](https://github.com/Melihakbulut221/nssoc/actions/runs/41239363169): 18 projection/refusal cases using explicit synthetic files. The earlier synthetic symlink fixture failure and its full 17-file proof are preserved; the correction changed only parentheses and its pin. Complete successful proof has 26 files.

Existing numerical workers already cover Via2/Metal3 within all seven metals and six vias. The source-only projection copies the new layout and flat LVS, retains immutable reference children and both original metadata files, and writes separately labeled derived metadata. Old native graph/RC results are not copied as new. The actual physical binding remains null and the native entry unconditionally refuses.

Physical PASS is now available. fresh_rc_next_audit owns the source-only host/admission/publication adapter; loaded_admission_review owns the native core and exact frozen-function/source-pin recovery. Combine and review their exact sources, bind the real report/source/run, and then regenerate the native view, preserving all 500 devices, 1,446 terminal records, 25 public ports and seven intrinsic MIMs. Authenticate all new resistance/capacitance branches and required observables. New topology counts may differ from the baseline. Only then run one matching nominal_late comparison with unchanged electrical thresholds and semantics.

## Mainchip observer failure and cloud-only diagnosis

Actual readonly [41236517605](https://github.com/Melihakbulut221/nssoc/actions/runs/41236517605) failed at 20:19:54 UTC after a 22 minute 27 second worker step. Its source controls and log prerequisite passed. Release 430152907 remained empty; no native geometry result is inferred. The complete visible proof is retained. The original 68-file artifact is 494,882 bytes, SHA e8de490cadbad36c2a969acc5e50f454fd63b2dbd05cb2550ab337fad133725a, and stays in GitHub.

First diagnostic collector 41238937909 passed eight controls but failed on the artifact download's media-type header. Header-only checks verified HTTP 415 with application/octet-stream and successful redirect with application/vnd.github+json; no artifact body was acquired locally. Its full failure is preserved.

Corrected source b1e4b4344b7f626aabf6c45bbd64fc9f9febc391 runs once as [41239406705](https://github.com/Melihakbulut221/nssoc/actions/runs/41239406705). Nine controls precede exact ZIP/68-member CRC+SHA authentication and strict known UTF-8 diagnostics. Full transport errors are retained, and unknown/partial native bytes remain in a separate cloud-only artifact directory. This corrected collector completed successfully, authenticating all 68 original members. Its complete 83-file proof and all 74 emitted derived files are preserved. Root independently verified the actual command, progress and failure records.

The actual native command hit elapsed_limit at 1,200.192 seconds, return code -15. It completed 142 of 373 endpoints and was processing VGND next. Group RSS was 1,135,636 KiB with 14,116,180 KiB host memory available; cgroup peak was 1,157,533,696 bytes and no OOM events occurred. VGND has one selected marker. The exact slow inner operation is not yet known.

A proven host defect explains the empty release: finish_record rethrew the primary failure before publication. The successor must publish complete failure evidence before rethrowing, add bounded native substage/batch progress and periodic stack diagnostics, and preserve all observations/census/digests. Root approved a 3,600-second readonly observation budget and an outer deadline of at least 3,900 seconds within the 90-minute workflow. Memory guards remain 10 GiB group RSS, 12 GiB container and 2 GiB host available; STA/electrical thresholds do not change. Actual dispatch still requires own-source controls, full proof and review.

Repeated encoded-path serialization is only a source-level hypothesis; no geometry algorithm change is selected from it.

The saved stale-wire-cleared.odb is preroute input and lacks iteration 10 mutable routes. Original route 41211382427 hit the 10 GiB RSS guard and produced no routed checkpoint. Preserve all 1,691 clock/fixed nets and use actual evidence to select the next bounded change. Final routing/setup/hold remain open.

## Acceptance and continuation

Full serial Gen3 x4 PHY, PLL/SERDES/TS/EQ/LTSSM, physical CDC and soc_top serial integration, final routing/setup/hold, RC min/max and production approval remain open. Keep UI 125 ps, sampler 100 mV/37.5 ps, XOR 100 mV/75 ps, HBT minimum VCE 0.4 V, maximum absolute VCE 1.6 V and VBE 1 V, actual Ic/emitter limit 3 mA, and PLL 62.5 ps. STA clocks remain 20/4/8/8 ns plus five percent, three PVT corners and zero setup/hold/slew/capacitance/fanout violations.

Monitor v194 tracks 512 handles every eight hours, read-only with automatic_native_dispatch=false. Earlier HTTP 502 is not claimed fixed. Use [skip ci], nonforce compare-and-swap updates and scoped Git trees.

Detailed state: docs/evidence/cloud-active-checkpoint-20261024.json
Immutable receipt: docs/evidence/cloud-collector-recipes-20261029/cloud-physical-recheck-and-mainchip-failure-v194.json
