# Next full650 nonlinear composition

Pending implementation after successful MIM extraction41728568165 and gate reduction41725473326. This document does not claim an assembled or simulated whole circuit.

## Exact current inputs

- Wire identity41712243960/sourcef3aece4ae3b048df220cb51277d74fcd026940ed/release433179003: native650 device and2046 terminal identity, current GDS c335..., full source correspondence, geometry anchors and200 physical gate contacts.
- MIM-aware metal41728568165/source1b40bf2db3844d6281c467022b248a2871ced6df/release433272698:28634R/18476C and7 explicit intrinsic MIM cards. Both native orders pass identical complete exports and22 faults each. Use native/mim-precise/wire/rc03/wires.spice, native/mim-precise/wire/anchors08.json, derived/precise-mim-result.json and the native raw/audit records in archive rootmos650-metal-rc. Bottom measurement points moved outside intrinsic masks; all other physical anchors and actual material stayed fixed.
- Gate reduction41725473326/source8d7874d8c9740725ed1e4cd8c3631ec1c81bc2e6/release433256009:50 groups,200contacts,250 models forN1/2/4/8/16. Each native/reduction-g{group}-n{N}/ports-and-matrices.json and reduced-positive-resistors.cir is bound to current original wire geometry. Preserve every real contact including the reference contact; it is not ground.
- Historical unchanged non-MOS compact parameters are in successful producer41547492718/sourcef1248c7a3709d8112da98d25b9c3d67bf39c83fe/release432088543, member binding/binding.json,351749B,SHAb490f24e709a1c7543955b170bd11d161671d9d2c3d1cffc5ad0f2709416ce82. Acquire only in cloud from its sealed archive. Reuse model parameters only after proving current identity/geometry; never reuse old wireRC.
- Runtime39029337682 remains a failed electrical producer and is runtime-only: original ngspice engine103134f6... and models. Intrinsic partition30392de6... qualifies a separate RF model copy with onlyRGO/RSHG removed, retainingRINT/RVPOLY/NQS. Full intrinsic variant model file hashdc3d592a... is already documented.

## Assembly that retains actual electrical attachment points

Build a new adapter for actual650 identities, not the old500-to650 expansion. Inspection of current derived identity shows all450 non-MOS layout parameter dictionaries exactly equal original_source.layout_parameters. Match origin_native_id and loaded_instance to the old canonical compact parameter binding. Preserve existing canonical native-SPICE versus binary geometry comparison from cloud_cdr_current_eight_drain_fresh_binding.py: absolute Decimal difference from Decimal.from_float(observed) no greater than one math.ulp(observed). This is the existing readback rule, not a new electrical tolerance.

Bind HBT/resistor/contact terminals through actual current native rows and unique physical anchors. Keep all643 intrinsic body/well terminal references and finite ptap compact models. Do not turn body references into ideal supply aliases; substrate spreading remains an explicit missing physical scope.

Use each of the seven current native extracted MIM cards exactly once at its actual exported RC nodes and unchanged w/l. The capture report supplies native_id and exact export correspondence. Do not strip the native MIM and relocate its compact model to a merely same-conductor measurement probe: retaining original exported attachment points avoids introducing a new plate-distribution approximation.

Map all rawR/C endpoints bijectively. Keep every raw resistance/capacitance token and attachment; retain extractor ground as a separate wire_cref port. All25 actual public ports remain, plus this explicit extraction reference.

For each gate group instantiate the selected positive-resistor macro with its reference and other GC ports bound to actual MIM-aware metal labels. Projected gate ports connect only to the matching native MOS device/stripe. Use N identical-dimension intrinsic MOS copies with m=1/N; retain actual W/L/AS/AD/PS/PD and the same ng=1,rfmode=1,pre_layout=0 settings used in the successful160-execution intrinsic partition proof. Total multiplicity for each physical device must remain1. Every copy retains actual drain/source physical anchors and its intrinsic body reference. Use the pinned separate RF model variant; attaching external gateR to the unchanged full RF gateR would double-count resistance.

## Whole-circuit evidence still required

Preserve the old256-bit stimulus,125ps UI,2ns start,34.25ns stop,0.3125ps maximum step,150fF output loads and all sampler/phase/current/device gates. Rebind data-pair collector probes, tail groups andVI current probes through current source correspondence. Sum appropriate fractional MOS currents while still checking every device voltage; do not drop weak units. Compare nonlinear full-loaded outcomes asN increases, retain every rejection and convergence issue.

The old bench uses an external8GHz clock. Passing it still does not prove recovered-clock operation or serialGen3x4. Gate extrinsicC, substrate, corner/temperature/physical parameter qualification, actual four-lane operation, chip routing and all-corner final timing remain required.
