# A separate execute stage for the pinned Ibex

Branch `timing/ibex-ex-stage`, based on `timing/ibex-execute`. Frozen constraints, unchanged here: `clk_i` 20 ns, corner `nom_slow_1p08V_125C` with 5% derate, the physical SDC and every acceptance threshold. Nothing under `hw/soc/rtl/pcie/` is touched.

Starting point (`docs/ibex-execute-timing.md` section 7): with every project-owned cut (`CHKDEFER`, the predecoded read address, `SOC_MEM_RDREG=2`) and two-cycle branches, slow-corner `clk_i` is -4.90 ns after the 1100-iteration repair. The worst path is register-file read, operand multiplexer, ALU and then the result or the stall cone: 57 cells, 26.9 ns arrival against about 22.0 ns required. The pinned core decodes, reads the register file and executes in one stage, so no local cut removes the read from that path. Option G of that document, a separate execute stage, is what this branch implements.

## 1. Summary

- **What.** `IBEX_EX_STAGE=1` (default 0) adds an ID/EX register between the IF/ID register and the pinned core's ID/EX logic. The register file is read in the new ID stage and the operands enter EX registered; the one write the read can miss is forwarded from the write port. It is a flow-applied patch to the generated `ibex_core.v`, like the earlier Ibex patches, and composes with the predecode patch and the two-cycle branches. With the knob off the synthesised netlist is byte-identical (`90f7045f...`) and the control timing is unchanged.
- **Hazards.** No interlock stall is needed: forwarding covers ALU, load, multiply/divide, CSR and link results. `pc_set` flushes the ID stage; `mepc`/`dpc` on interrupts and debug entry name the ID-stage instruction when there is one; IF hands nothing to ID around SYSTEM instructions, so the PMP check of the next instruction sees a CSR write, as the pinned core's pipeline flush guarantees.
- **Verification.** 327 new core-level tests (interrupts and debug requests at every cycle offset, single step, random latencies, PMP, `wfi`, `fence.i`, 12 random programs, six mutations of the patch that must be caught) pass in five configurations; the branch tests, `make soc-sim`, `make soc-boot-regression` and `soc-crash-cocotb` pass with the knob alone and with the earlier knobs; riscv-formal gives the unpatched core's verdicts on every check except `hang`, whose bound moves from 28 to 32 cycles. The native gate-level boot passes with the earlier knobs and two-cycle branches; without two-cycle branches it fails one firmware check, a timer race in the firmware check (section 3.4), now fixed in the firmware (section 3.5). The execute stage alone passes the full gate-level boot with system and Ethernet MBIST.
- **Cost.** +8.1% boot cycles alone, +7.9% on top of the earlier knobs; +0.13% area.
- **Timing.** Slow-corner `clk_i` after the 1100-iteration repair: -5.25 ns alone (control -5.84), **-4.40 ns** with `CHKDEFER`, predecode and `MEM_RDREG=2` (earlier best -4.90), -5.67 ns with two-cycle branches added. The register-file read is off the critical path; the LSU address, PMP and fabric arbitration path into the bus request register is now the worst `clk_i` path, and the asynchronous and `pcie_clk_i` groups are worse than `clk_i`.
- **Gap.** About 4.4 ns (22%) of the 20 ns period is still missing at the slow corner, now in three places none of which is the register-file read.

## 2. Design

