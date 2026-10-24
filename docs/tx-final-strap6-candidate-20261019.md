# Final TX return strap candidate, 2026-10-19

Native return diagnosis run39215983203 completed. Actual final-tail return resistances are4.894224347 and4.908058529ohm. The common resistorR105585 carries the full diagnostic unit current and contributes0.706551ohm. These are static extracted-network measurements, not dynamic rail-loss predictions; the dominant branches have not yet been localized to individual metal rectangles.

The new candidate widens only the existing final emitter TM1 strap from4to6um. It retains the baseline2x2 topvia and all lower access arrays. A previous12um/4x4 combined change shorted AVSS/SUB; that failed candidate remains rejected. The6um change is an engineering experiment, not a proven fix. No resistance is scaled in a model.

Before native checks, an independent whole-GDS comparison must prove exactly the prescribed added TM1 region, unchanged other drawing layers, ports, placement, reference circuit and via geometry. Three deliberately corrupted geometries must be rejected. The original1674-device deep/flat LVS,560-category DRC and transistor/connectivity fault controls remain required.

If physical checks pass, extract fresh native RC and rerun the full loaded32:1 waveform with the original256 source bits, sample phases and all HBT/MOS limits. A physical pass alone does not accept the serializer, serial Gen3x4 PHY, mainchip or production.

CDR run39215582013 reproduces the rejected input-drive-v10 gates. A/B pass the0.6UI and0.9UI sample points, but fail the required0.3UI point; C/D still have later errors. No observation phases or acceptance thresholds were changed. Both nominal input-drive full-wave tests remain rejected.

All execution and artifacts stay on GitHub-hosted runners. Mainchip route39202263552 remains a separate running experiment, not a timing pass.

## Native physical result

Run39217390888 at9be1ff7728c315c8b895ac02a7359e4ff1cabc03 passed the exact whole-GDS strap delta and its three corruption controls, deep/flat1674-device LVS,560-category DRC with zero markers, and the five original transistor/connectivity/grid fault controls. The original via geometry is unchanged. Fresh native RC extraction is the next gate; electrical acceptance remains false.

## Fresh native RC

Run39218007063 at1912e5b305e90ad4b795dc3e85b54b8faa96398c passed the original native graph, terminal ownership and capacitance conservation checks and13 raw-corruption controls. The new graph has116611 resistors and77514 capacitors across377 metal components, with1674 devices and3262 physical probes. Counts happen to match the old graph; values come from the new geometry and are not copied or scaled. Intrinsic body spreading and RF qualification remain outside this extractor. Full-device composition and loaded electrical tests are still required.

## Full-device model composition

Run39218951433 at0a38fc8312e4d5252038502044653ca493491990 passed full1674-device composition with the fresh116611R/77514C graph, six original composition corruption controls, and native binding of124 input legs to372 data bases. No ideal intermacro aliases or duplicate child parasitics were inserted. The next workflow runs the original full256-bit34ns loaded32:1 waveform and an actual swapped-leaf-select fault. All604 HBT and512 MOS limits, source bits, output phases, driver loads, clock references and solver settings remain unchanged; only the source-bound physical core model changes. This is still not a complete PLL/CDR or four-lane PHY.

## Model identity and simulation preflight

Run39219922079 stopped before SPICE because the old builder correctly rejected the new model hashes. Run39220553663 then independently matched all1674 compact devices using their physical positions within named macros, preserved all parameters and terminal topology, and rejected missing-device, changed-parameter, wrong-terminal and swapped-physical-identity corruptions. A separate strap6 builder now admits only the two verified new model hashes; its stimulus, solver, sample phases, device limits and review code are byte-preserved apart from the declared model binding. Its clock adapter only changes the imported builder module. Earlier preflight failures remain recorded.

## Measured static effect

Run39221326203 reduced the two final Nx8 tail return resistances from4.894224347/4.908058529ohm to4.805920344/4.816902225ohm (mean4.901141438 to4.811411285ohm). The sharedR105585 branch remains0.706551ohm and carries the full diagnostic unit current. The local strap improvement is modest; this does not predict a waveform pass. A read-only cloud review now locates the dominant branch endpoints in the exact native extractor coordinates before choosing another geometry change. Full waveform run39221063981 and mainchip route39202263552 are still running.
