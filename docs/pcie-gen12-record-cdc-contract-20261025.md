# Gen1/2 complete-record recovered-clock transport proposal

This proposal composes the qualified 16-symbol collector with the existing complete-block CDC. It transports candidate records and preserves every byte and flag. It does not identify protocol-accepted TS1/TS2, negotiate lanes or implement a training owner.

The frozen basis is root commit `63b26b74e767e9ac09a88b0c1514d7ea2e199fbd`. Exact reuse hashes and provenance are in `scripts/pcie-gen12-record-cdc-proposal.json`. No RTL or executable tests have been added yet.

## Proposed ports

`soc_pcie_gen12_record_cdc_v1`, parameter `DEPTH=32`, takes `por_ni`, `wr_clk_i`, `rd_clk_i`, clean level `wr_reset_i` and `rd_reset_i`, `wr_valid_i`, `wr_loss_i`, and complete fields `wr_data_i[127:0]`, `wr_k_i[15:0]`, `wr_code_error_i[15:0]`, `wr_disparity_error_i[15:0]`, `wr_comma_i[15:0]`. It returns `wr_running_o`, `wr_accept_o`, `wr_fault_o`, `wr_overflow_o`; read-side ports are `rd_running_o`, `rd_fault_o`, `rd_valid_o`, `rd_ready_i` and the identical five output fields. There is no source ready/request-to-pause interface.

The adapter instantiates the exact `soc_pcie_gen3_block_cdc_v1`. Its 194-bit payload is `{2'b0, comma, disparity_error, code_error, K, data}`; length code is the legal constant4 and SKP/EIEOS/realign metadata are zero. These fields are an internal opaque container, not a claim that a training record is a Gen3 block. All192 record bits cross without reinterpretation.

`soc_pcie_gen12_recovered_records_v1`, parameter `FIFO_DEPTH=32`, adds actual composition with the existing `soc_pcie_gen12_training_records`: `por_ni`, `recovered_clk_i`, `common_clk_i`, clean `recovered_reset_i`/`common_reset_i`, `raw_valid_i`, `raw_i[31:0]`, explicit `polarity_i` and recovered-domain `loss_i`. Outputs expose recovered running/boundary/RD/record acceptance/fault/overflow and common running/fault/record-valid plus ready and all five record fields. The qualified combined collector's TX half is tied inactive; its RTL is not copied or modified.

Collector `rx_rst_ni` is driven by the CDC write-domain running output, matching the existing recovered_x4_v4 integration pattern. Its complete-record ready input is actual CDC acceptance. Collector enable is fixed active only in that running epoch and its private force-realign is zero. A change in polarity while running, source collector overflow, or explicit loss faults the epoch. Disabling or requesting fresh alignment uses a coordinated clean reset request; it never silently removes only the collector's partial state.

## Reset, fault and epoch disposition

Either clean level reset request asynchronously asserts both existing reset synchronizers and masks public transfers. Release retains the exact three local release flops, four boot clocks and two peer-ready flops. A stopped clock cannot finish the mutual barrier. Reset discards raw32 residue, the registered decoder batch, partial16-symbol record, both complete collector slots, and all FIFO memory/prefetch state. No stale record may appear in the next episode.

The external owner must treat common-running low or common fault as invalidating its pending epoch state. No epoch number is invented. On a source fault, an already-buffered valid prefix may retire before the held fault crosses two common-clock flops. Once observed, public valid stays low until coordinated reset. The adapter does not promise instantaneous cross-clock loss notification. Source input is not retried or paused when a complete record cannot be accepted; capacity rejection immediately faults the episode. Code/disparity errors and internal COM flags remain record payload, with no semantic filtering.

Polarity must settle while reset/startup. A one-bit previous-polarity register tracks in the recovered domain during startup; a running change drives loss, not a reset feedback loop. Raw traffic before running is intentionally unadmitted; an owner must arrange fresh acquisition. The FIFO's finite DEPTH32 budget is not a protocol worst-case sizing proof.

## Planned independent proof

The adapter oracle is a public-port queue of complete192-bit records, independent of RTL pointers or shifting. Directed basis/complement and random records cover every payload and flag bit, ordering, held valid/data, multiple wraps and full-rate transfer. Tests cover depths4/8/32, independent clock ratios/phases and drift, bounded pressure, exact RAM-plus-prefetch overflow, explicit loss and reset recovery.

Composition tests drive real raw32 data through the unchanged aligner/decoder/collector and compare complete records with an independent global-bit/table oracle. They cover all record fields, internal COMs, valid gaps, 16-symbol records crossing four-symbol batches, wrong disparity and invalid codes, and resets with raw residue, pending batch, partial record, full collector queue and held CDC output. Both reset requests are exercised with either clock stopped, plus polarity changes and loss.

Compiling behavioral mutations must corrupt each field independently, break held output, drop/duplicate acceptance, suppress overflow/fault, bypass peer startup or reset only one side, preserve stale records, or disconnect source loss/polarity handling. Positive Icarus and Verilator, synthesis/check and mapped-netlist oracle replay remain required before an implementation pass. Resource supervision and bounded subprocess output will be reused; no new heavy proof is dispatched at this proposal stage.

Physical Gray-bus skew, synchronizer preservation, metastability/MTBF, reset recovery/removal and routed CDC constraints remain separate. Lane mapping, rate switching, clock muxing, ordered-set semantics, timers, LTSSM and link-up remain required unfinished integration work.
