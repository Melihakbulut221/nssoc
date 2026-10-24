# Four p4 native drive3 cells on the actual wire20 layout

The retained full32 waveform 39409002976 and native review 39438335576 reject
wire20: 79 wrong and 97 low output samples / 768, with six HBTs below the original
0.4 V active VCE bound. The first input-level wrong signs occur on p4_0 and p4_3;
all four p4 paths have weak input margin at the next stage. This is evidence for
testing stronger physical p4 drivers, not proof that sizing will close timing.

This candidate replaces all four 4:1-stage pre_low macros with the exact native
pre master already used by a and b. The generator checks that one translation
aligns all twelve actual pin rectangles for each replacement. Every parent
drawing, all sixty parent signal routes, all master cell drawings, LEF and
external ports remain unchanged. The complete high-drive circuit (including its
native resistors and references) is rebound by the original topology; no
individual model parameter is patched into an old parasitic graph.

Actual cell bounds are checked before replacement. The 54-device low-drive cell
contains 19 emitters; the existing 54-device high-drive master contains 55.
The whole core retains 1,674 devices and 589 HBTs but increases from 719 to 863
emitters. Four such cores would contain 3,452 emitters before PLL, CDR and other
devices. This does not establish compliance with the whole-chip emitter budget.
No PDK rule is disabled or waived.

The serialized GDS is independently read back. Controls replace a master
incorrectly, move its pins by 5 nm and remove real parent metal; each must be
rejected by the exact geometry checker. The unchanged native verifier then runs
all 560 DRC categories, hierarchical and flat transistor LVS, and the original
wrong-finger/missing-device/open/short/offgrid faults.

After physical acceptance, fresh native terminal binding and R/C extraction are
mandatory, followed by the original full34ns/256bit nominal and selector-fault
tests with all HBT/MOS limits. Increased clock and data load can create new
failures; final selector/tail headroom may still require a separate circuit fix.
Do not reuse the old wire20 parasitics or mark full PHY accepted.

The native instance replacement uses documented KLayout cell_index/dtrans
setters: https://www.klayout.org/downloads/master/doc-qt4/code/class_Instance.html .
All execution and evidence remain in GitHub.
