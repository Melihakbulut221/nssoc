# Ibex execute path at the slow corner

Branch `timing/ibex-execute`, based on `timing/pcie-boundary-skid`. Frozen constraints, unchanged here: `clk_i` 20 ns, corner `nom_slow_1p08V_125C` with 5% derate, the physical SDC and every acceptance threshold. Nothing under `hw/soc/rtl/pcie/` is touched.

Starting point (`docs/mainchip-impl-probe.md` on `analysis/impl-probe`, density 70%, `SOC_SYNTH_PREFIX_ADDER=1`): slow-corner `clk_i` after global route is -8.57 ns with the flow's capped repair. With uncapped repair, the worst slack over all groups is -6.54 ns with the SECDED register file and -5.69 ns (`clk_i`) with the upstream register file. Section 5 shows that the -6.54 ns is `pcie_clk_i`. The SECDED design's `clk_i` after repair is -5.84 ns.

## 1. Why these endpoints are on the register-file-read path

The core is the pinned Ibex (`34b07057`) in the `soc_top.v` configuration: RV32IMC, PMP with 4 regions, `BranchTargetALU = 0`, `WritebackStage = 0`. Every slow-corner path starts at a register-file flop or at the IF/ID instruction register that addresses the file. All of them share the same head:

- the register-file read: with CORRPRE, per-word correction followed by the 32:1 multiplexer; with the upstream file, the read-address fanout followed by the multiplexer;
- the operand multiplexer;
- the shared ALU's 32-bit adder. Branch comparisons use it as a subtractor, followed by a zero or sign reduction.

From there the paths fan out into the endpoint classes below.

| Endpoint class | What the register-file read reaches | RTL |
|---|---|---|
| `crash_dump[*]` | **Not a capture register.** After `flatten`, the 160-bit `crash_dump` wire in `soc_top` is the shortest public name on five core-internal registers: `[159:128]` `pc_id` (IF/ID register), `[127:96]` `pc_if` (prefetch FIFO address), `[95:64]` the LSU's `addr_last_q`, `[63:32]` `mepc_q`, `[31:0]` `mtval_q`. Their data or enables come from the execute cycle: `pc_id` is enabled by `id_in_ready = ~stall_id`, `mepc`/`mtval` by the CSR write enable, `addr_last_q` takes the adder's data address. | `ibex_core.sv` 1326-1330 |
| `mhpmcounter[2]` (minstret), `mcycle_counter_i.counter` | Not the increment. `counter_d = we ? csr_wdata : inc ? q+1 : q`, and `q+1` starts at the counter's own flops. The late signals are the **enables**. minstret's `inc` is `instr_ret`, derived from `instr_id_done`. Both counters' `we` is `csr_we_int = csr_wr & csr_op_en & ~illegal`, with `csr_op_en = csr_access & instr_executing & instr_id_done`. | `ibex_counter.sv`, `ibex_cs_registers.sv` 1624-1645, `ibex_id_stage.sv` 747 |
| `csr_mtvec_o`, `csr_pmp_addr_o`, `mie_q`, `mscratch_q`, `dscratch1_q`, `csr_depc_o` | The data is short: `csr_wdata = alu_operand_a_ex` (rs1). The enable is the same `csr_we_int` as above. | `ibex_core.sv` 1429 |
| `prefetch_buffer_i.fifo_i.rdata_q`, `stored_addr_q` | The FIFO pop is `id_in_ready = ~stall_id`. The fetch address is redirected by JALR (`rs1 + imm` from the ALU, in the first cycle) and by the second cycle of a taken branch. The instruction grant also depends on the fabric's arbitration against the data request. | `ibex_if_stage.sv`, `ibex_prefetch_buffer.sv` |
| `s_addr[*]`, `s_wdata[*]` (`soc_bus` request register, `REQ_REG=1`) | The winner's address. The data address is the adder output. The data request is gated by the PMP check of that address: `data_req_o = data_req_out & ~pmp_req_err[PMP_D]`. The arbitration select depends on that gated request. | `ibex_core.sv` 1063, `soc_bus.v` |
| register-file data and check bits | ALU result, then the result multiplexer, then the write-data multiplexer (write or scrub), then the SECDED encoder, then the flop. This is the intrinsic single-cycle loop. | `ibex_regfile_secded.v` |

