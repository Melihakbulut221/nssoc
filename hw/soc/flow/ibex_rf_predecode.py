# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Register a predecoded register-file read address beside Ibex's IF/ID register.

    ibex_rf_predecode.py <gen_dir> <out_dir>

Reads <gen_dir>/ibex_if_stage.v and <gen_dir>/ibex_core.v (the sv2v output
of the pinned Ibex) and writes patched copies to <out_dir>. It never
writes to its input. flow/ibex_sources.sh calls it when
IBEX_RF_PREDECODE=1 and substitutes both files.

WHY

The register file's read address is a slice of the IF/ID instruction
register (ibex_decoder: rf_raddr_a_o = instr_rdata_id[19:15], rf_raddr_b_o
= instr_rdata_id[24:20] in this configuration). Decoding five address bits
into 32 word selects for two 32:1 multiplexers is a fanout problem: the
slow-corner paths in docs/ibex-execute-timing.md spend 4.8-6.3 ns in
buffer trees between those flip-flops and the multiplexers.

The decode can be done one cycle earlier, from the value that is about to
be registered (instr_out), and registered with the same enable. The
result is the same function of the same register, so it is the decode of
rf_raddr_*_o in every cycle. hw/soc/rtl/ibex_regfile_secded.v (RDPRE = 1)
uses it and, in simulation, asserts that it equals the decode of raddr.

WHAT IT CHANGES

  ibex_if_stage.v  one 24-bit output, rf_raddr_pre_id_o, registered in
                   both IF/ID register variants (ResetAll or not) beside
                   instr_rdata_id_o: {onehot(rs2[2:0]), onehot(rs2[4:3]),
                   onehot(rs1[2:0]), onehot(rs1[4:3])}. Its reset value is
                   the predecode of the zero instruction, as
                   instr_rdata_id_o's is zero.
  ibex_core.v      connects it and drives rf_wcap_ecc_wb_o (the
                   capability write data, unused at BaseIsa = 0, which
                   ibex_top already wires to the register file's
                   wcap_a_i) with it, zero-extended, in the
                   gen_no_regfile_ecc arm that this configuration
                   elaborates.

No port is added to ibex_top or to the register file. Every anchor must
occur exactly once.
"""
import pathlib
import sys

PRE_D = ("{(8'd1 << instr_out[22:20]), (4'd1 << instr_out[24:23]), "
         "(8'd1 << instr_out[17:15]), (4'd1 << instr_out[19:18])}")
PRE_RST = "24'h011011"


def _once(text, needle, what, name):
    n = text.count(needle)
    if n != 1:
        raise SystemExit(
            "ibex_rf_predecode.py: anchor for {} occurs {} times in {}, "
            "expected exactly once.\n  anchor: {!r}\nThe pinned Ibex has "
            "moved under this patch; do NOT relax the anchor.".format(
                what, n, name, needle))


def _all(text, needle, count, what, name):
    n = text.count(needle)
    if n != count:
        raise SystemExit(
            "ibex_rf_predecode.py: anchor for {} occurs {} times in {}, "
            "expected {}.\n  anchor: {!r}".format(what, n, name, count, needle))


def patch_if_stage(text):
    name = "ibex_if_stage.v"
    if "rf_raddr_pre_id_o" in text:
        raise SystemExit(name + " is already patched")
    port = "\tinstr_rdata_id_o,\n"
    decl = "\toutput reg [31:0] instr_rdata_id_o;\n"
    rst = "\t\t\t\t\tinstr_rdata_id_o <= 1'sb0;\n"
    upd = "\t\t\t\t\tinstr_rdata_id_o <= instr_out;\n"
    _once(text, port, "the port list entry", name)
    _once(text, decl, "the port declaration", name)
    _once(text, rst, "the reset assignment", name)
    _all(text, upd, 2, "the IF/ID register update", name)
    _once(text, "\nendmodule", "the end of the module", name)
    text = text.replace(port, port + "\trf_raddr_pre_id_o,\n")
    text = text.replace(
        decl, decl
        + "\t// hw/soc/flow/ibex_rf_predecode.py: register-file read address,\n"
          "\t// predecoded and registered beside instr_rdata_id_o.\n"
          "\toutput reg [23:0] rf_raddr_pre_id_o;\n"
          "\twire [23:0] rf_raddr_pre_d;\n")
    text = text.replace(rst, rst + "\t\t\t\t\trf_raddr_pre_id_o <= %s;\n" % PRE_RST)
    text = text.replace(upd, upd + "\t\t\t\t\trf_raddr_pre_id_o <= rf_raddr_pre_d;\n")
    text = text.replace(
        "\nendmodule",
        "\n\tassign rf_raddr_pre_d = %s;\nendmodule" % PRE_D)
    return text


def patch_core(text):
    name = "ibex_core.v"
    if "rf_raddr_pre_id" in text:
        raise SystemExit(name + " is already patched")
    inst = "\tibex_if_stage #(\n"
    conn = "\t\t.instr_rdata_id_o(instr_rdata_id),\n"
    wcap = ("\t\t\tassign rf_wcap_ecc_wb_o = "
            "ibex_cheriot_pkg_cheriot_regcap_to_vec(rf_wcap_wb);\n")
    _once(text, inst, "the IF stage instance", name)
    _once(text, conn, "the IF stage instruction connection", name)
    _once(text, wcap, "the capability write data without register-file ECC", name)
    at = text.index(wcap)
    arm = text.rfind("begin : gen_no_regfile_ecc", 0, at)
    if arm < 0 or text.rfind("begin : gen_", arm + 1, at) >= 0:
        raise SystemExit(name + ": the capability assignment is not in gen_no_regfile_ecc")
    text = text.replace(inst, "\twire [23:0] rf_raddr_pre_id;\n" + inst)
    text = text.replace(conn, conn + "\t\t.rf_raddr_pre_id_o(rf_raddr_pre_id),\n")
    text = text.replace(
        wcap,
        "\t\t\t// hw/soc/flow/ibex_rf_predecode.py: the predecoded read\n"
        "\t\t\t// address rides the unused capability write data.\n"
        "\t\t\tassign rf_wcap_ecc_wb_o = {{(RegFileCapEccWidth - 24) {1'b0}}, "
        "rf_raddr_pre_id};\n"
        "\t\t\twire [RegFileCapEccWidth - 1:0] unused_rf_wcap_pre = "
        "ibex_cheriot_pkg_cheriot_regcap_to_vec(rf_wcap_wb);\n")
    return text


def main(argv):
    if len(argv) != 3:
        raise SystemExit("usage: ibex_rf_predecode.py <gen_dir> <out_dir>")
    gen = pathlib.Path(argv[1])
    out = pathlib.Path(argv[2])
    for f in ("ibex_if_stage.v", "ibex_core.v"):
        if not (gen / f).is_file():
            raise SystemExit("%s does not exist: run hw/soc/flow/sv2v_ibex.sh first"
                             % (gen / f))
    out.mkdir(parents=True, exist_ok=True)
    (out / "ibex_if_stage.v").write_text(
        patch_if_stage((gen / "ibex_if_stage.v").read_text()))
    (out / "ibex_core.v").write_text(patch_core((gen / "ibex_core.v").read_text()))
    print("wrote %s/ibex_if_stage.v and ibex_core.v" % out)


if __name__ == "__main__":
    main(sys.argv)
