# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Split Ibex's ID/EX stage: read the register file one stage earlier.

    ibex_ex_stage.py <gen_dir> <out_dir>

Reads <gen_dir>/ibex_core.v and writes <out_dir>/ibex_core.v. <gen_dir> is
the sv2v output of the pinned Ibex, or the output of
flow/ibex_rf_predecode.py when that knob is on as well; the patch applies
to both. It never writes to its input. flow/ibex_sources.sh calls it when
IBEX_EX_STAGE=1 and substitutes the output.

WHY

The pinned core (WritebackStage = 0) decodes, reads the register file and
executes in one stage. At the frozen slow corner the worst clk_i path is
register-file read, correction, operand multiplexer, ALU and then either
the result write or the stall/enable cone: about 27 ns of a 20 ns period
with every earlier cut applied (docs/ibex-execute-timing.md section 7).
No local cut removes the register-file read from that path; a pipeline
register between the read and the ALU does.

PIPELINE

  IF   prefetch buffer and compressed decoder (unchanged)
  ID   the IF/ID register of ibex_if_stage (unchanged). The register file
       is read here, addressed by rs1 = instr[19:15] and rs2 =
       instr[24:20] of the instruction in this register. That is exactly
       the address the pinned decoder already drives in this
       configuration, and the address flow/ibex_rf_predecode.py
       predecodes, so the register file and its RDPRE predecode see the
       same address source as before.
  EX   a new register, ID/EX, that holds the IF/ID fields the ID/EX logic
       consumes (instruction, PC, fetch-error and compressed flags) plus
       the two operands read in ID. Everything downstream (decoder,
       controller, ALU, multiplier/divider, LSU, CSRs) is unchanged and
       sees the ID/EX register where it used to see the IF/ID register.

The core's wires instr_valid_id, instr_rdata_id, pc_id, ... keep their
names and now carry the EX-stage instruction, so every consumer of them,
including crash_dump_o's PC and the CSR exception PC, refers to the
instruction being executed exactly as before.

HAZARDS

  * Read after write. The non-writeback core retires every register
    write of an instruction (ALU, CSR read, multiplier/divider result,
    load data) before the next instruction may enter EX. The only write
    the ID-stage read can miss is the one in the cycle in which the next
    instruction moves into EX, and that write is forwarded: rf_we_wb with
    rf_waddr_wb equal to the read address (and not x0) selects
    rf_wdata_wb, the exact value written to the register file, into the
    operand register. In every other cycle the ID stage re-reads the
    register file, so an earlier write is seen by the read itself. Load
    use, multiplier/divider results and CSR reads need no stall.
  * Operands are captured once, when the instruction enters EX, and held
    while it executes. Multi-cycle instructions (multiply, divide,
    misaligned load/store, two-cycle branches and jumps) use the values
    the instruction had when it was issued, which is the architectural
    definition.
  * Flush. pc_set (taken branch, jump, exception, interrupt, debug entry,
    mret/dret, fence.i, which Ibex implements as a jump) clears the ID
    stage together with whatever IF would deliver, and nothing enters EX
    in that cycle, exactly as the pinned IF stage does for its IF/ID
    register.
  * Precise interrupts and debug entry. The controller takes an
    interrupt or a debug request between instructions and saves pc_if
    as mepc/dpc (csr_save_if), i.e. the address of the next instruction
    not yet in EX. With the extra stage that instruction may be waiting
    in ID, so the CSR file's pc_if input is the ID-stage PC when the ID
    stage is valid and pc_if otherwise. The ID-stage instruction is then
    flushed by the same pc_set, and it is the first one fetched after
    mret/dret. crash_dump_o's next-PC field uses the same value.
  * WFI and pipeline-flushing CSR writes halt IF without pc_set. The
    instruction in ID stays there, like an instruction in the prefetch
    buffer, and enters EX when the controller resumes.
  * x0: a write with rf_waddr_wb = 0 is never forwarded.

The IF stage keeps its own interface. Its id_in_ready_i becomes "the ID
stage can take an instruction" (empty, or its instruction moves into EX)
and its instr_valid_clear_i becomes "the ID-stage instruction moved into
EX or was flushed".

