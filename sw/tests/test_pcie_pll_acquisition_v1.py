# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent edge/slip and real-file prerequisite rejection controls."""

import copy
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import characterize_pcie_pll_acquisition_v1 as m


def waveform(edges, times):
    values = np.zeros(len(times))
    for edge in edges:
        values[(times >= edge) & (times < edge + 2e-9)] = 2.5
    return values


def fixture(phase=None):
    t = np.linspace(0, m.STOP, 200001)
    reference = np.arange(14, 1000, 10) / 1e9
    feedback = reference + 200e-12 if phase is None else reference + phase(reference)
    return dict(
        time=t,
        **{
            "v(reference)": waveform(reference, t),
            "v(fb)": waveform(feedback, t),
            "v(vctrl)": np.ones(len(t)),
        },
    )


def test_actual_reference_edges_and_sustained_confirmation():
    result = m.acquisition(fixture())
    assert result["passed"] and result["ordinal_discontinuities"] == []
    assert result["sustained_window_start_s"] == 100e-9
    assert result["sustained_confirmation_s"] == 200e-9
    assert [x["interval_s"] for x in result["fixed_acceptance_windows"]] == [
        [800e-9, 900e-9],
        [900e-9, 1e-6],
    ]
    assert len(result["rolling_windows"]) == 81


def test_independent_linear_crossing_arithmetic():
    assert m.rising_edges(np.array([0.0, 2.0, 5.0]), np.array([0.0, 2.5, 0.0])) == [1.0]
    pairs, slips = m.pair_ordinals([0.0, 10e-9, 20e-9], [1e-9, 11e-9, 21e-9])
    assert slips == [] and [p["reference_ordinal"] for p in pairs] == [0, 1, 2]


@pytest.mark.parametrize("bad", ["nonfinite", "duplicate_time", "short"])
def test_edge_vector_rejections(bad):
    t, v = np.array([0.0, 1.0, 2.0]), np.array([0.0, 2.0, 0.0])
    if bad == "nonfinite":
        v[-1] = np.nan
    elif bad == "duplicate_time":
        t[-1] = t[-2]
    else:
        t = t[:1]
        v = v[:1]
    with pytest.raises(ValueError):
        m.rising_edges(t, v)


@pytest.mark.parametrize(
    "edge,kind",
    [([1e-9, 21e-9], "skip"), ([1e-9, 2e-9], "repeat"), ([11e-9, 1e-9], "regression")],
)
def test_explicit_ordinal_faults(edge, kind):
    _, slips = m.pair_ordinals([0.0, 10e-9, 20e-9], edge)
    assert len(slips) == 1 and slips[0]["kind"] == kind


def test_exact_half_period_is_ambiguous():
    pairs, _ = m.pair_ordinals([0.0, 10e-9, 20e-9], [5e-9])
    assert (
        pairs[0]["reference_ordinal"] == 0 and not pairs[0]["unambiguous_half_period"]
    )


def test_early_transient_is_reported_without_rewriting_late_acquisition():
    data = fixture()
    t = data["time"]
    data["v(fb)"][(t > 53e-9) & (t < 57e-9)] = 0
    result = m.acquisition(data)
    assert result["passed"] and result["ordinal_discontinuities"][0]["kind"] == "skip"
    assert result["sustained_window_start_s"] == 100e-9


@pytest.mark.parametrize(
    "fault",
    ["late_missing", "late_extra", "late_frequency", "late_control", "phase_ramp"],
)
def test_late_fault_cannot_be_hidden_by_early_qualifying_windows(fault):
    data = fixture()
    t = data["time"]
    if fault == "late_missing":
        data["v(fb)"][(t > 953e-9) & (t < 957e-9)] = 0
    elif fault == "late_extra":
        data["v(fb)"][(t > 950e-9) & (t < 951e-9)] = 2.5
    elif fault == "late_frequency":
        data = fixture(lambda edges: 200e-12 + np.maximum(edges - 800e-9, 0) * 0.001)
    elif fault == "late_control":
        data["v(vctrl)"][-10:] = 1.500001
    else:
        data = fixture(lambda edges: 200e-12 + edges * 0.0002)
    result = m.acquisition(data)
    assert not result["passed"]


def test_exponential_startup_reports_grid_confirmation_not_exact_lock():
    result = m.acquisition(
        fixture(lambda edges: 250e-12 - 3e-9 * np.exp(-edges / 115e-9))
    )
    assert result["passed"] and 600e-9 < result["sustained_window_start_s"] <= 800e-9
    assert (
        result["sustained_confirmation_s"]
        == result["sustained_window_start_s"] + 100e-9
    )


