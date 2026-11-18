# Residual parent crossing repair

The 56-buffer parent timing run 44350414168 cleared all four original
perimeter targets in slow, typical and fast libraries with nominal RC.
Total slew violations remained 50/39/27. One native buffer endpoint,
wire127/A on net128 driven by wire128/X, had a slow-corner slew of
2.645617723 ns against 2.507400036 ns. Its actual route is 4865.64 um long.

Native inventory run 44351769676, artifact 14447953699, SHA256
adc6d679eb9ac7c95e14ba9f5c2c40cd070dfdde38ae660de3ab459a61f5d820
was independently verified (12 outputs and protected source hashes).

Candidate run 44352635838 scans all native SIGNAL buf4-to-buf4 nets on
opposite vertical sides of the core with actual wire length over 3000 um.
Only net128 matched. It inserts 14 additional buffers around the left
perimeter, preserving all 2031 original instances and original connectivity
classes. Power connections are explicit and verified. Legalization moved
new cells by at most 4.089643 um; no new cell overlaps the core macro.
All 23 candidate outputs and protected repository sources were verified.

The crossing route workflow consumes the admitted candidate and expects
2045 instances and 2019 routed parent nets. DRC, visible geometry and strict
pre/post route identity must pass before fresh extraction and timing.
The previous four repaired nets must be rechecked after routing as well.

Neither a passed candidate audit nor parent-only timing is full-chip
production approval. Actual core/parent hierarchical timing, external I/O,
CDC, qualified min/max RC, SRAM characterization and internal LVS, physical
signoff and manufacturer approval remain required.

## Staged fresh extraction

The crossing timing workflow is staged, not yet dispatched. It accepts only
route run 44353658604 at b9f958703287713d4cff8adf98fd820bd63be945,
after independent artifact ID/SHA256 admission. It requires 2045 unchanged
instances, 2019 extracted parent nets and exact terminal/resistance connectivity.
The native electrical reports include both buffer additions (56 perimeter and
14 crossing buffers) and all ten original endpoint buffers. This checks for
regressions at the four previously repaired targets as well as wire127/A.
Clock periods, 5 percent derating, nominal-only RC and all signoff caveats are
unchanged.

## Read-only source download retry

The first crossing timing attempt 44355173769 at
867bea34fcaba157776d48fb78ebc145e53880ff stopped while downloading the pinned
route archive, before extraction or STA. Failure artifact 14452160703 has SHA256
79092b94552141d5629f0674684994c118d8f206ba9ac6e62e044fb6764d0e68;
the authenticated failure manifest contains zero outputs.

Read-only artifact downloads now permit at most three command attempts with
5/10 second backoffs. Fixed model/rule URL reads retry only network errors or
HTTP 429/500/502/503/504, also at most three times. Artifact IDs, expected source
head, digests and all output/source checks are unchanged. Failed hashes and
native design assertions still fail immediately. Extraction and STA processes
are not retried by these helpers.
