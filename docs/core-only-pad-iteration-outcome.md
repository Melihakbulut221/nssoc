# Pad iteration outcome and complete controls

Run44369604102/head6a39f0b767bb30b7bd78eeb6d2030249bf377e06: both itl4=100 and1000 failed at22.7529ns/vhold#branch with native Gear2 and iteration readback confirmed. Each artifact's archive digest and all64 declared output hashes were verified.

- itl4=100 artifact14459410807 SHA256225aad91071623b107d07b14c22c8f85e5d8b7a8381f6b5355afea26637ffeb9
- itl4=1000 artifact14458993979 SHA25609ad482e2cdf1f2e013ad07502fe599f9d5cbe64bfe07e79b1ad4a949f058713

Higher Newton iteration limits did not cure the failure. No incomplete capture is accepted. Next execute all six independent cases using unchanged itl4=100, circuit, PVT and tolerances; the new information is the constant controls and second data polarity, formerly skipped after first failure. The aggregate must fail if any capture fails.

The case-continuation failure-injection test passed on GitHub run44370319407/head d53da4e5b58edcc335c0c8290605a4b002e319a5 (native job log:1passed in0.22s). Both runner and test Git blobs match this candidate. This proves error propagation, not transistor behavior.

Capacity: cancelled only duplicate checks44367860149 after exact comparison from893e6e8007a56928b3221c1f5612723412af0bc0 proved only pad runner/workflow/doc changes. Earlier checks44365289855 remain active with identical RTL/formal sources. This released runners and all three previously queued diagnostics started. No physical job cancelled. Main route44337630426 remains active; inspect exact run before advancing to extraction.