The common factor of the first four classes is `stall_id`. At `BranchTargetALU = 0`, a conditional branch's first cycle computes `stall_branch = branch_decision_i` (`ibex_id_stage.sv` 925-927). The comparison result therefore goes through `stall_id` to `instr_done`, `instr_id_done`, `id_in_ready` and `csr_op_en`, which are the enables of nearly every architectural register. The two measured worst paths show both kinds:

- **Upstream register file, after uncapped repair (run42436769600, -5.69 ns).** The path runs from the instruction register through 6.3 ns of read-address buffer trees, the multiplexer and the adder. A zero reduction ends at 22.6 ns, then 4.9 ns of enable fanout trees reach a register enable.
- **SECDED register file, capped repair (-8.58 ns).** The path ends at a check bit: clock 2.65 ns, read and correction to 12.6 ns, adder sum at 21.4 ns, result multiplexer at 26.9 ns, encoder and write to 30.7 ns.

What this rules out:

- Registering `crash_dump` later gains nothing. `soc_boot`'s capture of `crash_dump[159:128]` is already a flop-to-flop path, and the slow endpoints carry that name only as an alias.
- Carry-save or pipelined counter increments gain nothing. The increment is not on the path; the enable is.
- A registered counter write removes only the `we` term. It also changes back-to-back CSR read semantics.

## 2. Candidates, ranked by expected gain against risk

| # | Change | Cuts | Expected gain (slow corner) | Risk and cost |
|---|---|---|---|---|
| A | **Two-cycle conditional branches** (`IBEX_BRANCH_2CYCLE`, implemented) | decision to `stall_id` to all enables (CSR, counters, `pc_id`/FIFO, `mepc`/`mtval`) | the 4-5 ns enable fanout on those classes; nothing on the register-file write loop, the LSU/PMP/bus path or the JALR fetch path | low: two expressions in one generated file. This is the same FSM path Ibex already uses in data-independent-timing mode. Not-taken branches take +1 cycle (+1.1% boot cycles). |
| B | **Branch-target ALU without the writeback stage** (`SOC_CORE_BT_ALU`, implemented) | decision to `stall_id`. The decision instead drives the fetch redirect, and that redirect continues to the fabric address register. | uncertain, because the cone moves rather than disappears. Earlier, writeback stage plus branch-target ALU measured -12.40 against -9.69 ns. | low: upstream parameter, no patch. Boot cycles -5.0%. |
| C | Deferred check bits in `ibex_regfile_secded.v` | encoder on the write loop | about 3-4 ns on check-bit endpoints only; data-flop endpoints stay about 1 ns behind | moderate: a one-cycle unprotected window per write, pending-register bypass, scrub and error-report masking, and the formal regfile contract needs extending |
| D | Detect-only read (raw operand, syndrome in parallel, stall and correct on error) | per-word correction on the read | at most the upstream/SECDED difference: 2.0 ns capped, 0.85 ns uncapped | moderate-high: needs a core stall input (Ibex patch) and a replay path |
| E | Registered read-address predecode (one-hot `rs1`/`rs2` registered with the IF/ID register) | about 4.8-6.3 ns of read-address buffer trees seen in both upstream paths | 2-4 ns on every class | moderate: an Ibex IF/ID patch and a new register-file port |
| F | PMP data check and request one cycle later | adder to PMP to arbitration | only on the LSU/bus class | high: every load and store gets +1 cycle. `soc_req_pipe`'s `gnt_o = req_i & !valid_q` is still combinational on the request, so `CORE_REQ_REG` does not cut it. |
| G | Split execute: registered operands, EX in the next cycle, forwarding | everything after the read | 8-12 ns; the only change sized to the full gap | high: a new pipeline stage in a pinned core |

The writeback stage without the branch-target ALU is not an option. `tb_ibex_branch_stall` keeps the pinned core's misdirected-branch counterexample for that combination.

A and B were implemented because they are the cheapest cuts of the class that dominates the endpoint census and the upstream worst path. A needs a patch, B is parameter-only.

