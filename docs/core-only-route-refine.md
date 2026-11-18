# Continued routed repair

The first routed repair (run44247595292, source ef88f086feac84f64b48cf77018fe0a92346bfb2) was independently verified: native artifact14402989198 SHA256938d630865cab913e1321ea3ea3802b7318c9da24a81527b66a7c11fcfd6898d, all217 output hashes, and six fresh corner metrics. Final slow setup369, worst -1.06756ns; hold0 in all corners; slew18/0/0, cap7/7/7, fanout748/748/748. Timing remains failing.

The worst final slow path starts at processor csr_addr[11], from $auto$ff.cc:337:slice$71813 to $auto$ff.cc:337:slice$72266. The repair used -max_iterations100, inserted57 setup buffers, resized45 instances, swapped23 pins, and inserted28 hold buffers. RSZ-0062 explicitly reports incomplete setup repair. Whether the bound rather than local search convergence caused termination is not established by the inspected excerpt.

Intermediate global-routing optimization emitted EST-0026 warnings; all three final independent STA process logs have zero EST-0026 occurrences. Global-route estimates are not detailed-route/extracted RC signoff.

The new trial restores all authenticated upstream archives and the saved final postGRT database, verifying every output, protected input, and all six baseline metrics before continuing electrical and timing repair. It keeps the native100-iteration setup/1000-iteration hold bounds, 20ns clock,5% derate and propagated clocks. It saves per-corner deltas rather than accepting any result automatically. Further improvement is a hypothesis to test, not a promised pass.

The separate CTS8 candidate's fanout1 result is NOT incorporated here. Its bus-clock root still drives16loads vs8limit and SRAM A_MEN slew remains. That topology branch still requires ECO and routed comparison. No physical signoff or production approval is claimed.
