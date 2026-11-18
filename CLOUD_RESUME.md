# Extracted core diagnostic checkpoint

Run 44303529050, head 20bedd917c6f98bf6afeea1ee991d2ca4c4f03ea completed RCX and three-corner native STA (return code 0), then failed annotation classification. Native artifact 14427169742 SHA256 a3b97b431600c7b068d4e904fb587adb7ab784ada4113c2bf0988fe124f982ab; summary 14428375522 SHA256 074b5910799da127485928512e1fc7e4f33067ff682c02f40c8dbb4caa279031. All 115 native output hashes verified independently. Nominal SPEF SHA256 38b6d8f67c527baa6bc49232097246d177bc9f43f60cc3c6c8ee7464c2edfbe1, 102601 nets, zero per-net capacitance-conservation inconsistencies. This is not coverage or RC accuracy signoff.

Slow: 118 setup failures, WNS -1.471498520 ns, hold 0/+0.429305492 ns. Typical setup/hold 0, worst +6.459904794/+0.112282409 ns. Fast setup 0/+10.337638593 ns; hold 1/-0.090147892 ns. Electrical violations remain: slow slew477/fanout171/cap41; typical5/171/41; fast1/171/44. All corners report 4072 unannotated drivers; zero filtered count is not a waiver.

The failed checker assumed SPEF numeric net IDs equal routed ODB IDs. LibreLane 3.0.5 RCX explicitly reads LEFs and DEF, reconstructing IDs. Observed SPEF ID3 maps net26171, while original ODB ID3 is a different escaped SpaceWire net. The replacement resolves only unique exact native-writer names; unknown or colliding names fail. No heuristic unescaping or alias guessing. Classification uses the same authenticated ODB/SPEF/STA logs and does not rerun extraction or change constraints.

Primary implementation: https://github.com/librelane/librelane/blob/3.0.5/librelane/scripts/openroad/rcx.tcl

Pending physical jobs: parent pad reroute 44304410132; routed functional boot/MBIST 44303624006; hierarchical SPEF qualification 44304940869. Preserve these jobs. Next actions: inspect current diagnosis and exact worst-path reports, then repair real slow setup and fast hold defects and verify all corners again. Full-chip IO/CDC, SRAM, LVS, foundry DRC, RC minmax and production approval remain open.
