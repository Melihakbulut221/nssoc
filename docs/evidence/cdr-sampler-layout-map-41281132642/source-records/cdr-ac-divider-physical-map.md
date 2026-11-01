# A/C divider candidate: complete physical instance map

This read-only GitHub analysis joins all500 native devices and4928 physical instances from the existing canonical GDS/LVSDB-derived reports. It does not load or alter GDS, run extraction, or claim physical acceptance.

The candidate is sourcee2e753c37fcff8b8fef85695208b8157a7399b57, controls41280673267, native run41280806504. Relative to q15 sourcee85179e6900c2be9d931a8b30549c99f47c7617d it must preserve all16 prior target tuples and add exactly eight A/C divider lengths: R227/229/238/2403.6->1.8um andR228/230/239/24121.6->10.8um, allW1um. Every terminal, cluster, original dimension and model identity is authenticated.

For each selected PCell definition, report all physical instance users, including users outside the500-device binding census. Also report any selected users requesting conflicting dimensions. Such definitions require per-instance private replacements; an in-place shared-definition edit is not valid.

Thirteen corruption refusals and three positive ownership scenarios cover complete census/terminal/dimension identity, preserved prior targets, exact additional targets, untargeted physical instances and conflicting requested dimensions. Inputs are byte/hash pinned to immutable commits; source and workflow are pinned by the local config read on the runner.

This mapping is preparation only. Native simulation gates remain unchanged; any candidate needs its own accepted electrical result, separately authored schematic reference, physical regeneration preserving canonical via2/M3 repairs, DRC/LVS, fresh RC and full-PHY/corner validation.
