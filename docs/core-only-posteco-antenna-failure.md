# Core detailed route completed; antenna repair now required

Run44337630426/head19924a826cfca054f30f19cdde091fbe6c744960 completed with native routing returncode0 but workflow failure at the strict antenna gate. It was not killed by a time limit. Artifact14463371089 SHA256cd3c228a0ec3cb5a901b5da88ae20c8af1112c3ce1daf7a607fcb80327f11ce3; all98 declared output hashes verified.

Native detailed-route DRC0. Identity105251 instances and exact connections/geometry/status/masters verified. Indexed visible wire/via/LEF connectivity has zero disconnected nets,missing terminal geometry or inter-net contacts. These are not foundry DRC or transistor LVS claims.

Antenna check:363nets/399pins violate. Existing1168antenna cells remain. Jumper-only detailed routing did not close them. Worst summary ratio5.39 on nssoc_sta_n_53322 TopMetal1; violations also occur on lower metals. RoutedODB SHA2569f437215e21f8004390ba0bcfac397a6b9113fb1ab38e2a7abe4600e0f99f6b3.

Do not dispatch staged signoff-gated extraction b75792d10e647522ecb6c554a35906708d718c57 against this failed candidate or weaken its antenna admission. First inspect exact violations and pinned native repair/incremental-routing command capabilities. Preserve completed routing for targeted repair instead of restarting the entire original flow blindly. If diodes are added, explicitly audit all additions,pin connectivity,placement/power and unchanged original cells; require new routing/antenna/geometry,actualRC timing and appropriate boot validation.

This new read-only diagnosis authenticates the failed source artifact,extracts layer/net/pin violations and records pinned native help plus source routing Tcl. It never claims repair or product acceptance. Latest diode-model research remains c8622b3a9be576bbb9221f1005e171efec8ef813; native derivative correction has not been built or tested. Resume that independent task after core repair preparation.
