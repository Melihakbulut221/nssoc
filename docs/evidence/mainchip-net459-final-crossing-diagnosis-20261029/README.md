# Selected net459 crossing after the guarded route

This is a bounded diagnosis of **run 40894408041**, source `8e9223b0be6e644d4c5684b94b13c2888c531e79`, observer-on route job 123520805697. Routing, physical, timing and PHY acceptance remain false. The audit jobs were still running at the recorded observation.

The remaining sampled Metal5 crossing is **net459** against **clknet_5_29__leaf_u_ibex.clk**. Its exact native-writer rectangle intersection is `[947420,1789940,947620,1790140]` DBU, or **x947.420–947.620µm / y1789.940–1790.140µm** (1000 DBU/µm). The net459 vertical centerline moved from x950.880µm to x947.520µm; it still crosses the unchanged clock centerline y1790.040µm.

All four snapshots preserve that selected clock's **133 internal/native material records and 365 raw opcode/data pairs exactly**. Both target signals changed: net36993 raw pairs 551→578 and net459 334→375. Each target's final internal layer/rectangle multiset equals the native-writer multiset. The sampled net36993-clock overlap is removed.

`after_writer` observes the in-memory OpenDB after `endFR`/`updateDb`. It does **not** replace the pending serialized-ODB reread, complete 1691-clock audit, original-class final DRC, timing or off/on-equivalence gates. The router log reports one Metal5 Short from iteration 27 through the last executed iteration 60; 61–64 were skipped.

A conditional next repair scope is **net459 only**: first authenticate the final audit marker, then read the full surrounding neighborhood in cloud and assess a legal layer bridge, potentially a Metal4 section with two Via4 landings. The three-net witness cannot clear other nets, pins or technology-rule spacing. Preserve the clock, the net36993 repair and every original gate; no geometry candidate or further engine change is approved by this document.

The [structured diagnosis](diagnosis.json) contains exact IDs, byte counts, full SHA256 values, source hooks and limitations. All seven complete original derived records are retained under `raw/`; no native archive, ODB, DEF, GDS or executable was acquired.

| Complete direct record | Asset ID | Bytes | SHA256 |
|---|---:|---:|---|
| [case-result.json](raw/case-result.json) | 689008674 | 16285 | `6c495c8f4c02ec48a4759d7d026f87e6871109b98941055928d5293bc6eb42bc` |
| [one-two-signal-routing-attempt.command.json](raw/one-two-signal-routing-attempt.command.json) | 689010229 | 1116 | `2be03878a218199b304eb3d4129d9cc7918e206dcf3e77c1209c901e85acb3e9` |
| [one-two-signal-routing-attempt.stdout](raw/one-two-signal-routing-attempt.stdout) | 689010311 | 77567 | `06a0f4d385ede18f61f8d3f968513bc6d0f1305c41e2cc28f0733d4cda574ea2` |
| [imported.jsonl](raw/imported.jsonl) | 689010681 | 249451 | `9459f149cb3b1cc8f0964be27eeec204e156b0ba5b28c20bca9781a00f01664d` |
| [before_dr.jsonl](raw/before_dr.jsonl) | 689010602 | 249452 | `503fe353231dcc39d3165c3888ced056977ed9861976056a0105e7df9e3ca02c` |
| [after_dr.jsonl](raw/after_dr.jsonl) | 689010427 | 254312 | `0b7f08b1d1c181fdc907596d6217506e7a95c6164c8e026a949ec6615a671d76` |
| [after_writer.jsonl](raw/after_writer.jsonl) | 689010514 | 262286 | `9caf4db65ed179882c5d4825a4abc2fbbbb68baf894f6e975d7f18a4d54a183e` |