`IBEX_EX_STAGE=1` selects `hw/soc/flow/ibex_ex_stage.py`, a patch to the generated `ibex_core.v` in the style of `ibex_rf_predecode.py` and `ibex_branch_2cycle.py`. It reads the sv2v output (or the predecode patch's output when `IBEX_RF_PREDECODE=1` as well), never writes to its input, and every anchor must match exactly once. `flow/ibex_sources.sh` writes it to `hw/soc/genp/gen-ex/` or `gen-pre-ex/` and substitutes it. Nothing else of Ibex changes: `ibex_if_stage.v`, `ibex_id_stage.v`, the controller, the decoder, the ALU, the LSU and the CSR file are the files they were.

| Stage | Holds | Does |
|---|---|---|
| IF | prefetch buffer | fetch, compressed decode (unchanged) |
| ID | the IF/ID register of `ibex_if_stage` (unchanged) | reads the register file at `rs1 = instr[19:15]`, `rs2 = instr[24:20]` of its instruction. That is the address the pinned decoder already drives in this configuration, so the register file and its `RDPRE` predecode keep the same address source. |
| EX | **new ID/EX register**: instruction, PC, compressed and fetch-error flags, and the two operands read in ID | the pinned ID/EX logic: decoder, controller, ALU, multiplier/divider, LSU, CSRs, write-back |

The core's wires `instr_valid_id`, `instr_rdata_id`, `pc_id` and the rest keep their names and now carry the EX-stage instruction, so every consumer (controller, CSR exception PC, `crash_dump_o`) refers to the instruction being executed, as before. The IF stage's `id_in_ready_i` becomes "the ID stage can take an instruction" and its `instr_valid_clear_i` "the ID-stage instruction moved into EX or was flushed". The new logic is in a generate block `g_ex_stage`, which `sim_soc.sh` asserts is elaborated exactly when the knob is on. In simulation, a check stops the run if the EX-stage decoder ever addresses the register file with anything but `instr[19:15]`/`instr[24:20]`, which is the assumption that lets ID read without decoding.

The register file is now read one stage ahead of the ALU: the read and its correction end at the operand register, and the EX-stage paths start at that register.

### 2.1 Hazard handling

The design is the simplest one that is correct for every instruction: no interlock stall at all, and one forwarding path.

| Hazard | Mechanism |
|---|---|
| Read after write, any producer (ALU, CSR read, multiply/divide result, load data, link register) | The non-writeback core finishes every register write of an instruction before the next one may enter EX. The only write the ID-stage read can miss is the one in the cycle the next instruction moves into EX. That write is forwarded: `rf_we_wb` with `rf_waddr_wb` equal to the read address selects `rf_wdata_wb`, the exact value the register file receives, into the operand register. In every other cycle ID simply re-reads the file. There is no load-use stall and no multiply/divide or CSR interlock. |
| x0 | A write with `rf_waddr_wb = 0` is never forwarded. |
| Multi-cycle instructions (multiply, divide, misaligned load/store, two-cycle branches and jumps) | Operands are captured once, when the instruction enters EX, and held while it executes. |
| Taken branch, jump, exception, interrupt, debug entry, `mret`/`dret`, `fence.i` (Ibex implements it as a jump) | `pc_set` clears the ID stage together with what IF delivers, and nothing enters EX in that cycle, which is the pinned IF/ID rule. |
| Precise `mepc`/`dpc` | The controller takes an interrupt or debug request between instructions and saves `pc_if` (`csr_save_if`). That has to be the next instruction not yet in EX, which may now be waiting in ID, so the CSR file's `pc_if` input is the ID-stage PC when ID is valid and `pc_if` otherwise. The same `pc_set` flushes the ID instruction, and it is the first one fetched after `mret`/`dret`. Exceptions keep saving `pc_id`, the EX-stage instruction. |
| CSR writes and the PMP | The pinned core flushes after a CSR write so that the IF stage's PMP check of the next instruction sees the new state; that check happens when an instruction is handed from IF. Here that is the IF-to-ID handover, so IF hands no instruction to ID while a SYSTEM-opcode instruction (CSR access, `ecall`, `ebreak`, `mret`, `dret`, `wfi`) moves into or executes in EX. CSR reads and writes execute in EX in program order, as before. |
| `wfi`, flushing CSR writes | They halt IF without `pc_set`. An instruction already in ID stays there, like one in the prefetch buffer, and enters EX when the controller resumes. |
| `fence` | A no-op in Ibex, unchanged. |

The writeback stage, the branch-target ALU and the register-file ECC of `SecureIbex` are not covered. The patch instantiates an undeclared module in those configurations, so elaboration stops in every tool, and `sim_soc.sh` and `syn_soc_top.sh` refuse the knob with `SOC_CORE_WB_STAGE` or `SOC_CORE_BT_ALU`.

### 2.2 Files

- `hw/soc/flow/ibex_ex_stage.py`: the patch. `hw/soc/flow/ibex_sources.sh`: `IBEX_EX_STAGE`, applied after the predecode patch.
- `hw/soc/flow/sim_soc.sh`, `syn_soc_top.sh`, `scripts/check_soc_corrpre_pcie_native_boot.sh`, `check_soc_corrpre_pcie_mbist_native_boot.sh`: the knob, its refusals, the `g_ex_stage` witness, the configuration record.
- `hw/soc/tb/tb_ibex_ex_stage.v`, `sw/tests/rv32_mini_asm.py`, `sw/tests/ibex_ex_programs.py`, `sw/tests/test_ibex_ex_stage.py`: the core-level tests; `sw/tests/test_ibex_branch_stall.py`: execute-stage cases.
- `hw/soc/rvformal/params.sh`, `checks.cfg.in`, `hw/soc/flow/rvformal.sh`: the parameter guard fix and `RVF_HANG_DEPTH`.
- `.github/workflows/cloud-evidence-summary.yml`: core tests, regressions, native boots, probes (with an optional slow-corner report with net names and a flip-flop-to-net map), riscv-formal.

### 2.3 The default build is unchanged

At `IBEX_EX_STAGE=0` (or unset) `ibex_sources` lists exactly the files it listed before; `test_default_sources_are_unpatched` checks that. The probe control of this branch (run42666896029, `r4_base`) synthesises a `soc_top` netlist with SHA-256 `90f7045f1f6955a4...6f909cd7b7`, byte-identical to the control of `docs/ibex-execute-timing.md` section 7.1, with the same boot ROM image (`ab744061...`), and gives exactly the same timing (-8.57 ns capped, -5.84 / 3.90 / 8.03 ns after the repair) and the same 647,591 boot cycles.

## 3. Tests

### 3.1 Core-level tests (new)

`hw/soc/tb/tb_ibex_ex_stage.v` runs `ibex_top` in `soc_top`'s configuration (RV32IMC, PMP with four regions, no writeback stage, no branch-target ALU) from a 16 KiB memory with randomised grant and response latencies on both ports, an instruction-fetch error region, a data error region, an external interrupt and a debug request. The programs are assembled by `sw/tests/rv32_mini_asm.py` (no cross compiler needed) from `sw/tests/ibex_ex_programs.py`. Each runs inside one frame: trap vectors, an interrupt handler and a debug handler that are transparent to the main program, an exception handler that belongs to it, and a dump of x1-x25. Self-checks exit with a nonzero code.

The testbench folds the **main program's architectural trace** into one hash: every retired PC, every register-file write and every store whose instruction is outside the interrupt and debug handlers. Interrupts, debug entries and bus latency are invisible to the main program, so every trial of a program must give the same hash, and the same hash as the unpatched core. A lost, duplicated or re-executed instruction, a wrong operand, a wrong `mepc`/`dpc` or a missed flush all change it.

| Program | Hazard class it targets |
|---|---|
| `alu` | distance-1/2/3 read-after-write chains, writes to x0 followed by reads of x0, `lui`/`auipc`, compressed ALU operations, a 100-iteration dependent loop |
| `load` | load-use into ALU, store data, load address (pointer chase), branch compare and `jalr` target; byte/half sign extension; misaligned word and half loads and stores (two bus accesses); back-to-back loads to one register; `c.lw`/`c.sw` |
| `muldiv` | every M instruction with dependent producers and consumers, divide by zero, overflow, multiply chains, divide result as load address, multiply result as store data and branch operand |
| `csr` | `csrw` then `csrr` of the same CSR, every CSR operation, read-modify-write with rs1 = rd, CSR result used immediately, `mstatus.MIE` and `mie` toggled with interrupts pending |
| `counters` | `minstret` deltas over known instruction counts (not swept: handlers retire instructions too) |
| `branch` | every branch type, taken and not taken, on operands written by the previous instruction; shadow instructions after taken branches; `jal`/`jalr` link values, `jalr rd = rs1`, `jalr` to a just-computed target; all compressed control transfers; 32-bit instructions at half-word addresses |
| `except` | `ecall`, `ebreak`, `c.ebreak`, illegal instructions (zero word, all ones, an unimplemented CSR), load and store access faults (the destination keeps its value), an instruction-fetch access fault, an exception right after a taken branch, `mepc`/`mcause`/`mtval` logged and compared |
| `fence` | self-modifying code with `fence.i`, the patched instruction directly behind it, in a loop; `fence` |
| `pmp` | a locked PMP entry that removes execute permission from the instruction right after the `pmpcfg0` write; it must fault with `mepc` at that instruction |
| `wfi` | `wfi` with interrupts enabled (handler, then the next instruction) and disabled (wake without trap, `mip` checked), under periodic interrupts |
| `rand1`-`rand12` | random mixes of all of the above with register choices biased toward the last three destinations, forward branches and jumps, `ecall` |

`sw/tests/test_ibex_ex_stage.py` runs them in five configurations: the unpatched core (`base`), the execute stage alone (`ex`), the unpatched core with the previous knobs (`base_knobs_br2`: SECDED register file with `CORRPRE`, `CHKDEFER`, `RDPRE`, the predecode patch and two-cycle branches), and the execute stage with those knobs without and with two-cycle branches (`ex_knobs`, `ex_knobs_br2`). Verilator runs the sweeps (about 300 times faster than Icarus here); Icarus runs the trace comparison as well, because it propagates unknown values.

| Test | What is required | Cases |
|---|---|---|
| `test_same_trace_fixed_and_random_latency` | every configuration gives the unpatched core's hash with fixed latency and over 20 random-latency seeds | 105 |
| `test_same_trace_four_state` | the same in Icarus | 50 |
| `test_interrupt_at_every_cycle` | one interrupt at **every** cycle offset from 1 to the program length + 40, with fixed and random latency: same hash in every trial | 40 |
| `test_debug_request_at_every_cycle` | the same for a debug request | 40 |
| `test_periodic_interrupts_random_latency` | repeated interrupts over the whole program at 60 phases (and `wfi`) | 44 |
| `test_single_step_with_interrupts` | the whole program single-stepped, then short single-step bursts mixed with periodic debug requests and interrupts | 40 |
| `test_mutated_patch_is_caught` | each of six mutations of the patch is detected: no forwarding on A, on B, x0 forwarded, no ID flush on `pc_set`, raw `pc_if` for `mepc`/`dpc`, no IF handover gate around SYSTEM instructions | 6 |
| `test_patch_refuses_unsupported_configurations`, `test_default_sources_are_unpatched` | elaboration stops with the writeback stage and branch-target ALU; the knob-off source list is the old one | 2 |

All 327 pass (unit job of run42666896029, 207 s). One property of the patched core showed up in the first version of the sweeps: with an interrupt or debug request re-raised faster than a handler round trip, a request is pending whenever a handler returns and the main program makes no progress. The pinned core has the same property at a somewhat shorter interval, because its handler round trip is shorter; the sweeps use intervals longer than a round trip.

### 3.2 The repository's tests

| Test | `ex` | `ex` + `CHKDEFER` + predecode + `MEM_RDREG=2` | the same + two-cycle branches |
|---|---|---|---|
| `test_ibex_branch_stall.py` (33, ten new execute-stage cases with five store-response delays) | pass (alone and with two-cycle branches) | with the knobs: `test_ibex_ex_stage.py` (`ex_knobs`) | with the knobs: `test_ibex_ex_stage.py` (`ex_knobs_br2`) |
| `test_regfile_execute_knobs.py` (15), the register-file cocotb suite (3 configurations) and the memory suite (`RDREG` 0/1/2) | pass | pass | pass |
| `make soc-sim` (28 checks, fail mask 0) | pass | pass | pass |
| `make soc-boot-regression` (normal, entry0, length0) | pass | pass | pass |
| `soc-crash-cocotb` (double fault, crash PC, watchdog, APB) | pass | pass | pass |
| native gate-level boot, CORRPRE + PCIe, no MBIST (`check_soc_corrpre_pcie_native_boot.sh`) | (the MBIST boot below is a superset) | **check 19 FAIL** (27 of 28 pass), section 3.4 | **pass**: 28 checks, fail mask 0, PCIe idle, 826,368 cycles, 5,911 s |
| native gate-level boot with system and Ethernet MBIST (`check_soc_corrpre_pcie_mbist_native_boot.sh`) | **pass**: 28 checks, fail mask 0, MBIST (983,043 cycles) and PCIe idle pass, 1,687,735 cycles, 16,273 s of the 18,000 s limit | not run (does not fit the wall clock at `MEM_RDREG=2`, `docs/ibex-execute-timing.md` 7.2) | not run |

The regressions are run42666896029. The RTL boot inside each native-boot and probe job (the same firmware and configuration) passes all 28 checks in every configuration.

### 3.3 riscv-formal

`docs/63`'s riscv-formal binding was run on the RVFI build of the core (upstream register file, `docs/63` phase 1), unpatched and with the execute stage. The patch applies to the RVFI tree too; there, the RVFI next PC (`rvfi_pc_wdata`) uses the same ID-stage PC as `mepc`. Two pre-existing obstacles had to be removed first. `hw/soc/rvformal/params.sh` read only literal parameter values, and since the execute-path knobs `soc_top` passes `BranchTargetALU` and `WritebackStage` as expressions, so setup stopped; the guard now evaluates them at `soc_top`'s defaults and still fails on a changed value. The `hang` bound became a knob, `RVF_HANG_DEPTH` (default 30).

The eight M-extension instruction checks and `liveness` were left out: `docs/63` section 8 found no verdict for six of them in 40 minutes each, `div`/`rem` fail against riscv-formal's own unsigned model, and `liveness` is bound by the 37-cycle divider.

| riscv-formal, boolector, run42668326127 | unpatched | execute stage |
|---|---|---|
| bounded checks run (62 instructions, `reg`, `pc_fwd`, `pc_bwd`, `causal`, `unique`, `hang`, `ill`, `cover`) | 70 of 70 PASS | **69 PASS, `hang` FAIL at check cycle 30** |
| cover jobs (the same 70: each check is reachable) | 70 of 70 PASS | 70 of 70 PASS |
| job-seconds, bounded / cover | 6,318 / 1,375 | 8,187 / 1,024 |
| `hang` at check cycles 26-40 (run42679133761) | FAIL at 26, PASS at 28-40 | FAIL at 26-30, **PASS at 32-40** |

Every instruction check and every consistency check that held on the pinned core holds on the patched one: register file (`reg`), PC continuity in both directions (`pc_fwd`, `pc_bwd`), causality, unique retirement order, and the all-zero instruction trap. `hang` asserts that some instruction retires within the bound from reset, under arbitrary interrupts, debug requests and bus delays. The counterexample at cycle 30 takes two interrupts during the first fetches before a store reaches EX; every redirect costs the extra stage one cycle before an instruction can execute. The pinned core passes from 28 (it fails at 26), the patched one from 32 (it fails at 30), so the bound moves by three to five cycles. This is a latency bound, not a deadlock: the same check passes from cycle 32 on, and `test_interrupt_at_every_cycle` above shows forward progress under interrupts at every offset.

### 3.4 The one gate-level failure

The native gate-level boot of the execute stage with `CHKDEFER`, predecode and `MEM_RDREG=2` (no two-cycle branches) fails check 19 and nothing else; the log shows the right vector and cause (`gptimer cfg=0x00000043 cause=0x80000013 vec=0x00000013`). The RTL boot of the same netlist's configuration passes all 28 checks, and the same knobs with two-cycle branches pass at gate level. Check 19 starts GPTIMER timer 1 periodic (41 ticks of a 4-cycle prescaler, one wrap every 164 cycles), takes the interrupt, and then stops the timer and clears its pending bit with one write, `GPT_CTRL(1) = GPT_IP`, and reads the bit back. `soc_gptimer.v` sets the pending bit when a wrap falls in the same cycle as that write ("the wrap wins"). The time from the first wrap to the clearing write is the interrupt entry, the handler and about twenty instructions of the test, which in this configuration (three-cycle memory, one more pipeline stage) is about one timer period. The gate-level boot is not cycle-identical to the RTL boot (it runs about 2,400 cycles longer in every configuration), so the interrupt lands at a different point of the spin loop, and a shift of a few cycles is enough to put the write on the second wrap. This is the most likely explanation, but the log does not say which of the check's terms failed, and it was not confirmed with a trace of the timer; that, and a rerun after the fix below, are the open items. A firmware change that makes the check independent of the timer phase, stopping the timer with one write and clearing the bit with a second, is the obvious fix; it does not change the synthesised netlist, because the application is loaded from flash.

### 3.5 Check 19: the race, and the firmware fix

Reading the firmware and the timer RTL confirms the race of section 3.4; it is a property of the check, not of the netlist.

- `hw/soc/rtl/soc_gptimer.v` lines 292-301: a control write sets `t_en` from the written EN bit, and in the same cycle `if (t_wrap[n]) t_ip[n] <= 1'b1; else if (pwdata_i[B_IP]) t_ip[n] <= 1'b0;`. `t_wrap` (line 188) is `t_en && t_src && (cnt == 0)` on the registered EN, so the write that stops the timer does not stop a wrap in its own cycle, and that wrap wins over the clear. From the next cycle on EN is 0 and nothing sets IP again.
- `hw/soc/tb/sw/test_ibex.c` (check 19, before the fix): the timer runs periodic (`GPT_SCRELOAD = 3`, `GPT_RLD(1) = 40`: one wrap every 4 x 41 = 164 cycles), the handler (`crt0.S` `irq_common`, lines 245-267) only masks the source in `mie` and leaves IP set, and the check then writes `GPT_CTRL(1) = GPT_IP` (EN = 0, IP = 1) to the running timer and requires IP to read back 0. If that write's APB access cycle is a wrap cycle, IP reads back 1 and the check fails. One cycle in every 164 fails, and which cycle the write lands on is set by the latency of everything between the timer start and the write.
- The failure message rules out the other terms: `cfg`, `cause` and `vec` are right, `irq_marker` was zeroed before the check so the handler ran in it, the handler masks the line so `irq_count` cannot advance twice, and 20,000 spin iterations is far above one 164-cycle period. The IP read-back is the only term that depends on the timer phase.

The fix (`test_ibex.c`, check 19) splits the write. `GPT_CTRL(1) = 0` stops the timer and clears nothing (a wrap in that cycle may set IP, which is harmless), then `GPT_CTRL(1) = GPT_IP` clears IP while EN is already 0, so no wrap can coincide with it, and the read-back is unchanged. APB transfers complete in order (`soc_apb_bridge.v` takes one request at a time), so the clear always follows the stop. The check's terms and its intent (the fast-interrupt vector and cause, the configuration register, IP is write-one-to-clear, the timer is left stopped) are unchanged, and so is `soc_gptimer.v`'s same-cycle priority. The firmware is the application loaded from flash, so no synthesised netlist and no boot ROM image changes. The open item is the rerun of the native gate-level boot of section 3.4 with the fixed firmware.

## 4. Cycle cost

Cycles to "core asleep" at the end of the boot firmware. The native-boot configuration is the one the probes boot (logic boot ROM, SRAM RAM, hardened memories); `make soc-sim` is the default regression configuration.

| Configuration | native-boot configuration | change | `make soc-sim` | change |
|---|---:|---:|---:|---:|
| control | 647,591 | | 430,231 | |
| execute stage | 700,326 | **+8.1%** | 475,721 | **+10.6%** |
| `CHKDEFER` + predecode + `MEM_RDREG=2` (`docs/ibex-execute-timing.md`) | 763,279 | +17.9% | 643,201 | +49.5% (the `soc-sim` control reads memory with `RDREG=0`) |
| the same + execute stage | 823,694 | +7.9% over that | 695,938 | +8.2% over that |
| the same + execute stage + two-cycle branches | 823,927 | +233 cycles | 696,073 | +135 cycles |

The execute stage costs about 8-11% of the cycles: every taken branch, jump and trap refills one more stage, CSR instructions wait for the ID-stage handover gate, and nothing else stalls. Load use, multiply/divide results and CSR reads are forwarded and cost nothing. The area cost is 2,152 µm² (+0.13% of `soc_top`, 1,619,527 → 1,621,679 µm² after synthesis). The new registers are at most about 200 flip-flops (instruction and its ALU copy, PC, flags, two operands); constant fields are removed by synthesis.


## 5. Timing

Density 70%, Kogge-Stone (`SOC_SYNTH_PREFIX_ADDER=1`), global-route parasitics, the flow's capped repair and then `repair_timing` bounded at 1100 iterations on the same database, the recipe of `docs/ibex-execute-timing.md` sections 5 and 7.3 (run42666896029; the reruns with net names, run42695115718 and run42695101874, reproduce the numbers exactly). `clk_i` setup worst slack in ns:

| Variant | Capped repair (slow) | After 1100-iteration repair: slow / typ / fast |
|---|---:|---|
| control | -8.57 | -5.84 / 3.90 / 8.03 |
| **execute stage** | -6.07 | **-5.25** / 4.06 / 9.46 |
| `CHKDEFER` + predecode + `MEM_RDREG=2` (section 7.3 of the earlier document) | -9.90 | -5.45 / 4.01 / 9.52 |
| the same + two-cycle branches (the earlier best) | -10.30 | -4.90 / 4.39 / 8.74 |
| **execute stage + `CHKDEFER` + predecode + `MEM_RDREG=2`** | -4.40 | **-4.40** / 4.65 / 9.63 |
| **the same + two-cycle branches** | -5.67 | **-5.67** / 3.87 / 8.55 |

- The execute stage alone gains 0.6 ns at the slow corner; with the register-file and memory knobs it gives **-4.40 ns, the best so far** (+1.44 over the control, +0.50 over the earlier best). Typical (+3.9 to +4.7 ns) and fast (+8.6 to +9.6 ns) close with margin in every variant.
- The flow's own capped repair now does almost all of the work: in the two knob variants the 1100 extra iterations leave `clk_i` exactly where the flow left it and are spent on the asynchronous and `pcie_clk_i` groups, which are now the worst groups (-5.48 and -5.89 ns with the knobs, -5.81 and -5.87 with two-cycle branches).
- **The register-file read is no longer on the worst path.** With the knobs, the ten worst `clk_i` endpoints are the fabric's request register (`s_addr[*]`, `u_bus.g_req_reg.r_tgt`) and the NPU's synapse memory (`u_npu.u_node0.u_lif.smem[*]`, from `ev_axon_r`, -3.75 to -3.83 ns). The worst path starts at the new EX-stage valid flop (`exs_ex_valid_q`): the LSU request and operand select (to 7.8 ns), the address adder (to 15.7 ns), the PMP check of that address and the gated data request (to 21.7 ns), and then the fabric's arbitration select fanning out to the request register's multiplexers (to 26.5 ns, against 22.1 ns required). This is the LSU/PMP/fabric class that `docs/ibex-execute-timing.md` section 6 listed third. The execute stage removed the register-file read from it (the adder now starts from a flop), and what is left is about 24 ns of logic between two flops.
- With two-cycle branches added, the worst path is the same class: it starts at the EX-stage instruction (`exs_ex_instr_rdata_alu_id_q[5]`, the opcode bit that tells loads from stores) and ends at the same request register (`s_addr`, `s_be`, `s_we`, `s_wdata`, the ten worst all there), 27.8 ns arrival. Two-cycle branches cut a cone (branch decision to the ID/EX stall) that is no longer critical, and the 1.3 ns between the two knob variants is most likely placement and repair variation on two different netlists of the same logic class, larger than the 0.4 ns the earlier document measured between logically identical netlists.

## 6. Remaining gap

With the execute stage and the earlier knobs, slow-corner `clk_i` is -4.40 ns, i.e. about 24.4 ns of a 20 ns period. What is left, in the order the measurements rank it:

1. **`pcie_clk_i` (-5.9 ns) and the asynchronous group (-5.5 to -5.8 ns)** are now worse than `clk_i`. They are outside the core and outside this branch.
2. **LSU address to the fabric request register** (`clk_i`, -4.40 ns): EX-stage control, address adder, PMP check, PMP-gated request, arbitration select, request-register multiplexers. Cutting it needs the data request to leave the core from a register: either the PMP check one cycle later (option F of `docs/ibex-execute-timing.md`, +1 cycle on every load and store), or an arbitration in `soc_bus` that does not select on the PMP-gated request in the same cycle.
3. **The NPU synapse-memory update** (`clk_i`, -3.8 ns), independent of the core.

The core's own loops (operand register, ALU, result, forwarding multiplexer, operand register; and ALU, result, write to the register file) are not among the ten worst `clk_i` paths of the best variant, so a deeper core pipeline is not the next step. A relaxed slow-corner period is not this branch's call.