## 3. What was implemented

Both knobs default to 0. At 0, the synthesis script and the simulation take exactly the path they took before.

- **`IBEX_BRANCH_2CYCLE=1`.** `hw/soc/flow/ibex_branch_2cycle.py` reads the sv2v output `ibex_id_stage.v` and writes `hw/soc/genp/<tree>-br2/ibex_id_stage.v`; it never writes to its input. In the first-cycle `id_fsm_d` and `stall_branch` expressions of a conditional branch, `branch_decision_i` is replaced by `1'b1`. After the patch the decision reaches only `branch_set_raw_d`, which is flopped at `BranchTargetALU = 0`. Each anchor must match exactly once. A generate block `g_branch_two_cycle` is the elaboration witness, and `sim_soc.sh` asserts it. `flow/ibex_sources.sh` substitutes the file. `syn_soc_top.sh` and `sim_soc.sh` refuse the knob together with `SOC_CORE_BT_ALU` or `SOC_CORE_WB_STAGE`, where it would be a no-op.
- **`SOC_CORE_BT_ALU=1`.** This sets the new `soc_top` parameter `CORE_BT_ALU`, and `.BranchTargetALU (CORE_BT_ALU != 0 ? 1 : CORE_WB_STAGE)`. Synthesis applies it as `chparam` and simulation as `defparam`. `sim_soc.sh` asserts `g_branch_target_alu`.
- The Kogge-Stone knob and `scripts/impl_probe.py` were carried over unchanged from `analysis/impl-probe`. `.github/workflows/cloud-evidence-summary.yml` runs the unit tests, the regressions, the native boot and the probe.

The expression gives the same integer parameter value as before at 0 and the same value as the measured `CORE_WB_STAGE | CORE_BT_ALU` form at 1. It is written so that Verilator reports no new width diagnostic and `soc_top.v` keeps its line count, so the recorded lint diagnostics in `hw/soc/lint-policy.json` still apply.

`scripts/run_core_ack_protocol.py` still pins the old `.BranchTargetALU (CORE_WB_STAGE)` text. Its C10 source pin of `soc_top.v` already differed on the base branch.

## 4. Functional regressions (run42460059397)

| Test | base | `IBEX_BRANCH_2CYCLE=1` | `SOC_CORE_BT_ALU=1` |
|---|---|---|---|
| `pytest sw/tests/test_ibex_branch_stall.py` (writeback hazard, plus new cases for both knobs, 5 response delays each) | pass | pass | pass |
| `make soc-sim` (28 checks) | pass | pass | pass |
| core asleep at cycle | 430,231 | 435,073 (+1.1%) | 408,881 (-5.0%) |
| `make soc-boot-regression` (normal, entry0, length0) | pass | pass | pass |
| `make soc-crash-cocotb` (double fault, crash PC, reset, APB) | pass | pass | pass |
| RTL boot, native-boot configuration (inside each probe job) | - | pass | pass |
| native gate-level boot, CORRPRE + PCIe + system/Ethernet MBIST | - | **pass** (rerun): 28 checks, 1,637,138 cycles | **pass**: 28 checks, PCIe idle, MBIST, 1,605,343 cycles |

The first attempt of the two-cycle native boot hit the gate simulator's 18000 s wall-clock limit (rc 124). At that point it was at cycle 1.55 M with MBIST done, application checks passing so far, and no SEC/DED or alert. The job rerun at the same commit passed: 28 checks, fail mask 0, PCIe idle and MBIST pass, 1,637,138 cycles in 9413 s. The branch-target-ALU boot took 11023 s, so the limit is close to the hosted runners' speed spread.

## 5. Timing (density 70%, `SOC_SYNTH_PREFIX_ADDER=1`, global-route parasitics)

`clk_i` setup worst slack, in ns:

Two dispatches of the same commit pair:

- **run42460059397**: knobs only, uncapped repair, 3.5 h limit.
- **run42488673709**: adds the knob-off control and bounds the repair at 1100 iterations, so every variant finishes and prints per-group, per-corner reports at equal repair effort.

The control reproduces the published capped numbers exactly (-8.57 / 2.07 ns).

