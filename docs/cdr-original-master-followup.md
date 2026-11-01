# Original-master controlled experiments: terminal results

Both candidates completed the actual native transient with engine return code 0, no diagnostics and unchanged source files. Both passed all original device predicates and failed the overall electrical screen. They are rejected circuit candidates; no new layout or fresh RC is accepted.

| Candidate | Native run | Source | Engine elapsed seconds | Full terminal proof |
| --- | --- | --- | ---: | --- |
| q15 | 41277054717 | e85179e6900c2be9d931a8b30549c99f47c7617d | 682.744926642 | 559d1879b2a461d2926279262695a9bd20efed83 |
| q20 | 41277056212 | edc7c8d04659f73d024c45bbfa4936b977c90c32 | 742.773587595 | a9b1c76d93d90fb57b8820f26b06ccccd1fcfebc |

Each terminal proof retains 64 files including complete measurements, original controls, source, job logs and cloud publication metadata. Native archives remain cloud-only.

## Exact experiment

Both restore master loads XD177/178/195/196/207/208/215/216 to original L2.6um/W32. Four pullups XD182/183/220/221 change L1.8->1.0um/W8; four shunts XD184/185/222/223 change L5->3.4um/W4. Eight output loads XD175/176/191/194/202/205/212/214 change L2.6->1.5um/W32 for q15, or L2.6->2.0um/W32 for q20. Exactly 16 intrinsic length tokens change from the authenticated original model.

All other 500-device fields, wire RC, 1151 saved vectors, 10ohm sources, 150fF sampler/50fF XOR loads, stimulus and frozen prepare/measure code remain unchanged. Source controls41276766920 and41276785721 passed 17 circuit and 5 archive refusals. Independent exact-source releases430382305/430382311 were reserved before native admission.

## Original-gate comparison

Actual comparison41278156089/source9525946fc408f2ada69b854466ae0b67d7d7cb6f and comparison41278276162/source869503434669eb2d885061cc8ca81b9c8eeef5ea passed all 13 corruption refusals and verified complete original measurements. Full 15-file proofs: d221360bf0cadffddc80a0c7fcd06262fd0337dc and7298b1f50c9a24d5169874544ad3b20f2537f75b.

| Stage | q15 max delay ps | q15 min signed mV | q15 result | q20 max delay ps | q20 min signed mV | q20 result |
| --- | ---: | ---: | --- | ---: | ---: | --- |
| A | 41.40625 | 65.427579 | fail | 43.59375 | 43.079583 | fail |
| B | 37.03125 | 105.807991 | pass | 39.53125 | 78.027343 | fail |
| C | 118.90625 | 33.754185 | fail | 118.90625 | 12.250414 | fail |
| D | 118.90625 | 22.772750 | fail | 114.84375 | 0.396389 | fail |
| X | 118.90625 | -108.363876 | fail | 118.90625 | -115.284513 | fail |
| Y | 118.90625 | -5.699940 | fail | 118.90625 | -5.943916 | fail |

Sampler limits remain 100mV/37.5ps; XOR limits remain 100mV/75ps. q15 has 96/0/194/129/759/748 samples below100mV in A/B/C/D/X/Y; q20 has129/64/181/129/752/713. Complete 1530 per-bit delays are retained in each report.

q15 phase7.742293mV and VI current25.505829uA fail30mV/50uA. q20 phase10.126912mV and VI current32.271976uA also fail. VI voltages7.084018mV/9.024841mV pass5mV; VI bias passes. Raising output load length improves phase output but worsens A/B sampled margins and timing. Neither candidate is a complete improvement. Do not continue a monotonic load-length sweep based only on phase amplitude.

## Physical mapping

Paired map41277369515/source7bea91b0ec7a6a4fd9f8205a0cb3f5808a069a71 passed11controls and complete500-device/4928-instance joins for both variants. Full16-file prooff89d371d49788e6e5bec240a65c242cafe22e7c8.

| Shared definition | Targeted outputs | Untargeted masters to preserve |
| --- | --- | --- |
| rppd$2$11 | 175,176,212,214 | 177,178,215,216 |
| rppd$2$10 | 191,194,202,205 | 195,196,207,208 |

The eight output instances need private cells. Pullup rppd$23 and shunt rppd$v59_cd_shunt definitions have no untargeted users in the complete census. No geometry was processed or changed by this map.

The legacy v58 generator cannot run unchanged on canonical v59. Preserve current via2/M3 repairs, use current LVSDB ownership and actual pin boxes, and patch independently authored schematic references. Rebind all 500 device identities after fresh extraction.

## Next diagnosis

See [operating-point evidence](cdr-sampler-operating-points.md). Examine transition transfer through the loaded sampler, divider/feedforward networks, input followers and XOR paths before choosing another intrinsic edit. Any new sizing experiment needs exact native bindings, independent source controls, unchanged gates, a reserved exact-source output release, actual native measurement and then physical regeneration/DRC/LVS/freshRC. Full serial PHY and final mainchip timing remain open.