def advisory():
    size = m.STOP / 2.5e-12 * 826 * 8 / 1024**3
    return f"Warning: memory required ({size:.6f} GB), made of\n       826 nodes and approximately 400000 time steps,\n       is more than the DRAM memory available (1.000000 GB)!\n       Swapping data to SSD may slow down the simulation.\n"


def test_exact_memory_advisory_is_recorded_not_called_clean():
    original = advisory() + "ngspice-47 done\n"
    cleaned, found = m.classify_advisory(original, 826, 2.5e-12, m.STOP, m.NG47_SHA, 0)
    assert len(found) == 1 and found[0]["literal"] == advisory()
    assert cleaned == "ngspice-47 done\n" and "Warning" in original


@pytest.mark.parametrize(
    "fault",
    [
        "nodes",
        "steps",
        "bytes",
        "twice",
        "unknown",
        "singular",
        "runtime",
        "returncode",
    ],
)
def test_memory_advisory_cannot_hide_other_failure(fault):
    log = advisory()
    if fault == "nodes":
        log = log.replace("826 nodes", "825 nodes")
    elif fault == "steps":
        log = log.replace("400000 time", "400001 time")
    elif fault == "bytes":
        log = log.replace("memory required (", "memory required (9")
    elif fault == "twice":
        log *= 2
    elif fault == "unknown":
        log += "Warning: unexpected event\n"
    elif fault == "singular":
        log += "singular matrix\n"
    with pytest.raises(ValueError):
        m.classify_advisory(
            log,
            826,
            2.5e-12,
            m.STOP,
            "0" * 64 if fault == "runtime" else m.NG47_SHA,
            1 if fault == "returncode" else 0,
        )


def native_fixture(tmp_path):
    """Synthetic receipt/files exercise binding only; never native evidence."""
    source = tmp_path / "original.spice"
    source.write_text("synthetic input for file-binding control\n")
    devices = [
        {"path": f"x{i}", "model": "npn13g2" if i < 64 else "rppd"} for i in range(539)
    ]
    prior = dict(
        devices=devices,
        config=dict(sources=[str(source)], fixture=["synthetic external stimulus"]),
        inputs={str(source): m.n.common.pin(source)},
    )
    folder = tmp_path / "native"
    folder.mkdir()
    names = [
        "bench.cir",
        "spinit",
        "execution.json",
        "run.log",
        "op.raw",
        "owned-processes.json",
        "capture/capture.json",
        "capture/header.bin",
        "capture/trailer.bin",
        "capture/parts/parts.json",
        "original.spice",
    ]
    for name in names:
        p = folder / name
        p.parent.mkdir(exist_ok=True, parents=True)
        p.write_text(
            '{"returncode": 0}\n'
            if name == "execution.json"
            else "synthetic output binding\n"
        )
    inputs = {
        **prior["inputs"],
        **{
            str(Path(p).resolve()): m.n.common.pin(p)
            for p in [
                m.previous.__file__,
                m.previous.previous.__file__,
                m.runtime.__file__,
            ]
        },
    }
    outputs = {name: m.n.common.pin(folder / name) for name in names}
    for name in ["bench.cir", "spinit", "original.spice"]:
        inputs[str((folder / name).resolve())] = outputs[name]
    bounds = [
        dict(
            **d,
            passed=True,
            **(
                dict(
                    min_settled_vce=0.8,
                    max_capture_vce=1.2,
                    max_capture_ic_per_nx=0.002,
                )
                if d["model"] == "npn13g2"
                else dict(voltage_limit=3.3, max_capture_terminal_difference=1.0)
            ),
        )
        for d in devices
    ]
    record = dict(
        status="FAIL_NATIVE_STREAM_FINITE_SCREEN",
        config=dict(**prior["config"], step_s=5e-12, stop_s=400e-9),
        devices=devices,
        safety=dict(
            passed=True, all_device_bounds=bounds, model_geometry_range_issues=[]
        ),
        zero_source_op=True,
        native_off_flags=["q." + d["path"] + ".qnpn13g2" for d in devices[:64]],
        clean_diagnostics=True,
        measurement=dict(passed=False),
        inputs=inputs,
        outputs=outputs,
    )
    path = folder / "result.json"
    path.write_text(json.dumps(record))
    return prior, path, record


