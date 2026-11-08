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

## Verification (no test expectations changed)

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

## Measured timing (screen above; baseline run 42463873679, final run 42464911092)

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

- the deepest worst-endpoint path drops from 21 to 17 logic cells, and from 30 to 27 cells;
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

## What remains

- **The credit loop is now the deepest cone**, at about 17 logic cells at sized and 20-22 at repaired. Two chains run through `soc_pcie_credit_tx`:
  - the reservation verdict, then the consume, then the same-cycle UpdateFC debit selection, into `dl`, `hl`, `ah`, `ad` and `confirmed`;
  - the UpdateFC check with two chained 12-bit subtractions (`fc - consumed - required`).

  Both are cycle-exact at the module ports, and `test_soc_pcie_credit_tx.py` checks them per cycle, including `same_cycle_update_debit_exhausts_exactly_once`. Splitting them needs a visible change: register the verdict and process UpdateFC one cycle later. That is conservative for flow control, but it needs a reviewed change of that test's oracle, and it was not made here.
- **Other blocks at 11-16 logic cells:**
  - the LCRC framer's next-byte select;
  - the receive-queue read multiplexer, where a one-hot read index or a prefetched byte would help;
  - the `soc_pcie_tlp_regs` request decode;
  - the replay send setup from the reservation handshake.
- **The physical result is still pending.** The implementation-probe pattern (density 70%, Kogge-Stone, upstream register file) was dispatched on this branch twice, in runs 42463784926 and 42465173872. Both failed on GitHub release download errors (HTTP 504, and a corrupted `sv2v` archive) before synthesis or flow, so no number comes from them. The comparison points are -8.74 ns slow and -4.11 ns typical before the extra repair (run 42257277688), and -5.76 ns and -2.31 ns after the uncapped repair (run 42436769600).
- **Reachability at 4 ns.** In this screen, typical is within about 1 ns after repair. The slow corner is still 3.7-4.6 ns short. At about 0.2 ns per cell at 1.08 V/125 C, a 4 ns stage holds about 14 cells including clock-to-Q, setup, uncertainty and buffering. Every block above is past that. The byte-wide packet path therefore needs about one more register stage per block at the slow corner, or a wider datapath at a lower `pcie_clk_i`. This change alone does not close 4 ns at the frozen slow corner.
