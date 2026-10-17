# XOR full-wire v3 rejected; output-shunt repair candidate v4

Actual v3 full-wire39045821084: nominal768correct,112.753734mVminimum, all19HBT bounds pass; hot768correct,124.121245mVminimum but12data HBTs fall below the unchanged0.4V active VCE bound (minimum0.335749V); cold768correct but12samples below100mV, minimum99.267090mV. Swapped output768wrong detected. No native numerical diagnostics; failed traces and all original gates are retained. Component/PHY acceptance remains false.

Candidatev4 changes only the two native output-to-AVSS shunt lengths from4.5um to8um at fixed8um width, keeping the two1.8um/18um collector loads,1.8um/8um output series resistors, all HBT sizes and27finitebodycontacts unchanged. Increasing shunt resistance should reduce static collector loading and resistive division, potentially recovering both hot collector headroom and cold output margin. This is a circuit hypothesis; output common mode, settling and all device bounds must be measured. No gain or timing margin is inferred from an estimated resistor ratio.

The frozen original34ns/256symbol8GT/s schematic campaign,19OFF readbacks,zero-sourceOP,100mV/0.4..1.6V/current bounds and actual output-swap control remain identical. Native physical generation,560categoryDRC/deepflat54LVS,faults,newparentmetalRC and loaded waveforms are required if schematic screening passes. No reuse or rescaling ofv3physicalRC is permitted. This does not yet implement sample alignment, common-mode conversion, a recovered clock or fullCDR/x4PHY.

All work remains cloud-only; local workspace empty. Active route39045601192, PLL39043210978, nativeboot39041981816 with placementhandoff39042752404 and TX39030593206 must not be restarted solely while live.