def test_failed_settling_receipt_can_only_gate_new_trial_with_valid_electrical_capture(
    tmp_path,
):
    prior, path, _ = native_fixture(tmp_path)
    assert m.bind_native(path, m.n.common.sha(path), 5e-12, 400e-9, prior)


@pytest.mark.parametrize(
    "fault",
    [
        "input_removed",
        "output_removed",
        "bench_changed",
        "source_changed",
        "bounds_forged",
        "graph_changed",
        "nonzero",
        "dirty",
        "failed_safety",
        "wrong_step",
        "generated_binding",
    ],
)
def test_actual_file_and_record_mutations_fail_closed(tmp_path, fault):
    prior, path, record = native_fixture(tmp_path)
    if fault == "input_removed":
        del record["inputs"][next(iter(prior["inputs"]))]
    elif fault == "output_removed":
        del record["outputs"]["op.raw"]
    elif fault == "bench_changed":
        (path.parent / "bench.cir").write_text("changed actual circuit\n")
    elif fault == "source_changed":
        Path(prior["config"]["sources"][0]).write_text("changed source\n")
    elif fault == "bounds_forged":
        record["safety"]["all_device_bounds"][0]["max_capture_ic_per_nx"] = 0.00300001
    elif fault == "graph_changed":
        record["devices"] = copy.deepcopy(record["devices"])
        record["devices"][0]["path"] = "changed"
    elif fault == "nonzero":
        (path.parent / "execution.json").write_text('{"returncode": 1}\n')
        record["outputs"]["execution.json"] = m.n.common.pin(
            path.parent / "execution.json"
        )
    elif fault == "dirty":
        record["clean_diagnostics"] = False
    elif fault == "failed_safety":
        record["safety"]["passed"] = False
    elif fault == "wrong_step":
        record["config"]["step_s"] = 2.5e-12
    else:
        del record["inputs"][str((path.parent / "bench.cir").resolve())]
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError):
        m.bind_native(path, m.n.common.sha(path), 5e-12, 400e-9, prior)


def test_manifest_requires_both_completed400ns_sources(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"first400": {}}))
    with pytest.raises(ValueError, match="Exact prerequisite set"):
        m.prerequisites(path, m.n.common.sha(path), 5e-12, {})


def test_duration_only_source_bridge_and_inherited_lifecycle():
    original = "example\n.control\ntran 5e-12 3.4e-08 0 5e-12\nwrite wave.raw all\n.endc\n.end\n"
    for step in [5e-12, 2.5e-12]:
        deck = m.stream_deck(original, step, m.STOP)
        restored = deck.replace(f".tran {step:.12g} 1e-06 0 {step:.12g}\n", "").replace(
            "run stream.fifo\nsetplot\ndisplay\nrusage space\n",
            "tran 5e-12 3.4e-08 0 5e-12\nwrite wave.raw all\n",
        )
        assert restored == original
    assert m.namespace["native_wait"] is m.previous.native_wait
    assert m.namespace["Meter"] is m.previous.Meter
    assert m.namespace["capture"] is m.capture
    assert m.namespace["measurements"] is m.measurements
    assert m.previous.namespace["measurements"] is m.previous.measurements
    with pytest.raises(ValueError):
        m.stream_deck(original, 1e-12, m.STOP)


def test_native_engineering_rounding_is_bounded_by_last_printed_decimal():
    exact = m.STOP / 2.5e-12 * 826 * 8 / 1024**3
    literal = advisory().replace(f"{exact:.6f} GB", f"{exact:.4f} GB")
    assert m.classify_advisory(literal, 826, 2.5e-12, m.STOP, m.NG47_SHA, 0)[1]
    wrong = literal.replace(f"{exact:.4f} GB", f"{exact + 0.0001:.4f} GB")
    with pytest.raises(ValueError, match="printed rounding"):
        m.classify_advisory(wrong, 826, 2.5e-12, m.STOP, m.NG47_SHA, 0)
    with pytest.raises(ValueError, match="display precision"):
        m.classify_advisory(
            literal.replace(f"{exact:.4f} GB", "2 GB"),
            826,
            2.5e-12,
            m.STOP,
            m.NG47_SHA,
            0,
        )


