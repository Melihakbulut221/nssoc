# Strict PGO/LTO experiment for full32 fine capture

The prior strictO3 compiler experiment38845036374 reproduced the4ns/0.25ps reference exactly but was about2percent slower. The full34ns fine capture remains incomplete after its hosted timeout. It must not be replaced by a shorter or coarser passing capture.

This new hosted experiment trains the same patched upstream on the actual32stream macroRC tree for1.2ns with0.25ps maximum step and all3060vectors, then rebuilds with GCC profile feedback and link-time optimization. All source/PDK/OSDI/patch hashes, zero-sourceOP,604HBT OFF flags, Sparse options and numerical tolerances remain explicit. It preserves native gcda data and compiler commands. The exact same build directory avoids accidentally renaming the feedback source. Profile mismatch remains fatal; missing hotVBIC/Sparse profiles are rejected. Partial-training mode avoids assuming unexecuted functions are unimportant.

The optimized engine must pass the existing NPN/PNP1nA charge invariant and a fresh paired4ns capture against the frozen reference engine on the same CPU. Every3060voltage vector is compared in both interpolation directions with the original1nV limit. No fast-math, floating contraction, solver or circuit shortcut is permitted. Candidate status additionally requires at least1.25wall and CPU speed ratios; this is an experiment selection criterion, not a claim that a future34ns capture will finish. Fullcapture, timestep qualification, real intermacroRC/clock distribution, PVT/CDR/x4 and mainchip acceptance remain open.

Training success alone is never waveform-equivalence or PHY acceptance. Failed training/build/comparison logs and complete native evidence remain published. All execution and artifacts stay on GitHub; no local checkout or simulation.

Primary compiler references: [GCC instrumentation](https://gcc.gnu.org/onlinedocs/gcc-14.3.0/gcc/Instrumentation-Options.html) describes collecting and consuming native profile data; [GCC optimization](https://gcc.gnu.org/onlinedocs/gcc-14.3.0/gcc/Optimize-Options.html) documents profile use, partial training and LTO. These document the mechanism; only this repository's paired measurements can establish an actual speedup or numerical agreement.


## Preserved training and configure repair

Run 38860616186 completed the original 1.2ns/0.25ps real-tree training, but failed in Autoconf before the profile-use simulator build. No numerical comparison or speedup was obtained. Its complete training evidence remains in release `cloud-results-38860616186-1-tree32-pgo` (131270752-byte archive SHA256 `7087cc08148b4d8bac5fed0e7e416ed7e4e9c332cd9616211448c5f344d10fd8`).

Cloud diagnosis 38863174613 reproduced the exact GCC 13.3 failure: successive `conftest.c` programs used incompatible control-flow counters from the instrumented configure profile. Moving only the 128-byte `conftest.gcda` out of the feedback directory made configure succeed, with all simulator profiles unchanged. Summary SHA256 `f09529fdc6e2919de50467be800757282f682fd9f62964a0d259e78597d8df78`; original and corrected config logs are retained. The mismatch error remains enabled, as recommended by the [GCC documentation](https://gcc.gnu.org/onlinedocs/gcc-14.3.0/gcc/Warning-Options.html#index-Wno-coverage-mismatch).

`tree32-pgo-resume-cloud` restores the exact archived training, original source inputs and runtimes at the same paths. It verifies the compiler version and every original inventory entry before quarantining only that exact configure-test profile. It rebuilds the unchanged simulator, then restores the test profile and rechecks the original immutable prepared-state inventory. The expensive training is not repeated. The unchanged 4ns paired comparison, 1nV/1nA gates and both 1.25 speed-ratio gates remain required. The original failing workflow is retained as evidence; use this resume workflow for this completed training.

## Completed resume measurement

Run38863635146 completed the corrected build and paired4ns/.25ps comparison. All3060voltage vectors agree within the unchanged1nV threshold and use the same time grid. Wall speed ratio0.8901564276031141 and CPU ratio0.8901256676697386 fail the original1.25selection threshold: the PGO/LTO runtime is slower and is not selected for full fine capture. The original training, configure failure, isolated repair and all paired raw outputs remain in release`cloud-results-38863635146-1-tree32-pgo-resume`. This does not complete the34ns fine capture or any full-PHY gate.
