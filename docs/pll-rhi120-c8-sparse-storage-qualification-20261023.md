# RHI120 archived-prefix cloud storage qualification

The live recovery 39941648965 remains unchanged. Its ordinary all-column raw file
and archive reserve grow with the original 1 us simulation. This separate job
tests lossless sparse working storage against the already archived initial
39925042125 checkpoint; it never activates or restores a simulator.

The adaptation changes only four namespace strings in the existing sparse I/O
helper. The source delta and every imported archive/storage method are pinned,
as are the current recovery controller and exact-column waveform reader.
The historical PLL845 metadata reconciliation does not apply to this source.

The job first runs the 16 corruption controls and exact append/header-backpatch
fixture oracle on the hosted runner. Then it verifies every ordered archive
part and the entire 23,042,563,898-byte archive, every recorded member, and the
complete 25,342,824,379-byte raw/payload hashes while restoring only retained
working head/tail bytes. A second complete immutable archive pass verifies the
logical file. The sparse working allocation must be below 16 MiB. Zero-filled
holes are never offered as waveform data.

Only the bounded proof report is published; the immutable original remains the
source of truth. A pass qualifies this storage operation only. Native resume,
publication of a newly grown logical capture, and full-reader materialization
need their own exact-current-checkpoint qualification after the live process
has saved. No original columns, rows, loads, solver methods, clocks or electrical
acceptance gates are reduced. Full PLL acquisition and serial PHY acceptance
remain open until the original gates actually pass.
