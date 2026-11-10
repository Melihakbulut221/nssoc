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