UNSUPPORTED CONFIGURATIONS

WritebackStage = 1, BranchTargetALU = 1 and RegFileECC = 1 are not
covered by this patch or its tests. In those configurations an
undeclared module, ibex_ex_stage_unsupported_configuration, is
instantiated, so elaboration stops in every tool.

WITNESS AND CHECK

The new logic is inside a named generate block, g_ex_stage, which the
simulation flow asserts. In simulation (not under SYNTHESIS) a check
stops the run if the EX-stage decoder ever addresses the register file
with anything but instr[19:15]/instr[24:20] of its instruction, which is
the assumption that lets the ID stage read without decoding.

Every anchor must occur exactly once.
"""
import pathlib
import sys

FILE = "ibex_core.v"
MARK = "g_ex_stage"

# IF/ID outputs of ibex_if_stage that the ID/EX register re-times:
# (port, core wire, width, reset value). instr_valid_id and instr_new_id
# are handled separately.
FIELDS = [
    ("instr_rdata_id_o", "instr_rdata_id", 32, "32'h00000000"),
    ("instr_rdata_alu_id_o", "instr_rdata_alu_id", 32, "32'h00000000"),
    ("instr_rdata_c_id_o", "instr_rdata_c_id", 16, "16'h0000"),
    ("instr_is_compressed_id_o", "instr_is_compressed_id", 1, "1'b0"),
    ("instr_gets_expanded_id_o", "instr_gets_expanded_id", 2, "2'd0"),
    ("instr_expanded_id_o", "instr_expanded_id", 16, "16'h0000"),
    ("instr_bp_taken_o", "instr_bp_taken_id", 1, "1'b0"),
    ("instr_fetch_err_o", "instr_fetch_err", 1, "1'b0"),
    ("instr_fetch_err_plus2_o", "instr_fetch_err_plus2", 1, "1'b0"),
    ("instr_fetch_cheriot_acc_vio_o", "instr_fetch_cheriot_acc_vio", 1, "1'b0"),
    ("instr_fetch_cheriot_bound_vio_o", "instr_fetch_cheriot_bound_vio", 1, "1'b0"),
    ("illegal_c_insn_id_o", "illegal_c_insn_id", 1, "1'b0"),
    ("dummy_instr_id_o", "dummy_instr_id", 1, "1'b0"),
    ("pc_id_o", "pc_id", 32, "32'h00000000"),
]


def _once(text, needle, what):
    n = text.count(needle)
    if n != 1:
        raise SystemExit(
            "ibex_ex_stage.py: anchor for {} occurs {} times in {}, expected "
            "exactly once.\n  anchor: {!r}\nThe pinned Ibex has moved under "
            "this patch; do NOT relax the anchor.".format(what, n, FILE, needle))


def _rw(width):
    return "" if width == 1 else "[%d:0] " % (width - 1)


def _swap(text, old, new, what):
    _once(text, old, what)
    return text.replace(old, new)


def patch(text):
    if MARK in text:
        raise SystemExit(FILE + " is already patched")
    inst = "\tibex_if_stage #(\n"
    _once(text, inst, "the IF stage instance")
    start = text.index(inst)
    end = text.index("\n\t);\n", start)
    if_inst = text[start:end]

    # 1. The IF stage's IF/ID outputs become ID-stage wires.
    conns = [("instr_valid_id_o", "instr_valid_id"), ("instr_new_id_o", "instr_new_id")]
    conns += [(p, w) for p, w, _, _ in FIELDS]
    for port, wire in conns:
        old = "\t\t.%s(%s),\n" % (port, wire)
        n = if_inst.count(old)
        if n != 1:
            raise SystemExit("ibex_ex_stage.py: IF stage connection %r occurs %d "
                             "times, expected once" % (old, n))
        if_inst = if_inst.replace(old, "\t\t.%s(exs_id_%s),\n" % (port, wire))
    # 2. Its handshake with ID/EX becomes a handshake with the ID stage.
    for port, wire, new in [("instr_valid_clear_i", "instr_valid_clear", "exs_id_clear"),
                            ("id_in_ready_i", "id_in_ready", "exs_id_ready")]:
        old = "\t\t.%s(%s),\n" % (port, wire)
        if if_inst.count(old) != 1:
            raise SystemExit("ibex_ex_stage.py: IF stage connection %r not found once" % old)
        if_inst = if_inst.replace(old, "\t\t.%s(%s),\n" % (port, new))
    text = text[:start] + if_inst + text[end:]

    # 3. Register-file read address from the ID stage; operands from ID/EX.
    text = _swap(text, "\tassign rf_raddr_a_o = rf_raddr_a;\n",
                 "\tassign rf_raddr_a_o = exs_id_raddr_a;\n", "the read address A")
    text = _swap(text, "\tassign rf_raddr_b_o = rf_raddr_b;\n",
                 "\tassign rf_raddr_b_o = exs_id_raddr_b;\n", "the read address B")
    rda = "\t\t\tassign rf_rdata_a = rf_rdata_a_ecc_i;\n"
    rdb = "\t\t\tassign rf_rdata_b = rf_rdata_b_ecc_i;\n"
    _once(text, rda, "the read data A without register-file ECC")
    _once(text, rdb, "the read data B without register-file ECC")
    at = text.index(rda)
    arm = text.rfind("begin : gen_no_regfile_ecc", 0, at)
    if arm < 0 or text.rfind("begin : gen_", arm + 1, at) >= 0:
        raise SystemExit(FILE + ": the read data assignment is not in gen_no_regfile_ecc")
    text = text.replace(rda, "\t\t\tassign rf_rdata_a = exs_ex_op_a_q;\n")
    text = text.replace(rdb, "\t\t\tassign rf_rdata_b = exs_ex_op_b_q;\n")

    # 4. The PC of the next instruction not yet in EX, for mepc/dpc and the
    #    crash dump.
    text = _swap(text, "\t\t.pc_if_i(pc_if),\n", "\t\t.pc_if_i(exs_pc_next),\n",
                 "the CSR file's IF PC")
    text = _swap(text, "\tassign crash_dump_o[127-:32] = pc_if;\n",
                 "\tassign crash_dump_o[127-:32] = exs_pc_next;\n", "the crash dump next PC")

    # 5. Declarations before the IF stage, logic at the end of the module.
    decl = ["\t// hw/soc/flow/ibex_ex_stage.py: ID-stage (IF/ID register) outputs",
            "\t// of the IF stage, and the ID/EX handshake.",
            "\twire exs_id_instr_valid_id;", "\twire exs_id_instr_new_id;"]
    decl += ["\twire %sexs_id_%s;" % (_rw(w), wire) for _, wire, w, _ in FIELDS]
    decl += ["\twire exs_id_ready;", "\twire exs_id_clear;", "\twire exs_ex_we;",
             "\twire [4:0] exs_id_raddr_a;", "\twire [4:0] exs_id_raddr_b;",
             "\twire [31:0] exs_pc_next;", "\treg [31:0] exs_ex_op_a_q;",
             "\treg [31:0] exs_ex_op_b_q;", ""]
    text = text.replace(inst, "\n".join(decl) + "\n" + inst)

    regs = "\n".join("\t\t\treg %sexs_ex_%s_q;" % (_rw(w), wire) for _, wire, w, _ in FIELDS)
    rst = "\n".join("\t\t\t\t\texs_ex_%s_q <= %s;" % (wire, rv) for _, wire, _, rv in FIELDS)
    upd = "\n".join("\t\t\t\t\t\texs_ex_%s_q <= exs_id_%s;" % (wire, wire)
                    for _, wire, _, _ in FIELDS)
    outs = "\n".join("\t\t\tassign %s = exs_ex_%s_q;" % (wire, wire) for _, wire, _, _ in FIELDS)
    body = """
	// hw/soc/flow/ibex_ex_stage.py: the ID/EX register. The register file
	// is read in ID, from the IF/ID instruction, and the operands enter EX
	// with the instruction. A write in the cycle the instruction moves into
	// EX is forwarded from the write port.
	generate
		if (WritebackStage || BranchTargetALU || RegFileECC) begin : g_ex_stage_unsupported
			ibex_ex_stage_unsupported_configuration u_unsupported();
		end
		if (1) begin : %(mark)s
			reg exs_ex_valid_q;
			reg exs_ex_new_q;
