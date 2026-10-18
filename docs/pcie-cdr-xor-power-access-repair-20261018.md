# CDR XOR local power access repair

The failed native PD484 waveform and source-bound power diagnosis39135161442 identify actual local power losses. XOR y MOS source XD0044 has effective AVSS resistance60.9574ohm; branchR2412 alone is50.2884ohm. Native coordinates place its terminal at(1653.75,4032.45)um and the riser start at(1644.6,4000.85)um. The physical XOR generator accesses a64um MOS source stripe only near its bottom, through one column of vias and a0.4um Metal3 escape. The parent M6 riser starts after that local access and cannot bypass its loss. The AVDD load resistorXD0259 has a16.3443ohm local access segment before its existing riser.

The v4 candidate retains the59 actual devices, transistor sizes, schematic, all original routes and finite substrate contacts. It adds actual Metal1-to-Metal3 vias along each of three MOS source stripes at4um pitch, including the strip midpoint, joined by0.4um Metal3. It also widens only AVDD rppd Metal3 horizontal escapes from0.4 to1.2um. The source strap stops below the existing drain escape. Every via is generated from the native PDK; no ideal electrical aliases or resistance scaling are introduced.

Native560-category DRC, unsimplified deep/flat59-device LVS and all seven actual fault checks are unchanged. Passing this leaf does not establish parent connectivity, resistance reduction, sampling, phase direction, device voltage bounds or fullPHY acceptance. Require an independent geometry/device conservation check, parent integration, fresh native MIM-awareRC and original full loaded transients before acceptance. All rejected candidates and source waveforms remain archived.


## First physical rejection and isolated correction

Run39137391978 generated the candidate, then failed the real560-category DRC with15 markers: M1.b6, M2.b3, V1.b3 and V2.b3. LVS was not reached. All failed geometry remains archived. Its recorded source-via centers show one0.4um pair on each of the three MOS stripes: the mandatory stripe-midpoint via was too close to the regular4um-pitch via. This is consistent with the observed metal/via spacing failures. The next candidate keeps the exact midpoint and both end access points, omits a periodic via within1.5um of a retained center, and asserts the actual retained-center spacing. Transistor sizes, M3 escape widths and all physical gates remain unchanged. Actual DRC/LVS must validate the correction; this is not a waiver.


The spacing-corrected run39137767974 passed all560 DRC categories with zero violations, unsimplified deep and flat59-device LVS without extraction diagnostics, and all seven real faults. This proves only the leaf physical checks. Independent drawing conservation and full PD484 integration/extraction/transient validation remain mandatory.
