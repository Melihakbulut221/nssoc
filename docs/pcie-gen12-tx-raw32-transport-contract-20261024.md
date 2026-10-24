# Gen1/Gen2 encoded-symbol to raw32 transmit transport

This source candidate implements the digital TX seam from one through four bytes/K flags to a raw32 bitstream. Four actual encoders use the reviewed code-table/vendor sources from codec86dbe41b. A72-bit FIFO preserves accepted symbol order across32-bit boundaries. Bit0 and slot0 are earliest on the wire. This is not a serializer, rate-generation circuit, LTSSM, low-rate analog qualification, or full PHY acceptance.

## Batch and output contracts

A request is accepted only on batch_valid_i && batch_ready_o. count_i must be1..4; unused data/K slots do not enter encoding or error classification. Every selected encoder receives the preceding selected symbol's running disparity. rd_o is the disparity after the last accepted valid input symbol; because encoded bits can remain queued, it is not the disparity of the currently transmitted output word.

force_negative_rd_i is a sideband on an accepted valid batch. It selects negative incoming disparity for that batch, then commits the actual resulting final disparity. It neither changes already queued symbols nor changes RD while stalled or rejected. The protocol owner decides when compliance permits this forced disparity.

Invalid count or selected invalid K rejects the whole batch: batch_error_o plus count_error_o or k_error_o pulses for that accepted request, with count error taking precedence. Invalid requests are ready even when the FIFO is full, since no bits are appended and input RD is preserved. An independent valid output handshake may still retire the existing32 bits. All error strobes clear on idle, disabled and flush cycles.

raw_valid_o means at least32 genuine buffered bits are available. raw_o is zero when invalid; no zero word is fabricated as valid. raw_ready_i retires exactly one complete word. Output bits remain stable across stalls, while later accepted input may append to the tail. A batch may enter when space after the simultaneous output pop is sufficient; a72-bit limit is enforced.

There is no input-to-output combinational fall-through. Input accepted at edgeN becomes eligible for transfer at a following edge. After prefill, a continuous four-symbol producer respecting ready sustains one raw32 output on every cycle; normal input backpressure absorbs the40-to32 rate difference. A producer holds valid payload/count/K/force until acceptance unless reset, disable or flush discards that request.

Reset asynchronously clears FIFO/RD/error state. Disabled or flush cycles synchronously discard every pending bit and reset disparity negative; combinational ready/valid/underflow are suppressed immediately. buffered_bits_o reports the actual stored occupancy. No partial final word is padded: a finite stream must receive additional real symbols or be deliberately flushed by its owner.

stream_active_i is a separate demand declaration, not a data generator. underflow_o is true exactly when enabled, out of reset, not flushing, stream_active_i && raw_ready_i is requesting a word, and no full32-bit word exists. A same-edge incoming batch does not hide that demand failure. The owner must prefill before asserting active demand.

## Independent proposed cloud proof

The oracle reads the separately published268-row code table and appends wire-first strings to a Python serial-bit list. It never invokes the encoder to create expected results and does not copy the RTL FIFO shifts/masks. Public handshakes consume exact32-bit slices.

The proposed proof covers all536 legal symbol/incoming-RD pairs; all488 invalid K/incoming-RD pairs; counts0..7; all selected invalid-K slots; poisoned unused slots; output and input backpressure; forced RD with queued bits and held input requests; full-FIFO rejection with no append; reset/disable/flush at all37 reachable even occupancies0..72; truthful underflow; and8192 consecutive output words with every bit compared and input payload held on stalls. Twelve thousand additional randomized cycles hold offered requests until handshake or explicit flush. Eighteen compiling behavioral mutants must fail. Icarus, Verilator and nonempty, non-black-box Yosys synthesis are all required.

## Unqualified source state

No native TX proof has run. The prerequisite is deliberately UNBOUND; there is no registered workflow, only a nonexecuting workflow template. The original codec proof40099402878 rejected because its testbench supplied no actual asynchronous reset edge before the first lane assertion. Its failure is preserved. A separately reviewed reset-only correction and its actual successful native artifact readback must be bound by exact source/run/attempt/member hashes before this TX checker can execute.

Even after that prerequisite and source review, native TX transport proof remains mandatory. The real serializer, Gen1/Gen2 analog rates, training/compliance owner and complete serial PHY remain open. All execution and artifacts belong in GitHub; no local native computation or artifact download is authorized.
