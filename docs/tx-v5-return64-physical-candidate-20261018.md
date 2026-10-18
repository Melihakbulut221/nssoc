# V5 original-placement return-rail candidate

The rejected full-wire v5 capture (39067769686) and its verified path review (39084981409) show about 0.172 V at the final selector tail emitters relative to the external return. Exact native device/geometry mapping (39085786545) places six failing HBTs in macro f and two in p8_7. Shortest raw resistor paths from the external AVSS port to the final tails are 16.18605 and 16.22470 ohm; these sums are not effective network resistance.

This candidate widens only five external TopMetal1 AVSS trunks and their bottom TopMetal2 bus from 32 to 64 um, retaining original 1000/600 um placement pitches, the actual v5 child drawings, 31 macros, 1674 native devices, 589 HBT instances and 719 emitters. Child stubs, the local final strap, power via arrays and signal routes remain unchanged. This is a physical experiment to reduce one measured failure mechanism, not an assumed cure for the other stage/clock failures.

The controller repeats the full native 560-category DRC, deep/flat LVS and five deliberate faults. It additionally compares flattened drawing regions against the exact v5 physical baseline from run39063951673 after undoing origin translations. Only union with the six explicit 64 um rectangles is allowed; unrelated added metal, removed device geometry and absent widening must be rejected. No old high3/tight/return64 model or proof is reused.

Next gates after physical success: regenerate native device/interface ownership, whole wire RC, exact composition and loaded original 256-bit waveform with unchanged voltage, margin and timing limits. All artifacts and rejected results remain on GitHub. Full serial Gen3 x4, clock distribution and mainchip integration are still open.

## Native physical result

Run39086629991 passed all560 DRC categories with zero markers, deep/flat1674device LVS and all five deliberate physical faults. The exact geometry comparison passed: only the six external AVSS rectangle unions changed; all three geometric corruption controls were rejected. The full receipt pins the native reports and every archive member. This does not prove electrical improvement.

The tx-v5-return64-extraction-cloud workflow now restores that exact archive, verifies every physical member, regenerates all4774 terminal references/3262probes and377wire components, then extracts fresh native R/C and repeats the unchanged13 raw RC corruption controls. No old resistance scaling or old extracted model is used.
