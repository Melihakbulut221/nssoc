## Native contact-count and actual gate resistance measured

Run41716341181/source44efb7eae677d57988386398073f7c83f6145c7d on codex/cdr-mos650-gate-contact-ac SUCCEEDED, release433203305. Complete current wire producer41712243960 was authenticated in the cloud. All200 current native MOS IDs, actual W/L/AS/AD/PS/PD,50 one-ended and150 two-ended electrodes were rebuilt and matched to the fixture. The8.885um geometry has only two-ended electrodes, so there are14 actual dimension/contact/QS-RF cases plus8 canonical reference cases.

All22 separate one-transistor native executions completed with no diagnostics. Every requested NGCON and actual RG/XGW/NF/W/L was read back from the frozen native simulator. The eight explicit NGCON2 cases reproduce the untouched original models with the ORIGINAL relative1e-9/absolute1e-7 complex-impedance tolerance and identical native resistance/geometry readbacks. Original model files remain unchanged; only a separate wrapper copy exposes the six formerly fixed NGCON arguments. All stdout/stderr, readbacks, decks and complete native archives are preserved.

Measured RF RG atW8um is73.09375ohm one-ended vs52.59375ohm two-ended; atW8.89um75.51709786276714 vs52.79209786276715; atW9um75.82407407407408 vs52.824074074074076. QS RG remains4.824074074074075 to5.427083333333333ohm despite RGO/RSHG0, because native RINT is1.3025e-11. RF RGO40/RSHG3, RVPOLY0, DLSIL0, SWGEO1 and nativeXGW100nm are recorded. Complete input impedance is not the gate resistor; atW8um/two-ended/RF/1GHz its real part is74.08834477288276ohm while actualRG is52.59375ohm.

First run41715622293/sourcee5b3fd44493da81faa269798b5b43667b6d74330/release433199094 FAILED the strict equivalence gate despite zero native diagnostics and correct NGCON readbacks. Its canonical8-device and explicit14-device decks differed in matrix size; seven real-impedance samples exceeded tolerance, max4.311324346417678e-6ohm. Successor controls this numerical confound with one device per native deck; the exact original comparison tolerance is unchanged. The first complete failure and measurements remain preserved. Source-only intermediate27409f8771edc1dd82ba63fa55ca726dd010c882 was not dispatched; native RG instrumentation is in44efb7.

This resolves a model diagnostic, not physical gate/poly/contact network composition. No full PEX, complete electrical, fullserialPHY or finaltiming acceptance is claimed. Current accepted metalRC remains41713023974:28619R/18469C,1428 distinct anchors and13raw corruption controls. Actual mainchip full64 routing41699812301 is polled independently; no duplicate route was started.


## Next physical composition

Use the complete actual current gate/contact polygons, all200 physical metal anchors and fresh metal/via network. Native XGW100nm is the model default and does not prove actual access length. Never identify a gate electrode with an arbitrary metal reference or force two physical contacts to one ideal node. Full multi-contact electrical behavior remains to be represented.

The measured RINT contribution must be accounted for separately from RF RGO/RSHG and from explicit physical poly/contact resistance. A candidate distributed intrinsic model must reproduce the unchanged device at equal electrode potentials before a physical network is applied. Preserve actual device dimensions and diffusion parasitics, and validate terminal currents/charges/admittance and refinement convergence. Compact-model input impedance is not a physical resistor.

The [PSP reference manual](https://www.leti-cea.fr/cea-tech/leti/pspsupport/Documents/psp103p7_summary.pdf), sections2.5.6/3.4, supplies the reference gate-resistance terms. This checkpoint additionally compares their numeric sum against the actual frozen native RG at all14 measured cases. It does not qualify every model mode or replace full loaded simulation.
