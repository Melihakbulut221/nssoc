# Actual active retime follower integration
Leaf run39470863624 passed all560 native DRC categories, deep/flat eight-device
LVS and seven deliberate device/geometry faults. This is physical evidence only.
The parent candidate replaces ac and bd in the exact v22 parent. Their original
six signal/return/substrate pin coordinates are identical; the added AVDD pin
receives a real Metal5 access, native via stacks, and TopMetal2 branch to the
existing verified AVDD rail. Other fourteen instances, all original placements,
external pins and existing parent metal remain. Unused same-net supply stubs
are intentionally retained and must be included in fresh RC extraction.
The native reference removes24 old leaf cards and inserts16 verified follower
cards:476 devices,120 HBT,46 NMOS,98 rppd,7 MIM and205 substrate contacts.
The independent serialized-child geometry check still covers all16 instances.
The complete native DRC and deep/flat LVS suite uses the same rule deck. Existing
applicable reference/geometry faults remain; the old retime MIM parameter fault
is replaced by actual follower collector/emitter reversal because those four
MIM devices are intentionally absent in this circuit. Baseline v22 and all its
fault records remain unchanged. No acceptance threshold is relaxed.
Parent physical evidence, whole-parent wire/MIM extraction, original loaded
early/late tests and stopped-clock/bias-off faults are required before adoption.
Full serial PHY, x4, mainchip routing and final setup/hold remain open.
