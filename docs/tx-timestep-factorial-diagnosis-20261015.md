# TSTEP / TMAX startup diagnosis (2026-10-15)

The full 34 ns strict comparison (run38774749514) still fails the unchanged1mV voltage bound: compact8.906847253mV and wire8.111543842mV. Tightening Newton tolerances did not remove the startup discrepancy. No source-bit, phase, observation window or device gate has been relaxed.

The original `.tran step stop 0 step` changes both TSTEP and TMAX. The [ngspice manual](https://ngspice.sourceforge.io/docs/ngspice-manual.pdf) distinguishes the suggested increment from the maximum integration step. That distinction motivates a factorial experiment; it is not evidence of the root cause yet.

The hosted controller restores the exact strict compact0.125ps source capture38763917040, hashes every archived input and repository circuit file, verifies the executable, and changes only the `.tran` parameters. It runs all four combinations of TSTEP/TMAX0.125ps and0.0625ps through1.2ns. All original models, sources, startup OFF flags, saves, solver options and zero operating point remain. Native raw files and logs are retained. The coarse diagonal is also compared with its original full capture through1.1ns to detect effects of shortening TSTOP.

This is a bounded startup diagnosis, never numerical or physical acceptance. The original0–34ns comparison remains failed until a valid full-capture rerun demonstrates otherwise. No startup removal, fitted timing, redefined oracle or passing substitute is permitted.

## Native result and next experiment

Run38777870655 reproduced the original prefix exactly through1.1ns. TSTEP alone changes at most37.6368nV, while TMAX alone reproduces8.906847247mV atv(mr). This rules out the TSTEP explanation for the millivolt discrepancy. All62startup flags and actual native option readbacks passed.

The refinement study holds TSTEP fixed, halves trap TMAX twice more, and compares trap with Gear2 at the original two TMAX values. Gear2 is a labelled numerical diagnostic: no device/source changes, minbreak remains1as, and no physical or full-wave acceptance follows from a short result. The next action depends on whether the differences converge, diverge or remain method-dependent.

## Refinement result

Run38778734039 failed to show convergence: successive trap differences are8.906847247,9.891831193 and12.234292598mV. Gear2 coarse/fine difference is8.317086327mV. No new long full-wave run is justified by this result. The native solver output says Sparse1.3. A separate KLU comparison now tests backend dependence with original circuit and tolerances, explicit availability preflight and actual native backend readback. [Official ngspice documentation](https://ngspice.sourceforge.io/applic.html) describes KLU as an optional alternative; its availability and numerical behavior in this executable must be measured.

## Matrix backend result

Run38780011601 completed the actual Sparse/KLU comparison. Native backend readbacks and all original startup controls passed. Backend differences were2.21823e-13V and3.39395e-13V at the two TMAX values; both backends retained8.906847247mV coarse/fine disagreement. Backend choice is ruled out as the significant source of this discrepancy. All three diagnostic receipts preserve original data and explicitly deny full-wave or physical acceptance. Next work must investigate frozen model evaluation and charge/bypass behavior with measured evidence, rather than repeat tighter timesteps or another backend.

## Charge-tolerance diagnosis

The captured strict native options retain chgtol1e-14C. The next experiment changes only this numerical tolerance to1e-20C at both original TMAX values. It also saves the exact frozen HBT/resistor model sources and native model parameter printout, for evaluation of active model features. Both requested and actual native tolerance are checked; source/device/geometry and full-wave acceptance remain unchanged. This is a hypothesis test, not a claim that the default caused the discrepancy.
