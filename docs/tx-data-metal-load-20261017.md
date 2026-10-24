# Actual TX data-metal load diagnosis, 2026-10-17

Cloud run39049047760/source4e571cab analyzed the exact return64 model that failed loaded serial transmission. The original114909R/76614C/1674devices are retained; all60intermacro data nets bind independently to their three actual receiver HBT bases and both source resistor terminals. Analytic/dense controls, sparse KCL residual, reciprocity and dissipated-power checks pass. This is a metal-only diagnostic, not transient or PHY acceptance.

| Receiver interface | Original reference-shunt C per conductor | Metal effective R from source resistor terminal to receiver base |
|---|---:|---:|
| level16 |95.22–109.07fF|26.46–28.77ohm|
| level8 |115.63–128.28fF|27.41–29.72ohm|
| level4 |138.71–189.84fF|28.66–32.81ohm|
| final |241.88–254.19fF|26.67–29.10ohm|

Actual interconductor coupling remains separate; summing it as capacitance to ground or using these figures as an eye prediction would be invalid. There are no within-conductor capacitors among these60nets. Semiconductor compact-model capacitances and native output resistor impedance are not part of these metal-only numbers. Source output series geometry at the lower stages is1umwidth/3.6umlength; output shunt is1um/30um. Final-input drivers use1.5um/1.8um series and1.5um/15.4um shunts. No resistor geometry or threshold was changed by this diagnosis.

Together with preserved waveform diagnosis39046963485 (clock public-to-selector delay under0.5ps; first wrong data signs at level8), these results motivate studying actual loaded driver/interstage placement changes. They do not establish which remedy will pass. Fresh transistor simulation, new physical geometry, native DRC/LVS, extracted RC and unchanged bit/device criteria are mandatory for any accepted repair. Six HBT headroom failures in the final macro remain separate explicit failures.

Initial diagnostic39048432696 failed because its parser incorrectly assumed all C were shunts. The corrected diagnostic preserves both terminals and all76614capacitors, separating reference-shunt and interconductor coupling. Original failed run and original serial waveform are retained. Full hash-bound evidence is in docs/evidence/tx-return64-data-network-20261017.json and the linked source release.
