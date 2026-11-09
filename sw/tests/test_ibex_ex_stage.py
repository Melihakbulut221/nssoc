# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Core-level tests of the separate execute stage (docs/ibex-ex-stage.md).

Each directed program in sw/tests/ibex_ex_programs.py targets one hazard
class; the random programs mix them. hw/soc/tb/tb_ibex_ex_stage.v folds
the main program's architectural trace (retired PCs, register writes,
stores) into a hash. The tests require, for every program:

  * the unpatched core and every patched configuration halt with exit
    code 0 and the same hash, with fixed and with random bus latencies;
  * the same hash when an interrupt or a debug request arrives at every
    cycle offset of the program, or periodically, and under single-step,
    which is only possible if mepc/dpc name exactly the next unexecuted
    instruction and the flushed ID-stage instruction is re-executed once;
  * mutated patches (no forwarding, no flush, raw pc_if) are caught.

IBEX_EX_TEST_SCALE (default 1) multiplies the sweep lengths.
"""
import functools
import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

import ibex_ex_programs as programs
import rv32_mini_asm as asm

ROOT = Path(__file__).resolve().parents[2]
SOC = ROOT / "hw/soc"
FLOW = SOC / "flow"
SCALE = int(os.environ.get("IBEX_EX_TEST_SCALE", "1"))

CONFIGS = {
    # name: (ex stage, project register file with the RF knobs, two-cycle branches)
    "base": (False, False, False),
    "ex": (True, False, False),
    "base_knobs_br2": (False, True, True),
    "ex_knobs": (True, True, False),
    "ex_knobs_br2": (True, True, True),
}
PATCHED = [c for c in CONFIGS if CONFIGS[c][0]]

TRIAL = re.compile(r"TRIAL (\d+) irq_at=(-?\d+) dbg_at=(-?\d+) seed=(-?\d+) halted=(\d) "
                   r"exit=([0-9a-fx]+) cycles=(\d+) hash=([0-9a-fx]+) retired=(\d+) writes=(\d+) "
                   r"stores=(\d+) irqs=(\d+) dbg=(\d+) exc=(\d+) alerts=(\d+)")


def _tools():
    iverilog, vvp = shutil.which("iverilog"), shutil.which("vvp")
    if not iverilog or not vvp or not (SOC / "gen/ibex_top.v").is_file():
        pytest.skip("Icarus and the pinned converted Ibex sources are required")
    return iverilog, vvp


def _sources(work, config, mutate=None):
    ex, knobs, br2 = CONFIGS[config]
    gen = SOC / "gen"
    files = {p.name: p for p in sorted(gen.glob("*.v"))}
    if knobs:
        subprocess.run(["python3", str(FLOW / "ibex_rf_predecode.py"), str(gen), str(work / "pre")],
                       check=True, capture_output=True)
        files["ibex_if_stage.v"] = work / "pre/ibex_if_stage.v"
        files["ibex_core.v"] = work / "pre/ibex_core.v"
    if br2:
        subprocess.run(["python3", str(FLOW / "ibex_branch_2cycle.py"), str(gen), str(work / "br2")],
                       check=True, capture_output=True)
        files["ibex_id_stage.v"] = work / "br2/ibex_id_stage.v"
    if ex:
        src = work / "pre" if knobs else gen
        subprocess.run(["python3", str(FLOW / "ibex_ex_stage.py"), str(src), str(work / "ex")],
                       check=True, capture_output=True)
        core = work / "ex/ibex_core.v"
        if mutate:
            text = core.read_text()
            old, new = mutate
            assert text.count(old) == 1, old
            core.write_text(text.replace(old, new))
        files["ibex_core.v"] = core
    extra = []
    if knobs:
        del files["ibex_register_file_ff.v"]
        extra = [SOC / "rtl/ibex_regfile_secded.v", ROOT / "hw/rtl/secded_enc.v",
                 ROOT / "hw/rtl/secded_dec.v"]
    return [*files.values(), *extra]


def build(work, config, mutate=None):
    iverilog, _ = _tools()
    work.mkdir(parents=True, exist_ok=True)
    binary = work / "tb.vvp"
    cmd = [iverilog, "-g2005-sv", "-DSG13G2_ICG_BEHAVIOURAL", "-s", "tb_ibex_ex_stage",
           "-o", str(binary)]
    if CONFIGS[config][1]:
        cmd += ["-DSOC_RF_EXEC", "-DTB_RF_KNOBS"]
    cmd += [str(SOC / "tb/tb_ibex_ex_stage.v"), str(SOC / "rtl/prim_clock_gating.v")]
    cmd += [str(f) for f in _sources(work, config, mutate)]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stdout + r.stderr
    if CONFIGS[config][0]:
        assert '"g_ex_stage"' in binary.read_bytes().decode("latin-1"), "patch not elaborated"
    return binary


_BUILD_ROOT = None


@functools.lru_cache(maxsize=None)
def built(config):
    """One compiled testbench per configuration, shared by the tests."""
    root = Path(os.environ.get("IBEX_EX_BUILD_DIR") or _build_root())
    return build(root / config, config)


def _build_root():
    global _BUILD_ROOT
    if _BUILD_ROOT is None:
        import tempfile
        _BUILD_ROOT = tempfile.mkdtemp(prefix="ibex-ex-")
    return _BUILD_ROOT


@functools.lru_cache(maxsize=None)
def image(name):
    body = programs.random_body(int(name[4:])) if name.startswith("rand") else \
        programs.DIRECTED[name]
    img, _ = asm.assemble(programs.framed(body))
    path = Path(_build_root()) / ("%s.hex" % name)
    path.write_text(asm.to_readmemh(img))
    return path


def run(binary, prog, timeout=1200, **plus):
    _, vvp = _tools()
    args = [vvp, "-n", str(binary), "+prog=%s" % image(prog)]
    args += ["+%s=%s" % kv for kv in plus.items()]
    r = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    out = r.stdout + r.stderr
    assert r.returncode == 0, out[-3000:]
    trials = [m.groups() for m in TRIAL.finditer(out)]
    assert trials, out[-3000:]
    assert "fatal" not in out.lower(), out[-3000:]
    rows = []
    for g in trials:
        row = dict(trial=int(g[0]), irq_at=int(g[1]), dbg_at=int(g[2]), halted=int(g[4]),
                   exit=g[5], cycles=int(g[6]), hash=g[7], retired=int(g[8]), irqs=int(g[11]),
                   dbg=int(g[12]), exc=int(g[13]), alerts=int(g[14]))
        assert row["halted"] == 1 and row["exit"] == "00000000" and row["alerts"] == 0, (row, out[-2000:])
        rows.append(row)
    return rows


@functools.lru_cache(maxsize=None)
def reference(prog):
    """The unpatched core's hash, fixed latency (the wfi program needs an interrupt)."""
    if prog == "wfi":
        return run(built("base"), prog, irq_at=40, irq_period=60)[0]
    return run(built("base"), prog)[0]


