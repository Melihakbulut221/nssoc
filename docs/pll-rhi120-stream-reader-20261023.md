# Full-column PLL stream reader qualification

The native 1 us acquisition contains 5106 columns and can exceed a standard
runner's ordinary-file capacity. This independent reader validates the complete
logical raw stream from immutable cloud archives in bounded memory. It checks
every column, complete row, original table identity, monotonic time, full raw and
payload hashes. It consumes the entire upstream iterator, including archive
verification after the raw member ends. Sparse working files are not inputs.

The original greater-than-3000000-row, zero-to-1us and 0.3125ps maximum-step
assertions are compared by AST, unchanged. Qualification reruns the original
16 corruption controls through the streaming path, compares every complete
recorded prefix sample bit, and rejects five transport/incomplete-capture
faults. Test-only short prefix fixtures cannot pass full capture.

This is reader qualification only. The active native PLL process and its
source-pinned controller remain unchanged. A completed terminal source gate,
full-stream invocation and original acquisition/device/PVT qualification remain
required. No full serial PHY, loop lock or final timing pass is claimed.
