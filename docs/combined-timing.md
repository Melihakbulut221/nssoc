# Combined core and PCIe timing: the Ethernet FIFO read and the BUSSTAT counters

Branch `timing/combined` (`docs/ibex-ex-stage.md` section 8, `docs/pcie-pipeline.md`). The constraints are frozen and unchanged here: `clk_i` 20 ns, `eth_rx_clk_i`/`eth_tx_clk_i` 8 ns, `pcie_clk_i` 4 ns, corner `nom_slow_1p08V_125C` with 5% derate, the physical SDC and every acceptance threshold.

## 1. Starting point

Run 42719414702, probe `c_ex_exec_pmpreg_d68`: the execute stage, `CHKDEFER`, predecode, `SOC_MEM_RDREG=2`, `IBEX_PMP_REQ_REG`, the pipelined PCIe RTL, density 68%, Kogge-Stone, and `repair_timing` bounded at 1100 iterations after global route, with net names (`path_nets`). Worst setup slack in ns after that repair:

| Corner | `clk_i` | `pcie_clk_i` | `eth_rx_clk_i` | `eth_tx_clk_i` | asynchronous | path delay |
|---|---:|---:|---:|---:|---:|---:|
| slow | -1.72 | -2.30 | -1.62 | -1.64 | -0.66 | -0.96 |
| typical | +6.25 | -0.48 | +1.93 | +1.94 | +0.98 | +2.24 |
| fast | +9.84 | +0.56 | +3.89 | +3.95 | +1.96 | +2.60 |

The `path delay` group (set_max_delay) is the boot block's protection voter (`u_boot.g_prot_tmr`) into reset pins; it is not addressed here. The probe `c_ex_exec_pmpreg_d70` of the same run (section 7) is worse on every group but `pcie_clk_i`, and its worst `clk_i` class is a different one.

`scripts/name_slow_paths.py` (new) names the ten worst slow-corner paths of each group after the repair by RTL register, from the `NSSOC_NETS` section of `deep-repair.log` and the flip-flop map `flop-map.tsv.gz` (`scripts/pcie_timing/trace_paths.py`). The probe job now runs it and uploads the map with the artifact.

## 2. The Ethernet FIFO SRAM read

### 2.1 The paths

All ten worst `eth_tx_clk_i` paths and eight of the ten worst `eth_rx_clk_i` paths start at a FIFO SRAM macro, `u_eth.u_mac.{rx,tx}_fifo.fifo_inst.u_sram.g_bank[k].u_mem`, and end at a flip-flop one bank multiplexer later:

| Group | Slack | End register | Port |
|---|---:|---|---|
| `eth_tx_clk_i` | -1.64, -1.61, -1.60 | `u_b_cross.compare_data`, `u_b.response_q`, `fifo_inst.m_axis_pipe_reg[1]` | B (read clock `tx_clk`): self-test and the FIFO's output stage |
| `eth_rx_clk_i` | -1.62, -1.61, -1.15 | `u_a_cross.compare_data`, `u_a.response_q` | A (write clock `rx_clk`): read only by the self-test |
| `eth_rx_clk_i` | -0.88, -0.87 | macro `A_REN`/`A_WEN` from `wr_ptr_reg` | the write request, section 2.5 |

The read path (tx, -1.60): clock 1.16 ns, macro `B_CLK` to `B_DOUT` 5.40 ns, then `buf_4`, `a22oi_1` 1.93 ns, `and4_1` 1.11 ns, `o21ai_1` 0.20 ns, arrival 10.05 ns against 8.45 ns required. The 8:1 bank multiplexer gathers outputs of eight macros placed apart, so its first gate drives a long wire.

### 2.2 The macro's clock-to-output

`RM_IHPSG13_2P_256x16_c2_bm_bist`, IHP-Open-PDK `c4b8b4e`, `B_CLK`/`A_CLK` rising to `B_DOUT`/`A_DOUT` (input transition 0.008-0.595 ns, load 0.8-64 fF):

| Liberty | rise | fall |
|---|---|---|
| `slow_1p08V_125C` | 5.07-5.39 ns | 4.96-5.25 ns |
| `typ_1p20V_25C` | 2.98-3.18 ns | 2.92-3.10 ns |

At the slow corner the macro alone uses 62-67% of the 8 ns period (5.40 ns in the report with the derate). With the launch clock latency (1.2-1.6 ns) and the capture side (uncertainty 0.25 ns, setup 0.2 ns, capture latency 0.9-1.2 ns), about 1.7-2.0 ns are left after the macro, and the bank multiplexer alone took 3.2-3.4 ns.

### 2.3 Design (`SOC_ETH_FIFO_RDREG=1`, default 0)

- **Wrapper** (`hw/soc/rtl/dft/soc_eth_fifo_sram.v`). Each bank's output is registered next to its macro (`g_rdreg`: 16 bits per bank and port), the bank select is delayed with it, and the 8:1 multiplexer follows the registers. A macro output now drives one flip-flop. Port A is read only by the self-test, so its registers load in every cycle. Port B's registers are the FIFO's pipeline stage one: they load with a new input, `rnext_i`, the FIFO's stage-one enable, while the FIFO owns the port, and in every cycle while the self-test owns it. The macro holds its output between reads, so a register that loads in a cycle without a read reloads the same word.
- **Self-test.** `soc_sram_mbist` already has `READ_LATENCY`; both engines use 2. `soc_sram_zero_check` gains `READ_LATENCY` (1 or 2, compiled only with the knob): at 2 a wait state follows the request. Request sequences, addresses, counts (122,880 March and 2,048 cross-port reads per port) and the failure reports are unchanged.
- **FIFO** (`hw/soc/flow/adapt_eth_mbist.py`, `hw/soc/rtl/soc_eth.v`). The MAC instantiates its FIFOs with `TX_FIFO_RAM_PIPELINE = RX_FIFO_RAM_PIPELINE = 2` instead of 1. That is upstream's own prefetch pipeline (`axis_async_fifo`): stage zero is the RAM read, each stage moves on when the output is taken or a later stage is empty, and it sustains one word per cycle. In the SRAM adaptation stage zero is the macro and stage one is the wrapper's register; `rnext_i = m_axis_tready_pipe || |(~m_axis_tvalid_pipe_reg[RAM_PIPELINE:1])`, which is exactly the condition under which the pinned loop loads stage one. Without the self-test wrapper (inferred memory, or the techmapped macros of the legacy profile) the knob is the same two-stage upstream FIFO.
- **Behaviour.** Frame contents, order, the frame commit, drops and the events are unchanged. The FIFO's read side shows a word one read-clock cycle later after the FIFO was empty; nothing else moves, because the second stage is filled ahead. On the TX side the MAC reads at 125 MHz and a gap inside a frame would be a `tx_error_underflow` event and a broken frame on the wire; on the RX side the reader is the 50 MHz APB.
- **Self-test time.** Every March and cross-port read waits one more clock: per port 307,200 March and 8,192 cross-read clocks instead of 245,760 and 6,144, so the power-on Ethernet self-test at 50 and 125 MHz takes 8.83 ms instead of 7.05 ms before the MAC is released. The joint PCIe/Ethernet bench bounds that release; its bound is 9.0 ms with the knob and stays 7.2 ms without (`test_soc_pcie_ethernet.py`). Its first run with the vendor SRAM models and the knob (run 42764629921) failed both tests: 8.83 ms of self-test cannot finish inside the old 7.2 ms bound, while the same bench passed with the knob on inferred memory and with the vendor models without the knob.
- **Cost.** 512 data flip-flops (2 FIFOs x 2 ports x 8 banks x 16 bits) and 12 select flip-flops, about 25,000 um^2 or 1.5% of `soc_top`. Only the A port of the receive FIFO and the B port of the transmit FIFO are on 8 ns paths; the other two ports are in the 20 ns `clk_i` domain and are registered for symmetry, so a cheaper variant could leave out 256 of them.

