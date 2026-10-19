# Cloud-only continuation, 2026-10-20

The user's latest instruction requires all calculations, design outputs and
continuation evidence to remain in GitHub. It supersedes earlier local-work
instructions. The local project directory was verified empty; no local
openroad, ngspice, klayout, yosys, magic or netgen process was present.
Do not recreate a local checkout, CAD workspace, waveform or artifact cache.
GitHub API orchestration uses memory only. Unrelated user repositories and
user-supplied review documents are outside the cleanup scope.

## Recovered TX extraction

Run 39340687625 remains **failed** because publication returned HTTP 500.
Its native extraction step passed; its fallback artifact preserved the outputs.
Recovery run 39341750762 passed without rerunning CAD, restored the exact
SHA-pinned artifact, verified the original summary and published the original
files under their original source head. See the two linked evidence receipts:

- [Extraction receipt](evidence/tx-fast-wire24-extraction-recovered-pass-20261020.json)
- [Publication recovery receipt](evidence/tx-wire24-publication-recovery-pass-20261020.json)

The new 2.4 um fast-route geometry has 116611 native exported resistors and
77538 capacitors, 377 connected wire components, 1674 devices and 4774 device
terminals. The original 13 corruption controls passed. These counts equal
the previous candidate's counts; values and geometry still require the new
model and cannot be substituted with the old RC model.

Next: compose the new native model with exact geometry, source and clock
bindings; run the original loaded waveform and device gates. Neither recovery
nor successful extraction establishes electrical acceptance or qualified PEX.

## CDR diagnosis

Run 39341051275 completed the native passive-network diagnosis. The original
early/late sampling failures remain failures. The complete source-bound report
is retained in [the evidence receipt](evidence/cdr-v16-retime-passive-networks-20261020.json).

For the C positive/negative source components, total connected wire capacitance
is about 820.81/893.80 fF; measured source-to-filter metal resistance spans
51.62--62.66 ohm. The corresponding D source components are about
468.56/518.02 fF and 45.51--56.68 ohm. Capacitance covers the connected component,
including branches; it is not a single edge capacitance. Intrinsic resistors
and MIM devices were not replaced by linear approximations. These numbers
identify loading/access to investigate, not a proven delay or approved repair.

Next: inspect actual routes and branch loading, select a substantive physical
or circuit repair, then regenerate physical evidence and fresh extraction.
Do not repeat the unchanged failed simulation or relax the original gates.

## Main chip and remaining scope

At this checkpoint run 39331918238 is still in progress on a GitHub-hosted
runner: the 128-buffer candidate's native routing, extraction and three-corner
STA. Do not launch a duplicate or infer timing closure from job status.

Full serial PHY, recovered-clock operation, main-chip timing closure and
manufacturing approval remain open. Preserve failed evidence and follow
CLOUD_RESUME.md for the cloud-only continuation.
