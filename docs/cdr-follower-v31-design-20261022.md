# v31 follower sink candidate

The actual v30 full-wave measurements show ac/bd follower collector current becoming nonpositive during10.7–15.9% of active samples. The early ac output differential falls to about-101.7/+98.3mV, versus approximately-274/+254mV for v29. C/D master inputs are weak and delayed. Both full nominal electrical cases remain rejected.

The changed v30 sampler resistor network pulls follower emitters upward more strongly. The observation is consistent with insufficient follower pull-down current; it is a design hypothesis, not proof of a completed repair.

This candidate changes only the two native rppd pull-down lengths from4.5um to2.25um at unchanged4um width. Two Nx4 HBTs, topology, substrate taps, seven ports and placement/routing algorithm remain unchanged. The layout top name remains nssoc_cdr_retime_follower_layout_v23 for direct parent replacement, but source/circuit/output hashes and v31 evidence identify the changed device geometry. Resistance does not scale exactly with length because contact resistance remains; actual native models and extraction determine performance.

The cloud leaf run requires all560 DRC categories, unsimplified deep/flat8-device LVS, four reference faults and three physical faults. The intentionally wrong resistor reference remains1.7um, distinct from2.25um. Passing these gates is only leaf physical acceptance.

Next: replace only ac/bd leaves in the actual476-device v30 parent, recheck parent geometry/DRC/LVS, regenerate wire/intrinsic-MIM parasitics, and rerun the original34.25ns/256bit full-wave matrix. Keep8GHz,150fF/50fF loads, all transistor limits,100mV/37.5ps sampler requirements and phase/current gates unchanged. A/B timing remains unresolved even if C/D drive recovers.
