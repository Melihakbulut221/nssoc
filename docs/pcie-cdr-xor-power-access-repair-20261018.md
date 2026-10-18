# CDR XOR local power access repair

The failed native PD484 waveform and source-bound power diagnosis39135161442 identify actual local power losses. XOR y MOS source XD0044 has effective AVSS resistance60.9574ohm; branchR2412 alone is50.2884ohm. Native coordinates place its terminal at(1653.75,4032.45)um and the riser start at(1644.6,4000.85)um. The physical XOR generator accesses a64um MOS source stripe only near its bottom, through one column of vias and a0.4um Metal3 escape. The parent M6 riser starts after that local access and cannot bypass its loss. The AVDD load resistorXD0259 has a16.3443ohm local access segment before its existing riser.

The v4 candidate retains the59 actual devices, transistor sizes, schematic, all original routes and finite substrate contacts. It adds actual Metal1-to-Metal3 vias along each of three MOS source stripes at4um pitch, including the strip midpoint, joined by0.4um Metal3. It also widens only AVDD rppd Metal3 horizontal escapes from0.4 to1.2um. The source strap stops below the existing drain escape. Every via is generated from the native PDK; no ideal electrical aliases or resistance scaling are introduced.

Native560-category DRC, unsimplified deep/flat59-device LVS and all seven actual fault checks are unchanged. Passing this leaf does not establish parent connectivity, resistance reduction, sampling, phase direction, device voltage bounds or fullPHY acceptance. Require an independent geometry/device conservation check, parent integration, fresh native MIM-awareRC and original full loaded transients before acceptance. All rejected candidates and source waveforms remain archived.


## First physical rejection and isolated correction

Run39137391978 generated the candidate, then failed the real560-category DRC with15 markers: M1.b6, M2.b3, V1.b3 and V2.b3. LVS was not reached. All failed geometry remains archived. Its recorded source-via centers show one0.4um pair on each of the three MOS stripes: the mandatory stripe-midpoint via was too close to the regular4um-pitch via. This is consistent with the observed metal/via spacing failures. The next candidate keeps the exact midpoint and both end access points, omits a periodic via within1.5um of a retained center, and asserts the actual retained-center spacing. Transistor sizes, M3 escape widths and all physical gates remain unchanged. Actual DRC/LVS must validate the correction; this is not a waiver.


The spacing-corrected run39137767974 passed all560 DRC categories with zero violations, unsimplified deep and flat59-device LVS without extraction diagnostics, and all seven real faults. This proves only the leaf physical checks. Independent drawing conservation and full PD484 integration/extraction/transient validation remain mandatory.


## Full parent integration candidate

The next cloud run restores the verified new XOR cell and the seven unchanged child types. An independent KLayout comparison reconstructs every leaf drawing layer from the original cell plus only native source-via stacks, source Metal3 straps and AVDD rppd Metal3 widening. It checks original device/route/port/boundary metadata and identical schematic/LEF except the top name, and rejects three actual drawing mutations. The16-macro/41-card parent plan changes only the XOR physical master; all484 devices and25 public ports remain. The established base placement and supply-riser methods are unchanged. Fresh native parent DRC/LVS and physical faults precede any new extraction or loaded waveform acceptance.


## Full parent physical result

Run39139188554 passed the independent22-drawing-layer XOR reconstruction, native560-category DRC with zero violations, unsimplified deep/flat484-device LVS and five actual parent faults. The checker coordinate issue was an integer-overload ambiguity in DTrans, not a defective PDK pin: explicitly floating-point translation restored exact full pin containment and actual native MOS Metal1 conservation. Both failed preparation runs are retained. The leaf comparison's legacy fault label `changed_original_device_layer` removed Metal4 geometry; it is an unrelated original-drawing fault, not an active-device fault.

The next stage independently compares every whole-parent drawing layer against the original parent plus only the two placed XOR leaf deltas, then binds all158 child/public planes,51 nets and1394 device terminals with the original19 corruption controls. Physical acceptance does not establish lower loaded rail loss or correct sampling; fresh MIM-awareRC and full original transients remain required.


Run39139774141 verified all28 parent drawing layers against the original parent plus exactly the two actual XOR leaf additions. All16 placements, routes, public ports, supply overlay and484 reference devices/connections are unchanged; three actual geometry mutations were rejected. All158 child/public planes,51 nets and1394 native terminals bound successfully with19 fault controls. The next cloud stage recovers exact primitive pin annotations and binds the921 metal terminals,473 retained intrinsic body references and25 public ports for fresh RC extraction.
