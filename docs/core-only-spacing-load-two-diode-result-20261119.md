# Two load-isolation antenna diodes: verified preparation — 2026-11-19

Run https://github.com/Melihakbulut221/nssoc/actions/runs/44494801363 succeeded at head 56a2b9d33ad08ae632486f6248e8ffc75e5b60c6, attempt 1.
Artifact 14515255856; SHA256 48c52b4678a6115d8e161e91468cfe78d9f2f6aee0c41d11467cda0e204247ff. All 13 output hashes verified.

Source ODB: 0cb063d1069d079d08912d11c1cf23429e1d53417e5185b822df4b4d27da6fc7.
Prepared ODB: 44e5b8fe6d989394000395ca7449744007dc812710149bc856efaa6172aad9d4.

ANTENNA_2567 and ANTENNA_2568 are sg13g2_antennanp cells with signal A on nssoc_slewiso_1_net, VDD on VPWR and VSS on VGND. Four positive-area native supply contacts passed; no wrong-supply contacts; synthetic and native rail-removal negative controls passed. All 106654 original instance geometries and connections are unchanged; total instances now 106656. Existing power geometry/ports/die are unchanged. 103087 unselected non-power net records and all 2113 clock nets were preserved, including the existing NDR assignments and layer rules.

Next route only nssoc_slewiso_1_net from this prepared ODB. Keep all other routes encoded FIXED during DRT and restore their ROUTED status afterward; require exact identity/preservation, DRC zero, antenna zero and independent geometry clean. Preparation is not routed antenna closure or production acceptance. Fresh RC, three-corner timing, full-chip and manufacturing signoff remain required. Clock constraints and derating are unchanged.
