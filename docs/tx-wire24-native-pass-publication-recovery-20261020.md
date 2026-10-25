# TX wire24 extraction passed; recover publication failure without rerunning CAD

Run39340687625/source1b51dd2c56591b87b3b614c28315d4d44bd51d4f
passed the native extraction step and emitted
PASS_ACTUAL_NATIVE_RC_GRAPH_AND_13_FAULT_CONTROLS_REQUIRES_WAVEFORMS.
Its release creation then received GitHubHTTP500, so the overall run remains
failed. The fallback artifact upload completed successfully.

Recovery is bound to artifact12228916534,19967840bytes,
SHA256d4cd6d865458e1bc69ff3545105bc52ac93e9ea0186b33258cdceac89f471bbe.
The cloud job verifies original run/head/step outcomes, artifact identity,
archive digest and safe member paths. It preserves the original report bytes,
all source physical hashes and every extracted file, and verifies native
377-component/4774-terminal census plus all13raw corruption controls.

It publishes these unchanged results under the original run's result tag,
with explicit recovery provenance and a separate recovery receipt. Native
CAD is not repeated and the original workflow failure is not relabeled.
Release lookup precedes any retry of uncertain creation. Existing asset
differences are never overwritten. New archive packaging has its own hashes;
original file hashes and the original native summary remain unchanged.
