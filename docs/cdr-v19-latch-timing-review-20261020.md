# CDR selector v19: actual latch timing diagnosis

The original complete early and late v19 captures from run 39400191012
failed loaded electrical acceptance. This read-only cloud analysis restores
those immutable raw files and the actual v19 MIM geometry from run 39397118280.
It reproduces all 116 original HBT bounds and all four sampler checks exactly
before diagnosing individual master/slave terminals and clock steering.

The v16 diagnostic is retained as a hashed baseline. An exact edit manifest
changes only the source receipts, physical-model census, output names and
checks for the actual 32 Nx4 selector HBTs. The 32 sampler data/hold HBTs
remain Nx8. Every physical parallel selector base combination is preserved.
No stimulus, sample phase, acceptance threshold or native waveform is changed.

The original wrong/low-margin samples remain rejected. Internal 100 mV
markers and nearest clock crossings are diagnostic observations, not
new acceptance criteria or causal-delay proofs. The external clock used
by the source experiment still does not demonstrate a complete closed-loop PHY.

Both cases execute entirely on GitHub Actions. Only the diagnostic,
checksums and input provenance are published; large original waveforms
remain in their source releases. Analysis results are pending.

Initial diagnostic run 39413465640 stopped before analysis because the compact
receipt omits the large native vector map and was compared as an entire object.
The comparison now checks every stored compact capture field against the
SHA-bound full report. Subsequent raw reader equality still compares the full
capture to the original full report, including every vector. No raw field,
numerical gate or sample has been removed from that reproduction check.
