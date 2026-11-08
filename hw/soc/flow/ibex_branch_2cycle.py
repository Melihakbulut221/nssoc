# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Make every conditional branch of Ibex take two cycles.

    ibex_branch_2cycle.py <gen_dir> <out_dir>

Reads <gen_dir>/ibex_id_stage.v (the sv2v output of the pinned Ibex) and
writes <out_dir>/ibex_id_stage.v. It never writes to its input, so
hw/soc/ext/ibex stays pristine and hw/soc/gen stays exactly what
flow/sv2v_ibex.sh produced. flow/ibex_sources.sh calls it when
IBEX_BRANCH_2CYCLE=1 and substitutes the output for the generated file.

WHY

At BranchTargetALU = 0 the ID/EX FSM of ibex_id_stage.sv decides in the
FIRST cycle of a conditional branch whether to stall:

    id_fsm_d     = (data_ind_timing_i || (!BranchTargetALU && branch_decision_i))
                   ? MULTI_CYCLE : FIRST_CYCLE;
    stall_branch = (~BranchTargetALU & branch_decision_i) | data_ind_timing_i;

`branch_decision_i` is the ALU comparison of the two register-file
operands: register-file read, operand multiplexer, a 32-bit subtraction
and its zero/sign reduction. `stall_branch` feeds `stall_id`, and
`stall_id` feeds `instr_done`, `instr_id_done`, `id_in_ready` and
`csr_op_en`. Those are the enables of nearly every architectural
register in the core: the CSR writes (mtvec, the PMP addresses, mie,
mscratch, dscratch, depc, mepc, mtval), both 64-bit counters (minstret
increment, mcycle write), the IF/ID pipeline register (pc_id) and the
prefetch FIFO pop. docs/ibex-execute-timing.md traces the slow-corner
critical paths of the main chip to exactly that cone.

The decision is used by nothing else in the first cycle at
BranchTargetALU = 0: the branch request itself, `branch_set_raw_d`, is
already flopped (`g_branch_set_flop`) and acted on in the second cycle,
where the shared ALU computes the target.

WHAT IT CHANGES

The decision in those two statements is replaced by a constant 1, so a
conditional branch ALWAYS enters MULTI_CYCLE and stalls its first cycle,
whatever its outcome. That is the timing Ibex already gives every branch
in its data-independent-timing mode (cpuctrl.data_ind_timing), minus
that mode's redirect to pc+4 on a not-taken branch:

  * taken branch: unchanged. Two cycles in ID/EX, then the fetch
    redirect from the flopped branch-set request, exactly as before.
  * not-taken branch: one cycle more than before. The second cycle
    completes it with `branch_set_raw_q` = 0, so there is no redirect
    and the prefetched fall-through instruction is used.

Architectural results do not change; only the cycle count of a not-taken
branch does. With BranchTargetALU = 1 both edited expressions reduce to
their unpatched values, so the patch has no effect there, and the SoC
flows refuse that combination rather than rely on it.

A named generate block, `g_branch_two_cycle`, holding one constant wire,
is added so a simulation flow can assert that the patched file was
elaborated.

Every anchor must occur exactly once. A pin that restructures the FSM
stops the build with the anchor named instead of patching the wrong
statement.
"""
import pathlib
import re
import sys

FILE = "ibex_id_stage.v"
MARK = "g_branch_two_cycle"

ANCHORS = (
    ("the first-cycle stall of a conditional branch",
     re.compile(r"(stall_branch\s*=\s*\(\s*~\s*BranchTargetALU\s*&\s*)"
                r"branch_decision_i(\s*\)\s*\|\s*data_ind_timing_i\s*;)")),
    ("the first-cycle FSM transition of a conditional branch",
     re.compile(r"(id_fsm_d\s*=\s*\(?\s*\(?\s*data_ind_timing_i\s*\|\|\s*"
                r"\(\s*!\s*BranchTargetALU\s*&&\s*)"
                r"branch_decision_i(\s*\))")),
)


def patch(text):
    if MARK in text:
        raise SystemExit("%s: input already carries %s; refusing to patch "
                         "a patched file" % (FILE, MARK))
    for what, rx in ANCHORS:
        hits = rx.findall(text)
        if len(hits) != 1:
            raise SystemExit(
                "ibex_branch_2cycle.py: anchor for {} occurs {} times in {}, "
                "expected exactly once.\n  pattern: {}\nThe pinned Ibex has "
                "moved under this patch. Re-read the generated file before "
                "going further; do NOT relax the anchor.".format(
                    what, len(hits), FILE, rx.pattern))
        text = rx.sub(lambda m: m.group(1) + "1'b1" + m.group(2), text)
    if text.count("\nendmodule") != 1:
        raise SystemExit("%s: expected exactly one endmodule" % FILE)
    text = text.replace(
        "\nendmodule",
        "\n\t// hw/soc/flow/ibex_branch_2cycle.py: every conditional branch"
        "\n\t// takes two cycles. Elaboration witness only, no logic."
        "\n\tgenerate\n\t\tif (1) begin : %s\n\t\t\twire unused_branch_two_cycle = 1'b0;"
        "\n\t\tend\n\tendgenerate"
        "\nendmodule" % MARK)
    return text


def main(argv):
    if len(argv) != 3:
        raise SystemExit("usage: ibex_branch_2cycle.py <gen_dir> <out_dir>")
    src = pathlib.Path(argv[1]) / FILE
    if not src.is_file():
        raise SystemExit("%s does not exist: run hw/soc/flow/sv2v_ibex.sh "
                         "first" % src)
    out = pathlib.Path(argv[2])
    out.mkdir(parents=True, exist_ok=True)
    dst = out / FILE
    dst.write_text(patch(src.read_text()))
    print("wrote %s" % dst)


if __name__ == "__main__":
    main(sys.argv)
