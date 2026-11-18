# Isolate current I/O inverter LVS mismatch

The complete pad LVS run 44418807867 rejects deep and flat comparison. Its deep cross-reference reports an unmatched substrate-related extra pin in sg13g2_io_inv_x1, while the two MOS devices match and the tap device is marked W. The selected official CDL has `R0 vss sub! ptap1 A=624.1f P=3.16` in this inverter, whereas sg13g2_io_tie has `P=3.16u`. This is an observed source discrepancy, not permission to change units to fit the layout.

Run the same authenticated upstream GDS/CDL/deck snapshot cc9afba57e0ec1b5ba77e6bbb638ba9dbe5866b8 with sg13g2_io_inv_x1 as top, in deep and flat mode. Preserve strict ports, tap extraction and empty implicit connections. Do not add inferred globals, change A/P or normalize geometry. The previously exercised strict negative controls remain mandatory. This separates a primitive tap/reference problem from parent context and aggregation. A passing isolated cell would not imply full pad/chip LVS.

The concurrent full core antenna repair is run 44420129432, head 3e56fb282941bad19a74019ff73a65d41f058141. It must be observed through its own immutable source and output manifest; this diagnostic does not replace it.
