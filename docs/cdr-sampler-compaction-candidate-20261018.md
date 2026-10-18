# CDR sampler physical compaction candidate

All work runs on GitHub-hosted runners. No native artifacts are restored locally.

The original loaded PD394 v3 failed both nominal cases, and all six external bias/common-mode experiments in run39088526670 failed. None is adopted. Existing layout evidence shows four sampler leaves each880um wide, with27 active/passive primitives on a32um pitch and a10um signal-bus pitch. The parent has long external detours in addition to these leaf wires; the sampler is only one required part of the repair.

This candidate regenerates real native GDS with device pitch20um, eight substrate-tap pitch60um, signal-row pitch6um and outline width560um. It preserves all15HBT12rppd8contacts, device parameters, netlist, wire widths, native via arrays and external circuit. There is no uniform shape scaling, RC multiplier, new source bias or relaxed electrical gate. The original source remains intact.

The hosted run regenerates both layouts, verifies every native PCell drawing and exact reference after top-name normalization, then runs the unchanged560-category DRC, deep/flat unsimplified35device LVS, ten original fault controls and actual OpenROAD LEF readback. The verifier differs only in the imported candidate top name. Physical failures must be retained. The geometry audit is not a DRC, LVS or electrical acceptance substitute.

After a physical pass, replace all four sampler instances through a source-bound parent manifest, regenerate the entire parent layout and evaluate parent routing compaction. Repeat parent DRC/LVS, fresh native MIM-aware RC, exact device/terminal binding and complete original loaded early/late tests. Reusing old native IDs or the old sampler RC is invalid. Clock recovery, full serialx4 integration, all-corner timing and production acceptance remain open.

## First native result and tap-lane correction

Run39090257244 generated560x191.03um (45.52percent of original area); identical native PCells/reference and all560DRC categories passed, but unsimplified35device LVS rejected connectivity. No electrical or physical acceptance is taken from the area reduction or DRC alone. The failed archive remains in its release and the full receipt is preserved.

Hosted diagnosis39090663060 restored the exact archive and found five actual M4 tap/signal centerline coincidences at151,211,331,391,451um. Native extraction explicitly merged QN|QP|SUB. With primitive pitch20um, the original tap origin30um puts the native tap center on an HBT collector escape lane. The correction moves the eight taps to x=22+60*i um, leaving their native area/perimeter and all other candidate geometry rules unchanged. This selects a separate M4 lane; it does not change substrate connectivity in the reference.

The revised audit reconstructs every M4 vertical route from its actual recorded terminal/via endpoints, verifies each rectangle exists in the flattened native GDS, and checks distinct-net overlaps. Both original and candidate must have no overlap; the restored failed GDS must reproduce exactly five overlaps. The complete unchanged native physical gates still determine acceptance.

## Corrected native physical result and full parent integration

Run39090817026/source724ba3ec3d613c3a03ee254e9eee116d53d343ce passed native560categoryDRC, unsimplified35device deep/flat LVS, all ten original fault controls and native LEF readback. The independent route audit finds zero distinct-net M4 overlaps in both original and corrected GDS, while reproducing five in the preserved rejected GDS. The proof and hashes are in evidence/cdr-sampler-compact-physical-pass-20261018.json. No post-layout electrical result follows from this physical pass.

The next parent candidate replaces exactly four sampler physical identities through an eight-child pinned manifest. All41source cards,16macros,394devices,25ports and original native circuit remain. Existing placement optimization, signal wiring and23supply-shunt generation rerun against the new actual pins and dimensions. The new physical top is nssoc_cdr_retimed_pd394_compact_supply_v1. All original parent560DRC/deep-flat394deviceLVS/fivefault gates apply. Fresh whole-parent native plane binding, MIM-aware RC and original full loaded tests are mandatory afterward.
