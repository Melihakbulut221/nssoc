# Actual PLL raw-column reader qualification

The observed capture has5106 columns, including internal voltages and17 currents. New cloud qualification checks exact inclusion and voltage units for1694 unique prepared vectors covering2737 native terminals, against the original circuit and instrumentation. Missing vectors fail.

A separate reader candidate binds the entire observed raw table and checks all values for finiteness and all sample times for strict monotonicity. It rejects table identity/type changes, omitted requested or extra columns, truncated payloads and mismatched point counts. Full capture retains the original1us interval, more than3million rows and at most.3125ps maximum step. Lock/safety analysis is a separate mandatory gate.

Qualification uses the actual saved native prefix plus explicit synthetic corruption fixtures spanning a reader chunk boundary. Only a temporary short-prefix test fixture has its point count set to its complete rows; the preserved source remains byte-identical and the fixture must fail full-capture acceptance. Extra internal-voltage NaN and source-current infinity must be rejected. This candidate is not yet wired into the live simulator/controller; original source contracts and frozen reader remain unchanged.

No claim of complete acquisition, lock, safety, full-capture capacity or PHY acceptance follows from reader tests.
