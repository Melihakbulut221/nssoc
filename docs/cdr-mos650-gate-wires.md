# Current physical wire and gate-contact binding

Input: physical41710162510, actual GDS SHA256
c335182048dc1696821ab875fb34447e5b5a9ba0f1a24d5d16d572680906c16c.
All560 DRC categories passed with0markers; deep/flat650 LVS and13 fault
controls passed. This consumer re-extracts actual IDs and semantic owners
from both current native LVS databases; all15 identity corruptions per mode
and original wire controls remain.

M1/M2/Via1 drawing polygons were deliberately moved to the top cell.
Source-pin recovery therefore authenticates the complete prior650 wire
archive and original GDS, binds each old pin record to its FULL original
primitive drawing, proves every current primitive's nonrelocated material,
all hierarchy and ALL pin annotations/text remain identical, then records
the current full drawing signature. Every selected metal point still must
pass current native-LVS and physical-wire ownership probes. No relaxed
global signature or schematic alias is used as physical identity.

The old ideal one-point-per-intrinsic-gate shortcut is removed. All200 actual
intrinsic gate electrodes remain separate rows requiring distributed poly
RC. All200 REAL gate contacts on50 physical poly groups become independent
metal solver anchors, with exact contact polygons, group membership, native
owner and actual current wire component. Remaining1203 metal terminal
references,643 intrinsic body references and25 public ports remain explicit.
No ideal gate-to-metal edge is asserted. Each complete metal/via layer is
read back against the exact GDS. Native readback compares every group's
complete real contact set with its anchors.

The existing five corrupted-wire tests are retained and five gate-specific
corruptions added: missing group/contact, duplicated contact point, an
intrinsic gate collapsed onto metal, wrong intrinsic membership.
Fresh metal/via/poly/contact RC, compact-model gate-resistance composition,
MIM/coupling/substrate qualification and full loaded electrical gates are
still required. This is not full PHY, mainchip route or final timing success.
All native work and failure evidence stay in cloud releases.
