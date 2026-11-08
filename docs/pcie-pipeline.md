# PCIe packet-domain pipelining

Branch `timing/pcie-pipeline`, based on `timing/pcie-boundary-skid` (`docs/pcie-boundary-register-slices.md`).

## Why

The main-chip implementation probe (`analysis/impl-probe`, run 42436769600, `docs/mainchip-impl-probe.md`) ran an unbounded `repair_timing` on the post-global-route database. The worst `pcie_clk_i` path was still -5.76 ns at the frozen slow corner (`nom_slow_1p08V_125C`, 5% derate, 4 ns period) and -2.31 ns typical. It ran about 47 cells flop to flop, already upsized. The remaining gap is logic depth, so the packet logic needs fewer levels per `pcie_clk_i` stage. Clocks, SDC periods and acceptance thresholds are unchanged here.

## How the paths were measured

`scripts/pcie_timing/` is a pre-placement screen of the packet domain. It runs in the cloud through `.github/workflows/cloud-evidence-summary.yml` (`timing_sides`):

- `pcie_timing_top.v` reproduces the packet-async PCIe instantiation of `soc_top.v`: the reset release, the link status registers, `u_pcie` with only the ports `soc_top` connects, and the APB mailbox. The system-clock side of the mailbox becomes ports.
- `run.sh` synthesises the same 21 PCIe sources with the `soc_top` recipe used by the implementation probe. That recipe is Kogge-Stone carry mapping, typical-corner `dfflibmap`/`abc -D 20` and the same `abc.constr`. The netlist-naming steps drop `-purge`, which changes names only. Flip-flops are renamed after the register they drive, or after their source line where no public net exists.
- OpenROAD (LibreLane 3.0.5 AppImage) places the netlist alone: 40% utilisation, density 0.6, the PDK `LAYERS_RC`, ideal clocks and a fanout limit of 10. It then reports four stages:
  - `synth`: unplaced and unbuffered, not useful;
  - `placed`: after `repair_design`;
  - `sized`: after a sizing-only `repair_timing -skip_buffering`;
  - `repaired`: after an unbounded `repair_timing`.

  Each stage is reported at the typical and slow corners, with the SDC's 0.25 ns uncertainty, 0.15 ns clock transition, ±5% derate and 0.8 ns PCIe port delays.
- `paths.py` and `families.py` summarise the reports. A second report set leaves out the link status and reset release flops as startpoints. Their fanout trees are an artefact of placing this block alone, and in this screen they hide the logic behind them. "Logic cells" means cells other than buffers and inverters, counted after the launch flop.

These are estimates for comparing RTL variants, not sign-off. The `sized` stage is the steadiest comparison. The `repaired` stage adds long `buf_1` chains in this unrouted context, and its worst slack moved by about 1 ns between runs of nearly identical RTL. The screen is about 1.5 ns more optimistic than the implementation probe: baseline repaired slow -4.07 ns here, against -5.76 ns after global route there.

## Where the deep paths were (baseline `eb088ef4c`, run 42463873679)

Worst path per capturing block, `sized` stage, link status startpoints excluded:

| Block (capturing registers) | Slow slack | Typical slack | Cells / logic cells | Start -> end |
|---|---:|---:|---:|---|
| Receive consumers: DLLP decode, LCRC check (`soc_pcie_dllp_rx`, `soc_pcie_lcrc_rx`) | -5.98 | -2.29 | 25 / 19 | `receive_ownership.output_index` -> `receiver.ack_sequence_o` |
| Replay store capture (`soc_pcie_replay_tx`: `next_store_sequence`, `count`, `tail`, `bytes`, `lengths`, `halt`) | -5.95 | -2.39 | 28 / 19 | `transmit_packet.state` (LCRC framer) -> `retry.next_store_sequence` |
| Credit reservation and FC update (`soc_pcie_credit_tx`: `dl`, `hl`, `dc`, `hc`) | -5.86 | -2.24 | 30 / 21 | `retry.new_slot` -> `credits.dl` |
| Boundary arbiter and slice (`soc_pcie_buffered_flow_packets`) | -5.30 | -1.96 | 24 / 17 | `transmit_packet.state` -> `boundary_slice.main_data` |
| Replay send setup (`read_pos`, `replay_read_onehot`, `write_pos`) | -5.07 | -1.79 | 26 / 18 | `transmit_packet.state` -> `retry.write_pos` |
| Receive queue (`soc_pcie_rx_credit`) | -4.74 | -1.55 | 20 / 13 | `receive_ownership.qread` -> `output_dllp` |

The cones behind these paths:

1. **Transmit link stream into the replay store.** The LCRC framer `soc_pcie_lcrc_tx` selects its byte with a word, byte-order and state multiplexer. The byte goes through the ACK/TLP merge `soc_pcie_packet_tx` and into the replay store's capture checks: LCRC residue compare, sequence compare and capacity. Those checks drive `halt`, `source_error_o`, the slot bookkeeping and the 1216 store write enables. In the other direction, the store's `in_ready_o` gated the framer's state and CRC update. The same stream reached the boundary arbiter and slice through two more arbiters.
2. **Receive queue read into the consumers.** `soc_pcie_rx_credit` reads its byte with a 38:1 index multiplexer per bank, a head-slot multiplexer through `order[qread]`, and the DLLP select. The consumers' end-of-frame decisions follow in the same cycle: the DLLP CRC and kind decode in `soc_pcie_dllp_rx`, and the residue compare and state in `soc_pcie_lcrc_rx`.
3. **Credit reservation.** The replay store first multiplexes the stored header bytes of `new_slot` and decodes class and payload. The chain then continues through the rounding adder, the per-class limit-minus-consumed subtraction, the credit compare and `reserve_ready_o`. After that come the consumed-credit update and the same-cycle FC-update debit selection into `dl`, `hl` and `confirmed`.
4. **Receive commit.** The TLP header decode, length arithmetic and free-slot search feed the write enables of every queue byte.

The worst baseline paths start at `pcie_link_up_q`, about 44 cells including the link-status fanout tree. The impl-probe launch flop `$auto$ff.cc:337:slice$1193821` is consistent with the sliced `{pcie_link_up_q,...}` register of `soc_top`. Behind that tree lies cone 1 or cone 2, about 20 logic cells.

## Changes

| Commit | Module | Change | Port latency |
|---|---|---|---|
| `7bc09fc1c` | `soc_pcie_reliable_packets` | Transmit register slice (`soc_pcie_stream_skid`) between the link layer and the replay store / DLLP arbiter | TLPs into the store and generated ACK/NAK DLLPs: +1 cycle |
| `7bc09fc1c` | `soc_pcie_reliable_packets` | Receive register slice in front of the DLLP and TLP consumers. A TLP frame still starts only when the TLP consumer can take its first beat and the slice is empty | Received DLLPs and TLPs: +1 cycle |
| `7bc09fc1c` | `soc_pcie_credit_tx` | Available credit per class in registers (`ah`/`ad`), kept equal to limit minus consumed by every branch that writes either. The data check is `dw <= 4*available`, the same as `ceil(dw/4) <= available` | none; same ports cycle for cycle |
| `7bc09fc1c`, `76e53ea95` | `soc_pcie_rx_credit` | The staged TLP is checked in one cycle and committed in the next from a registered verdict, slot and units. The commit is one register per slot, so each slot's write enable is a flop | TLP commit into the queue: +1 cycle |
| `7bc09fc1c`, `76e53ea95` | `soc_pcie_replay_tx` | Reservation class and payload decoded into registers one cycle ahead, for the slot `new_slot` will hold | none at a reservation handshake |
| `76e53ea95` | `soc_pcie_replay_tx` | Captured bytes are written to the store one cycle after the accept, from registers | none |
| `76e53ea95`, `92b21548a`, `145488b95`, `3b102cca0` | `soc_pcie_lcrc_tx` | The LCRC is accumulated one DWORD per collected word, folded a cycle after the accept as balanced parity trees, with the sequence-prefix state in a register. The transmitted byte is a register loaded from the next state's selection | none; same ports cycle for cycle |
| `92b21548a` | `soc_pcie_replay_tx` | The last read position of the frame being sent is registered at send start | none |
| `92b21548a` | `soc_pcie_rx_credit` | The queue head slot is a register that tracks `order[qread]` from next-state values | none |

### Why the added cycles are protocol-safe

End-to-end effect:

- received TLP to its ACK/NAK on the wire: +3 cycles (receive slice, receive commit, transmit slice);
- received ACK/NAK or UpdateFC to its effect: +1 cycle;
- locally generated completion to the wire: +1 cycle;
- the replay store, replay ordering and replay timer start are unchanged. The timer still starts at the wire-side end of frame.

Reasons the added cycles are safe:

