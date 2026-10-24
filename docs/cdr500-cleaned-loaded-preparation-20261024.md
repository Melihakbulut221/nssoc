# Fresh PD500 loaded-wave continuation prepared

The runner is prepared but has no workflow or dispatch until the current MIM-aware two-order precision and composition result passes. It restores that new immutable composition and the cleaned parent planes; it cannot substitute the old PD476 RC or model.

The full 10-case list and original 34.25 ns, 256-bit stimulus, 0.3125 ps timestep, sampling margins and settling deadlines, VI phase/current and device-voltage limits remain unchanged. All 124 HBTs and 50 MOS devices are measured at their actual native terminals. The four added 53.335 um gain MOS devices belong to two actual parallel drain groups, one under irc and one under ird. Their summed instantaneous stage currents face the same 0.5 mA gate as existing sampler stages; every individual device still faces all original voltage and nonnegative-current gates. Native geometry proves two 36 um four-device sampler tails plus one 53.335 um two-device gain tail in each C/D sampler.

A preparation-only mode verifies the actual fresh netlist, native plane binding, all saved voltage/current vectors, 13 corruption controls and original complete stimulus before any simulation. It makes no transient or electrical acceptance claim. The streamed capture and electrical checks remain required for every actual waveform run.

## Native prerequisite passed; gated workflow activated

Run 40079062179 passed both native precision orders, all raw/intrinsic controls and fresh composition with 500 devices, 24,550 resistors and 15,678 capacitors. Its immutable receipt is now pinned in the loaded method manifest. The new workflow `cdr500-cleaned-loaded-cloud.yml` first runs `prepare`; only success permits the ten `loaded (case)` jobs. At most two waveform cases run concurrently. Every case uses the same complete source-bound composition and publishes its full native pass or rejection evidence. No loaded acceptance is claimed until those jobs pass their original electrical gates.