### 2.4 Expected effect

With the multiplexer behind the register, the macro-launched path is macro, a short wire and setup: about 1.2 + 5.4 + 0.3 = 6.9-7.3 ns against 8.4-8.8 ns, so about +1.1 to +1.5 ns. The registered multiplexer into the FIFO's last stage and the self-test compare starts at a flip-flop (clock-to-output about 0.4 ns) and has the same 3.3 ns of gates and wire, so about +2.5 ns. To be measured by the probes of section 6.

### 2.5 Not cut: the write request

The next `eth_rx_clk_i` paths (-0.88 at d68) end at the macros' `A_REN`/`A_WEN`: `wr_ptr_reg`, the full and drop predicate of the frame FIFO, the write strobe `aw`, and 3.4 ns of buffers to eight macros. Registering the write moves the macro write one cycle behind the write pointer, and the read side can then see a committed pointer before the last word is in the macro: the commit crosses in two read-clock cycles, and the transmit FIFO's read clock (8 ns) is faster than its write clock (20 ns). It needs a delayed commit and its own proof, so it is left for a separate change. The read-side port B request (`rd_ptr_reg` to `B_ADDR`/`B_MEN`) is the transmit-side analogue.

## 3. `clk_i`: the BUSSTAT counters

### 3.1 The ten worst `clk_i` paths after the repair (d68)

| # | Slack | Start register | End register |
|---:|---:|---|---|
| 1 | -1.72 | `u_ibex.u_ibex_core.exs_id_instr_rdata_alu_id[23]` (ID-stage instruction, `raddr_b[3]`) | `u_busstat.cnt[2][14]` (RFDED) |
| 2 | -1.41 | same | `u_busstat.cnt[2][12]` |
| 3 | -1.00 | same | `u_busstat.cnt[2][13]` |
| 4 | -0.75 | same | `u_busstat.cnt[1][14]` (RFRD) |
| 5-10 | -0.68 to -0.65 | `u_ibex.u_ibex_core.cs_registers_i.csr_addr[9]` (EX-stage instruction) | `register_file_i.rf_reg_q[31]` of x14, x19, x6, x23, x18, x15 |

**Paths 1-4.** Since the execute stage, the register file is read in the ID stage, and the read ends at the EX operand register. The read ports' SEC/DED reports (`rf_ecc_err[2:1]`) go on combinationally: read-address fanout (to 11.2 ns), the read AND-OR, the syndrome XOR tree (to 13.9 ns), the double-error and pending-register masks, and into `soc_busstat`, where the event selects between the counter's increment, its saturation and its clear for all 16 bits (to 23.7 ns against 22.0 ns). Three hold buffers (`dlygate4sd3_1`, 0.68 ns each, 2.0 ns together) sit on the last 2 ns of this path; hold repair inserted them for the counter's short paths (its own increment and the APB clear), which share those nets.

**Paths 5-10** are the core's own execute loop: EX-stage CSR address and operands, the ALU, the result and write-data multiplexers, a register-file data flip-flop, 55 cells. They are about 1 ns behind path 1.

**At d70** the ten worst `clk_i` paths are all the NPU's synapse-memory update, `u_npu.u_node0.u_lif.ev_axon_r[1]` to `u_npu.u_node0.u_lif.smem[*]` (-2.11 to -1.67 ns, 24.5 ns arrival, the axon-index fanout, the synapse read multiplexer, SECDED decode, the update and re-encode). That class was already third in `docs/ibex-ex-stage.md` section 6, and at d68 it is not among the ten worst (better than -0.65 ns), so it moves by more than 1.4 ns between the two densities. It is in `hw/rtl/lif_core.v`, frozen pilot RTL with a pinned hash in `hw/soc/lint-policy.json`, so it is not cut here; the BUSSTAT paths are not among the d70 ten.

### 3.2 Design (`SOC_BUSSTAT_EVPEND=1`, default 0)

`hw/soc/rtl/soc_busstat.v`: each source's event is not added in the cycle it arrives. It is loaded into `ev_pend_q`, by a branch on the event (the block's X rule for unreset read addresses in simulation), and added one cycle later. What the bus, the interrupt and the properties see is `cnt = cnt_q + ev_pend_q`, saturating:

- no clear: `cnt_q <= cnt`, `ev_pend_q <= ev`; the next visible count is `sat(cnt + ev)`, the original update;
- clear: `cnt_q <= 0`, `ev_pend_q <= ev`; the next visible count is 1 with an event and 0 without, the original's event-wins-clear rule;
- the sticky bits are updated as before.

So the visible count equals the original counter in every cycle, and the block is cycle-identical at its ports. A late event now ends at one flip-flop; the increment runs from flip-flops in the next cycle, and the APB read multiplexer gets the 16-bit increment in front of it (from flip-flops, in the 20 ns APB cycle). It is compiled only under `SOC_BUSSTAT_EVPEND`, so the default netlist does not move, although a pure retiming like this one could be on by default.

**Proof.** `hw/soc/formal/soc_busstat_props.v` gains B8 under the define: a reference counter with the original update runs beside every source and `cnt` must equal it in every cycle. The statement is inductive by itself, so `prove` closes it for every state. B1-B7 hold unchanged.

### 3.3 Expected effect

Paths 1-4 end at `ev_pend_q`, about 2 ns earlier (the increment and multiplexers, about 1.1 ns, and the hold buffers on the counter inputs), so at d68 the worst `clk_i` path becomes the execute loop of paths 5-10, about -0.7 ns, within the placement noise of the probes (up to 0.9 ns). At d70 the frozen NPU path (-2.1 ns) limits `clk_i` whatever happens to BUSSTAT.

## 4. Physical: timing-driven placement

The flow's global placement is routability-driven already (`global_placement -density 0.68 -routability_driven` in `run.log`; LibreLane's `PL_ROUTABILITY_DRIVEN` defaults to true) and not timing-driven (`PL_TIMING_DRIVEN` false). The probe entries `c_cut_td_d70` and `c_cut_td_d68` add `"PL_TIMING_DRIVEN": true` to the overrides and are otherwise identical to `c_cut_d70`/`c_cut_d68`. The probe step now prints the `global_placement` commands that ran, which shows whether the flag took.

## 5. Tests and workflow

All in `.github/workflows/cloud-evidence-summary.yml`:

