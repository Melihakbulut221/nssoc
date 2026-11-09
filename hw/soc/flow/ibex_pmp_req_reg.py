# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Register the data request, with its PMP verdict, at the core boundary.

    ibex_pmp_req_reg.py <in_dir> <out_dir>

Reads <in_dir>/ibex_core.v and writes <out_dir>/ibex_core.v. <in_dir> is
the sv2v output of the pinned Ibex or the output of any of the earlier
ibex_core.v patches (flow/ibex_rf_predecode.py, flow/ibex_ex_stage.py);
this patch touches only the load/store unit's bus connections and the
data-side PMP inputs, which those patches leave alone. It never writes
to its input. flow/ibex_sources.sh calls it when IBEX_PMP_REQ_REG=1 and
substitutes the output.

WHY

With the separate execute stage and the register-file and memory knobs,
the worst slow-corner clk_i path is: EX-stage control, LSU request and
operand select, address adder, data-side PMP check of that address, the
PMP-gated request (data_req_o = data_req_out & ~pmp_req_err[PMP_D]),
the fabric's arbitration select (soc_bus d_wins, which depends on that
request) and the request register's 70 multiplexers (s_addr, s_be, s_we,
s_wdata). docs/ibex-ex-stage.md section 5: 26.5 ns arrival against
22.1 ns required, of which the arbitration and the request-register
multiplexers are the last 4.8 ns. Nothing outside the core can cut it:
the request soc_bus selects on is already PMP-gated when it leaves the
core, and soc_req_pipe (CORE_REQ_REG) grants combinationally on it.

DESIGN

A one-entry request register between the load/store unit and the core's
data port, inside ibex_core:

  * The LSU's request is taken UNGATED. The register accepts it whenever
    it is empty: the LSU's grant is data_req_out & ~valid, which depends
    on the LSU's own request and one flip-flop, not on the address adder,
    the PMP or the fabric.
  * In the accepting cycle the register stores address, write enable,
    byte enables, write data and tag, and sets valid to the PMP verdict
    of that request: valid <= ~pmp_req_err[PMP_D]. A request the PMP
    refuses is dropped there and never reaches the port.
  * From the next cycle on the port presents the registered request
    (data_req_o = valid) and holds it until data_gnt_i. Responses
    (data_rvalid_i, data_err_i, data_rdata_i) go to the LSU unchanged.

The LSU itself is unchanged and still receives the same combinational
PMP verdict (data_pmp_err_i) in the cycle its request is granted; it
latches it into pmp_err_q exactly as before and answers a refused access
from that flip-flop, never from the bus. What the LSU sees differently
is only legal bus behaviour: a grant whenever the register is empty, a
response at least one cycle after the register forwards the request, and
a grant (instead of no grant) for a PMP-refused request. Every access
starts in IDLE with the register empty and is granted at once; the second
half of a misaligned access (issued from WAIT_RVALID_MIS) waits only while
the first half is still in the register, and the first response cannot
arrive before the register has passed that half on. So WAIT_GNT and
WAIT_GNT_MIS are never entered. In the states that are, the LSU takes each
half's verdict into pmp_err_q (IDLE and WAIT_RVALID_MIS with the grant,
WAIT_RVALID_MIS_GNTS_DONE for a second half granted before the first
response) and answers a refused access from it.

PRECISE EXCEPTIONS

A refused access is dropped before the port, so a refused store writes
nothing and a refused load reaches no slave (no read side effect). The
LSU reports the fault through lsu_resp_valid with load_err/store_err as
before, so the exception is taken on the same instruction with the same
mcause and the same mtval (addr_last). Misaligned accesses keep the
pinned core's behaviour half by half: each half is accepted, checked and
dropped or issued on its own, and the LSU decides which halves it issues
exactly as before.

COST

Every load and store, and each half of a misaligned one, reaches the bus
one cycle later, so every data access is one cycle longer. The register
is about 70 flip-flops plus the valid bit.

