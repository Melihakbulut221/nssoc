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


def _verilator():
    v = shutil.which("verilator")
    if not v or not shutil.which("g++") or not (SOC / "gen/ibex_top.v").is_file():
        pytest.skip("Verilator, g++ and the pinned converted Ibex sources are required")
    return v


def build(work, config, mutate=None, sim="verilator"):
    """Compile the testbench for one configuration.

    Verilator (two-state, about 300 times faster here) runs the sweeps;
    Icarus (four-state) runs the trace comparison as well, so that an
    unknown value reaching architectural state is not hidden.
    """
    work.mkdir(parents=True, exist_ok=True)
    defines = ["SG13G2_ICG_BEHAVIOURAL"]
    if CONFIGS[config][1]:
        defines += ["SOC_RF_EXEC", "TB_RF_KNOBS"]
    srcs = [SOC / "tb/tb_ibex_ex_stage.v", SOC / "rtl/prim_clock_gating.v",
            *_sources(work, config, mutate)]
    if sim == "icarus":
        iverilog, _ = _tools()
        binary = work / "tb.vvp"
        cmd = [iverilog, "-g2005-sv", "-s", "tb_ibex_ex_stage", "-o", str(binary)]
        cmd += ["-D" + d for d in defines] + [str(f) for f in srcs]
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        assert r.returncode == 0, r.stdout + r.stderr
        if CONFIGS[config][0]:
            assert '"g_ex_stage"' in binary.read_bytes().decode("latin-1"), "patch not elaborated"
        return binary
    verilator = _verilator()
    mdir = work / "vl"
    cmd = [verilator, "--binary", "--timing", "-j", str(os.cpu_count() or 2), "-Wno-fatal",
           "-Wno-lint", "-Wno-style", "-Wno-MULTIDRIVEN", "-Wno-UNOPTFLAT",
           "--top-module", "tb_ibex_ex_stage", "-Mdir", str(mdir), "-o", "tb",
           # The system compiler, not whatever a packaged Verilator was built with.
           "-MAKEFLAGS", "CXX=g++ LINK=g++ AR=ar"]
    cmd += ["+define+" + d for d in defines] + [str(f) for f in srcs]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    assert r.returncode == 0, (r.stdout + r.stderr)[-5000:]
    return mdir / "tb"


_BUILD_ROOT = None


@functools.lru_cache(maxsize=None)
def built(config, sim="verilator"):
    """One compiled testbench per configuration and simulator, shared by the tests."""
    root = Path(os.environ.get("IBEX_EX_BUILD_DIR") or _build_root())
    return build(root / ("%s-%s" % (config, sim)), config, sim=sim)


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
    if binary.suffix == ".vvp":
        _, vvp = _tools()
        args = [vvp, "-n", str(binary)]
    else:
        args = [str(binary)]
    args += ["+prog=%s" % image(prog)]
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


RANDOM = ["rand%d" % i for i in range(1, 1 + 12 * SCALE)]
SWEPT = ["alu", "load", "muldiv", "csr", "branch", "except", "fence", "pmp", "rand1", "rand2"]
ALL = sorted(set(SWEPT + RANDOM)) + ["counters"]


@pytest.mark.parametrize("config", list(CONFIGS))
@pytest.mark.parametrize("prog", ALL)
def test_same_trace_fixed_and_random_latency(config, prog):
    ref = reference(prog)
    rows = run(built(config), prog)
    rows += run(built(config), prog, trials=20 * SCALE, seed=7, ilat=3, dlat=4)
    assert {r["hash"] for r in rows} == {ref["hash"]}, (ref, rows)


@pytest.mark.parametrize("config", list(CONFIGS))
@pytest.mark.parametrize("prog", ["alu", "load", "muldiv", "csr", "counters", "branch", "except",
                                  "fence", "pmp", "rand1"])
def test_same_trace_four_state(config, prog):
    """The same comparison in Icarus, which propagates unknown values."""
    ref = reference(prog)
    rows = run(built(config, "icarus"), prog)
    rows += run(built(config, "icarus"), prog, trials=2, seed=3, ilat=2, dlat=3)
    assert {r["hash"] for r in rows} == {ref["hash"]}, (ref, rows)


