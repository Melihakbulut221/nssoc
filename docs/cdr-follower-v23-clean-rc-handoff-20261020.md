# Clean parent handed to fresh native extraction
Run39475461885 identified and removed20 entirely parent-owned floating metal
components with zero device terminals and zero public pins. The independent
wire graph contained131 components before cleanup and111 retained components,
matching the previously declared functional conductor count. Every removed
polygon is retained in the diagnosis receipt. No native child geometry or
circuit card changed. SchematicSHA remains
dbcdefd2ca36d6fee65fbad2b84c2540130c3e816f845cd5ebc367c90f773b63.
The full560-category DRC, deep/flat476-device LVS, all nine fault controls and
all16-child placement checks passed again. Clean GDS:
cb96ccb956903a12e0237ec98e51cfe0aaa8108334942d096f9130fb0d68b6e0.
The extraction retry is now bound to this immutable parent. The original strict
no-floating-metal assertion remains unchanged. No result from failed extraction
39474349718 or dependent MIM39474781983 is treated as acceptance. Fresh terminal
binding, native model mapping, wire RC and original corruption controls must
pass before the MIM-aware and loaded electrical stages proceed.
