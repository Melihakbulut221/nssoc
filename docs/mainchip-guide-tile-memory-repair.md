# Bound guide region memory without dropping routing scope

Full64 single-worker route41552715162 failed after4560.29 seconds, with11793076 KiB process-group RSS crossing the unchanged11534336 KiB guard. Two workers had failed at the same guide iteration previously. Reducing concurrent worker lifetime alone did not resolve the failure.

Pinned upstream FlexDR::guideTilesFlow merges intersecting same-direction guide rectangles without a region-size limit. The final single-worker iteration exhausted memory; exact failing box dimensions were not logged. This repair targets the unbounded individual search region, not a proven leak.

After the original guide selection and merge, partition each merged rectangle into windows bounded by args.size times the first native GCell span, with one GCell overlap. Each closed union equals the original rectangle, all original guides remain unchanged, and every partition enters the existing independent-batch calculation and single-worker processing. The original64-iteration strategy, constraints, search costs, netlist, pins and acceptance thresholds remain unchanged. New source logs each split box and total bounded-region count.

The actual helper is compiled in a standalone C++ coverage test including255 cases, integer-limit coordinates, degenerate dimensions and overlap boundaries. An independent boundary/slab coverage oracle rejects missing boundary tiles, oversized windows and outside coverage; invalid bounds are rejected. Original lifetime controls remain.

A complete native engine build and actual-chip qualification are required before full routing. Changed worker decomposition can change routing outcomes; equivalence or timing acceptance is not claimed. Full original net, clock, PG, physical DRC/LVS, fresh RC and setup/hold gates remain mandatory. Native evidence stays in the cloud.
