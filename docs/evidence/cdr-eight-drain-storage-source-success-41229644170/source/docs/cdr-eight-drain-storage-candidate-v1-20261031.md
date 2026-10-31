# Loaded CDR storage candidate v1

The original vi_bias_off job failed its unchanged 16 GiB initial storage gate before creating a result. Its always-publication step then reported a missing result. The original source did not save the actual free byte count. Full checkout of 33,275 files is observed, but its contribution to low disk space is not measured.

The new separately named stage creates an outer result before storage qualification, writes an exclusive fsynced storage record containing actual free/required bytes before refusal, and retains the primary failure through the existing finalizer/publisher. Native acquisition and execution are not reached after insufficient storage. Initial 16 GiB, copy/publication max(4 GiB,2*source_bytes+1 GiB), every original worker byte, all analog limits and the entire original1961-file protection map remain unchanged.

The source-only workflow uses pinned actions/checkout11bd71901bbe5b1630ceea73d27597364c9af683 with exact anchored sparse paths and noncone mode. Explicit filter is omitted: the pinned action chooses blob:none for sparse checkout. Actual disk is measured before/after checkout. The closure includes all1961 original protected files, the original manifest, three additional transitive Python sources identified by source-only AST inspection, and all new source files. Hardware flow imports remain in the original protected set.

The native CLI is unconditionally disabled. This is a storage/source candidate, not a single-case execution admission. A separately reviewed exact-source vi_bias_off admission, successful same-source controls, fresh empty reservation and explicit native activation are required later. It must not rerun nine completed cases, lower disk/electrical limits, delete source/evidence or infer PHY acceptance.

Validation is entirely GitHub-hosted: complete frozen current source controls, actual boundary/refusal journal tests, original production publication fixtures with the new stage, and an actual outer failure lifecycle with native functions forbidden. No native archive/model/waveform is acquired by these controls.

Official checkout sources: https://github.com/actions/checkout/blob/11bd71901bbe5b1630ceea73d27597364c9af683/action.yml and https://github.com/actions/checkout/blob/11bd71901bbe5b1630ceea73d27597364c9af683/src/git-source-provider.ts .
