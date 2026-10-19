# Final TX return strap candidate, 2026-10-19

Native return diagnosis run39215983203 completed. Actual final-tail return resistances are4.894224347 and4.908058529ohm. The common resistorR105585 carries the full diagnostic unit current and contributes0.706551ohm. These are static extracted-network measurements, not dynamic rail-loss predictions; the dominant branches have not yet been localized to individual metal rectangles.

The new candidate widens only the existing final emitter TM1 strap from4to6um. It retains the baseline2x2 topvia and all lower access arrays. A previous12um/4x4 combined change shorted AVSS/SUB; that failed candidate remains rejected. The6um change is an engineering experiment, not a proven fix. No resistance is scaled in a model.

Before native checks, an independent whole-GDS comparison must prove exactly the prescribed added TM1 region, unchanged other drawing layers, ports, placement, reference circuit and via geometry. Three deliberately corrupted geometries must be rejected. The original1674-device deep/flat LVS,560-category DRC and transistor/connectivity fault controls remain required.

If physical checks pass, extract fresh native RC and rerun the full loaded32:1 waveform with the original256 source bits, sample phases and all HBT/MOS limits. A physical pass alone does not accept the serializer, serial Gen3x4 PHY, mainchip or production.

CDR run39215582013 reproduces the rejected input-drive-v10 gates. A/B pass the0.6UI and0.9UI sample points, but fail the required0.3UI point; C/D still have later errors. No observation phases or acceptance thresholds were changed. Both nominal input-drive full-wave tests remain rejected.

All execution and artifacts stay on GitHub-hosted runners. Mainchip route39202263552 remains a separate running experiment, not a timing pass.

## Native physical result

Run39217390888 at9be1ff7728c315c8b895ac02a7359e4ff1cabc03 passed the exact whole-GDS strap delta and its three corruption controls, deep/flat1674-device LVS,560-category DRC with zero markers, and the five original transistor/connectivity/grid fault controls. The original via geometry is unchanged. Fresh native RC extraction is the next gate; electrical acceptance remains false.