- **ACK/NAK latency.** The AckNak latency limit and the replay timeout are hundreds of symbol times. This design's replay timer is `REPLAY_TIMEOUT_CYCLES` = 1024 packet clocks. Three more cycles on each side of the round trip do not approach it.
- **Flow control.** An UpdateFC that arrives one cycle later only delays credit, which is conservative. Credit is still debited exactly once per original TLP.
- **No receive deadlock.** The receive slice keeps the rule that made DLLP bypass safe. A TLP frame leaves the receive queue only when the TLP consumer is ready for its first beat, and only with the slice empty. With nothing in flight, that consumer's ready cannot fall before the beat arrives. Its ready falls only on its own end of frame (`packet_good_o`/`packet_bad_o`, then `ack_valid_o`). A TLP the consumer cannot start therefore stays in the queue. DLLPs, including the ACKs that free the replay store, are never held behind it.
- **Ordering.** Both slices are single in-order streams, so TLP/DLLP order is unchanged. The transmit slice carries both TLPs and ACK/NAK DLLPs.
- **Equivalence of the internal rewrites.** The `soc_pcie_lcrc_tx` and `soc_pcie_credit_tx` rewrites are port-equivalent to the originals. A local Icarus random co-simulation against the base-branch modules found no port mismatch:
  - `soc_pcie_lcrc_tx`: 400,000 cycles, 6,928 frames, random stalls, errors and short frames;
  - `soc_pcie_credit_tx`: 500,000 cycles, 176,072 grants, random UpdateFC, resets and link loss.
- **Replay store invariants.** The `soc_pcie_replay_tx` rewrites rely on invariants stated in the RTL comments:
  - a slot is offered for reservation only after its commit, at least eleven cycles after header bytes 2, 4 and 5 were written;
  - an offered slot is never rewritten;
  - no stored byte is read within a cycle of its write.

## Verification of the first round (no test expectations changed)

No test needed an updated expectation. Every check passed on the final RTL (`3b102cca0`, run 42464911092, unit) and on `145488b95` (run 42463965609, unit, SoC lint and traffic). The only difference between those two commits is the port-equivalent parity-tree LCRC fold.

| Check | Base branch (`eb088ef4c`) | This branch |
|---|---|---|
| `soc_pcie_replay_tx` | 7/7 (run 42458808702) | 7/7 |
| `soc_pcie_flow_packets` | 3/3 | 3/3 |
| `soc_pcie_buffered_flow_packets` | 5/5 | 5/5 |
| `soc_pcie_reliable_packets` | 4/4 | 4/4 |
| `soc_pcie_credit_tx`, `rx_credit`, `fc_tx`, `fc_tx_eop`, `lcrc_tx`, `packet_endpoint`, `link_packets` (modules changed or compiled with changed modules) | - | 5/5, 5/5, 3/3, 1/1, 2/2, 6/6, 3/3 |
| Joint SoC PCIe + Ethernet traffic, asynchronous packet clock | PASS 2/2 (skid doc) | PASS 2/2 |
| Joint SoC PCIe + Ethernet traffic, synchronous packet clock | PASS 2/2 | PASS 2/2 |
| `check_soc_lint.py` base and full | PASS, no new or stale warnings | PASS, no new or stale warnings |

The simulated time of `soc_pcie_buffered_flow_packets` grows from 41,790 ns to 41,940 ns. That is the added latency over its five tests.

## Measured timing of the first round (baseline run 42463873679, first-round head run 42464911092)

Packet-domain register-to-register setup, ns:

| Stage | Corner | Baseline WNS | Final WNS | Baseline TNS | Final TNS | Baseline violating | Final violating |
|---|---|---:|---:|---:|---:|---:|---:|
| sized | typical | -2.45 | **-1.48** | -4280 | -1648 | 3557 | 2594 |
| sized | slow | -6.00 | **-4.56** | -16497 | -10593 | 4748 | 4895 |
| repaired | typical | -1.19 | **-0.92** | -2205 | -118 | 3479 | 841 |
| repaired | slow | -4.07 | **-3.72** | -13049 | -6425 | 4747 | 4776 |

Reading the table:

- The final design has more flops: 4958 endpoints reported before, more than 5000 now. Its counts and TNS cover the worst 5000 endpoints only.
- Without the link status startpoints, sized slow TNS goes from -16091 to -5386 ns, with 4624 and 4063 violating endpoints.
- `repaired` varies by about ±0.5 ns between runs. `145488b95` measured -0.38 ns typical and -2.77 ns slow.

Logic depth, `sized` stage:

- the largest logic depth among the worst paths per endpoint drops from 21 to 20 logic cells, and the number of such paths over 12 logic cells from 1318 to 210 (corrected; an earlier version of this table reported the path with the most cells instead);
- the per-block worst moves as follows.

| Block | Baseline slow (logic cells) | Final slow (logic cells) | Final typical |
|---|---:|---:|---:|
| Replay store capture | -5.95 (19) | -2.87 (8) | -0.38 |
| Receive consumers / receive slice | -5.98 (19) | -4.27 (13) | -1.22 |
| Credit reservation and FC update | -5.86 (21) | **-4.56 (17)** | -1.48 |
| Replay send setup and reservation metadata | -5.07 (18) | -3.57 (15) | -0.83 |
| Receive queue | -4.74 (13) | -3.50 (11) | -0.75 |
| Boundary arbiter and slice | -5.30 (17) | not among the worst 1500 | - |
| LCRC framer output byte | (registers unnamed) | -4.22 (16) | -1.25 |
| TLP register backend (`soc_pcie_tlp_regs` decode) | not among the worst 1500 | -3.60 (12) | -0.85 |
| FC advertiser (`soc_pcie_fc_tx`) | not among the worst 1500 | -3.33 (9) | -0.68 |