| Job (input) | What | Knob off / on |
|---|---|---|
| `eth-knobs`, part `busstat` (`pcie_jobs` contains `eth`) | `test_soc_busstat.py` cocotb; SymbiYosys `bmc`, `prove`, `prove_w16`, `cover`, `prove_to`, `prove_to_w16` (B1-B8) | both |
| part `eth-rtl` | `test_soc_eth.py` (6 tests: full-size TX at line rate with no underflow, RX across clocks, bad FCS, RX overflow, oversize TX and flush, registers): inferred memory, and the SRAM wrapper with the vendor functional models and its power-on self-test | both, four configurations |
| part `eth-mbist` | `scripts/check_eth_mbist.py` (37 cases: complete test with operation counts, missing clock, POR rerun, injected bank faults on both ports and both phases, engine state corruption, cross-port data and output hold) | both (`--fifo-rdreg`) |
| parts `eth-gl-0`, `eth-gl-1` | `hw/soc/flow/test_eth_sram.sh`: the MAC synthesised with the mapped wrapper and 16 macros, `test_soc_eth.py` at gate level with the vendor models | 0 / 1 |
| part `joint` | `scripts/check_pcie_ethernet_soc.py`: actual Ibex, PCIe packet traffic and GMII loopback together, synchronous and asynchronous PCIe clock, inferred and vendor-SRAM FIFOs (`--define`) | both knobs on; the vendor-SRAM case also off |
| `regress`, entry `ex_exec_pmpreg_cut` (`variant`) | `make soc-sim`, `make soc-boot-regression`, the crash cocotb recipe with the best core knobs and both new knobs | on |
| `native-boot`, entry `ex_exec_pmpreg_cut` | gate-level boot, CORRPRE + PCIe, no MBIST | on |
| `probe`, entries `c_cut_d70`, `c_cut_d68`, `c_cut_td_d70`, `c_cut_td_d68` | RTL boot (Ethernet loopback in the firmware), synthesis, placement to global route, 1100-iteration repair, named paths | on |

The knobs are threaded through `syn_soc_top.sh` and `sim_soc.sh` (one global define each, nothing emitted when off; `sim_soc.sh` checks that `ev_pend_q` is elaborated when the BUSSTAT knob is on), `check_soc_corrpre_pcie_native_boot.sh` (recorded in `core-configuration.json`), `test_eth_sram.sh`, `check_eth_mbist.py`, `check_pcie_ethernet_soc.py` and the cocotb makefiles (`EXTRA_COMPILE_ARGS`, `ETH_EXTRA_SOURCES`, `JOINT_DEFINES`). `tb_eth_fifo_mbist.v` waits one more read-clock edge with the knob. The new input `variant` selects regress and native-boot entries, like `probe_variant`, and then skips riscv-formal (the core is unchanged).

**Default build unchanged.** All new logic is under the two defines. The adaptation adds only `ifdef` arms to the generated interface bundles, so `hw/soc/lint-policy.json` gets their new hashes (regenerated with `prepare_interfaces.py` at the pinned commits; the old hashes were reproduced first) and 42 recorded diagnostics moved to their new line numbers with their unchanged source lines.

**Status.** Runs 42760405570 (probes, regress, native boot) and 42764629921/42769681544 (eth-knobs). Passed: unit, regress `ex_exec_pmpreg_cut`, BUSSTAT cocotb and formal off/on, the 37-case wrapper suite off/on, the MAC cocotb suite 6/6 in all four configurations (the job was marked failed by a simulator crash at exit under the OSS CAD Suite cocotb build), joint traffic `knobs-async`, `knobs-sync` and `sram-off-async`. `sram-knobs-async` failed on the self-test release bound of section 2.3, fixed in the bench; the gate-level runs failed to start the cocotb embed under the OSS CAD Suite vvp wrapper, fixed by the launcher of `scripts/cocotb_icarus_runtime.py`. Those two fixes are not run yet. To rerun the Ethernet jobs:

```
gh workflow run cloud-evidence-summary.yml --ref timing/combined \
  -f probe_variant=none -f variant=none -f pcie_jobs=eth
```

## 6. Results

Run 42760405570 (both knobs, otherwise the configuration of section 1), worst setup slack in ns after the 1100-iteration repair, slow corner; the last column is typical `pcie_clk_i`, the only typical group that failed before. The probe log confirms `global_placement ... -timing_driven -routability_driven` for the `td` entries.

| Probe | `clk_i` | `pcie_clk_i` | `eth_rx_clk_i` | `eth_tx_clk_i` | asynchronous | typ `pcie_clk_i` |
|---|---:|---:|---:|---:|---:|---:|
| `c_ex_exec_pmpreg_d70` (before, run 42719414702) | -2.11 | -2.16 | -2.17 | -2.14 | -0.79 | -0.43 |
| `c_ex_exec_pmpreg_d68` (before) | -1.72 | -2.30 | -1.62 | -1.64 | -0.66 | -0.48 |
| `c_cut_d70` | -1.43 | -1.47 | -1.33 | -1.35 | -1.13 | -0.02 |
| `c_cut_d68` | -1.05 | -1.07 | -0.84 | -0.91 | -0.68 | +0.32 |
| `c_cut_td_d70` | **-0.47** | **-0.81** | **+0.84** | **-0.23** | -0.75 | +0.57 |
| `c_cut_td_d68` | -0.93 | -0.92 | **+0.36** | **+0.34** | -0.89 | +0.31 |

- **Ethernet.** No macro output is followed by logic on any reported path any more; the macro-to-register paths have +0.7 to +1.2 ns. Without timing-driven placement the worst paths are the wrapper's ownership multiplexers in front of the macros (`axfail`, `rp[1]`, `sel_a_q` into the macro address and enables, -0.8 to -1.3 ns), the class of section 2.5; with it both Ethernet clocks close at d68, and at d70 only the registered bank multiplexer into `u_b.response_q`/`m_axis_pipe_reg[2]` is left (-0.23).
- **`clk_i`.** BUSSTAT is gone from the reported paths. What is left is placement-dependent: the frozen NPU synapse update (-1.43 / -1.05 without timing-driven placement), the core's EX loop into the register file (-0.93, `td_d68`) and the EX-stage load/store address into the fabric request register `s_addr` (-0.47, `td_d70`).
- **`pcie_clk_i`** (RTL unchanged) improves by about 1.1 ns on the new netlists without timing-driven placement, more than the 0.9 ns placement noise, and by about 1.4 ns with it; typical closes in five of six probes and in every `td` probe.
- **asynchronous** (PCIe link-status into `u_pcie_cdc` resets) stays at -0.7 to -1.1 ns; the max-delay group closes in all four (+0.2 to +1.8).

## 7. The d70 probe of run 42719414702

Same netlist as d68 (same configuration), density 70%. Worst setup slack in ns after the 1100-iteration repair:

| Corner | `clk_i` | `pcie_clk_i` | `eth_rx_clk_i` | `eth_tx_clk_i` | asynchronous | path delay |
|---|---:|---:|---:|---:|---:|---:|
| slow | -2.11 | -2.16 | -2.17 | -2.14 | -0.79 | -1.43 |
| typical | +5.93 | -0.43 | +1.16 | +1.56 | +0.83 | +2.10 |
| fast | +9.41 | +0.57 | +3.12 | +3.64 | +1.68 | +2.85 |

- `clk_i`: the frozen NPU synapse update (section 3.1), not BUSSTAT.
- Ethernet: the same class as d68, about 0.5 ns worse: all ten `eth_rx_clk_i` paths are port A of the receive FIFO into the self-test (`u_a.response_q`, `u_a_cross.compare_data`), all ten `eth_tx_clk_i` paths are port B of the transmit FIFO into `m_axis_pipe_reg[1]` and the self-test. The write request of section 2.5 is not among the ten.
- asynchronous: `pcie_sys_rst_n` into `u_pcie_cdc.source_reset_n`/`source_release` (-0.79), then the packet link status into its slices (-0.26); at d68 the receive slice's reset (-0.66).
- `pcie_clk_i`: the receive quarantine into the transaction stream's completion header (-2.16), the same wall as `docs/pcie-pipeline.md`.

Between the two densities the same netlist moves by 0.4-0.5 ns on the Ethernet and `clk_i` groups and by 0.14 ns on `pcie_clk_i`, and the worst `clk_i` class changes.

## 8. Remaining gap

