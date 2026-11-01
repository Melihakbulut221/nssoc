# PD650 failure analysis from existing native raw data
The immutable producer is run41288195752, source d638e0e3cd15a0ee930212c27ab1f238b5085237,
release430445706. It is an electrical rejection, despite a clean native engine
exit and passing transistor voltage/current guards.

This workflow authenticates every archived member on a GitHub runner, retains
all1301 original vectors and113475 raw rows through the original pinned parser,
and reproduces all six original sampling measurements and the phase average.
It then reports per-bit transition-conditioned margins, actual worst-case node
and collector/tail current samples, full HBT state and logical device topology.
Only derived JSON is published. The existing native archive stays cloud-only.
No simulator is invoked, no model/threshold changes are made, and no new physical,
timing or serial PHY acceptance follows from a successful analysis.
Twenty source/parser/refusal/measurement/archive-path controls run before archive acquisition.

The initial reader source4516b4ce.../run41293342915 was cancelled after static inspection found the producer tar stores a cloud-sampler-load/ prefix. The corrected reader requires that exact prefix and authenticates every stripped relative member against the original complete index. The initial attempt remains preserved; no simulation was rerun.
