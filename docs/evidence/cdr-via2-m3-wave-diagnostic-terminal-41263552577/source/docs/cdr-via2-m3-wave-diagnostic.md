# Existing loaded waveform diagnosis

This workflow diagnoses the complete raw capture from rejected loaded run
41260582673. It does not change or run the analog circuit. All native acquisition,
archive parsing, controls and numerical processing happen on GitHub runners.

The exact original reader from source 84b8b591e10be32716947c8d6b079fd7a21ce18d
is hash-bound and only its digest/read_streamed_wave definitions are loaded.
All four native archive parts, their combined hash, and every one of the 113
archived files are checked. Only the original wave.raw is materialized for
analysis. No native bytes are emitted to local-bound logs.

The original parser must reproduce the complete capture record, all 124 HBT
metrics, six stage metrics, all 1,530 per-bit timing values, and phase/VI values.
The active device mask remains t >= 2 ns, with UI 125 ps and step 0.3125 ps.
Only after that agreement does the report locate the actual low-VCE events of
T061/T062/T115/T116, their collector/base/emitter voltages and collector currents,
and simultaneous recorded clock/data/bias/output voltages. Every contiguous
below-VCE interval and every under-100-mV sampler/XOR sample is retained.

The seven hosted source controls exercise the unmodified raw reader, original
current-vector aliases, finite/complete/monotonic raw requirements, the exact
active mask, known margin/sign events and complete archive ownership/digests.
Source-controls run independently before the actual diagnose mode is dispatched.

Results preserve primary failures, input metadata, full derived reports and
cloud-only partial acquisitions on failure. Native originals remain on release
430292142. Successful diagnostics are not proof of a causal repair, closed-loop
CDR operation, a full serial Gen3 x4 PHY, or final chip timing.