Before these cuts the slow corner misses by 2.16-2.30 ns (`pcie_clk_i`, 4 ns period, a wall of endpoints within 0.3-0.4 ns, `docs/pcie-pipeline.md`), 1.72-2.11 ns (`clk_i`), 1.6-2.2 ns (both Ethernet clocks), 0.96-1.43 ns (the boot protection voter's max-delay group) and 0.66-0.79 ns (asynchronous, PCIe resets), over d68 and d70. Typical misses only on `pcie_clk_i` (-0.43 to -0.48 ns). If the cuts behave as sections 2.4 and 3.3 expect, what is left is:

1. `pcie_clk_i`, about -2.2 ns; RTL cuts now move it less than the placement noise, and timing-driven placement (section 4) is the measurement that tells whether the physical side helps.
2. `clk_i`: the frozen NPU synapse update (-2.1 ns at d70, better than -0.65 ns at d68) and the core's EX loop (CSR and operands, ALU, result, register-file write; about -0.7 ns at d68). The first needs either a change to the frozen pilot RTL or placement that keeps the synapse memory together.
3. `eth_rx_clk_i`, about -0.9 ns: the FIFO write request (section 2.5), and the transmit FIFO's read request on the other side.
4. The boot protection voter's max-delay paths (-0.96 ns) and the PCIe receive reset (asynchronous, -0.66 ns), outside this change.

## 9. Routed measurement (set up, not run yet)

Global-route parasitics have been 1-2 ns optimistic against extracted RC on this design, so the best configuration gets a routed measurement. The probe entries `r_cut_td_d70` and `r_cut_td_d68` are `c_cut_td_*` (both knobs, timing-driven placement, the 1100-iteration post-global-route repair) and write the repaired database. Two further hosted jobs continue from it, each within the 6 h limit:

- `route`: the interface flow's own steps, `hw/soc/pnr/routed_measure_flow.py` (`RoutedMeasureRoute`): detailed placement (legalizes the repair's buffers), global routing with the flow's settings, detailed routing with orphan-guide cleanup bounded by `DRT_OPT_ITERS` (input `drt_iters`, default 15), removal of the routing obstructions. DRC markers left by the bounded routing are reported (`route__drc_errors` and the per-iteration violation counts), not waived.
- `routed-sta`: `ReplayOnehotRoutedExtraction` of `hw/soc/pnr/replay_onehot_routed_extraction_flow.py`, the recipe of `analysis/mainchip-sta` (`scripts/mainchip_sta_measure.py`): `AuditedRCX` (nominal OpenRCX with the pinned rules, SPEF audit) and `AuditedRoutedSTA` (standalone OpenSTA, derate guard, original clocks 20/4/8/8 ns, every clock propagated) in the three corners. `scripts/routed_sta_summary.py` prints the gate metrics per corner, the worst setup and hold slack per path group and corner, and each group's worst slow-corner path by RTL register.

`scripts/routed_handoff.py` carries the LibreLane state and every file it names between the jobs. Dispatch:

```
gh workflow run cloud-evidence-summary.yml --ref timing/combined \
  -f probe_variant='r_cut_td_d70 r_cut_td_d68' -f variant=none \
  -f repair_iterations=1100 -f path_nets=true -f drt_iters=15
```

## 10. Routed result and the next cuts

Run 42873725806 (`r_cut_td_d68` and `r_cut_td_d70`; detailed routing at `DRT_OPT_ITERS=12` without the in-route antenna repair, then AuditedRCX and AuditedRoutedSTA). Worst slack in ns, setup slow / typ / fast | hold slow / typ / fast:

| Group | d68 | d70 |
|---|---|---|
| `clk_i` | -1.63 / 6.67 / 10.21 \| 0.19 / 0.12 / 0.03 | -2.74 / 5.90 / 9.42 \| 0.24 / 0.11 / -0.04 |
| `pcie_clk_i` | -1.03 / 0.71 / 1.35 \| 0.34 / 0.13 / 0.01 | -1.30 / 0.38 / 1.16 \| 0.27 / 0.07 / -0.06 |
| `eth_rx_clk_i` | -0.15 / 2.35 / 3.22 \| 0.57 / 0.25 / 0.06 | 0.48 / 2.89 / 3.58 \| 0.40 / 0.13 / -0.01 |
| `eth_tx_clk_i` | 0.50 / 3.20 / 4.79 \| 0.49 / 0.29 / 0.09 | 0.05 / 2.95 / 4.59 \| 0.54 / 0.23 / 0.07 |
| asynchronous | -0.73 / 0.70 / 1.52 \| 0.43 / 0.17 / 0.02 | -0.55 / 0.96 / 1.72 \| 0.47 / 0.16 / -0.01 |
| path delay | 1.85 / 2.36 / 2.64 \| - | 1.20 / 1.95 / 2.36 \| - |

Detailed routing ends with 0 DRC markers and 0 antenna violations at d68 (98,979 markers after the first iteration, 0 after the eighth). Against the global-route estimate of the same configuration (`c_cut_td_*`, section 6) the routed `clk_i` is 0.7 ns (d68) and 2.3 ns (d70) worse, `pcie_clk_i` 0.1-0.5 ns worse and the Ethernet groups 0.2-0.5 ns worse; the worst `clk_i` class is new (below).

### 10.1 What the routed reports name, and the cuts

- **`clk_i`: the system RAM self-test compare** (147 of the 192 violating d68 endpoints; all of the worst at d70). `soc_sram_test_port` runs `soc_sram_mbist` without `PIPELINE_COMPARE`, so the RAM macro (9.5 ns clock to output at the slow corner), its bank multiplexer, the 64-bit comparison and the enables of every failure-record register (`mbist_fail_*_o`, background, address) fall in one cycle. The record registers are already flip-flops, so registering the ports would not help; `SOC_SRAM_MBIST_PIPE=1` (new, default 0) registers the read word before the comparison (`PIPELINE_COMPARE=1`, the setting the Ethernet wrapper already uses). Requests, addresses and records are unchanged; every read takes one more clock, 327,680 more cycles for the 8192 x 64 March (the accesses stay 655,360).
- **`pcie_clk_i`: the receive queue commit** (`commit_slot[b]` into the 304 byte flip-flops of its bank, 51 of the worst 100 d70 endpoints). `SOC_PCIE_RX_STAGED_COMMIT=1` (new, default 0, `soc_pcie_rx_credit.v`) copies the bank in groups of eight bytes, group g g cycles after the commit, each from its own register (a shift of `commit_slot`), so no enable drives more than 64 flip-flops. Byte w is first read w output handshakes after the commit and its group is written before that; staging bytes are not overwritten before the end of cycle commit+2+w. Cycle-identical at the block's ports.
- **`pcie_rx_valid_i` -> `port_valid` (d70) and `pcie_link_up_i` -> `u_pcie_cdc.destination_release` (asynchronous)**: both already end at the first flip-flop behind the port (`port_valid` is the boundary register; `destination_release` is the reset synchronizer). The setup failures are hold-repair buffers: four to five `dlygate4sd3` cells (3.9-5.0 ns) inserted for the min input delay against a capture clock with about 2.5 ns of insertion latency. No RTL register can be placed in front of them, and the reset synchronizer must keep asserting with its clock stopped, so it cannot take a registered copy. These two need a physical or constraint decision (input-flop clock latency, hold margin on the port paths), outside this branch's rules.
- **`eth_rx_clk_i`: the registered bank select** (`sel_a_q` -> `u_a.response_q`, -0.15 at d68). With `SOC_ETH_FIFO_RDREG` the select of the registered word is now kept one-hot and the output is an AND-OR of the eight bank registers (inside the existing knob; the knob-off netlist does not move).

