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

## Fourth round: receive input slice, credit next state, packet reset leaf

### Changes (`02792dcdb`)

- **Receive input register slice** (`soc_pcie_buffered_flow_packets`). A `soc_pcie_stream_skid` now sits in front of the receive queue. `pcie_rx_ready_o` is the slice's room (a flop) ANDed with the block's registered reset copy, so it stays low in reset. The receive queue's paths start at registers instead of the input ports. Beats keep their order and are never retracted. The queue's kind-dependent ready applies at the slice output, so a beat the queue cannot take waits in the slice, as it waited at the PHY before, with everything behind it. Received beats arrive one cycle later.
- **`soc_pcie_credit_tx` next state** (ports unchanged cycle for cycle; random co-simulation against the third-round module: four seeds, about 71,000 grants each, 0 mismatches):
  - the verdict, and the UpdateFC first stage's balances and advance signs, are computed per class from that class's registers; the request or event class selects a finished result;
  - every register's next value is computed twice, for "consumed in this cycle" and "not consumed", from registers only, and the consume is the last select;
  - the consumed counts after a debit (`hc+1`, `dc+required`) are registered one cycle ahead. This is exact: a consume never follows a consume, only a consume changes a consumed count, and the two-cycle request hold keeps `request_data` across the cycle.
- **Packet reset leaf** (`soc_top.v`, packet-async build only). A dedicated `clk_i` flop, `pcie_sys_rst_n`, asserts with `rst_raw_n` (together with `rst_sys_n`) and releases one `clk_i` cycle after `rst_sys_n`. It resets only the packet-domain reset synchronizer `packet_reset_release` and the APB mailbox release flops (through the existing `reset_ni` combination). Their recovery path now starts at this flop instead of the end of the CPU's `rst_sys_n` tree. Asynchronous assertion, synchronous release and the CDC structure are unchanged. No SDC exception covers these paths, and none was added. All recorded `soc_top.v` lint warnings are before line 716, so the lint ledger is unaffected.

### Added latency in this round

- Received beats: +1 cycle (input slice). Received TLP to its ACK/NAK on the wire is now +4 cycles in total, and ACK/NAK or UpdateFC to its effect +3, all far inside the 1024-cycle replay timer and the AckNak limits.
- Packet-domain release after a system reset: +1 `clk_i` cycle.

### Logic depth in `soc_pcie_credit_tx`

A bare registered 12-bit adder maps to 12-13 logic cells with this library and the `abc -D 20` recipe, with or without Kogge-Stone carries, and a hand-written carry-select version maps the same. The remaining `credit_tx` cones of 13-16 logic cells are such additions, now with only a register or a final select around them:

- the UpdateFC first stage: `fc - consumed` and its carry-save debit variant, `fc - limit`;
- the registered `dc + required`;
- `ad`'s consume value.

Going below 12 would need each addition split across another register stage.

### Verification of the final head (`02792dcdb`, run 42533689396)

- unit tests 64/64 with no test changed in this round;
- joint SoC PCIe + Ethernet traffic PASS 2/2 asynchronous and PASS 2/2 synchronous;
- `check_soc_lint.py` base and full PASS with no new or stale warnings.

### Block screen (run 42533689396), ns, worst slack / TNS

| Stage | Corner | Third round | Fourth round |
|---|---|---:|---:|
| repaired | typical | +0.15 / 0 | **+0.90 / 0** |
| repaired | slow | -2.07 / -3281 | **-0.77 / -832** |
| sized | typical | -1.10 / -299 | -0.33 / -7 |
| sized | slow | -3.98 / -5906 | -2.62 / -4267 |

The largest logic depth among the worst paths per endpoint (sized slow) is 16 logic cells, in the UpdateFC first stage. 97 paths are over 12, against 148. Packet-internal recovery is met (+0.10 ns sized, +0.38 ns repaired, slow).

### Physical probe

Run 42533689396 on `02792dcdb`, same configuration as before. Setup worst slack, ns:

| Corner | `pcie_clk_i` capped (third round) | `pcie_clk_i` after uncapped repair (third round) | asynchronous capped (third round) | asynchronous after uncapped repair (third round) |
|---|---:|---:|---:|---:|
| slow | -3.21 (-3.60) | **-1.44** (-1.75) | -1.50 (-3.32) | **-0.58** (-1.65) |
| typical | -0.68 (-1.30) | **+0.29** (-0.08) | +0.42 (-0.78) | **+1.01** (+0.21) |
| fast | +0.56 (-0.17) | +1.08 (+0.86) | +1.37 (+0.64) | +1.73 (+1.26) |

The uncapped repair stopped with RSZ-0062 after 1498 resizes, 614 buffers and 376 pin swaps. Against the reference at the start of this branch (-5.76 slow, -2.31 typical after uncapped repair):

- `pcie_clk_i` is now met at typical and 1.44 ns short at slow;
- the asynchronous group is met at typical and 0.58 ns short at slow.

The capped worst `pcie_clk_i` path is internal again; the receive input slice removed the boundary paths. After repair, the worst slow path (6.44 ns arrival, 24 cells) has the shape of the UpdateFC first stage: XNOR/XOR carry-save cells followed by a 15-cell `o21ai`/`a21o` carry chain into a register. That is `fc - consumed - required`, which this mapping builds as a ripple carry.

