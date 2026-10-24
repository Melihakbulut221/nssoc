# Lower-output-impedance serializer candidate, 2026-10-17

Candidate budget_drive_v1 changes only four native output resistor geometries in each of the30pre-mux cells. All19HBT sizes per cell, final77emitters, clock source, inputs, original256bit/threephase oracle, startup, operating points and device limits stay fixed. Total719treeemitters/lane remains a census, not whole-chip emitter-budget acceptance.

The completed return64 physical waveform failed364of768serial samples and six HBT headroom bounds. Its native metal-only data measurements found95–254fFreference-shunt C plus separately retained interconductor coupling. A smaller output resistance is now tested as a circuit repair hypothesis. No native metal R/C is scaled or reused as a new physical model.

| Pre-mux type | XSP/XSN width,length (um) | XFPR/XFNR width,length (um) |
|---|---|---|
|28lower stages, Nx1 |1,3.6 ->4,3.6 |1,30 ->1,12.77 |
|2fast stages, Nx3 |1.5,1.8 ->6,1.8 |1.5,15.4 ->1.5,6.55 |

For a first-order constant collector current, output voltage is `(VDD-Ic*Rc)*Rf/(Rc+Rs+Rf)`. ReducingRs toRs/4 and scalingRf by `(Rc+Rs/4)/(Rc+Rs)=20/47` preserves this simple divider ratio while lowering its resistance. Geometric rounding is below0.1percent. Actual contacts, native compact parasitics, loading, temperature and self-heating invalidate treating that algebra as circuit equivalence; native nominal/hot/cold simulation decides the candidate. Four real parameter/connectivity corruptions per primitive and a full-tree deepest-selector fault retain independent failure evidence.

The controller hash-binds the original52999bc9 source and preserves its original all604HBT/512MOS captures and engineering reviewer. A schematic engineering failure now also fails the workflow after publishing its full report. Passing schematic tests will only justify producing fresh native GDS, DRC/LVS, terminal binding, extraction/composition and full-wire loaded cases. It does not close the serial PHY or mainchip integration.
