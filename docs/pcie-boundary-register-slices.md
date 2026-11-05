# PCIe boundary register slices

## Why

Fresh RC and three-corner STA on the current main-chip route (run42047826928, `docs/mainchip-sta-measurement.md` on `analysis/mainchip-sta`) put the typical- and fast-corner worst paths on the 4 ns `pcie_clk_i`:

- **Register to output port.** These paths end at `pcie_tx_data_o` (-5.39 ns typical, -2.62 ns fast) and at `pcie_tx_sop_o`, `pcie_tx_eop_o`, `pcie_tx_valid_o` and `pcie_tx_replay_o`. The arbitrated transmit stream of `soc_pcie_buffered_flow_packets` reached the ports through combinational muxes.
- **Register to register.** There are 988 violating paths, the worst at -3.35 ns typical with 43 logic levels. They start at the replay store `u_pcie.flow.packets.retry.bytes[...]` and run through the one-hot AND-OR read into link-layer registers.
- **Link status input.** At the fast corner, `pcie_link_up_i` fanned out combinationally into 639 packet-domain registers and the transmit ports (-0.68 ns, -1.34 ns).

The sizing-feasibility probe (run42051193750) showed that cell sizing cannot close the port paths. After unbounded `repair_timing`, `pcie_tx_data_o[0]` still arrived 4.27 ns late through about 35 logic levels.

## Change (branch `timing/pcie-boundary-skid`)

- `soc_pcie_stream_skid` is defined in `soc_pcie_replay_tx.v`, which every PCIe source list already compiles. It is a two-entry valid/ready register slice. The outputs and the upstream ready come from flops, an offered beat is never retracted, and beats leave in order.
- `soc_pcie_replay_tx` sends its transmit stream through one slice. The replay timer still starts on the wire-side end of frame: the first-replayed-frame mark travels with the bytes, and the timer starts from the output handshake. A first version started the timer on the core handshake, one cycle early, and failed `expiry_preempts_new_credit_and_frame_but_not_an_inflight_packet`. That unit test checks the timer start to the cycle.
- `soc_pcie_buffered_flow_packets` sends the arbitrated stream through a second slice before the ports. The arbiter's lock and round-robin state follow the slice's input handshake.
- `soc_top` registers `pcie_link_up_i`, `pcie_training_i` and `pcie_retrain_done_i` once each in the packet clock domain, together, so their relative timing is unchanged.

The transmit stream gains two cycles of latency. The stream protocol is unchanged.

## Verification (no thresholds or tests changed)

| Check | Baseline (`codex/complete-open-work`) | Change | Run |
|---|---|---|---|
| `soc_pcie_replay_tx` unit tests | 7/7 | 7/7 | 42060057879 |
| `soc_pcie_flow_packets` | 3/3 | 3/3 | 42060057879 |
| `soc_pcie_buffered_flow_packets` | 5/5 | 5/5 | 42060057879 |
| `soc_pcie_reliable_packets` | 4/4 | 4/4 | 42060057879 |
| Joint SoC PCIe + Ethernet traffic, asynchronous packet clock | PASS 2/2 | PASS 2/2 | 42060520447 |
| Joint SoC PCIe + Ethernet traffic, synchronous packet clock | PASS 2/2 | PASS 2/2 | 42060520447 |
| `check_soc_lint.py` base profile | PASS, no new or stale warnings | PASS, no new or stale warnings | 42061430658 |
| `check_soc_lint.py` full profile | PASS, no new or stale warnings | PASS, no new or stale warnings | 42061430658 |

The timing effect needs a new synthesis and physical implementation; it is not measured here. Closing `clk_i` also needs placement work, because the Ibex datapath nets are placement-limited (see the STA measurement document).