## Second round: one more stage per remaining deep block

The first round left the credit loop at 17-22 logic cells and several blocks at 11-16. The second round adds one register stage to each, aiming at no more than about 12 logic cells per `pcie_clk_i` stage at the slow corner in the block screen. The credit change alters `soc_pcie_credit_tx` port timing by design, and its unit oracle was revised for it (next section). No other test was changed.

| Commit | Module | Change | Port latency |
|---|---|---|---|
| `def7be2f5`, `ac0a5f90c` | `soc_pcie_credit_tx` | Registered verdict: a request is judged against the current credit and initialization, and granted in the next cycle only if it is unchanged and nothing was consumed in between. UpdateFC is registered with its new-limit-minus-consumed balances (with and without that cycle's debit, carry-save form) and applied one cycle after it is presented, after that cycle's own debit | A new request is granted 1 cycle after it appears; no grant in the cycle after a consume; UpdateFC effect +1 cycle |
| `ceb3e0533` | `soc_pcie_lcrc_tx` | Words stored in transmission byte order; a cursor register names the position of the byte after the current one, so loading the next byte is a register-addressed select and advancing the cursor is separate | none; same ports cycle for cycle (random co-simulation against the first-round module, 6,928 frames) |
| `ceb3e0533`, `2fd0a2c70` | `soc_pcie_rx_credit` | One-hot read cursor and one-hot head slot (two AND-OR levels instead of binary multiplexers); head length, class and units in registers; both candidate next heads resolved from registers before the removal selects one | none (random co-simulation against the previous module, 300,000 cycles) |
| `ceb3e0533` | `soc_pcie_replay_tx` | An ACK/NAK is retired from the sequence distance and classification registered at its first presentation; every slot's header decoded in parallel, the next slot only selects | ACK/NAK retirement +1 cycle |
| `ceb3e0533` | `soc_pcie_buffered_flow_packets` | Register slice on the FC advertiser's stream | FC DLLPs to the wire +1 cycle |
| `ceb3e0533`, `ac0a5f90c` | `soc_pcie_buffered_flow_packets`, `soc_pcie_flow_packets`, `soc_pcie_reliable_packets` | Registered link/reset copies per consumer block: receive queue, FC advertiser, arbiter and slices, credit logic, packet path, replay store, link layer. Each is cleared asynchronously with the combined reset, so link loss and retraining reach every block at once, and is released one clock later; each block uses its copy as both its reset and its link status. The copies have different but equivalent D inputs, because synthesis merges identical flops even with `keep` | Release after reset, link up or retraining: +1 cycle (queue, advertiser, arbiter), +2 (credit logic, DLLP receiver), +3 (replay store, link layer) |

`soc_pcie_tlp_regs`: a decode-then-act stage (`7bf63b3b8`) was reverted (`68ee22d4b`). It moves the APB setup phase one cycle later, and `apb_wait_states_and_completion_backpressure` checks that phase cycle by cycle; that test may not change. Its decode stays in the descriptor handshake cycle.

### `test_soc_pcie_credit_tx.py` oracle changes

| Where | Old expectation | New expectation | Why it is protocol-safe |
|---|---|---|---|
| `Driver.tick`, grant | `reserve_ready_o` = initialized and affordable in the same cycle | `reserve_ready_o` = not in reset, link up, and the same request in the previous cycle, initialized and affordable then, with no consume in that cycle | Once initialized, credit falls only by a consume, which blocks the next grant, and rises only by UpdateFC. A registered grant is therefore never one the current state would refuse. There is no early consume, and every debit is still taken exactly once at the grant. |
| `Driver.tick`, UpdateFC | Checked and applied at the end of the cycle it is presented, after that cycle's debit; `protocol_error_o` after that cycle | Checked and applied one cycle later, after that later cycle's debit; `protocol_error_o` one cycle later; an UpdateFC presented in a reset or link-down cycle is dropped as before | An UpdateFC taking effect one cycle later only delays credit. The half-range and non-negative checks still use the post-debit balance of the cycle in which it is applied, so a simultaneous debit is never returned. |
| `Driver.grant` (new helper) | - | Presents a request with valid low for one cycle, then with valid high, and returns the grant | Exercises a request the way the replay store presents it: request lines settled before valid rises |
| `initialization_and_finite_atomic_reservations` | Each request size presented for one cycle | Each request size presented through `grant`; one more cycle of the 1-DWORD request after the UpdateFC; the 5-DWORD and illegal requests through `grant` | Without the hold, no request would be granted and the test would check nothing. The debit sizes and pools checked are unchanged. |
| `infinite_pools_replay_and_link_reset` | `(2,4)` request for one cycle; TLP confirmation directly after the third InitFC1 | `(2,4)` through `grant`; one idle cycle before the TLP, so the delayed third InitFC1 is applied before the TLP confirms InitFC2 | Same events in the same order |
| `modulo_counters_random_credit_return_and_stalls` | 12,000 cycles, a new random request each cycle | 24,000 cycles, each random request held for two cycles (12,000 requests, same random sequence) | Same request stream. The progress assertion (more than 256 headers and 4096 data credits per class) still holds. |
| `corrupt_credit_events_never_grant_or_reset_limits` | Requests for one cycle; grant in the cycle after the restoring UpdateFC | Requests through `grant`; one idle cycle after the restoring UpdateFC | The corrupt events still neither grant nor change limits. |
| `same_cycle_update_debit_exhausts_exactly_once` | UpdateFC and debit presented in the same cycle; back-to-back grants | UpdateFC presented one cycle before the debit, so that it is applied in the debit's cycle; the cycle after each consume is asserted not ready; exhaustion asserted after it; the restoring update is followed by one idle cycle; the idle-bus check waits one more cycle before inspecting limits | Every original assertion is kept: one returned credit is granted exactly once, an update to another class does not overwrite a debit, the half-range check uses the post-debit balance, data and header exhaustion are separate, and an idle-bus request cannot rescue an invalid UpdateFC. |

The per-cycle comparison of `header_limit_o`, `header_consumed_o`, `data_limit_o`, `data_consumed_o` and `infinite_o` against unbounded counters is unchanged. It checks that no credit is lost or duplicated.

### Added latency, both rounds together

| Path | Added cycles | Limit it must stay within |
|---|---|---|
| Received TLP to its ACK/NAK on the wire | +3 (receive slice, receive commit, transmit slice) | AckNak latency; the peer's replay timer |
| Received ACK/NAK to retirement in the replay store | +2 (receive slice, registered retirement) | This design's replay timer, 1024 packet clocks |
| Received UpdateFC to credit, and to a reservation grant | +2 to credit (receive slice, delayed update); a grant needs one more cycle | Credit only arrives later (conservative) |
| New TLP reservation | +1 (registered verdict, when the request has just changed) | none; flow control only delays |
| Locally generated completion to the wire | +1 (transmit slice) | none |
| FC DLLP advertisement to the wire | +1 (advertiser slice) | FC update timer: microseconds |
| Release after reset, link up or retraining | +1 to +3 by block; link loss and retraining assert at once | Link training takes microseconds |

All of these are a few 4 ns cycles. The replay timer is 1024 packet clocks (4 us), and the AckNak and UpdateFC limits are hundreds of symbol times. Replay ordering and the replay timer start at the wire-side end of frame are unchanged.

### Verification of the final head

On `19418ffa9` (RTL as of `2fd0a2c70`), run 42474676706:

- unit tests 64/64:
  - `replay_tx` 7, `flow_packets` 3, `buffered_flow_packets` 5, `reliable_packets` 4, `credit_tx` 5 (revised oracle), `rx_credit` 5, `fc_tx` 3, `fc_tx_eop` 1, `lcrc_tx` 2;
  - `packet_endpoint` 6, `link_packets` 3, `tlp_regs` 6, `tlp_stream` 6, `tlp_integrity` 6, `gpio` 2;
- joint SoC PCIe + Ethernet traffic PASS 2/2 with an asynchronous packet clock and PASS 2/2 with a synchronous one;
- `check_soc_lint.py` base and full PASS with no new or stale warnings.

The workflow now retries transient release-download failures (`19418ffa9`). This run still met HTTP 504s and passed after retries.

### Block screen, before and after both rounds

Packet-domain register-to-register setup in the screen described above, ns:

- baseline: `eb088ef4c`, run 42463873679;
- first round: `3b102cca0`, run 42464911092;
- final: run 42474676706.

"Core" leaves out the link status, reset release and registered link/reset copy flops as startpoints.

| Stage | Corner | View | Baseline WNS / TNS | First round WNS / TNS | Final WNS / TNS |
|---|---|---|---:|---:|---:|
| repaired | typical | all | -1.19 / -2205 | -0.92 / -118 | **-0.22 / -3.4** (88 endpoints) |
| repaired | typical | core | -1.17 / -2107 | -0.92 / -61 | **-0.22 / -0.65** (5 endpoints) |
| repaired | slow | all | -4.07 / -13049 | -3.72 / -6425 | **-2.60 / -4537** |
| repaired | slow | core | -4.06 / -12577 | -3.72 / -4126 | **-2.60 / -2912** |
| sized | typical | all | -2.45 / -4280 | -1.48 / -1648 | -2.10 / -1221 |
| sized | typical | core | -2.44 / -4200 | -1.48 / -412 | -1.62 / -561 |
| sized | slow | all | -6.00 / -16497 | -4.56 / -10593 | -5.45 / -8797 |
| sized | slow | core | -5.98 / -16091 | -4.56 / -5386 | -4.73 / -4889 |

In the final sized "all" view, the worst paths start at the registered link/reset copies. Each copy still drives a whole block's resets and enables, and this standalone placement's sizing-only stage builds deep buffer trees for them. Repair removes most of that.

The final design has more flops, and the TNS figures cover the worst 5000 endpoints only.

Logic cells (non-buffer, non-inverter) of the worst path per block, sized slow, with the deepest reported path of the block in parentheses:

| Block | Baseline | First round | Final |
|---|---:|---:|---:|
| Replay store capture | 19 (20) | 8 (9) | 10 (11) |
| Replay send setup and reservation | 18 (19) | 15 (19) | 9 (12) |
| Credit reservation and UpdateFC | 21 (21) | 17 (17) | 17 (17) |
| LCRC framer | - | 16 (18) | 13 (13) |
| Receive slice and consumers | 19 (21) | 13 (14) | 8 (11) |
| Receive queue | 13 (13) | 11 (20) | 11 (17) |
| FC advertiser | - | 9 (14) | 8 (9) |
| TLP register backend | - | 12 (13) | 10 (12) |

The largest logic depth among the worst paths per endpoint (sized slow) is:

- baseline: 21 logic cells, with 1318 paths over 12;
- first round: 20, with 210 over 12;
- second round: 17, with 138 over 12.

An earlier version of this sentence used a summary line that picked the path with the most cells; `paths.py` now reports the path with the most logic cells.

### Physical probe

The main-chip implementation probe ran on this branch's RTL (`19418ffa9`), run 42474676706, with the configuration of the reference rows:

- density 70%;
- Kogge-Stone carry mapping;
- upstream register file;
- LibreLane `PacketInterfaces` up to and including global route, antenna repair and the capped post-GRT repair;
- three-corner OpenROAD STA with propagated clocks and global-route parasitics.

Setup worst slack per clock group, ns:

| Corner | `pcie_clk_i` this branch | `pcie_clk_i` reference before extra repair (run 42257277688) | asynchronous | `clk_i` | `eth_rx_clk_i` | `eth_tx_clk_i` |
|---|---:|---:|---:|---:|---:|---:|
| slow | **-3.55** | -8.74 | -3.42 | -4.58 | -1.51 | -1.91 |
| typical | **-0.84** | -4.11 | -0.84 | 4.33 | 1.97 | 1.78 |
| fast | 0.28 | -1.46 | 0.62 | 9.69 | 3.44 | 3.85 |

Notes on these numbers:

- The worst slow-corner `pcie_clk_i` path arrives at 8.35 ns over about 24 cells, against 10.65 ns over about 47 cells in run 42436769600. The worst typical-corner path ends at the `pcie_rx_ready_o` output port.
- Before any extra repair, the slow corner is now better than the reference after its uncapped repair (-5.76 ns).
- The asynchronous group also improves, from -7.71 ns to -3.42 ns at slow. The link/reset copies take the combined reset off the large recovery fanout.
- `clk_i` and Ethernet are not changed here; their differences reflect placement.

The uncapped setup repair ran on the same database in the same run (deep variant). It used `repair_design` and `repair_timing -setup -setup_margin 0 -repair_tns 100 -max_iterations 1000000`. It finished in 24 minutes with RSZ-0062, after 655 resizes, 272 buffers and 135 pin swaps.

| Corner | `pcie_clk_i` this branch | `pcie_clk_i` reference after uncapped repair (run 42436769600) | asynchronous | `clk_i` |
|---|---:|---:|---:|---:|
| slow | **-2.61** | -5.76 | -2.16 | -2.52 |
| typical | **-0.26** | -2.31 | 0.06 | 5.68 |
| fast | 0.55 | -0.34 | 1.34 | 9.87 |

The capped stage of this deep job reproduced the -3.55/-0.84/0.28 ns of the capped job. After repair, the worst `pcie_clk_i` path arrives at 7.41 ns at slow over 32 cells. It is mostly a chain of alternating `o21ai`/`a21oi` cells, which is the shape of a ripple carry or long priority chain. Its registers are unnamed (`$auto$ff.cc`) in the probe netlist.

## Third round: the routed worst path, the receive gate and the asynchronous group

### Changes (`4077a84cb`)

**`soc_pcie_credit_tx`, the routed worst path.** After uncapped repair the worst routed `pcie_clk_i` path (run 42474676706) was:

- 32 cells, starting at a mux2, then XNOR, then 12 alternating `o21ai`/`a21oi`/`a21o` carry cells, then the sign, then `nand4`/`or4`, then a fanout tree, then the register.

That is the second UpdateFC stage: `d_idle_remaining` (a mux of `update_d_debit`/`update_d_idle`) plus `request_data_negated`, whose sign gates `d_update_ok` and therefore every limit and balance write. In the block screen it is `credits.update_d_debited` -> `credits.ad`/`dl`/`hl`/`confirmed`. The second stage also ran the limit-advance subtractions `update_data - dl` and `update_header - hl`.

The second stage is now pure selection:

- **Two-cycle request hold.** A request is granted only after it has been presented unchanged for two cycles (new `request_stable` register). A debit that meets an UpdateFC in either of the UpdateFC's two cycles therefore uses the same registered required credit, and two consumes are never adjacent. The first stage's "one debit" balance (`update_d_debit`, `update_h_debit`) is then exact for a debit in either cycle.
- **Advance signs in the first stage.** The first stage registers the limit-advance sign twice: against the current limit, and against the limit the UpdateFC applied in that same cycle writes. It also registers whether that write hits the same class. The second stage selects, which is exact for back-to-back UpdateFCs of one class.

This is protocol-safe for the producer in this SoC. `soc_pcie_replay_tx` presents the class and payload of the offered slot from registers that stay fixed for the whole offer, so the hold only costs one more cycle when the offered slot changes. The request is still cancellable until the handshake.

**`soc_pcie_buffered_flow_packets`.** The receive queue's FC-initialization gate (`peer_init1_done && local_init2_sent`) is a register. Initialization only rises once per link epoch. TLPs are accepted one cycle after FC initialization. No test changed.

**FC refresh counter.** The 32-bit `soc_pcie_fc_tx` refresh counter was a suspect, but it is not on the worst paths: the FC advertiser's worst is at most 9-11 logic cells. It was left unchanged.

### `test_soc_pcie_credit_tx.py` changes in this round

| Where | Second-round expectation | Third-round expectation | Why it is protocol-safe |
|---|---|---|---|
| `Driver.tick`, grant | Same request in the previous cycle | Same request in each of the two previous cycles (`stable`), affordable and initialized in the previous one, no consume in it. The request registers are modelled as the module keeps them: cleared by reset, held across link loss | A grant waits longer, never earlier. Every debit still happens exactly once at the grant. |
| `Driver.grant` | One cycle with valid low, then valid | Two cycles with valid low, then valid | As above |
| `modulo_counters_random_credit_return_and_stalls` | 24,000 cycles, each request held two cycles | 36,000 cycles, each request held three cycles (12,000 requests, same random sequence) | Same request stream. The progress assertion still holds. |
| `same_cycle_update_debit_exhausts_exactly_once` | Request first presented together with the UpdateFC | One settling cycle with the request before the UpdateFC cycle, in the three blocks that present an UpdateFC just before a debit | Every assertion is unchanged |

All original assertions remain: exactly-once debit, exhaustion, class isolation, the post-debit half-range check, data vs header exhaustion, and the idle-bus check. The per-cycle comparison of limits and consumed counts against unbounded counters is unchanged.

### Added latency in this round

- New reservation after the offered slot changes: +1 more cycle, 2 in total.
- Receive queue opening after FC initialization: +1 cycle, once per link epoch.

Neither path is bounded by the replay timer or the AckNak limits.

### Asynchronous group

The worst asynchronous paths in the probe (run 42474676706) launch in the core clock domain. The startpoint is a `clk_i` flop driving the synchronized system reset `rst_sys_n`, which feeds a 4-6 stage buffer tree. The endpoints are the `RESET_B` pins of two `pcie_clk_i` flop pairs, both reset-synchronizer first stages:

- `soc_top`'s `packet_reset_release[1:0]`, reset directly by `rst_sys_n`: -2.16 ns slow after uncapped repair;
- `u_pcie_cdc`'s `source_release[1:0]`, reset through the `nor3` of `rst_sys_n && pcie_link_up_i && !pcie_retrain_done_i`: -3.42 ns before repair.

These are recovery checks of a core-domain reset on synchronizer inputs. Per the round's rule they are reported here and not changed. Possible remedies, outside the packet RTL:

- give the PCIe synchronizers their own leaf of the `rst_sys_n` tree;
- or constrain the asynchronous-assertion inputs of the two synchronizers.

Inside the packet domain, the per-block link/reset copies of the second round already give every block its own registered, synchronously released reset that asserts asynchronously. In the block screen the packet-internal recovery is met at both corners: +0.15 ns slow and +1.47 ns typical after repair, with 0 violating endpoints.

### Verification of the final head (`4077a84cb`)

- unit tests 64/64 (run 42522225587), with `credit_tx` 5/5 under the revised oracle;
- joint SoC PCIe + Ethernet traffic PASS 2/2 asynchronous and PASS 2/2 synchronous (run 42522972371);
- `check_soc_lint.py` base and full PASS with no new or stale warnings (run 42522972371).

### Block screen (run 42522225587), ns, worst slack / TNS

| Stage | Corner | Second round | Third round |
|---|---|---:|---:|
| repaired | typical | -0.22 / -3.4 | **+0.15 / 0** (0 violating) |
| repaired | slow | -2.60 / -4537 | **-2.07 / -3281** |
| sized | typical | -2.10 / -1221 | -1.10 / -299 |
| sized | slow | -5.45 / -8797 | -3.98 / -5906 |

The largest logic depth among the worst paths per endpoint stays at 17 logic cells: 148 paths are over 12, against 138 in the second round. The second UpdateFC stage is no longer among them. The 17-cell cones now are:

- the UpdateFC first stage, `receiver.fc_class_o` -> `credits.update_d_debit`: the class mux of the consumed count, the carry-save step and one 12-bit adder into a register;
- the consume, `credits.request_class` -> `credits.dc`.

### Physical probe (run 42522972371)

Same configuration as before, on `4077a84cb`. Setup worst slack, ns:

| Corner | `pcie_clk_i` capped (second round) | `pcie_clk_i` after uncapped repair (second round) | asynchronous capped (second round) | asynchronous after uncapped repair (second round) |
|---|---:|---:|---:|---:|
| slow | -3.60 (-3.55) | **-1.75** (-2.61) | -3.32 (-3.42) | **-1.65** (-2.16) |
| typical | -1.30 (-0.84) | **-0.08** (-0.26) | -0.78 (-0.84) | **+0.21** (+0.06) |
| fast | -0.17 (+0.28) | +0.86 (+0.55) | +0.64 (+0.62) | +1.26 (+1.34) |

The uncapped repair stopped with RSZ-0062 after 689 resizes, 227 buffers and 120 pin swaps. After it, `pcie_clk_i` is 1.75 ns short at slow and 0.08 ns at typical, against 5.76 and 2.31 before this branch.

Before the extra repair, the worst `pcie_clk_i` paths at both corners are now RX boundary paths, not internal ones:

- input port `pcie_rx_dllp_i`, through a `dlygate4sd3` hold-fix cell, into `soc_pcie_rx_credit`'s kind-dependent `rx_ready_o` and its staging write enables (-3.60 ns slow);
- the same logic to output port `pcie_rx_ready_o` (-1.30 ns typical).

Both carry the 0.8 ns input and output delays of the SDC. The capped numbers therefore did not improve in this round, but the uncapped repair removes these paths.

After the uncapped repair, the worst internal path (slow, 6.67 ns arrival, 24 cells) is again carry-shaped: about 10 `o21ai`/`a21oi` cells. In the block screen the candidates are the UpdateFC first stage (`fc_class_o` -> `update_d_debit`) and the consume adder into `dc`, both 17 logic cells.

The asynchronous worst is unchanged in kind. It is the core-domain `rst_sys_n` (`clk_i` flop) into the `u_pcie_cdc` release synchronizer through the `nor3`, reported above.

## What remains

- **RX boundary.** The capped worst paths start at the input ports: `pcie_rx_dllp_i` reaches `rx_ready_o` and the staging enables combinationally, and hold repair puts a delay cell on that input. An input register slice before the receive queue would make `pcie_rx_ready_o` a flop output and start the queue's paths at registers. It costs one cycle, and stream order and frame-start blocking are unchanged, since the PHY stream is in order.
- **Two 17-logic-cell cones in `soc_pcie_credit_tx`.**
  - The UpdateFC first stage (a class mux of the consumed count, carry-save, one 12-bit adder): registering the per-class "limit minus consumed" balance of the incoming class one cycle ahead would split it.
  - The consume into `dc`: the grant feeds a 12-bit add-and-select; selecting a precomputed `dc + required` would remove the adder from behind the grant.
- **Asynchronous group (core domain).** `rst_sys_n` from the `clk_i` reset synchronizer reaches the PCIe-domain synchronizer inputs through the core reset buffer tree. It needs its own reset leaf, or constraints for asynchronous-assertion inputs. This is outside the packet RTL and was not changed here.
- **Closure.** After uncapped repair, typical is within 0.08 ns. Slow `pcie_clk_i` still needs about 1.75 ns, and the asynchronous group about 1.65 ns.