@pytest.mark.parametrize("config", ["base"] + PATCHED)
@pytest.mark.parametrize("prog", SWEPT)
def test_interrupt_at_every_cycle(config, prog):
    """One interrupt at each cycle offset: mepc must be the next unexecuted instruction."""
    ref = reference(prog)
    n = ref["cycles"] + 40
    rows = run(built(config), prog, trials=n, irq_at=1, irq_step=1)
    rows += run(built(config), prog, trials=n, irq_at=1, irq_step=1, seed=21, ilat=2, dlat=2)
    bad = [r for r in rows if r["hash"] != ref["hash"]]
    assert not bad, bad[:5]
    assert sum(r["irqs"] for r in rows) >= n // 2


@pytest.mark.parametrize("config", ["base"] + PATCHED)
@pytest.mark.parametrize("prog", SWEPT + ["wfi"])
def test_periodic_interrupts_random_latency(config, prog):
    ref = reference(prog)
    n = 60 * SCALE
    step = max(1, ref["cycles"] // n)
    rows = run(built(config), prog, trials=n, irq_at=3, irq_step=step, irq_period=23,
               seed=11, ilat=2, dlat=3)
    assert {r["hash"] for r in rows} == {ref["hash"]}, rows[:5]
    assert all(r["irqs"] > 0 for r in rows)


@pytest.mark.parametrize("config", ["base"] + PATCHED)
@pytest.mark.parametrize("prog", SWEPT)
def test_debug_request_at_every_cycle(config, prog):
    """Debug entry at each cycle offset: dpc must be the next unexecuted instruction."""
    ref = reference(prog)
    n = ref["cycles"] + 40
    rows = run(built(config), prog, trials=n, dbg_at=1, dbg_step=1)
    rows += run(built(config), prog, trials=n, dbg_at=1, dbg_step=1, seed=23, ilat=2, dlat=2)
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
    # The request intervals are longer than a handler round trip. With
    # shorter ones a request is pending again whenever a handler returns,
    # and no core makes progress (interrupt storm, not a hazard).
    rows += run(built(config), prog, trials=30 * SCALE, dbg_at=5, dbg_step=37, dbg_period=150,
                steps=3, irq_at=9, irq_step=11, irq_period=70, seed=5, ilat=2, dlat=2)
    assert {r["hash"] for r in rows} == {ref["hash"]}, rows[:5]


# Negative controls: each mutation removes one hazard mechanism and must be
# caught by the programs above.
MUTATIONS = {
    "no_forwarding_a": ("(exs_fwd_a ? rf_wdata_wb :", "(1'b0 ? rf_wdata_wb :"),
    "no_forwarding_b": ("(exs_fwd_b ? rf_wdata_wb :", "(1'b0 ? rf_wdata_wb :"),
    "x0_forwarded": ("& (exs_id_raddr_a != 5'd0)", "& 1'b1"),
    "no_id_flush": ("assign exs_id_clear = exs_ex_we | pc_set;", "assign exs_id_clear = exs_ex_we;"),
    "no_system_gate": ("& ~(exs_ex_we & exs_id_sys)) & ~exs_ex_sys;", ");"),
    "raw_pc_if": ("assign exs_pc_next = (exs_id_instr_valid_id ? exs_id_pc_id : pc_if);",
                  "assign exs_pc_next = pc_if;"),
}


@pytest.mark.parametrize("mutation", list(MUTATIONS))
def test_mutated_patch_is_caught(tmp_path, mutation):
    binary = build(tmp_path / mutation, "ex", MUTATIONS[mutation])
    caught = []
    for prog in ["alu", "load", "branch", "except", "muldiv", "csr", "pmp", "rand1", "rand2"]:
        ref = reference(prog)
        limit = 20 * ref["cycles"] + 2000
        try:
            rows = run(binary, prog, max_cycles=limit, trials=10, seed=9, ilat=3, dlat=3)
            rows += run(binary, prog, max_cycles=limit, trials=300, irq_at=1, irq_step=1)
            rows += run(binary, prog, max_cycles=limit, trials=300, dbg_at=1, dbg_step=1)
        except AssertionError:
            caught.append(prog)
            break
        if any(r["hash"] != ref["hash"] for r in rows):
            caught.append(prog)
            break
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