WHAT IS LEFT ON THE PATH

The address adder and the PMP check still run in the cycle of the
request: they now end at the valid flip-flop's D input and at the LSU's
existing pmp_err_q, which is the path the pinned core already has into
pmp_err_q. Cutting that too needs the PMP check to run from the
registered address, which changes how the fault is reported to the LSU
(docs/ibex-ex-stage.md section 7).

UNSUPPORTED CONFIGURATIONS

WritebackStage = 1 (the next access may then be issued before the
previous response, which the argument above excludes)
and the CHERIoT base ISA (capability accesses, BaseIsa = 1) are not
covered by this patch or its tests. In those configurations an undeclared
module, ibex_pmp_req_reg_unsupported_configuration, is instantiated, so
elaboration stops in every tool.

WITNESS

The register is inside a named generate block, g_pmp_req_reg, which the
simulation flow asserts. Every anchor must occur exactly once, and after
the patch the core's data-port names may appear nowhere but in their
declarations and in the new block.
"""
import pathlib
import re
import sys

FILE = "ibex_core.v"
MARK = "g_pmp_req_reg"

# LSU port -> (core net it drove or read, new internal net, width).
LSU_PORTS = [
    ("data_gnt_i", "data_gnt_i", "pmq_lsu_gnt", ""),
    ("data_addr_o", "data_addr_o", "pmq_lsu_addr", "[31:0] "),
    ("data_we_o", "data_we_o", "pmq_lsu_we", ""),
    ("data_be_o", "data_be_o", "pmq_lsu_be", "[3:0] "),
    ("data_wdata_o", "data_wdata_o", "pmq_lsu_wdata", "[MemDataWidth - 1:0] "),
    ("data_tag_o", "data_tag_o", "pmq_lsu_tag", ""),
]
PORT_NAMES = ["data_req_o", "data_gnt_i", "data_addr_o", "data_we_o", "data_be_o",
              "data_wdata_o", "data_tag_o"]
GATE = "\tassign data_req_o = data_req_out & ~pmp_req_err[ibex_pkg_PMP_D];\n"
PMP_ADDR = "{2'b00, data_addr_o[31:0]}"
PMP_TYPE = "(data_we_o ? 2'b01 : 2'b10)"


def _fail(msg):
    raise SystemExit("ibex_pmp_req_reg.py: " + msg + "\nThe pinned Ibex has moved under "
                     "this patch; do NOT relax the anchor.")


def _once(text, needle, what):
    n = text.count(needle)
    if n != 1:
        _fail("anchor for {} occurs {} times in {}, expected exactly once.\n  anchor: {!r}"
              .format(what, n, FILE, needle))


def patch(text):
    if MARK in text:
        raise SystemExit(FILE + " is already patched")

    # 1. The PMP no longer gates the port; the request register does.
    _once(text, GATE, "the PMP-gated data request")
    inst = "\tibex_load_store_unit #(\n"
    _once(text, inst, "the load/store unit instance")
    if text.index(GATE) > text.index(inst):
        _fail("the PMP-gated request is not before the load/store unit instance")

    # 2. The LSU's bus side becomes internal nets.
    start = text.index(inst)
    end = text.index("\n\t);\n", start)
    lsu = text[start:end]
    if lsu.count("\t\t.data_req_o(data_req_out),\n") != 1:
        _fail("the LSU request is not connected to data_req_out")
    for port, net, new, _ in LSU_PORTS:
        old = "\t\t.%s(%s),\n" % (port, net)
        if lsu.count(old) != 1:
            _fail("LSU connection %r occurs %d times, expected once" % (old, lsu.count(old)))
        lsu = lsu.replace(old, "\t\t.%s(%s),\n" % (port, new))
    text = text[:start] + lsu + text[end:]

    # 3. The PMP checks the LSU's request, not the registered port.
    n = text.count(PMP_ADDR)
    if n not in (1, 2):
        _fail("the data-side PMP address occurs %d times, expected one or two "
              "(the CHERIoT and the plain arm)" % n)
    text = text.replace(PMP_ADDR, "{2'b00, pmq_lsu_addr[31:0]}")
    _once(text, PMP_TYPE, "the data-side PMP access type")
    text = text.replace(PMP_TYPE, "(pmq_lsu_we ? 2'b01 : 2'b10)")

    decl = ["\t// hw/soc/flow/ibex_pmp_req_reg.py: the LSU's bus side, before the",
            "\t// data request register."]
    decl += ["\twire %s%s;" % (w, new) for _, _, new, w in LSU_PORTS]
    text = text.replace(GATE, "\n".join(decl) + "\n")

    # Nothing else of the core may read the data port (port names of
    # submodule connections, ".name(", do not count): the RVFI tree, for
    # one, would need its own treatment.
    body_start = text.index(");\n") + 3   # after the port list
    for name in PORT_NAMES:
        uses = [m.start() for m in re.finditer(r"(?<!\.)\b%s\b" % name, text[body_start:])]
        decl = re.findall(r"\n\t(?:input|output) wire (?:\[[^\]]+\] )?%s;" % name, text)
        if len(decl) != 1 or len(uses) != 1:
            _fail("%s is used %d times outside its declaration" % (name, len(uses) - 1))

    block = """
	// hw/soc/flow/ibex_pmp_req_reg.py: the data request register. The LSU's
	// ungated request is accepted whenever the register is empty, stored
	// with the PMP verdict of its address, and presented to the port from
	// the next cycle; a request the PMP refuses is dropped here.
	generate
		if (WritebackStage || (BaseIsa == 32'sd1)) begin : g_pmp_req_reg_unsupported
			ibex_pmp_req_reg_unsupported_configuration u_unsupported();
		end
		if (1) begin : %(mark)s
			reg pmq_valid_q;
			reg [31:0] pmq_addr_q;
			reg pmq_we_q;
			reg [3:0] pmq_be_q;
			reg [MemDataWidth - 1:0] pmq_wdata_q;
			reg pmq_tag_q;
			assign pmq_lsu_gnt = data_req_out & ~pmq_valid_q;
			always @(posedge clk_i or negedge rst_ni)
				if (!rst_ni)
					pmq_valid_q <= 1'b0;
				else if (pmq_lsu_gnt)
					pmq_valid_q <= ~pmp_req_err[ibex_pkg_PMP_D];
				else if (pmq_valid_q & data_gnt_i)
					pmq_valid_q <= 1'b0;
			always @(posedge clk_i or negedge rst_ni)
				if (!rst_ni) begin
					pmq_addr_q <= 32'h00000000;
					pmq_we_q <= 1'b0;
					pmq_be_q <= 4'h0;
					pmq_wdata_q <= {MemDataWidth {1'b0}};
					pmq_tag_q <= 1'b0;
				end
				else if (pmq_lsu_gnt) begin
					pmq_addr_q <= pmq_lsu_addr;
					pmq_we_q <= pmq_lsu_we;
					pmq_be_q <= pmq_lsu_be;
					pmq_wdata_q <= pmq_lsu_wdata;
					pmq_tag_q <= pmq_lsu_tag;
				end
			assign data_req_o = pmq_valid_q;
			assign data_addr_o = pmq_addr_q;
			assign data_we_o = pmq_we_q;
			assign data_be_o = pmq_be_q;
			assign data_wdata_o = pmq_wdata_q;
			assign data_tag_o = pmq_tag_q;
		end
	endgenerate
""" % {"mark": MARK}
    _once(text, "\nendmodule", "the end of the module")
    return text.replace("\nendmodule", block + "endmodule")


def main(argv):
    if len(argv) != 3:
        raise SystemExit("usage: ibex_pmp_req_reg.py <in_dir> <out_dir>")
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
