# Pad current diagnostic continuation

The user confirmed package, PCB, external devices and interface rates are not yet selected. Experimental clamp/load values are not a qualified product IO contract. Continue internal timing and native pad characterization; external IO closure must await explicit interface/load budgets.

Initial SPICE run 44364763413 at cdd5d2f1d37dac48569cf24a08a51884c44542e8 failed. Artifact 14454199956 SHA256 3ba1ae242a3c0e8ed765604ebf0eb2b9f8ebf6ed10e194b202049b717b76dc3e verified. The simulator returned code 0 despite an aborted transient at 22.7529 ns (vsense branch). The runner rejected the diagnostics; no partial waveform was accepted. An initialization-path warning was also present.

New candidate provides an explicit minimal startup file containing only num_threads=1 through documented SPICE_SCRIPTS. All three required OSDI models remain explicitly loaded by their original pinned paths. Use Gear integration maxord=2 and 5 ps maximum step, leaving device models, supply voltages, temperature, ideal pad clamp, stimulus, convergence tolerances and native initial DC solution unchanged. No uic/nodeset/forced initial state. Require complete finite 50 ns captures and no numerical warnings/errors. Passing this test does not qualify Liberty edits or physical pad signoff; timestep/solver independence is still needed.
