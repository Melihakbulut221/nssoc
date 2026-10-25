# Preserve inherited proof directories when resuming the native PLL

Run 39637767590 restored and verified the prior capsule, then failed before
native activation: capture_ready tried mkdir(exist_ok=False) on the inherited
preallocated-storage-proof directory. Its only recorded command was final log
ownership cleanup. The full failed archive remains published; it is not a new
checkpoint and must never be selected for continuation.

The correction preserves every inherited proof and gives the current run and
attempt a new storage-evidence/run-ID-attempt-N/preallocated-storage-proof path.
The original capture_ready implementation, allocation, Btrfs mounts, compression,
12GiB native reserve and 4GiB host reserve are unchanged. No waveform sample,
native process, solver, load, analysis duration or reader gate changes.

The new controller differs only in helper import and adding the old allocation
module to the method hash inventory. The migration verifies all eighteen current
methods against the explicit delta and the frozen seventeen-method baseline.
Controls reject duplicate namespaces, traversal, invalid attempts, unknown
controllers, changed/missing native methods, changed old/new storage and extra
methods. They also verify migration from the real last valid39602655093 summary.

Only after these cloud controls pass, continue the exact saved native process
from39602655093. Do not cold restart; do not resume the failed39637767590 record.
This fixes proof bookkeeping, not full1us storage capacity or PHY qualification.