### 10.2 The next five slow-corner setup paths per failing group (d68), after those cuts

- `clk_i`: `load_store_unit_i.ls_fsm_cs[0]` -> fabric request `s_wdata[20]`, `[22]`, `[9]` (-0.66 to -0.63); EX-stage instruction `exs_ex_instr_rdata_alu_id_q[1]` -> register file `rf_reg_q[30]` of x15, x2 (-0.49, -0.48).
- `pcie_clk_i`: receive read cursor `next_onehot[27]` -> `bank_byte[3]` (-0.85); `flow.packet_rejected_o` -> `receive_ownership.head_last[3]`, `head_units` (-0.76); `quarantine.cursor[26]` -> `endpoint.byte_data[2]` (-0.74); `retry.replay_read_onehot[10]` -> `read_replay_bank[0].registered` (-0.68); `quarantine.index[1]` -> `endpoint.word_index[3]` (-0.66). At d70 also `flow.credits.b_dd` -> `credit_data_limit_o`/`credit_header_limit_o`, `advertiser.link_up_i` -> `sent_data_o`, `retry.write_address` -> `retry.bytes`.
- asynchronous: `receive_input_slice.rst_ni` -> `receive_ownership.next_onehot[*]` (-0.46, 24 endpoints, the cursor's reset tree); `pcie_sys_rst_n` -> `u_pcie_cdc.source_reset_n`/`source_release` (-0.30, the same hold-buffer pattern as `pcie_link_up_i`).
- `eth_rx_clk_i`: nothing else violates.

### 10.3 Tests and runs

`regress` and `native-boot` entries `ex_exec_pmpreg_cut2`, native-boot `ex_mbist_cut2` (system and Ethernet MBIST gate-level boot, execute stage alone, every knob), probes `r_cut2_td_d68`/`r_cut2_td_d70` with `route` and `routed-sta`, the PCIe unit suites of the receive queue with `-DSOC_PCIE_RX_STAGED_COMMIT`, joint PCIe/Ethernet traffic with all knobs (`cut2-*`), and the SoC MBIST integration bench (`scripts/check_soc_mbist_integration.py --define ...`, eth-knobs part `soc-mbist`), knobs off and on. The MBIST gate-level boot was already at 16,273 s of its 18,000 s simulator limit; 327,680 more MBIST cycles may not fit, in which case the RTL integration bench is the MBIST evidence.

## 11. Third routed round

Run 42939627387, `r_cut2_td_d68` (DRC 0), setup slow / typ / fast | hold slow / typ / fast: `clk_i` -0.68 / 6.51 / 9.56 | 0.36 / 0.13 / -0.00; `pcie_clk_i` -2.34 / -0.04 / 1.28 | 0.30 / 0.09 / -0.03; asynchronous -0.42 / 0.88 / 1.56; `eth_rx_clk_i` +0.38; `eth_tx_clk_i` -0.53 / 2.58 / 4.30; path delay +1.52; fast hold -0.027 (3 endpoints). `r_cut2_td_d70` (DRC 4) is worse in every group; d70 is dropped from the routed probes.

What the worst paths consist of:

- **`pcie_clk_i`, `receive_ownership.qwrite[0]` -> `order[3][0]` (-2.34).** Five logic cells (the write-position decode and the order entry's multiplexer) and three hold buffers (`dlygate4sd3_1`, 2.33 ns, one of them at the D pin). The logic of this path is not changed by the staged commit; the hold buffers make it critical. Under `SOC_PCIE_RX_STAGED_COMMIT` the queue write position is now also kept one-hot (`qwrite_oh`), so an order entry's write enable is the commit and one register bit. Probe `r_cut3n_td_d68` measures every other cut without the staged commit.
- **`clk_i`, `u_mbist.phase_q[2]` -> `mbist_fail_actual_o[32]` (-0.68).** The expected word (background from `background_q`, inverted by phase) is generated in the comparison cycle, through under-sized gates with 1.9-4.9 ns slews, then the 64-bit comparison and the record enables. Under `SOC_SRAM_MBIST_PIPE` the expected word is registered in READ (`expected_q`): with `PIPELINE_COMPARE` the comparison is always in COMPARE, whose previous cycle is READ, and `phase_q`/`background_q` never change in READ, so the registered word is the current one. Records and timing of the test are unchanged.
- **`eth_tx_clk_i`, `u_sram.bxdone` -> `g_bank[1].u_mem` (-0.53).** `bxdone` is already a flip-flop; the path to the macro's address and enable pins is five logic cells and eight hold buffers (5.73 ns of the 8.9 ns arrival), inserted for the macro pins' hold requirement. A register in front of the macro would carry the same hold padding, so this is not changed in RTL.
- **asynchronous, `quarantine.rst_ni` -> `quarantine.cursor[15]` (-0.42)**, a reset-copy tree into the quarantine cursor.

The common pattern of the remaining routed failures (the PCIe input ports, `pcie_link_up_i`, `bxdone`, `qwrite`) is hold padding on paths with little logic: the flow's hold repair runs with `PL_RESIZER_HOLD_SLACK_MARGIN` 0.1 ns and `GRT_RESIZER_HOLD_SLACK_MARGIN` 0.05 ns at the fast corner and inserts buffers on segments the setup paths share. Those margins are flow settings, not SDC, but changing them is a sign-off decision and is not done here.

Runs: probes `r_cut3_td_d68` (all knobs) and `r_cut3n_td_d68` (all but the staged commit) with routing and extracted STA; the functional entries of section 10.3 (`ex_exec_pmpreg_cut2`, `ex_mbist_cut2`, the receive-queue suites with the staged commit, joint traffic and the SoC MBIST bench) cover the changed knobs.

## 12. Fourth routed round: post-route hold repair, the receive-queue read and the fabric write data

Runs 42987022661 (route) and 43052000192 (extracted STA), d68, DRC 0. Worst slow-corner setup slack in ns, and hold:

| Probe | `pcie_clk_i` | `clk_i` | asynchronous | Ethernet | hold |
|---|---:|---:|---:|---|---|
| `r_cut3n_td_d68` (all knobs but the staged commit) | -1.87 | -0.63 | -0.44 | met | fast -0.02 (1 endpoint) |
| `r_cut3h_td_d68` (same, `PL_`/`GRT_RESIZER_HOLD_SLACK_MARGIN` 0) | -1.37 | -0.61 | -0.20 | met | slow -0.012 (1), typ -0.003 (1), fast -0.07 (92) |

Typical setup is met in both. The staged receive commit (`r_cut3_td_d68`) is worse and stays off.

### 12.1 Post-route hold repair (flow, measurement only)

Without the extra hold margin, placement and global-route repair pad fewer paths, which is what moved `pcie_clk_i` by 0.5 ns and the asynchronous group by 0.24 ns, but hold is then short by up to 0.07 ns on the extracted wires. LibreLane 3.0.5 has no resizer step after detailed routing, so `hw/soc/pnr/routed_measure_flow.py` gets one, `PostRouteHold` (`hw/soc/pnr/post_route_hold.tcl`), and the flow `RoutedHoldRepair` = `PostRouteHold`, then detailed routing (`CleanOrphanGuides`, the same step and `DRT_OPT_ITERS` as the route job, no in-route antenna repair):

- the routed database with the flow's libraries, SDC (the same derate) and propagated clocks; the four clock periods are checked;
- global routing in memory (the flow's settings), so the resizer can re-estimate the nets it changes and the later incremental route has a starting point;
- OpenRCX of the routed wires with the nominal rules AuditedRCX uses (`RCX_RULESETS`, `-lef_res`), the SPEF read into every STA corner; every net the repair does not touch keeps these parasitics;
- `repair_timing -hold -setup_margin 0 -hold_margin 0.01 -max_buffer_percent 10` in all three corners (`NSSOC_POST_ROUTE_HOLD_MARGIN`, `NSSOC_POST_ROUTE_HOLD_MAX_BUFFER_PCT`). The hold margin is a repair target against the small change rerouting brings, not an acceptance threshold. A buffer may spend positive setup slack only (the resizer's default `-setup_margin 0`; setup violations are not allowed);
- no existing pin moves. Every library cell but the hold buffer cells (`dlygate4sd1/2/3_1`, `buf_1`, `buf_2`) is dont_use, so no existing instance can be resized; an original whose master changed anyway is swapped back; the new buffers are legalized with every original placed instance FIRM (if that fails, the ordinary legalization runs and the moved originals count as changed), between `global_route -start_incremental` and `-end_incremental`;
- the wires of exactly the changed nets (every signal net on a new buffer or on a moved original) are destroyed, so the detailed routing step routes those and keeps every other wire. A separate step before detailed routing, `RemoveNonOrthogonalWires` (`hw/soc/pnr/remove_nonorthogonal_wires.py`), works on the written database: any wire the changed nets still carry, and any signal wire with a segment that is neither horizontal nor vertical, is removed, with counts and the first segments printed (`NSSOC_WIRE_CLEANUP`, `NSSOC_NONORTHOGONAL`);
- the step prints, before and after, the worst slack per corner and kind, and a census of the hold-violating endpoints by the setup slack the repair may spend there (negative, below the hold deficit, room), and the new cells by master (`NSSOC_HOLD_*`).

First attempt (runs 43060919192, 43060983426): the resizer inserted one hold buffer (RSZ-0064), but 371 instances were new or had a new master, so about 370 existing instances were resized. The held legalization left those movable and moved them (4,457 um in total), their pins left the existing wires, and detailed routing stopped on non-orthogonal segments (DRT-1010). The estimated-after report used `report_worst_slack -corner` and failed (STA-0562); it now uses `report_checks -corner`, as the probe's corner STA does.

Second attempt (run 43109026710): 371 hold buffers (`dlygate4sd3_1`), no original instance resized or moved, no estimated hold violator left, and the 726 changed nets had no wire when the step checked them; detailed routing still stopped on DRT-1010 non-orthogonal Metal2 segments, among them port nets (`eth_mdio_o`, `spw_do_o`, from the pad edge at y = 0.2 um to y = 36 um). The wire cleanup step above removes those wherever they come from, and `NSSOC_HOLD_DONE changed_nets_with_wires=` and `changed_wires_removed=` show whether the changed nets regain wires after the check.

Then the routed-sta job extracts and times the result again, like every routed variant. New workflow job `route-hold` (between `route` and `routed-sta`), its own 6 h budget. Matrix: `r_cut4h_td_d68` (below) and `r_cut3hh_td_d68`, which is the routed `r_cut3h_td_d68` database with the repair alone. With `route_run` and `sta_variant`, `route-hold` takes the routed database of the earlier run, so `r_cut3hh_td_d68` needs no new probe or route. Its databases are the artifacts `routed-hold-db-*`.

Risks: the repair only adds hold buffers; setup paths that are themselves short of setup keep their hold violations (the setup protection forbids buffering them). Incremental detailed routing of a routed database is the mechanism LibreLane's own post-route antenna loop uses; a changed net whose wires move may leave DRC markers, which are reported (`route__drc_errors`), not waived.

### 12.2 `pcie_clk_i`: the receive-queue bank read (`SOC_PCIE_RX_READ_AHEAD=1`, default 0)

The worst path in both probes ends at a bank register: `receive_ownership.packets[24][3]` -> `bank_byte[0][3]` (-1.87), `packets[80][1]` -> `bank_byte[1][1]` (-1.37). Each bank register loads, at a mid-frame handshake, the byte at the next read index: per bit an AND-OR of 64 queue bytes (the bank's 38 and, for the flat array's bounds, 26 of the next bank's) with the one-hot cursor, and the handshake multiplexer. `soc_pcie_rx_credit.v` under the define:

- the bank's 38 bytes are taken in five groups of eight lanes. Each group keeps a read-ahead register `ahead[g] = packets[bank*CAP + 8g + (index+1)%8]`, so the byte the bank register loads at a handshake is `ahead[(index+1)/8]`: an AND-OR of five registers selected by a one-hot register (`ahead_group`);
- `ahead[g]` loads, at a mid-frame handshake, the AND-OR of its eight bytes selected by the lane after that (`ahead_lane` rotated, a register); lane 1 at an end of frame; otherwise it holds, because neither the bytes nor the cursor change. A commit rewrites the bank from staging in that cycle, so a committed bank's read-ahead registers load the same selection from staging (one shared selection; the bank's commit register picks it). Reset and link loss free every bank, and its next commit loads them before any byte of it is read;
- the reads across a bank boundary are left out. They are never loaded: the cursor passes a TLP's last index (at most CAP-1 = 37, the shape check) or a DLLP's (at most 5) only at an end of frame, which reloads byte 0. The bench checks that bound in every cycle.

So the longest path into a bank register is five registers and the handshake multiplexer, and into a read-ahead register eight local bytes and two multiplexers. The handshake now selects 288 registers instead of 48 (it already selected the cursor and the bank registers); that buffer tree is the new risk. Cost: 240 read-ahead and 13 cursor flip-flops, against 48 x 64-input AND-ORs replaced by 48 x 5 and 240 x 8. Not combinable with `SOC_PCIE_RX_STAGED_COMMIT` (the staged commit writes the bank after the read-ahead registers have read it): an undeclared module stops elaboration, and `syn_soc_top.sh`/`sim_soc.sh` refuse both at 1.

Equivalence: `hw/soc/tb/tb_pcie_rx_credit_read_ahead.v` with `scripts/check_pcie_rx_read_ahead.sh` compiles the file twice (the reference renamed, without the define; the candidate with it) and compares every output in every cycle, data and error while valid. Stimulus: legal TLPs of every class, malformed ones (length, traffic class, digest, oversize, undersize, missing start, error beats), good and bad DLLPs, gaps, back-pressure, random verdicts, link loss, training, FC-initialization gaps and resets. Eight runs of 300,000 cycles: four seeds at the SoC's parameters (8 DW, 2 slots per class, completer-only), two with requester traffic, two at 4 DW and one slot per class. A run passes only with no mismatch, the cursor below CAP, more than 1,000 frames and more than 100 commits during a frame. The queue's cocotb suites (`soc_pcie_rx_credit`, `soc_pcie_buffered_flow_packets`) run with the define too.

The cocotb makefiles of those two suites applied `EXTRA_COMPILE_ARGS` only with `PCIE_NATIVE=1`, so the section 10 runs "with `SOC_PCIE_RX_STAGED_COMMIT`" compiled the default build. The knob arguments now apply to RTL runs as well.

### 12.3 `clk_i`: the fabric request register's write data (`SOC_BUS_WDATA_OWN=1`, default 0)

`cs_registers_i.csr_addr[7]` -> `s_wdata[18]`/`[13]` (-0.63/-0.61) ends at `u_bus.g_req_reg.r_wdata`. With `IBEX_PMP_REQ_REG` the data port's write data is a flip-flop, so the path is not the store data: it is the instruction port. A CSR instruction in the execute stage decodes its address (illegal CSR, side effects), the controller sets the PC, the prefetch buffer raises `instr_req_o` with the new address, and in `soc_bus` that request (`can_issue_i`, through the address decode and the same-slave lock compare) decides `d_wins`, which selects `win_wdata = d_wins ? md_wdata_i : 0` into the 32 `r_wdata` flip-flops. The round's `ls_fsm_cs[0]` -> `s_wdata` paths of section 10.2 are the same mechanism from the load/store unit's state.

Under the define the data port's write data has its own register, `r_wdata_d`, loaded when the data port can be accepted (`cap_ok && can_issue_d`, which implies an accept), and `s_wdata_o = r_own ? r_wdata_d : 0`. It equals `r_wdata` in every cycle: after an accept won by the data port both hold `md_wdata_i` and `r_own` is 1; after one won by the instruction port `r_own` is 0 and `r_wdata` is 0; without an accept neither the registers nor `r_own` change; reset gives 0. So the ports are cycle-identical; it is compiled only with the define. Nothing from the instruction port reaches the write-data flip-flops; the slaves see one AND gate after them. `s_addr` (`win_addr`) has the same select and is not changed: its data input is the instruction address itself, so a split register would move a 32-bit multiplexer onto the slave side, into the grant paths.

### 12.4 Asynchronous group

- `pcie_link_up_i` -> `u_pcie_cdc.source_release[0]` (-0.20, `r_cut3h`) and `pcie_sys_rst_n` -> `source_reset_n` are the hold-padding pattern of section 10.1: the reset synchronizer's clear from an input port, padded for the minimum input delay against the capture clock's insertion latency. The post-route repair only adds buffers and does not remove these; with the hold margins at 0 the padding is already smaller (-0.73 to -0.20 between rounds). What is left needs a physical decision (the synchronizer placed at the port, or a smaller clock insertion latency at it), not RTL.
- `receive_input_slice.rst_ni` -> `receive_ownership.stage_write_at[21]` (-0.44, `r_cut3n`) is not padding: it is the recovery check of the receive queue's asynchronous reset, from the registered reset copy `up_rx` through its tree to every reset flip-flop of the queue and the input slice. Proposed, not done: a second registered copy for the queue (as `up_rx_link` is for its link input), so the slice and the queue have separate trees, or a separate copy for `stage_write_at` and the other wide reset vectors. Both are cycle-identical (all copies are equal at all times).

### 12.5 Runs

- Probe `r_cut4h_td_d68` (`r_cut3h_td_d68` plus `SOC_PCIE_RX_READ_AHEAD` and `SOC_BUS_WDATA_OWN`), then `route`, `route-hold`, `routed-sta`.
- `r_cut3hh_td_d68`: the hold repair alone, from the routed `r_cut3h_td_d68` of run 42987022661.
- `regress` and `native-boot` entry `ex_exec_pmpreg_cut4` (the `cut2` knobs without the staged commit, plus both new ones).
- `pcie-unit`: the queue suites with each queue knob, and the co-simulation. `eth-knobs` part `joint-cut4`: joint PCIe/Ethernet traffic with the new knobs, asynchronous and synchronous packet clock, inferred and vendor-SRAM FIFOs.

## 13. Routed results, rounds 3 and 4 (extracted RCX, three-corner STA, density 68%)

All variants route with 0 detailed-routing markers and 0 antenna violations. Setup slack is listed as slow / typical / fast, in ns:

| Variant | pcie_clk_i setup | clk_i setup (slow) | asynchronous setup (slow) | Ethernet (slow) | Hold |
|---|---|---|---|---|---|
| r_cut3n (receive staged commit off) | -1.87 / +0.26 / +1.33 | -0.63 | -0.44 | met | fast -0.02 (1 endpoint) |
| r_cut3h (as r_cut3n, pre-route hold margins 0 / 0) | -1.37 / +0.58 / +1.33 | -0.61 | -0.20 | met | slow -0.012, typ -0.003, fast -0.07 (92) |
| r_cut3m (as r_cut3n, margins 0.05 / 0.03) | -1.97 / +0.20 / +1.37 | -0.66 | -0.40 | met | fast -0.04 (12) |
| r_cut4m (r_cut3m plus `SOC_PCIE_RX_READ_AHEAD`, `SOC_BUS_WDATA_OWN`) | -2.83 / -0.35 / +1.09 | -0.82 | -0.60 | eth_rx -1.91 | fast -0.15 (23) |

Runs: 42987022661 (routes), 43052000192 (extraction of those routes), 43119350543 (r_cut3m and r_cut4m).

- **Staged receive commit and receive read-ahead** both make `pcie_clk_i` worse. The read-ahead's handshake fanout tree becomes the new worst path (`read_bank[2].ahead_bytes`). Both knobs stay off.
- **Pre-route hold margins.** Zero margins buy about 0.5 ns of `pcie_clk_i` setup, at the cost of small post-route hold violations. The intermediate margins keep neither the setup gain nor clean hold. Run-to-run placement noise is about ±0.5 ns at this level.
- **Post-route hold repair on the routed database** (`route-hold`, `post_route_hold.tcl`) inserts 371 hold buffers without moving any original instance, and estimated hold then has 0 violators. The following incremental detailed routing still fails with DRT-1010, "unsupported non-orthogonal wire". It fails on nets the repair did not touch as well, so re-routing a re-read routed database is not usable in this tool chain yet.
- **Remaining slow-corner limits:**
  - `pcie_clk_i`: the 96-entry receive-queue read multiplexer `receive_ownership.packets[] -> bank_byte[]`.
  - `clk_i`: CSR address decode into fetch and bus address (`csr_addr -> stored_addr_q` / `s_addr`).
  - asynchronous: the link-up reset into the replay state.

## 14. Fifth round: two-stage receive read, instruction request register, reset copies, hold-margin split

Starting point: the routed `r_cut3h_td_d68` and `r_cut3n_td_d68` of run 43052000192 (section 13). What their slow-corner reports show in the cells:

- `pcie_clk_i`, `receive_ownership.packets[80][1]` -> `bank_byte[1][1]` (-1.37): the 64-input AND-OR of bank 1 reads byte 80, which is byte 4 of bank 2 (a cross-bank read of the flat array). Its first gate, an `a22oi_1`, drives 0.12 pF of wire (1.43 ns, 1.59 ns slew); the next ones are a `nand4_1` and a `nor4_2`. The other worst paths start at the cursor (`next_onehot[14]`, `[20]`) and look the same. The path is wire-bound: the AND-OR gathers bytes from two banks' placement regions.
- `clk_i`, `cs_registers_i.csr_addr[7]` -> `r_wdata` (-0.61): `csr_addr` is `instr[31:20]` of the execute-stage instruction register (ibex_decoder), so the start point is that register, not a CSR. About 14.3 ns go to the redirect (`pc_set`/branch target, an `or3` with a fanout of about 30 through four `buf_1`), then the prefetch buffer's address multiplexer (`branch_i ? addr_i : ...`), the fabric's address decode of the instruction port, the same-slave compare, `can_issue_i`, `d_wins`, and the select of the request register; `stored_addr_q` is reached through the grant (`stored_addr_en` uses `instr_gnt_i`).
- asynchronous, `retry.link_up_i` -> retry reset pins (-0.41, `r_cut3n`) and `receive_input_slice.rst_ni` -> queue reset pins (-0.44): both are the net of one registered copy (`up_retry`, `up_rx`) feeding every reset pin of its block through a chain of eight `buf_1`/`buf_2` levels (5.3 ns arrival), with one or two hold buffers on the receive side. `up_retry` is also the replay store's `link_up_i`.

### 14.1 `SOC_PCIE_RX_READ2=1` (default 0): two-stage registered bank read

`soc_pcie_rx_credit.v`. The bank's CAP bytes are split into three groups (13 lanes each at 8 DW). The cursor moves by at most one per cycle, so the byte a bank register may load at the end of the next cycle is at c+1 (no handshake now), c+2 (a mid-frame handshake now) or 1 (end of frame, link loss or reset now). Stage 1 loads every cycle, per bank and group, the lane of c+1 and the lane of c+2 (a 13-input AND-OR selected by rotations of a registered one-hot lane, c mod 13), from staging instead of the bank in a commit cycle; it has no enable and no handshake. Stage 2, the bank register's next byte, is an AND-OR of the six stage-1 registers and byte 1, selected by seven one-hot pick registers that the handshake sets (no handshake: the group of c+1; mid-frame: the group of c+2; end of frame, link loss, reset: byte 1). So the pick registers, not the stage-1 registers, absorb the extra cycle, and no read latency is added: in every cycle the stage-2 value is the byte the default build's AND-OR selects for the in-bank indices. Cross-bank reads are left out, as in section 12.2: a mid-frame handshake happens only below a frame's last index, so c+1 <= CAP-1 whenever a bank register loads it, and the bank registers equal the default build's in every cycle. The module's ports are cycle-identical, so no unit-test expectation changes. Cost: 288 stage-1 flip-flops (6 banks x 3 groups x 2 x 8) and 23 cursor and pick flip-flops; the handshake reaches only the pick and cursor registers and the bank registers' multiplexer, as in the default build. Not combinable with `SOC_PCIE_RX_READ_AHEAD` or `SOC_PCIE_RX_STAGED_COMMIT`: an undeclared module stops elaboration, and the flow scripts refuse the combinations.

Evidence: `scripts/check_pcie_rx_read_ahead.sh OUT CYCLES SOC_PCIE_RX_READ2` (the script now takes the defines; with none it tests the read-ahead build as before), the random co-simulation of section 12.2 against the default build: eight configurations of 300,000 cycles, every output compared in every cycle, the cursor below CAP, more than 1,000 frames and more than 100 commits during a frame. The queue suites (`soc_pcie_rx_credit`, `soc_pcie_buffered_flow_packets`) run with the define.

### 14.2 `SOC_BUS_IREQ_REG=1` (default 0): instruction request register in the fabric

`soc_bus.v`. The core's instruction request is granted into a one-entry register (`ir_val`, `ir_addr`) whenever it is empty or being issued in the same cycle; the arbitration, the address decode `tgt_i`, the same-slave check, the request register's multiplexers (`win_addr`), the outstanding count and lock (`cnt_i`, `lock_i`, now on the fabric's grant `i_take`) read the register. The core's grant is `issue_en && mi_req_i && (!ir_val || i_take)`: no address decode and no arbitration with the data port. The execute-stage redirect still reaches the prefetch buffer's request and address and the register's D inputs, but no longer the select of `r_addr`/`r_wdata`/`r_be`/`r_we`/`r_tgt`/`r_own` or the grant-dependent `stored_addr_q` enable. The clock-gate enable gains `ir_val` (a held request can be issued with no request at either port). It works with `REQ_REG` 0 and 1.

This is not cycle-identical: every instruction fetch reaches its slave one cycle later. Ibex holds `req` and `addr` until `gnt` (protocol rule 1; the prefetch buffer's `stored_addr_q`), takes one grant per cycle as before, and the same-slave rule and in-order responses are unchanged, so the core sees only a longer fetch latency. The fabric's formal properties (`hw/soc/formal/soc_bus_props.v`) are stated for the default build and are not re-run with the knob. Evidence: the regressions and the native gate-level boot without MBIST (`ex_exec_pmpreg_cut5`), and the joint SoC traffic (`joint-cut5`). The cycle budget of the native boot (2,000,000) is unchanged; a fetch-latency-bound boot may need more.

The data port's write-data register (`SOC_BUS_WDATA_OWN`, section 12.3) is not needed with this knob, since `d_wins` no longer depends on the instruction port, and stays off.

### 14.3 `SOC_PCIE_RESET_COPIES=1` (default 0): more registered reset/link copies

- `soc_pcie_buffered_flow_packets.v`: `up_rx_slice` (receive input slice and FC-initialization gate) and `up_rx_copy` (new port `rst_copy_ni` of `soc_pcie_rx_credit`: the read cursor `read_onehot`, the staging write select `stage_write_at` and, with `SOC_PCIE_RX_READ2`, its cursor and pick registers). `up_rx` keeps the rest of the queue.
- `soc_pcie_reliable_packets.v`: `up_retry_link` (the replay store's `link_up_i`, so its link clears and link-qualified logic no longer share the net of its asynchronous reset) and `up_retry_copy` (new port `rst_copy_ni` of `soc_pcie_replay_tx`: the replay read cursor and the transmit slice).

Every copy is cleared asynchronously by the same `local_reset` as the existing copy and set one clock later (the D inputs are 1 whenever `local_reset` is high and differ only so synthesis keeps the flip-flops), so assertion stays asynchronous, release stays synchronous, and all copies are equal at all times. Inside the two modules the moved registers are in their own always block with the same next-state function. The new ports exist only with the define; the `soc_pcie_rx_credit` and `soc_pcie_replay_tx` benches and the co-simulation drive them with `rst_ni`. The input-port paths of section 12.4 (`pcie_link_up_i` -> `u_pcie_cdc.reset_ni`, `pcie_sys_rst_n` -> `source_reset_n`) are not changed by this knob. Evidence: the receive-queue, replay, reliable, flow and buffered suites with the define, and the co-simulation with `SOC_PCIE_RX_READ2 SOC_PCIE_RESET_COPIES`.

### 14.4 Which hold margin costs the setup

Probes with routing and extracted STA, all r_cut3n settings plus the three knobs:

| Probe | `PL_RESIZER_HOLD_SLACK_MARGIN` | `GRT_RESIZER_HOLD_SLACK_MARGIN` |
|---|---:|---:|
| `r_cut5n_td_d68` | 0.1 (flow default) | 0.05 (flow default) |
| `r_cut5a_td_d68` | 0.0 | 0.05 |
| `r_cut5b_td_d68` | 0.1 | 0.0 |

`r_cut5n` measures the knobs at the flow's margins (against `r_cut3n`); `r_cut5a` and `r_cut5b` against it show which stage's margin costs the setup slack. These are flow settings of the measurement probes, not the SDC or an acceptance threshold. Functional entries: `regress` and `native-boot` `ex_exec_pmpreg_cut5` (the cut2 knobs without the staged commit, plus the three new ones), `pcie-unit` (the suites and the co-simulations above) and `eth-knobs` part `joint-cut5` (asynchronous and synchronous packet clock, inferred and vendor-SRAM FIFOs).

Risks: the stage-1 registers add about 300 flip-flops to the packet domain at d68 (the read-ahead registers' area moved other groups in `r_cut4m`); each bit of the cursor lane register drives about 340 stage-1 gates (both rotations, six banks and the staged selection) through a buffer tree; the instruction request register costs fetch bandwidth after every redirect; the reset copies help only if the placer gives each tree its own region.