SWEPT = ["alu", "load", "muldiv", "csr", "branch", "except", "fence", "rand1", "rand2"]
ALL = SWEPT + ["counters", "rand3", "rand4", "rand5", "rand6"]


@pytest.mark.parametrize("config", list(CONFIGS))
@pytest.mark.parametrize("prog", ALL)
def test_same_trace_fixed_and_random_latency(config, prog):
    ref = reference(prog)
    rows = run(built(config), prog)
    rows += run(built(config), prog, trials=3 * SCALE, seed=7, ilat=3, dlat=4)
    assert {r["hash"] for r in rows} == {ref["hash"]}, (ref, rows)


@pytest.mark.parametrize("config", ["base"] + PATCHED)
@pytest.mark.parametrize("prog", SWEPT)
def test_interrupt_at_every_cycle(config, prog):
    """One interrupt at each cycle offset: mepc must be the next unexecuted instruction."""
    ref = reference(prog)
    n = min(ref["cycles"] + 20, 400 * SCALE)
    rows = run(built(config), prog, trials=n, irq_at=1, irq_step=1)
    bad = [r for r in rows if r["hash"] != ref["hash"]]
    assert not bad, bad[:5]
    assert sum(r["irqs"] for r in rows) >= n // 2


@pytest.mark.parametrize("config", ["base"] + PATCHED)
@pytest.mark.parametrize("prog", SWEPT + ["wfi"])
def test_periodic_interrupts_random_latency(config, prog):
    ref = reference(prog)
    rows = run(built(config), prog, trials=12 * SCALE, irq_at=3, irq_step=5, irq_period=17,
               seed=11, ilat=2, dlat=3)
    assert {r["hash"] for r in rows} == {ref["hash"]}, rows[:5]
    assert all(r["irqs"] > 0 for r in rows)


@pytest.mark.parametrize("config", ["base"] + PATCHED)
@pytest.mark.parametrize("prog", SWEPT)
def test_debug_request_at_every_cycle(config, prog):
    """Debug entry at each cycle offset: dpc must be the next unexecuted instruction."""
    ref = reference(prog)
    n = min(ref["cycles"] + 20, 400 * SCALE)
    rows = run(built(config), prog, trials=n, dbg_at=1, dbg_step=1)
    bad = [r for r in rows if r["hash"] != ref["hash"]]
    assert not bad, bad[:5]
    assert sum(r["dbg"] for r in rows) >= n // 2


