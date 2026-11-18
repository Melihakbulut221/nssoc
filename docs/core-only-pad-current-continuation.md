# Pad current diagnostic continuation

The user confirmed package, PCB, external devices and interface rates are not yet selected. Experimental clamp/load values are not a qualified product IO contract. Continue internal timing and native pad characterization; external IO closure must await explicit interface/load budgets.

Initial SPICE run 44364763413 at cdd5d2f1d37dac48569cf24a08a51884c44542e8 failed. Artifact 14454199956 SHA256 3ba1ae242a3c0e8ed765604ebf0eb2b9f8ebf6ed10e194b202049b717b76dc3e verified. The simulator returned code 0 despite an aborted transient at 22.7529 ns (vsense branch). The runner rejected the diagnostics; no partial waveform was accepted. An initialization-path warning was also present.

New candidate provides an explicit minimal startup file containing only num_threads=1 through documented SPICE_SCRIPTS. All three required OSDI models remain explicitly loaded by their original pinned paths. Use Gear integration maxord=2 and 5 ps maximum step, leaving device models, supply voltages, temperature, ideal pad clamp, stimulus, convergence tolerances and native initial DC solution unchanged. No uic/nodeset/forced initial state. Require complete finite 50 ns captures and no numerical warnings/errors. Passing this test does not qualify Liberty edits or physical pad signoff; timestep/solver independence is still needed.

## Gear2 readback correction

Run 44365737463 / 8948d901727f99ee73c64666cd17bc24efca34ea failed. Artifact 14454989944 SHA256 ac1ca2f13fd4dbfae191a192f84ce9667424b89287350db4d1411484a773d24c. Initialization warning was removed, but transient stopped at the same 22.7529 ns. Pre-analysis option output still said TRAPEZOIDAL; .options in the deck alone does not prove the method active at the requested reporting point. Next run explicitly issues control option method=gear maxord=2 and requires post-transient native readback. It rejects incomplete capture and timestep failures unchanged. The exact normal option-summary line Truncation error correction, charge based, is selected: is no longer misclassified as an error; no other diagnostic suppression is added.