| Variant | Capped repair (flow): slow / typ / fast | + `repair_timing` 1100 iterations: slow / typ / fast |
|---|---|---|
| control (SECDED, CORRPRE) | -8.57 / 2.07 / 8.03 | **-5.84** / 3.90 / 8.03 |
| `IBEX_BRANCH_2CYCLE=1` | -15.44 / -2.22 / 5.66 | **-5.90** / 3.54 / 9.10 |
| `SOC_CORE_BT_ALU=1` | -14.81 / -1.09 / 6.16 | **-5.97** / 3.56 / 8.40 |
| `IBEX_BRANCH_2CYCLE=1`, upstream register file | -5.35 / 4.15 / 9.05 | -5.35 / 4.15 / 9.05 (run to completion: -5.35) |
| upstream register file, reference (run42436769600) | -6.55 / 3.48 / 8.77 | -5.69 / 4.03 / 8.77 (run to completion) |

Corrections and observations:

- **The published "-6.54 ns uncapped" for the SECDED design was not `clk_i`.** It is the all-group WNS, and with per-group reports it is `pcie_clk_i` (-6.54). The control's `clk_i` after the same repair is -5.84 ns, so the baseline for comparison is -5.84, not -6.54.
- **The capped numbers of both knobs are much worse.** The worst path is still the same register-file-to-register-file loop, but 7 ns longer: long single-drive nets after the flow's 100-iteration repair. That is placement and repair variance on a changed netlist, not logic depth. Once the repair is given equal effort, the gap disappears.
- **After repair, neither knob moves the slow corner** (-5.84 to -5.90 / -5.97 ns, inside the run-to-run spread). Typical is 0.3 ns lower, fast 0.4-1.1 ns higher. With the upstream register file the two-cycle knob gives +0.34 ns at slow (-5.69 to -5.35).
- What limits `clk_i` after repair:
  - **control:** the RAM read return. `u_ram...u_b2/A_CLK` with a 9.5 ns SRAM read arc, then 15 cells of the memory's ECC and bank logic into a register: 27.87 ns arrival.
  - **with either knob:** the core loop. Register-file flop, CORRPRE syndrome and correction (to 12.5 ns), read multiplexer, operand multiplexer and adder (to 22.7 ns), SECDED encoder, register-file D: 28.2 ns arrival, 56-66 cells.

  The enable cone that A and B cut was therefore only about 0.1 ns behind these two classes. Removing it exposes them.

## 6. Is 20 ns at the slow corner reachable?

**No, not by these cuts and not by any other single local cut.** After equal repair the slow-corner `clk_i` is about -5.9 ns, which needs about 25.9 ns of the 20 ns period. Three independent path classes sit within about 0.1 ns of each other:

1. The core execute loop, register file to register file, about 25.3 ns of logic. Option C (encoder off the write: about 3 ns) and option D (correction off the read: about 1-2 ns, bounded by the measured 0.3-2 ns upstream/SECDED difference) together still leave it about 1-2 ns short. Option E (registered read-address predecode) is needed on top, and the sum is optimistic. The change sized to the gap is option G: a separate execute stage with forwarding, in effect a three-stage core. That is not a parameter of the pinned Ibex.
2. The SRAM read return: 9.5 ns macro arc plus about 15.7 ns of memory ECC and bank logic before the `MEM_RDREG` register. It needs the correction moved behind a register (one more read cycle) or split across two stages, in `soc_mem_sram.v`/`soc_mem_ecc.v`. This is independent of the core.
3. The LSU/PMP/fabric and fetch-redirect classes, which were not exposed here but follow next.

Separately, `pcie_clk_i` (-5.9 to -6.0 ns after repair) and the asynchronous group (-5.8 to -6.2 ns) also miss at the slow corner; they are outside this branch.

Recommendation: keep both knobs off. A costs +1.1% cycles and B gains 5.0% cycles, and neither gains slack. B is a free performance option if the slow corner is ever relaxed. The next measurements worth making are C plus D in the project-owned register file, which needs no Ibex change, and a registered memory ECC. Both are needed before a core pipeline change can show whether 20 ns is in reach.
