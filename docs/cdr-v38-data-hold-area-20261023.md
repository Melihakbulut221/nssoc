# v38 slave data/hold capacitance candidate

Complete v36 load10 results leave A very close to the unchanged37.5ps requirement:37.656ps early and37.969ps late. B passes both; C/D and phase/V-I still fail. No failing result is rounded or promoted.

This bounded candidate compares five and four emitters against the parent's six, only on the16 slave data/hold HBTs. It keeps the parent54um slave MOS drive, Nx3 selectors,1.0um collector loads and slave bleeds. Smaller intrinsic data/hold capacitance may reduce loading on the master outputs and accelerate settling. Actual current, headroom, gain, timing and phase effects must be measured, not inferred.

The parent worst observed data/hold current per emitter is about1.780mA at Nx6. Scaling the *old* total current to Nx4 would suggest about2.670mA per emitter, below the3mA gate, but the modified circuit can redistribute current and that estimate is NOT a safety result. Both variants undergo the original complete device/phase/data checks.

The unchanged controller is reconstructed byte-for-byte with only the disclosed namespace/choice/protected-file edits. Five negative geometry controls reject the wrong parent emitter count, wrong emitter dimensions and undeclared target counts. The existing diffusion corruption controls remain. Candidate reversal must recover the complete original476-device composition; all17918R/12850C wire cards remain unchanged. Data_area4 has48 changed native primitives versus the original baseline; data_area5 has64. Relative to v36 load10, each changes only16 HBT counts.

Both early/late cases retain8GHz clocks, all256 bits,34.25ns/1104columns,150fF/50fF loads,100mV/37.5ps output predicates and original per-device/phase/current limits. The v36 MOS diffusion hypothesis and frozen wire RC remain disclosed. Any useful candidate still requires actual new GDS/DRC/LVS/fresh RC and complete PVT/timestep/closed-loop qualification. This test is independent of v37 C/D input-bias changes; combining useful results would require another full validation.
