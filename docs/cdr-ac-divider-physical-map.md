# A/C divider candidate: complete physical instance map

This read-only GitHub analysis joins all500 native devices and4928 physical instances from the existing canonical GDS/LVSDB-derived reports. It does not load or alter GDS, run extraction, or claim physical acceptance.

The candidate is sourcee2e753c37fcff8b8fef85695208b8157a7399b57, controls41280673267, native run41280806504. Relative to q15 sourcee85179e6900c2be9d931a8b30549c99f47c7617d it must preserve all16 prior target tuples and add exactly eight A/C divider lengths: R227/229/238/2403.6->1.8um andR228/230/239/24121.6->10.8um, allW1um. Every terminal, cluster, original dimension and model identity is authenticated.

For each selected PCell definition, report all physical instance users, including users outside the500-device binding census. Also report any selected users requesting conflicting dimensions. Such definitions require per-instance private replacements; an in-place shared-definition edit is not valid.

Thirteen corruption refusals and three positive ownership scenarios cover complete census/terminal/dimension identity, preserved prior targets, exact additional targets, untargeted physical instances and conflicting requested dimensions. Inputs are byte/hash pinned to immutable commits; source and workflow are pinned by the local config read on the runner.

This mapping is preparation only. Native simulation gates remain unchanged; any candidate needs its own accepted electrical result, separately authored schematic reference, physical regeneration preserving canonical via2/M3 repairs, DRC/LVS, fresh RC and full-PHY/corner validation.

## Completed authenticated map

Run41281132642, sourceb0e1a6f7cdd955eea951b8ceb7f28704a121b7c9, succeeded. All13 corruption refusals and the three positive ownership scenarios passed; all500 devices and4928 physical instances joined. Complete17-file proof: ad03e9fda6cf2c0a9867d7953b6ee830afa616cf, docs/evidence/cdr-sampler-layout-map-41281132642.

| Definition | Selected native IDs | Requested length/width | Other instance users |
| --- | --- | --- | --- |
| rppd$8 |227,229,238,240|1.8um/1um|none|
| rppd$1$3 |228,230,239,241|10.8um/1um|none|
| rppd$23 |182,183,220,221|1um/8um|none|
| rppd$v59_cd_shunt |184,185,222,223|3.4um/4um|none|
| rppd$2$11 |175,176,212,214|1.5um/32um|177,178,215,216 must remain unchanged|
| rppd$2$10 |191,194,202,205|1.5um/32um|195,196,207,208 must remain unchanged|

The full4928-instance audit found no additional unbound physical users for the selected definitions and no conflicting requested dimensions within a target group. Eight output-load instances still require private replacement cells to preserve the original eight master loads. The new A/C divider definitions have no untargeted users, so this ownership check does not require private cells for them. This establishes ownership only; pin connectivity, geometry legality, real schematic agreement and fresh extraction still require native validation after an accepted circuit result.

The selected paths are retained in the full result, including the original resistor PCell transforms, boxes and terminal identities. This map is tied to baseline GDS42ed5bcd567518786b718248947771172e9f5cc419d0aaa8fc8c49d8cfa4e876 and LVSDB3e133656d97d0c191390365919187102d9e5f1c75361bf53120e48eea9001295. Preserve existing via2/M3 repairs when regenerating and rebind all500 devices afterward.
