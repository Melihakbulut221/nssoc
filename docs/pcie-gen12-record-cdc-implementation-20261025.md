# Complete-record recovered-clock transport candidate

This source-only candidate implements two thin wrappers. Neither new wrapper has
been simulated, synthesized, physically qualified or imported into the root design.
The existing codec, record collector, Gen3 CDC/reset and vendor FIFO bytes are frozen.
The parent approved the interface and source-only implementation, including the
one-edge polarity arming stage; cloud execution remains unauthorized.

## Interfaces and exact fields

soc_pcie_gen12_record_cdc_v1 accepts one complete 192-bit candidate on wr_clk_i.
The five independent fields are data[127:0], K[15:0], code_error[15:0],
disparity_error[15:0], comma[15:0], in that order from least significant bits.
wr_valid_i is a live presentation, not a backpressured request. wr_accept_o is the
actual transfer event at the rising edge. A live record rejected for capacity
faults the epoch. rd_valid_o/rd_ready_i transfer the entire record on rd_clk_i.
Held output fields are stable; all five fields are zero when rd_valid_o is false.

The frozen Gen3 module is an opaque container: payload194 is the 192-bit record
plus two zero high bits; fixed length_code 4 is only its legal container selector;
SKP/EIEOS/realign metadata are zero. This does not interpret a Gen1/2 record as a
Gen3 block or accept any protocol field. No new FIFO or reset synchronizer is added.
The original MIT FIFO must be fetched at the immutable vendor ref in the proposal,
hash-verified, and compiled exactly once. It is not copied into another RTL glob.

soc_pcie_gen12_recovered_records_v1 composes the exact qualified raw32 collector,
including its aligner/decoder and RD state, with this transport. raw_i bit 0 is
earliest. polarity_i is explicit; loss_i comes from the recovered-domain owner.
The collector's unused TX side is disabled and all its inputs are constants.
Its output ready equals actual CDC acceptance, so no second RD or record owner
is introduced. Data/K/errors/internal COM survive as evidence; they are not
training-set acceptance conditions. No negative-RD forcing is added.

## Startup, reset and loss

Either clean reset-quality request or POR asserts reset across both clock domains.
Release uses the frozen three local reset flops, four boot clocks and two peer-up
flops. Both clocks must resume for a new epoch to start. Those held peer-up bits
are a startup barrier only, **not a clock-loss detector during an existing epoch**.

The internal CDC write-running signal releases the frozen collector reset.
On the next clean recovered rising edge, the collector/decoder settle the
explicit initial polarity, and source_armed becomes one. Public
recovered_running_o is internal CDC running AND source_armed. Raw valid is masked
until that public signal is high. Thus the first raw word presented with public
running high before a rising edge is admitted; the polarity-settling edge is not
publicly admitted. Both initial polarities are tested. Polarity must settle during
reset/startup and remain stable in an epoch. A later change produces sticky loss,
not an independent local reset that might leave old CDC records alive.

The collector resets on loss of internal CDC running. Either reset request clears
raw residue, pending decoder batch, partial record, both collector records and
the asynchronous FIFO/prefetch state. There is no local disable/realign input
independent of this coordinated reset. The downstream owner must discard its
uncommitted protocol state whenever common_running drops or common_fault rises.
There is no epoch-number field and no claim that earlier retired records can be
retracted.

External known loss, collector overflow or a running polarity change feeds the
frozen sticky write fault. Capacity rejection also sets the original overflow
flag. The held fault crosses two common flops. An ordered accepted prefix may
retire before it becomes visible; no record retires after common fault until
reset. The tests do not demand zero-prefix latency.

If the writer clock stops mid-epoch, already buffered records may drain and the
peer-up state remains high. If the reader stops, finite backlog may fill and fault
the writer; common fault is observed only when that clock resumes. An external
owner must report a detected discontinuity. With a stopped writer, loss must stay
asserted until sampled after its clock resumes, or the owner must assert a clean
coordinated reset. No watchdog, clock mux, automatic loss detector or rate owner
is invented.

## Independent test source

The two cocotb benches observe public ports only. A Python list/deque checks every
accepted complete record, held fields, order and absence of duplicates. The direct
bench includes all 192 single-bit basis patterns and their complements, random
records, three asynchronous ratios/phases, wraparound, exact DEPTH+2 capacity under
the specified spaced-write/read-prefetch schedule, explicit loss without valid,
both resets, stopped-clock startup and distinct mid-epoch pauses.

The composed bench uses the frozen independently published 268-row code table
and the qualified global-bit-coordinate SerialOracle. It does not feed a DUT
encoder back into its decoder or inspect internal FIFO state. All 32 offsets,
both initial RDs and polarities, serial gaps, raw invalid codes, late error flags,
internal COM and complete records are checked through the actual collector and
CDC. A separate first-public-word case tests polarity arming. Reset cases retain
in-flight raw residue, decoder batches, partial candidates and held complete
records; new-epoch records must contain no old fields. Polarity changes after
each of 16 measured candidate prefix lengths are checked against the actual
oracle partial length.

There are six direct and five composed tests. The intended hosted matrix is both
Icarus and Verilator at depths 4, 8 and 32 (66 named positive test executions).
Eighteen behavioral mutation definitions have unique source anchors and named
tests. They are **not yet compiled or executed**. A compile/setup/resource failure
must never count as detection of a behavioral mutation. The public collector
overflow connection is source-bound; no unreachable internal force is presented
as a public-port coverage test.

The Makefile is hosted-only and requires an explicit source list. There is no
registered workflow or execution controller in this candidate. After review,
the hosted controller must authenticate sources/vendor, bound subprocesses using
the existing qualified memory/cleanup supervision, check complete XML names and
zero skipped tests, require each mutation to compile and fail its named behavioral
test, and perform full synthesis/check plus mapped-netlist tests. The previously
qualified optional -noshare synthesis flow may be reused only by an exact reviewed
adaptation. No synthesis or resource result follows from these source files.

## Remaining ownership and physical scope

DEPTH32 is a finite functional configuration, not a worst-case protocol buffering
proof. Reset quality, metastability/MTBF, Gray-bus and reset physical constraints,
PMA continuity/rate changes, lane mapping/deskew, complete TS1/TS2 acceptance,
LTSSM/equalization and negotiated x4 Gen3 link-up remain separate unfinished work.