The asynchronous worst path now starts at the new `clk_i` leaf flop and reaches the mailbox release flop's `RESET_B` through only `nor4`/`nand2`/`buf` (the `reset_ni` combination). The remaining -0.58 ns is the cross-clock recovery requirement itself: launch on `clk_i` and capture on `pcie_clk_i`, with the clocks' insertion-delay difference. That is not logic depth. The right fix is a constraint on the asynchronous-assertion input of these synchronizers (for example a false path or max delay to their `RESET_B`), not more RTL. No such exception exists today, and none was added.

## Fifth round: credit and receive-path additions across register stages

### Changes (`bfa1bc32a`)

- **`soc_pcie_credit_tx`: UpdateFC in three stages.**
  - Stage A registers the event.
  - Stage B forms, from this cycle's consumed counts, limits and registered required credit:
    - the balances without a debit and with one debit (carry-save form);
    - the limit-advance sums against the current limit and against the limit written by the event applied in B's cycle.

    Each is built in 4-bit blocks: the low block, and the middle and high blocks for both carries in. Each class is computed from its own registers and the event's class selects.
  - Stage C chains two carry selects and applies the update.

  A debit in A's cycle is already in B's consumed counts. Debits in B's and C's cycles are never adjacent, and the two-cycle request hold makes B's required credit the one for either debit. A two-debit variant is therefore not needed.
