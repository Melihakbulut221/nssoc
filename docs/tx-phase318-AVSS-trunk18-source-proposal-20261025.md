# AVSS-only trunk-width hypothesis from the completed phase318 capture

The existing capture now has an authenticated native AVSS graph and exact 42-row ledger. All 36 graph/row, 32 coordinate and 40 physical-route refusals passed. The unchanged original review still rejects 17 tail HBTs and phase behavior. This document proposes one layout variable; it does not authorize native execution or claim a repaired circuit.

At the 17 HBTs' actual minimum-VCE rows, emitter returns sit 194.296–238.499mV above the source's AVSS=0. Their actual collector voltages relative to source0 are 581.540–624.223mV, while local VCE is 345.386–398.875mV. These are same-row identities, not a prediction obtained by forcing emitters tozero.

The worst is xdut.XD105 / PHASE__XS__XHOLD__XT at row23023, 6.911120895ns: C=582.996mV, E=237.611mV, VCE=345.386mV, VBE=825.946mV and native Ic=1.16650mA with Nx4. Its 54.614mV VCE shortfall accompanies this measured return-potential decomposition:

| Actual node interval | Drop |
|---|---:|
| Public AVSS to P_AVSS.n12 | 50.241mV |
| P_AVSS.n12 to P_AVSS.n25 | 167.287mV |
| P_AVSS.n25 to emitter A0314 | 20.083mV |

Across the 42 prescribed rows and three macros, the middle span stays 166.127–168.106mV. Its endpoints lie at (111.020,89.010) and (112.980,2199.050)um in the native frame, inside the recorded AVSS TopMetal1 trunk. Actual edges R1021..R1033 form a tapped graph chain; their resistance sum is not an equivalent return resistance. Some extracted edges include access or multiple material portions, so no individual edge is assigned a layer or rescaled from these coordinates.

The source entry also matters: R1016 is1.02992ohm and drops47.9258mV at the worst row, with46.5335mA computed from its actual endpoint voltages. First cross-row edgeR1021 is.743101ohm and drops33.0801mV at44.5163mA. The parallel branch whose endpoints align with the source Metal5 trunk includesR1048=15.94ohm with54.9745mV/3.44884mA. These are linear wire-resistor calculations, not Ic=Ie or full-KCL claims.

At row9674, the passive XRUN.XAND_SKEW return is199.644mV above source0; release/ARM/run differential voltages are69.474/170.631/8.992mV. This connects the return issue to the actual steering/bias neighborhood but does not establish why the clock or run state fails.

The proposed isolated change is to widen only the existing AVSS TopMetal1 cross-row rectangle from6um to18um, retaining centerx112um and y89..2371um: [109,89,115,2371] becomes[103,89,121,2371] in the original generator frame. The qualified native translation remains(0,-3.97)um. The AVDD trunk remains[93,81,99,2363], leaving a4um source-rectangle gap; this is not a DRC clearance result. Added AVSS area is27,384um². The15 TopMetal2 row buses,101 native vias,source/public port,all244 compact devices,90 finite taps,other nets and all signals remain unchanged. Leaving the entry/row buses unchanged isolates the long cross-row return gradient as the variable.

Implementation should derive a new candidate from the exact physical generator44d99b14 and frozen base d81291d4, with reversible edits confined to the AVSS trunk half-width and its full-overlap check. Preserve the tested source. Require exact old/new shape delta, native ownership of the added region, fresh both-polarity560-rule DRC/deep+flat334 LVS/terminal-body-wire controls and all faults. Then require fresh two-order wire/MIM RC, measured graph/vector census, loaded binding and actual318 OFF/zeroOP. Do not scale the old extracted R values. Only after those prerequisites and source review should one original34ns p-high transient run with unchanged prescribed histories,100mV signal margin,62.5ps first-fall and all device/numerical gates. The result may improve safety without curing phase; all failures must remain visible.

Exact numerical witnesses,17 device rows,126 interval samples,source hashes and release asset identities are in the companion AVSS-return-headroom correlation JSON. No layout source has been changed and no new extraction or simulation has run.
