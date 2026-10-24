# Gen1/Gen2 raw32 receive decoding integration

This source candidate supplies the next digital receive seam: an explicitly aligned raw32 word stream becomes zero through four decoded bytes per recovered-word cycle. It is not a link-up detector, training state machine, PIPE implementation, or acceptance of 2.5/5 GT/s analog operation.

## Interface and latency

The inputs are the aligner's recovered clock/reset, enable, forced realignment, explicit polarity, raw validity and 32 raw bits. Bit 0 is earliest on the wire. Outputs are 32 packed data bits, four K/code-error/disparity-error/comma bits, the valid symbol count, delivered boundary/acquisition indicators and running disparity. Byte slot 0 is earliest. Unused slots and error flags are zero.

The aligner captures a raw word at edge N. Its resulting complete symbol batch is decoded and registered at edge N+1. The acquisition batch seeds its first decoder from the COM's incoming disparity, rather than the wrapper's previous RD. Four combinational cores chain RD through only the actual slots. Every received slot advances RD, including invalid codes. No-symbol cycles hold RD.

Current disable, forced realignment or polarity change takes priority at edge N+1: both the pending batch and that edge's raw word are discarded. Reset also flushes both stages. These controls clear delivered outputs, boundary and acquisition indicators and reset RX RD negative. The caller must provide domain-safe reset release and convert electrical idle, rate changes, bit slips and actual discontinuities into explicit flushes. A raw-valid gap adds no bits but still allows a previously pending batch to retire; it is not a flush. Boundary/acquisition indicators travel with the delayed delivered batch.

## Source state and prerequisite gates

The codec comes from the separately reviewed and tested codec branch. The aligner will be imported byte-for-byte only after the exact final aligner proof succeeds. Until then the prerequisite file is explicitly UNBOUND, there is no registered integration workflow, and the checker rejects before native work. The workflow template is not an executable GitHub workflow. This source checkpoint does not claim successful integration.

The final binding will require both exact completed native runs, original source heads, attempts and successful named jobs, together with immutable imported RTL hashes. It will retain the standard-table fixture and the codec's full vendor provenance.

## Independent verification

A serial-coordinate oracle accumulates the corrected input stream in global bit positions and finds the first full COM. It obtains expected data/K/error classifications from the independent 268-row numeric table, never by invoking the RTL encoder. A one-cycle queue expresses the public latency contract. The oracle advances received-subblock RD independently, including on invalid input.

Coverage requires all 64 acquisition offsets across two words, both explicit polarities and COM disparities, all 2,048 actual incoming-RD/raw10 pairs, valid-gap retirement, code and disparity errors, four-symbol batches, all ten measured flush residues for every control, pending four-symbol flushes and search-state flushes. Both Icarus and Verilator must agree; synthesis must contain real cells and no black boxes. Twelve compiling RTL mutations must fail behaviorally, including dropped acquisition seed, broken RD chaining, invalid-code RD hold, unused-slot RD advance, every flush, dropped valid-gap retirement, byte reversal, hidden errors and a missing fourth slot.

All execution and artifacts stay in GitHub. No simulator, synthesis or artifact download runs on the user's computer.