- **`soc_pcie_credit_tx`: consumed count after a debit.** The low half of `dc + required` and its carry are registered a cycle ahead, and the high half is finished in the consume's cycle. This is exact: there are no adjacent consumes, and the request hold keeps the required credit.
- **`soc_pcie_rx_credit`.** The low half of the released data credit (`data_limit + units` of the head's class) is registered a cycle ahead and finished at the removal. A removal never follows a removal, and the head is fixed while a verdict is awaited. Slots now store their last index instead of their length, so the frame end needs no decrement. Ports are unchanged (random co-simulation: 300,000 cycles, 0 mismatches).
- **`soc_pcie_sequence_rx`.** `expected - received`, `expected + 1` and `expected - 1` are registered a cycle ahead. `expected` changes at most once per received packet, and `received` is fixed from the packet's second byte until its verdict. Ports are unchanged.

`soc_pcie_credit_tx` equals the fourth-round module with its UpdateFC inputs delayed by one register, cleared in reset and link-down (Icarus random co-simulation: four seeds, about 71,000 grants each, 0 mismatches).

### `test_soc_pcie_credit_tx.py` changes in this round

| Where | Fourth-round expectation | Fifth-round expectation | Why it is protocol-safe |
|---|---|---|---|
| `Driver.tick`, UpdateFC | Applied one cycle after it is presented | Applied two cycles after it is presented (two-entry pending queue, emptied by reset and link loss), after that cycle's debit | Credit only arrives later. The post-debit balance checks are unchanged. |
| `Driver.init` | Ends one cycle after the InitFC2-confirming event | Ends two cycles after it | The confirming event takes effect before the tests start, as before |
| `infinite_pools_replay_and_link_reset` | One idle cycle before the confirming TLP | Two idle cycles | The third InitFC1 is applied before the TLP, as before |
| `same_cycle_update_debit_exhausts_exactly_once` | UpdateFC presented one cycle before the debit; one cycle after an invalid update; one idle-bus cycle | One more settling cycle in each, so the update is still applied in the debit's cycle, and the idle-bus check still looks after the update is applied | Every assertion is unchanged |

All original assertions remain, along with the per-cycle comparison of limits and consumed counts against unbounded counters.

### Added latency in this round

UpdateFC to its effect: +1 cycle. Against the baseline, a received UpdateFC now takes effect four cycles later: the input slice, the receive slice, and two added UpdateFC stages. Credit only arrives later; nothing else moved.

### What constraint the asynchronous group needs

The worst asynchronous paths (run 42533689396, -0.58 ns slow after repair) start at `soc_top`'s `pcie_sys_rst_n` flop (`clk_i`). They end at the `RESET_B` pins of:

- `packet_reset_release[0]` and `packet_reset_release[1]` (`pcie_clk_i`);
- `u_pcie_cdc.source_release[0]` and `[1]` (`pcie_clk_i`), through the `reset_ni` combination with `pcie_link_up_i` and `pcie_retrain_done_i`.

Both pairs are two-flop reset synchronizers with asynchronous assertion and synchronous release in `pcie_clk_i`. The release edge launched in `clk_i` is asynchronous to `pcie_clk_i` by design, and the second stage resolves its metastability. A recovery/removal check across the two clocks therefore does not describe a real requirement. The remaining -0.58 ns is the cross-clock window plus the clock insertion-delay difference, not logic.

The correct exception, written as the existing `pcie_soc_constraints.py` binds the mailbox CDC (from the mapped netlist's net names, since the flops themselves are `$auto` cells), would be:

- `set_false_path -from [get_clocks clk_i] -to <RESET_B of packet_reset_release[1:0] and u_pcie_cdc.source_release[1:0]>`, for recovery and removal. A false path is the right kind because neither the assertion (asynchronous) nor the release (resynchronized) needs `clk_i`-to-`pcie_clk_i` timing.
- Optionally, if the owner wants the two stages of each synchronizer to receive the reset within one `pcie_clk_i` cycle of each other: `set_max_delay -ignore_clock_latency 4.0 -from <pcie_sys_rst_n flop/CLK> -to <the same RESET_B pins>` together with `set_false_path -hold` on the same paths. This follows the 8.0 ns `-ignore_clock_latency` max-delay style the SDC already uses for its CDC groups, and bounds skew without inventing a clock relationship.
- The `u_pcie_cdc.destination_release` flops are clocked by `clk_i` like their source, so their checks stay as they are.

No such exception exists in the SoC SDC today; the standalone mailbox constraints only false-path their `reset_ni` port. The SDC was left unchanged.

### Verification of the final head (`bfa1bc32a`)

- unit tests 64/64 (run 42545552350), `credit_tx` 5/5 under the revised oracle;
- SoC lint and joint traffic: run 42545773596 (see below).

### Block screen (run 42545552350), ns, worst slack / TNS

| Stage | Corner | Fourth round | Fifth round |
|---|---|---:|---:|
| repaired | typical | +0.90 / 0 | +0.88 / 0 |
| repaired | slow | -0.77 / -832 | -0.78 / -1687 |
| sized | typical | -0.33 / -7 | **0.00 / 0** |
| sized | slow | -2.62 / -4267 | **-2.19 / -5911** |

The largest logic depth among the worst paths per endpoint goes from 16 to 14 logic cells. The UpdateFC first stage is no longer among the deepest. The deepest are now the replay transmit slice (`main_valid` -> `spare_data`) and `credit_tx`'s consume value for `ad` (`ad + (-required)`, a full 12-bit addition behind the grant). After repair, the screen's slow corner is unchanged within the run-to-run spread.

### Physical probe (run 42545773596)

Run 42545773596 on `bfa1bc32a`. SoC lint (base and full: no new or stale warnings) and joint traffic (asynchronous and synchronous: PASS 2/2 each) pass in the same run. Setup worst slack, ns:

| Corner | `pcie_clk_i` capped (fourth round) | `pcie_clk_i` after uncapped repair (fourth round) | asynchronous capped (fourth round) | asynchronous after uncapped repair (fourth round) |
|---|---:|---:|---:|---:|
| slow | -3.95 (-3.21) | **-2.42** (-1.44) | -0.51 (-1.50) | **-0.51** (-0.58) |
| typical | -1.01 (-0.68) | **-0.49** (+0.29) | +0.85 (+0.42) | **+0.85** (+1.01) |
| fast | +0.50 (+0.56) | +0.58 (+1.08) | +1.59 (+1.37) | +1.59 (+1.73) |

**`pcie_clk_i` regressed in this run.** The credit cones are no longer on the worst path. The new worst slow path (7.55 ns arrival, 4.80 ns required after the 0.19 ns launch/capture clock skew) has only 10 logic cells; its delay is in weak cells driving long nets:

- an `a22oi_1` driving 0.126 pF (1.26 ns);
- a `nand4_1` (1.29 ns);
- a `nor4_2` (0.92 ns).

They follow a high-fanout flop through `buf_16` stages. That is the shape of a wide one-hot AND-OR select, most likely `soc_pcie_rx_credit`'s 228-byte read into the receive slice, whose logic has not changed since the second round. The uncapped repair (814 resizes, 235 buffers) stopped with RSZ-0062 without upsizing these cells. The third-worst endpoint is the `pcie_error_o` output port (-2.34 ns), an OR of error pulses with a 0.8 ns output delay.

This round's changes shorten logic only, and the paths they touch are not among the worst. Run-to-run placement spread in this probe has been about 1 ns. The regression is therefore attributed to placement of the receive-queue read, not to the split additions, but that is unconfirmed. A rerun of the fourth-round head with the same seed would separate the two.

## Sixth round: noise measurement, registered receive-queue read, registered error report

### Changes (`b9dd20e38`; `9b6e3da7d` only fixes the workflow file)

- **`soc_pcie_rx_credit`: registered read per bank.** Each bank's byte at the current read index is a register. It is loaded with:
  - the byte at the next index on a mid-frame handshake (the AND-OR select now uses the next one-hot cursor);
  - byte 0 at an end of frame, link loss or reset;
  - `staging[0]` when the bank is committed;
  - otherwise its own value.

  A committed bank is free, so it is never read mid-frame, and it is first read at index 0. Every byte that leaves therefore equals the array's. The output needs only the one-hot head select of six registers. Ports and ordering are unchanged (random co-simulation against the fifth-round module: four seeds, 300,000 cycles each, 163,065-163,405 output beats, 0 mismatches).
- **`soc_pcie_buffered_flow_packets`: registered `error_o`.** The same one-cycle error pulses leave from a flop, one cycle later. The only consumer is `soc_top`'s `pcie_error_o`. The only test that reads it, `test_soc_pcie_ethernet.py`, adds it into an error count and requires the count to be zero, so no test change is needed. The buffered tests do not read `error_o`.
- **No placement region was added.** The LibreLane 3.0.5 flow used here has no configuration variable for a standard-cell region or group. One would need a custom floorplan script that also constrains the placement around the other blocks, which this round was not to touch.
- **Workflow.** The implementation-probe matrix is an input, with an optional RTL commit per entry, so older heads can be probed with the current scripts.

### Probe noise

LibreLane 3.0.5 has no placement seed, and its global placement is deterministic. Rerunning the fourth- and fifth-round heads at the reference settings reproduced every reported slack line of their original probes (runs 42533689396 and 42545773596) exactly. A fixed netlist therefore has no run-to-run noise; the variation between heads is the placement's sensitivity to small changes in its input. To measure that sensitivity, each head was probed at the reference target density (70%) and at a perturbed one (68%), with otherwise identical settings (run 42556633463, uncapped repair for every entry; "capped" is the post-GRT state before it).

Worst slack in ns. "Capped" is the post-GRT state, "deep" the state after the uncapped repair. The asynchronous group is not changed by the uncapped repair except in the first row.

| Head | Density | Capped pcie_clk_i slow / typ | Deep pcie_clk_i slow / typ | Deep asynchronous slow / typ |
|---|---:|---:|---:|---:|
| fourth round `02792dcdb` | 70% | -3.21 / -0.68 | -1.44 / +0.29 | -0.58 / +1.01 |
| fourth round `02792dcdb` | 68% | -3.43 / -0.76 | -1.69 / +0.07 | -1.20 / +0.52 |
| fifth round `bfa1bc32a` | 70% | -3.95 / -1.01 | -2.42 / -0.49 | -0.51 / +0.85 |
| fifth round `bfa1bc32a` | 68% | -4.53 / -1.37 | -1.54 / +0.14 | -0.99 / +0.55 |
| sixth round `b9dd20e38` | 70% | -3.01 / -0.65 | -1.47 / +0.24 | -0.78 / +0.70 |
| sixth round `b9dd20e38` | 68% | -2.98 / -0.73 | -1.30 / +0.25 | -0.01 / +1.17 |

Findings:

- A 2% density change moves the deep slow `pcie_clk_i` slack by 0.25 ns (fourth round), 0.88 ns (fifth round) and 0.17 ns (sixth round). The fifth-round regression at 70% (-0.98 ns against the fourth round) is the same size as this sensitivity: at 68% the fifth round beats the fourth round. The fifth-round RTL was not worse; its 70% placement was unlucky.
- The sixth round has the best worst-of-two slow slack (-1.47, against -1.69 and -2.42) and the smallest spread. Its typical slack is positive at both densities, and its capped slack is the best of the three heads at both densities.
- `pcie_error_o` is no longer among the violating `pcie_clk_i` endpoints (fifth round: -2.34 ns slow).
- The worst sixth-round path (70%) is a wide AND-OR: a reset flop with fanout 8, two buffers, then `a22oi`, `nand4`, `nor4`, `and3` and `o21ai`. The slow four-input cells and the buffered fanout take most of the delay, not the logic depth. The artifact's flop names are anonymous, so the path could not be tied to a source register.
- The asynchronous group spans -1.50 to -0.01 ns across the twelve placed states. It depends on placement alone, which supports the constraint recommendation above over further RTL work.

### Verification of the final head (`9b6e3da7d`)

- unit tests 64/64 (run 42556623897);
- joint SoC PCIe + Ethernet traffic PASS 2/2 asynchronous and PASS 2/2 synchronous (run 42556623897);
- `check_soc_lint.py` base and full PASS with no new or stale warnings (run 42556623897).

Block screen (run 42556623897), worst slack / TNS in ns, against the fifth round:

| Stage | Corner | Fifth round | Sixth round |
|---|---|---:|---:|
| sized | slow | -2.19 / -5911 | -1.89 / -2753 |
| sized | typical | 0.00 / 0 | +0.17 / 0 |
| repaired | slow | -0.78 / -1687 | -1.29 / -1782 |
| repaired | typical | +0.88 / 0 | +0.59 / 0 |

## Seventh round: paths tied to RTL registers, and the cuts they asked for

### Path tracing in the implementation probe

The probe now reports the 300 worst slow-corner `pcie_clk_i` endpoints with full paths, twice: after the capped post-GRT repair and after the uncapped repair. `scripts/pcie_timing/trace_paths.py` looks up every instance on these paths in the synthesized netlist (the Yosys JSON that enters placement, where instance names survive placement and repair; only inserted buffers are new). It names each flip-flop by the public net on its Q pin, which carries the RTL register name and bit, and by its `src` attribute. Two cases need care when reading the names:
- a flop whose register name was purged keeps the name of a port it drives, for example `u_pcie.flow.credits.link_up_i` for the credit logic's link copy in `soc_pcie_flow_packets`;
- a one-hot cursor bit can show as its rotated alias, for example `next_onehot[k]` for `read_onehot[k-1]`.

The `src` attribute settles both. The artifact also has every flop of the netlist mapped this way (`flop-map.tsv.gz`), the netlist itself, and the traced reports (`capped-trace.txt`, `deep-trace.txt` and the JSON with every cell).

### Where the traced head was slow (`76c259aca`, run 42569863473, after the uncapped repair)

That head is the sixth round plus the `ad` split below. At 70% target density the ten worst register pairs at the slow corner were (slack in ns; endpoint count among the 300 reported):

| # | Slack | Start register (block) | End register (block) | Endpoints | This round |
|---:|---:|---|---|---:|---|
| 1 | -1.36 | `commit_slot` (rx_credit) | `head_units` (rx_credit) | 5 | next head without a slot-indexed commit lookup |
| 2 | -1.35 | `replay_read_onehot` (replay_tx) | `transmit_slice` data (replay_tx) | 8 | not cut |
| 3 | -1.35 | `send_last` (replay_tx) | `reserve_class_q` (replay_tx) | 2 | not cut |
| 4 | -1.35 | `read_onehot` (rx_credit) | `read_bank.registered` (rx_credit) | 10 | reload terms removed; cursor not replicated |
| 5 | -1.34 | `up_credits` (flow_packets) | `dl` (credit_tx) | 24 | own link copy; grant without link term |
| 6 | -1.34 | `reserve_payload_dw_q` (replay_tx) | `verdict` (credit_tx) | 1 | not cut |
| 7 | -1.34 | `owner` (reliable_packets) | the slice register driving `link_sop` (reliable_packets) | 1 | not cut |
| 8 | -1.33 | `up_credits` (flow_packets) | `hl` (credit_tx) | 13 | as 5 |
| 9 | -1.33 | port `pcie_rx_valid_i` | `receive_input_slice` (buffered) | 1 | not cut (input port) |
| 10 | -1.32 | `header` (tlp_stream) | `pstrb` (tlp_regs) | 4 | not cut |

At 68% the worst pairs were close:
- the next queue head (`qread` to `head_units`, -1.17);
- the receive-queue read (`read_onehot` to `bank_byte`, -1.17);
- the lcrc_rx quarantine index to the endpoint's header words (-1.17);
- the replay read position to the reservation registers (-1.16);
- the staging write (`input_count` to `staging`, -1.16).

Behind those came the packet path's link copy into the DLLP receiver's registers (ten endpoints near -1.10) and the receive queue's reset copy into its storage write enables (146 endpoints near -1.13).

Two findings shape what can be gained:
- **The distribution after the uncapped repair is a wall.** The 300 reported endpoints lie within 0.19 ns (70%) and 0.10 ns (68%) of the worst. Cutting a few paths moves the worst slack only as far as the next ones, so this round cut every structural cause in the list that has an exact fix.
- **The reset copies were the biggest single cause.** Before the uncapped repair (and across 146 or more endpoints after it), the per-block reset copies used as the blocks' link status (`up_rx`, `up_fc`, `up_credits`, `up_packets`, `up_link`) drove asynchronous reset pins and logic from one net. Their buffer trees, up to six `buf_16` deep, ran through the link term of a grant into hundreds of next-state selects. The "fanout-8 reset flop" of the sixth round was not one of these, though: it was the receive queue's read cursor (`read_onehot`) into the per-bank AND-OR select.

### Changes (`76c259aca` for the `ad` split and the tracing, `fc4cec6f4` for the cuts)

- **`soc_pcie_credit_tx`: `ad` consume split.** `ad-required` is finished from a low half (`ad[5:0]+(-required)[5:0]` with its carry) registered in the cycle before. For that low half to see the same `ad`, a grant is now refused in the cycle after an FC event's application (`applied`, set by every event that reaches the update stage). A consume is already never in the cycle after a consume, and apart from reset and link loss (which clear the verdict) only those two change `ad`. Random co-simulation against the sixth-round module, whose reserve input is gated by the new ready:
  - four seeds × 500,000 cycles, 0 mismatches;
  - the new ready equals the old one with `!applied` in every cycle;
  - about 57,000 grants per seed, and about 19,200 grants refused by `applied`. The stimulus has an FC event in one of four cycles; real UpdateFC DLLPs are far rarer.
- **`soc_pcie_credit_tx`: grant without reset and link in the next state.** The consume that selects every register's next state uses the grant without the `rst_ni`/`link_up_i` terms: under reset or link loss the registers are cleared regardless. `reserve_ready_o` keeps both terms.
- **Separate link copies (`soc_pcie_buffered_flow_packets`, `soc_pcie_flow_packets`, `soc_pcie_reliable_packets`).**
  - The receive queue, the FC advertiser and the credit logic take `link_up_i` from a copy of their own (`up_rx_link`, `up_fc_link`, `up_credits_link`), so their asynchronous reset nets feed no logic.
  - The PHY-side `rx_ready_o` has its own copy (`up_in`).
  - The DLLP receiver has its own reset copy (`up_dllp`) instead of the combinational `local_reset`. Every copy is cleared asynchronously with its block's reset and is equal to the others at all times.
  - The DLLP receiver's copy is released one cycle after `local_reset`, the earliest cycle its first beat can come from the receive slice.
  - The D inputs differ only so synthesis keeps the flops; a local synthesis confirmed every copy is a separate net.
- **`soc_pcie_rx_credit`: storage writes.**
  - A commit copies the staged TLP into its bank from an `always` block outside the reset/link block, enabled by the slot's commit register alone. The only difference is a commit register still set in the first cycle of a link loss: that bank is free afterwards and is rewritten whole before it is read.
  - Staging bytes are written one cycle after acceptance, from a registered one-hot byte select and a registered byte. A staged TLP is committed two cycles after its last byte at the earliest, and its header bytes, which the check reads, are at least twelve bytes earlier.
- **`soc_pcie_rx_credit`: read registers and next head.**
  - A bank's read register is reloaded with byte 0 only at an end of frame, not at reset or link loss, after which every bank is reloaded by its next commit.
  - The next head is formed without a slot-indexed commit lookup. Without a removal the head stays (its registers) unless an empty queue takes the staged TLP. With a removal it is the staged TLP if one TLP was queued (a commit never meets a full queue), and else the next queued slot, which is occupied and so not the one being committed.
  - Random co-simulation against the sixth-round module, comparing every output in every cycle and data while valid, with link loss every 32 to 8192 cycles and random resets: four seeds × 300,000 cycles, 52,000-163,000 output beats, 0 mismatches.
- **`soc_pcie_fc_tx`.** Each class's limits are compared with its sent values directly, and the class index selects a finished comparison. While idle, the frame's credit fields and CRC seed are loaded every cycle: they are read only while a frame is active, and a frame starts with its start cycle's values as before. Co-simulation against the sixth-round module, comparing every output in every cycle including `tx_data_o`: four seeds × 400,000 cycles, about 38,000 frames each, 0 mismatches.
- **`soc_pcie_buffered_flow_packets`: registered function identity.** The static `function_id_i` strap is registered at the boundary. It was the worst capped path at 68%: the input port, four hold buffers, then the configuration target check into `completion_data` (-3.68). A change now takes effect one cycle later. Every test drives it as a constant.

### `test_soc_pcie_credit_tx.py` changes in this round

| Where | Sixth-round expectation | Seventh-round expectation | Why it is protocol-safe |
|---|---|---|---|
| `Driver.tick`, ready | Granted if presented unchanged for two cycles, affordable and initialized in the previous one, and no consume in it | The same, and no FC event applied in the previous cycle (`applied`, cleared by reset and link loss) | A grant is only delayed by one cycle; credit checks are unchanged |
| `modulo_counters_random_credit_return_and_stalls` | 36,000 cycles | 4 × 36,000 cycles, because with an FC event in three of four cycles the refusal removes three of four grant windows | The same number of grants as before: header consumption 3,790 per class against 3,789 with the old module and old length. The wrap assertion is unchanged |

All original assertions remain.

### Added latency in this round

- A grant is refused in the cycle after an FC event's application.
- The DLLP receiver leaves reset one cycle after its block. No beat can reach it earlier.
- A change of `function_id_i` takes effect one cycle later.

Nothing else moved at any port.

### Verification of the final head (`fc4cec6f4`)

- unit tests 64/64 (run 42582592672), `credit_tx` 5/5 under the revised oracle. The changed blocks' own tests, including `dllp_rx`, also pass locally;
- `check_soc_lint.py` base and full PASS with no new or stale warnings, and joint SoC PCIe + Ethernet traffic PASS 2/2 asynchronous and 2/2 synchronous (run 42584110146). The SoC job of run 42582592672 failed before any check: the OSS CAD Suite download returned HTTP 504 three times.

Block screen (run 42582592672), worst slack / TNS in ns:

| Stage | Corner | Sixth round | Seventh round |
|---|---|---:|---:|
| sized | slow | -1.89 / -2753 | -1.34 / -2605 |
| sized | typical | +0.17 / 0 | +0.55 / 0 |
| repaired | slow | -1.29 / -1782 | -0.71 / -866 |
| repaired | typical | +0.59 / 0 | +0.95 / 0 |

### Physical probe (run 42582592672, same settings as the sixth round)

Worst slack in ns, as in the sixth round ("capped" after the capped post-GRT repair, "deep" after the uncapped repair).

| Head | Density | Capped pcie_clk_i slow / typ | Deep pcie_clk_i slow / typ | Deep asynchronous slow / typ |
|---|---:|---:|---:|---:|
| sixth round `b9dd20e38` (run 42556633463) | 70% | -3.01 / -0.65 | -1.47 / +0.24 | -0.78 / +0.70 |
| sixth round `b9dd20e38` (run 42556633463) | 68% | -2.98 / -0.73 | -1.30 / +0.25 | -0.01 / +1.17 |
| traced `76c259aca` (run 42569863473) | 70% | -4.32 / -1.35 | -1.36 / +0.16 | -1.08 / +0.60 |
| traced `76c259aca` (run 42569863473) | 68% | -3.68 / -1.11 | -1.17 / +0.23 | -1.12 / +0.47 |
| seventh round `fc4cec6f4` | 70% | -3.05 / -0.46 | -1.03 / +0.36 | -0.90 / +0.77 |
| seventh round `fc4cec6f4` | 68% | -3.36 / -0.68 | -1.40 / +0.23 | -1.06 / +0.54 |

- **Deep slow slack.** The final head is the best of all heads at 70% (-1.03) but worse than the traced head at 68% (-1.40 against -1.17). Its worst-of-two (-1.40) and mean (-1.21) are slightly better than the sixth round's (-1.47, -1.39). These differences are within the placement sensitivity measured in the sixth round. Typical slack is positive at both densities.
- **The reset-copy paths are gone from the top of the list.** At 70% the final head's worst pairs are:
  - the input port `pcie_rx_valid_i` into the receive input slice (-1.03);
  - the FC advertiser's byte `index` into its registers (-1.02);
  - the `tlp_stream` header into the `tlp_regs` completion fields (32 endpoints, -1.01);
  - the replay store's write address into its bytes, and its read select into the transmit slice (-1.00).

  At 68% they are:
  - `link_sop` into the replay store's `lengths` and `next_store_sequence` (26 endpoints, -1.40);
  - the receive-queue read select (-1.39);
  - the quarantine index into the endpoint header words (-1.39).

  The wall is unchanged: 300 endpoints within 0.13 ns (70%) and 0.17 ns (68%) of the worst.
- **Capped state.** It improved at both densities against the traced head, by 1.27 ns at 70% and 0.32 ns at 68%.
- **Asynchronous group.** It stays placement-dependent (-1.12 to -0.01 across the six heads and densities) and still needs the constraint described in the fifth round.

## Eighth round: one more register stage across the remaining deep blocks

### Changes (`f6179a44a`, `ce66157da`, final `d32d3a1f1`)

- **`soc_pcie_replay_tx`, store read.** Each bank's byte at the read position is a register, so the transmit slice now takes a bank select of four registers.
  - While no frame is sent, every bank register is loaded with its byte 0.
  - When a byte is taken mid-frame, it is loaded with the next byte, selected as an AND-OR by the rotated one-hot cursor.
  - A slot is committed before its send starts, and only the free tail slot is written while a frame is sent.
- **`soc_pcie_replay_tx`, capture.** The frame-end checks now start at registers:
  - the upper 24 bits of the LCRC residue comparison are tracked with the CRC state;
  - the stored sequence bytes are compared with the expected sequence a cycle ahead (both are fixed for the last sixteen or more bytes of any frame that passes the length check);
  - the reservation metadata selects between the decodes of both candidate slots.
- **`soc_pcie_lcrc_rx` (quarantine).**
  - The byte store is written through a registered one-hot port one cycle after acceptance. A stored data byte is read no earlier than the cycle after the EOP, which follows it by four LCRC bytes.
  - The output byte is a register: byte 0 while idle, then the next byte through a one-hot cursor. The binary index no longer drives a 32:1 multiplexer into the endpoint.
- **`soc_pcie_lcrc_tx`.**
  - Words are written through a registered port. The first word is read at the PREFIX1 byte, two cycles after the EOP at the earliest.
  - The next sequence number plus one is kept in a register.
- **`soc_pcie_rx_credit`.**
  - The released data limit has both high halves registered a cycle ahead.
  - A copy of the read cursor per bank (CAP bits each) was tried in `f6179a44a`/`ce66157da` and measured. At 68% the read select was no longer the worst path. At 70% the copies were placed far from their banks: 0.41 pF on a cursor bit, -7.58 ns capped and -2.64 ns after the uncapped repair on that path. The final head returns to one cursor.
- **`soc_pcie_tlp_stream` / `soc_pcie_tlp_regs`.** `soc_pcie_tlp_regs` has a new parameter `PREDECODE`, default 0, under which its standalone APB cycle-exact test runs unchanged.
  - With `PREDECODE=1`, every decision and field of the descriptor decode is taken from a register loaded in the previous cycle. This covers the shape and target checks, the configuration read data and BAR write value, the completion fields, and the APB address, strobes and data.
  - `soc_pcie_tlp_stream` sets `PREDECODE=1` and presents a collected descriptor from its second SUBMIT cycle on (`armed`), so the descriptor is stable for a cycle before it is presented.
  - `bar0` and `memory_enable` change only while a descriptor is processed, and the next one is processed two cycles later at the earliest.
- **`soc_pcie_buffered_flow_packets`, receive port.** A boundary register sits in front of the receive input slice. An accepted beat is held there until the slice takes it; the port is ready when the register is empty or the slice has room. Ready still comes from flops, and beats still flow one per cycle.
- **`soc_pcie_credit_tx`.** The update stage takes the event's class infinite flags and zero tests from stage B registers. Only an InitFC applied in stage C writes those flags, so the registered flag takes that write when the two events have the same class.

No test was changed.

### Equivalence

Each changed block was compared by random co-simulation against its seventh-round version, with resets, link loss and backpressure. Every output was compared in every cycle, and data while valid. 0 mismatches:

- `lcrc_tx` with `lcrc_rx`: the transmitter's output feeds both receivers, with corrupted bytes and errors. 4 seeds × 300,000 cycles, about 2,800 good packets each.
- `replay_tx`: fed with real encoded frames by an `lcrc_tx`, with random ACK/NAK, reservation, transmit stalls, training and retraining. 4 seeds × 400,000 cycles, about 8,100 transmitted frames each.
- `rx_credit` (with and without the per-bank cursor): 4 seeds × 300,000 cycles, link loss every 32 to 8,192 cycles.
- `credit_tx`: 4 seeds × 500,000 cycles, about 57,000 grants each.
- `tlp_regs` with `PREDECODE=0`: its own cycle-exact unit test. With `PREDECODE=1`: the `tlp_stream`, `tlp_integrity`, `packet_endpoint` and `link_packets` tests.
- The receive boundary register is covered by the buffered and SoC tests.

### Added latency in this round

| Path | Added | Bound it must stay inside |
|---|---|---|
| PHY receive beat to the receive queue (boundary register) | +1 cycle | Received ACK/NAK and UpdateFC DLLPs reach the replay store and credit logic one cycle later. The replay timer is 1,024 cycles. The ACK for a received TLP is sent one cycle later. |
| Collected TLP to the register backend (APB setup, completion) | +1 cycle | The APB timeout (256 cycles) counts from SETUP and is unchanged. The completion leaves one cycle later. |
| Replay store read and frame-end checks, LCRC receiver and transmitter stores, released limit, credit update, reservation metadata | 0 | |

### Verification of the final head (`d32d3a1f1`)

- unit tests 64/64 (run 42690727661; also 64/64 on `ce66157da`, run 42659849705, and on `f6179a44a`, run 42653400180);
- `check_soc_lint.py` base and full PASS with no new or stale warnings, and joint SoC PCIe + Ethernet traffic PASS 2/2 asynchronous and 2/2 synchronous (run 42690727661, and on both earlier heads).

Block screen, slow corner, worst slack / TNS in ns; the last column counts paths over 12 logic cells among the 1,500 worst-endpoint paths:

| Head | Sized | Repaired | Paths over 12 logic cells (sized / repaired) |
|---|---:|---:|---:|
| seventh round `fc4cec6f4` | -1.34 / -2605 | -0.71 / -866 | 52 / 73 |
| `f6179a44a` | -1.79 / -1642 | -0.26 / -20 | 2 / 7 |
| `ce66157da` | -1.56 / -2072 | -0.88 / -71 | 7 / 35 |
| final `d32d3a1f1` | -2.51 / -2562 | -0.97 / -1055 | 17 / 17 |

The ten-logic-cell target is not met everywhere. The deepest paths left in the block screen are 11 to 13 logic cells:
- the credit update's stage C into `ad`/`ah`/`dl`;
- the ACK distance compare into `ack_was_stale`/`ack_was_allowed`;
- the replay transmit slice's ready into its spare register;
- the DLLP link slice into the boundary slice;
- the released-limit precompute (the depth moved into its register).

The block screen's own placement spread (about ±0.5 ns, more in TNS) is larger than the differences between these heads. The count of paths over 12 logic cells is the steadier measure, and it fell from 52 to between 2 and 17 at the sized stage.

### Physical probe

Worst slack in ns, same settings as the sixth and seventh rounds. The probe of `f6179a44a` was cancelled to free runners for `ce66157da`.

| Head | Density | Capped pcie_clk_i slow / typ | Deep pcie_clk_i slow / typ | Deep asynchronous slow / typ |
|---|---:|---:|---:|---:|
| seventh round `fc4cec6f4` (run 42582592672) | 70% | -3.05 / -0.46 | -1.03 / +0.36 | -0.90 / +0.77 |
| seventh round `fc4cec6f4` (run 42582592672) | 68% | -3.36 / -0.68 | -1.40 / +0.23 | -1.06 / +0.54 |
| per-bank cursor `ce66157da` (run 42659849705) | 70% | -7.58 / -3.66 | -2.64 / -0.42 | -1.91 / +0.02 |
| per-bank cursor `ce66157da` (run 42659849705) | 68% | -3.00 / -0.51 | -1.16 / +0.47 | -0.70 / +0.96 |
| final `d32d3a1f1` (run 42690727661) | 70% | -3.20 / -0.58 | -1.33 / +0.14 | -1.09 / +0.61 |
| final `d32d3a1f1` (run 42690727661) | 68% | -3.10 / -0.58 | -1.52 / +0.01 | -1.09 / +0.63 |

- **The extra stage did not move the probe's worst slack.** The final head is 0.30 ns (70%) and 0.12 ns (68%) behind the seventh round, inside the placement sensitivity, and typical slack stays positive.
  - The capped state improved at 68% (-3.10 against -3.36) and is a little worse at 70% (-3.20 against -3.05).
  - The 300 reported endpoints still lie within 0.29 ns (70%) and 0.38 ns (68%) of the worst.
- **New worst paths.** The final head's worst paths are new kinds:
  - the combinational `pcie_initialized_o` output from the credit logic (-1.33 at 70%, -1.52 at 68%; an output-delay budget);
  - the LCRC transmitter's word fold into its CRC;
  - the LCRC receiver's received count;
  - the registered replay and receive-queue bank reads (their AND-OR into the register);
  - the replay capture from `link_data`.
- **Per-bank cursor.** It measured better at 68% (-1.16) but placed badly at 70% (-2.64), so it was not kept.

## What remains

- **The wall after the uncapped repair.** Two rounds of cuts (the seventh's structural ones and the eighth's extra register stage) left the probe's worst slow-corner slack between -1.0 and -1.5 ns, with the 300 worst endpoints within 0.3-0.4 ns of each other. Their paths are now mostly four to eight logic cells; the remaining delay is clock-to-Q, setup with slow input slews, skew, and wire load from placement spread. Further RTL cuts move the worst slack less than the placement sensitivity, so the next gains should come from the physical side. Options, none of which change the RTL:
  - timing-driven global placement (`PL_TIMING_DRIVEN` is 0 in this flow);
  - a placement region for the PCIe packet block;
  - more repair effort.
- **Remaining logic-depth outliers** (11-13 logic cells in the block screen):
  - the credit update's stage C;
  - the ACK distance compare;
  - the replay transmit slice's ready;
  - the LCRC transmitter's state into its word index;
  - the combinational `pcie_initialized_o` output.
- **Asynchronous group.** It needs the constraint described in the fifth round, not RTL.
- **Comparisons.** Compare heads at two densities: differences below about 0.9 ns at the slow corner are within the placement sensitivity measured in the sixth round.