@pytest.mark.parametrize("config", ["base"] + PATCHED)
@pytest.mark.parametrize("prog", SWEPT)
def test_single_step_with_interrupts(config, prog):
    """Single-step the whole program, then a few steps, with interrupts and debug mixed."""
    ref = reference(prog)
    rows = run(built(config), prog, dbg_at=1, steps=100000)
    assert rows[0]["dbg"] >= ref["retired"], (rows, ref)
    rows += run(built(config), prog, trials=6 * SCALE, dbg_at=5, dbg_step=37, dbg_period=50,
                steps=3, irq_at=9, irq_step=11, irq_period=29, seed=5, ilat=2, dlat=2)
    assert {r["hash"] for r in rows} == {ref["hash"]}, rows[:5]


# Negative controls: each mutation removes one hazard mechanism and must be
# caught by the programs above.
MUTATIONS = {
    "no_forwarding_a": ("(exs_fwd_a ? rf_wdata_wb :", "(1'b0 ? rf_wdata_wb :"),
    "no_forwarding_b": ("(exs_fwd_b ? rf_wdata_wb :", "(1'b0 ? rf_wdata_wb :"),
    "x0_forwarded": ("& (exs_id_raddr_a != 5'd0)", "& 1'b1"),
    "no_id_flush": ("assign exs_id_clear = exs_ex_we | pc_set;", "assign exs_id_clear = exs_ex_we;"),
    "raw_pc_if": ("assign exs_pc_next = (exs_id_instr_valid_id ? exs_id_pc_id : pc_if);",
                  "assign exs_pc_next = pc_if;"),
}


@pytest.mark.parametrize("mutation", list(MUTATIONS))
def test_mutated_patch_is_caught(tmp_path, mutation):
    binary = build(tmp_path / mutation, "ex", MUTATIONS[mutation])
    caught = []
    for prog in ["alu", "load", "branch", "except", "muldiv", "csr"]:
        ref = reference(prog)
        try:
            rows = run(binary, prog, timeout=600, trials=60, irq_at=1, irq_step=1)
            rows += run(binary, prog, trials=60, dbg_at=1, dbg_step=1)
        except AssertionError:
            caught.append(prog)
            continue
        if any(r["hash"] != ref["hash"] for r in rows):
            caught.append(prog)
    assert caught, "mutation %s was not detected by any program" % mutation


def test_patch_refuses_unsupported_configurations(tmp_path):
    iverilog, _ = _tools()
    work = tmp_path / "wb"
    work.mkdir(parents=True)
    srcs = _sources(work, "ex")
    tb = (SOC / "tb/tb_ibex_ex_stage.v").read_text().replace(
        ".WritebackStage(0)", ".WritebackStage(1)").replace(".BranchTargetALU(0)",
                                                            ".BranchTargetALU(1)")
    (work / "tb.v").write_text(tb)
    r = subprocess.run([iverilog, "-g2005-sv", "-DSG13G2_ICG_BEHAVIOURAL", "-s",
                        "tb_ibex_ex_stage", "-o", str(work / "x.vvp"), str(work / "tb.v"),
                        str(SOC / "rtl/prim_clock_gating.v"), *map(str, srcs)],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode != 0 and "ibex_ex_stage_unsupported_configuration" in r.stdout + r.stderr


def test_default_sources_are_unpatched(tmp_path):
    """IBEX_EX_STAGE=0 (and unset) lists exactly the files it listed before."""
    def listing(env):
        e = {k: v for k, v in os.environ.items() if not k.startswith("IBEX_")}
        e.update(env)
        r = subprocess.run(["bash", "-c", '. "$0/flow/ibex_sources.sh"; ibex_sources "$0"', str(SOC)],
                           capture_output=True, text=True, env=e, check=True)
        return r.stdout.split()
    if not (SOC / "gen/ibex_core.v").is_file():
        pytest.skip("the pinned converted Ibex sources are required")
    assert listing({}) == listing({"IBEX_EX_STAGE": "0"})
    on = listing({"IBEX_EX_STAGE": "1"})
    assert str(SOC / "genp/gen-ex/ibex_core.v") in on and str(SOC / "gen/ibex_core.v") not in on
    both = listing({"IBEX_EX_STAGE": "1", "IBEX_RF_PREDECODE": "1"})
    assert str(SOC / "genp/gen-pre-ex/ibex_core.v") in both
    assert str(SOC / "genp/gen-pre/ibex_core.v") not in both
    assert str(SOC / "genp/gen-pre/ibex_if_stage.v") in both
