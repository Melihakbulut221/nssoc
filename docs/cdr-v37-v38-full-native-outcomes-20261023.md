# CDR v37/v38 complete native outcomes

All eight cases complete the same34.25ns,113475-row,1104-column capture without native numerical diagnostics and retain passing original device gates. All eight reject full data/phase/current acceptance. Immutable release/source/capture SHA256s are in the corresponding evidence receipts.

v37 balanced input/bias widths6/8um worsen C/D against the matching v36 load12 parent. Width6 gives64 wrong apertures in each C/D stage in both early/late cases. Width8 gives C128 in both cases,D166early/122late. Width8late alone passes phase and VI criteria while data is incorrect, which cannot qualify the circuit.

v38 reduces only slave data/hold HBT emitter count from6 to5 or4 on v36 load10. Early A and B pass both variants; late A still misses the original100mV/37.5ps gates. Both C/D fail every case. For area5, C/D wrong apertures are18/4early and1/2late; area4 gives32/6early and12/5late. Smaller area is therefore not a complete repair or an accepted direction to continue blindly. No candidate is promoted to physical or full-loop acceptance.

The v36/v37 controlled loading diagnostic is run39867076460 at02623b5abf1d3da2966cc9b09144863f27893bca. It compares actual same-gate complete capture data before selecting another circuit. The separate actual17-PCell inventory establishes a54um MOS placement-envelope mismatch requiring real layout replanning and full DRC/LVS/fresh RC. No guard or foundry rule is waived.
