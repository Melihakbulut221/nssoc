# A separate execute stage for the pinned Ibex

Branch `timing/ibex-ex-stage`, based on `timing/ibex-execute`. Frozen constraints, unchanged here: `clk_i` 20 ns, corner `nom_slow_1p08V_125C` with 5% derate, the physical SDC and every acceptance threshold. Nothing under `hw/soc/rtl/pcie/` is touched.

Starting point (`docs/ibex-execute-timing.md` section 7): with every project-owned cut (`CHKDEFER`, the predecoded read address, `SOC_MEM_RDREG=2`) and two-cycle branches, slow-corner `clk_i` is -4.90 ns after the 1100-iteration repair. The worst path is register-file read, operand multiplexer, ALU and then the result or the stall cone: 57 cells, 26.9 ns arrival against about 22.0 ns required. The pinned core decodes, reads the register file and executes in one stage, so no local cut removes the read from that path. Option G of that document, a separate execute stage, is what this branch implements.

## 1. Summary

@@SUMMARY@@

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

### 2.2 The default build is unchanged

At `IBEX_EX_STAGE=0` (or unset) `ibex_sources` lists exactly the files it listed before; `test_default_sources_are_unpatched` checks that. @@HASH@@

## 3. Tests

@@TESTS@@

## 4. Cycle cost

@@CYCLES@@

## 5. Timing

@@TIMING@@

## 6. Remaining gap

@@GAP@@