def op_fixture():
    columns = ["time"] + [f"v(node{i})" for i in range(824)] + ["i(vdd)"]
    log = "No. of Data Rows : 1\nNo. of Data Rows : 100\nCurrent op1 Operating Point\n"
    log += "\n".join(f"    node{i} : voltage, real, 1 long" for i in range(824))
    log += "\n    vdd#branch : current, real, 1 long\nMaximum ngspice program size = 59.238 MB\n"
    return log, dict(rows=100, columns=columns)


def test_retained_op_requires_every_single_point_vector_and_no_tran_plot():
    log, capture = op_fixture()
    proof = m.retained_op_proof(log, capture)
    assert proof == dict(
        retained_plot="op1_only", retained_vector_length=1, native_peak_mb=59.238
    )


@pytest.mark.parametrize(
    "fault", ["count", "plot", "identity", "length", "peak", "missing", "duplicate"]
)
def test_retained_op_and_actual_memory_reject_changes(fault):
    log, capture = op_fixture()
    if fault == "count":
        log = log.replace("Rows : 100", "Rows : 99")
    elif fault == "plot":
        log += "Current tran1 Transient Analysis\n"
    elif fault == "identity":
        log = log.replace("node823 :", "wrong_node :")
    elif fault == "length":
        log = log.replace("real, 1 long", "real, 100 long", 1)
    elif fault == "peak":
        log = log.replace("59.238 MB", "128 MB")
    elif fault == "missing":
        log = log.replace("    node823 : voltage, real, 1 long\n", "")
    else:
        log += "    node823 : voltage, real, 1 long\n"
    with pytest.raises(ValueError):
        m.retained_op_proof(log, capture)


def test_prerequisite_first1us_must_be_functionally_qualified(tmp_path):
    prior, path, record = native_fixture(tmp_path)
    record["config"].update(step_s=5e-12, stop_s=m.STOP)
    record["inputs"][str(Path(m.__file__).resolve())] = m.n.common.pin(m.__file__)
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="First1us merits"):
        m.bind_native(path, m.n.common.sha(path), 5e-12, m.STOP, prior, True)
    record["measurement"]["passed"] = True
    path.write_text(json.dumps(record))
    assert m.bind_native(path, m.n.common.sha(path), 5e-12, m.STOP, prior, True)


@pytest.mark.parametrize("mutation", ["duplicate", "wrong", "removed"])
def test_prerequisite_off_identity_is_exact_not_just_a_count(tmp_path, mutation):
    prior, path, record = native_fixture(tmp_path)
    if mutation == "duplicate":
        record["native_off_flags"][-1] = record["native_off_flags"][0]
    elif mutation == "wrong":
        record["native_off_flags"][-1] = "q.wrong.qnpn13g2"
    else:
        record["native_off_flags"].pop()
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError, match="OP/OFF/numerics"):
        m.bind_native(path, m.n.common.sha(path), 5e-12, 400e-9, prior)


@pytest.mark.parametrize(
    "status,exitcode",
    [
        ("PASS_NATIVE_STREAM_FINITE_SCREEN", 0),
        ("FAIL_NATIVE_STREAM_FINITE_SCREEN", 1),
        ("ERROR_NATIVE_OR_STREAM_CAPTURE", 1),
        ("RUNNING", 1),
    ],
)
def test_only_exact_completed_pass_returns_cli_success(monkeypatch, status, exitcode):
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "acquisition",
            "--out",
            "/never-created",
            "--prefix",
            "fixture",
            "--step-ps",
            "5",
            "--reference",
            "/never-read",
            "--reference-sha",
            "0" * 64,
            "--prerequisites",
            "/never-read",
            "--prerequisites-sha",
            "0" * 64,
        ],
    )
    # This test isolates exit-status dispatch; native-runtime rejection has
    # independent real guard tests below and in test_pcie_pll_loop_runtime_v2.
    runtime_calls = []
    monkeypatch.setattr(
        m.runtime, "check_runtime", lambda *args: runtime_calls.append(args)
    )
    monkeypatch.setattr(m, "run", lambda *args: {"status": status})
    assert m.main() == exitcode
    assert runtime_calls == [
        (sys.version_info, np.__version__, callable(getattr(np, "trapezoid", None)))
    ]


def test_main_rejects_unvalidated_runtime_before_run(monkeypatch):
    monkeypatch.setattr(sys, "version_info", (3, 14, 0))
    launched = []
    monkeypatch.setattr(m, "run", lambda *args: launched.append(args))
    with pytest.raises(RuntimeError, match="requires validated Python3.12"):
        m.main()
    assert launched == []