%(regs)s
			wire exs_fwd_a;
			wire exs_fwd_b;
			assign exs_id_raddr_a = exs_id_instr_rdata_id[19:15];
			assign exs_id_raddr_b = exs_id_instr_rdata_id[24:20];
			// The ID-stage instruction moves into EX when EX accepts one and
			// the fetch is not being redirected (pinned IF/ID rule).
			assign exs_ex_we = (exs_id_instr_valid_id & id_in_ready) & ~pc_set;
			assign exs_id_ready = ~exs_id_instr_valid_id | exs_ex_we;
			assign exs_id_clear = exs_ex_we | pc_set;
			assign exs_pc_next = (exs_id_instr_valid_id ? exs_id_pc_id : pc_if);
			assign exs_fwd_a = (rf_we_wb & (rf_waddr_wb == exs_id_raddr_a)) & (exs_id_raddr_a != 5'd0);
			assign exs_fwd_b = (rf_we_wb & (rf_waddr_wb == exs_id_raddr_b)) & (exs_id_raddr_b != 5'd0);
			always @(posedge clk_i or negedge rst_ni)
				if (!rst_ni) begin
					exs_ex_valid_q <= 1'b0;
					exs_ex_new_q <= 1'b0;
%(rst)s
					exs_ex_op_a_q <= 32'h00000000;
					exs_ex_op_b_q <= 32'h00000000;
				end
				else begin
					exs_ex_valid_q <= exs_ex_we | (exs_ex_valid_q & ~instr_valid_clear);
					exs_ex_new_q <= exs_ex_we;
					if (exs_ex_we) begin
%(upd)s
						exs_ex_op_a_q <= (exs_fwd_a ? rf_wdata_wb : rf_rdata_a_ecc_i[31:0]);
						exs_ex_op_b_q <= (exs_fwd_b ? rf_wdata_wb : rf_rdata_b_ecc_i[31:0]);
					end
				end
			assign instr_valid_id = exs_ex_valid_q;
			assign instr_new_id = exs_ex_new_q;
%(outs)s
`ifndef SYNTHESIS
			// The ID stage reads without decoding: rs1/rs2 are fixed fields
			// of the instruction. Stop if the EX-stage decoder ever addresses
			// the register file differently.
			always @(posedge clk_i)
				if ((rst_ni && exs_ex_valid_q) && ((rf_raddr_a !== exs_ex_instr_rdata_id_q[19:15]) || (rf_raddr_b !== exs_ex_instr_rdata_id_q[24:20]))) begin
					$display("ibex_ex_stage: decoder read address %%0d/%%0d differs from instr[19:15]/[24:20] of %%h", rf_raddr_a, rf_raddr_b, exs_ex_instr_rdata_id_q);
					$fatal(1, "ibex_ex_stage read-address assumption violated");
				end
`endif
		end
	endgenerate
""" % {"mark": MARK, "regs": regs, "rst": rst, "upd": upd, "outs": outs}
    _once(text, "\nendmodule", "the end of the module")
    text = text.replace("\nendmodule", body + "endmodule")
    return text


def main(argv):
    if len(argv) != 3:
        raise SystemExit("usage: ibex_ex_stage.py <gen_dir> <out_dir>")
    src = pathlib.Path(argv[1]) / FILE
    if not src.is_file():
        raise SystemExit("%s does not exist: run hw/soc/flow/sv2v_ibex.sh first" % src)
    out = pathlib.Path(argv[2])
    out.mkdir(parents=True, exist_ok=True)
    dst = out / FILE
    dst.write_text(patch(src.read_text()))
    print("wrote %s" % dst)


if __name__ == "__main__":
    main(sys.argv)
