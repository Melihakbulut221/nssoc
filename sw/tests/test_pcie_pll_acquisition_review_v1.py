# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent acquisition arithmetic and real file/payload rejection controls."""

import copy
import hashlib
import json
import lzma
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import review_pcie_pll_acquisition_v1 as review


def signal_data(delay=100e-12):
    times = np.linspace(0, 1e-6, 50001)
    return {
        "time": times,
        "v(reference)": 1.25 + np.sin(2 * np.pi * 1e8 * (times - 2.5e-9)),
        "v(fb)": 1.25 + np.sin(2 * np.pi * 1e8 * (times - 2.5e-9 - delay)),
        "v(vctrl)": np.full_like(times, 1.1),
    }


@pytest.mark.parametrize(
    "fault",
    ["none", "missing_edge", "wrong_frequency", "late_phase", "control_excursion"],
)
def test_independent_actual_edge_windows(fault):
    d = signal_data()
    t = d["time"]
    if fault == "missing_edge":
        d["v(fb)"][(t >= 840e-9) & (t < 850e-9)] = 0
    elif fault == "wrong_frequency":
        d["v(fb)"] = 1.25 + np.sin(2 * np.pi * 1.01e8 * (t - 2.6e-9))
    elif fault == "late_phase":
        d["v(fb)"][t >= 930e-9] = 1.25 + np.sin(
            2 * np.pi * 1e8 * (t[t >= 930e-9] - 2.8e-9)
        )
    elif fault == "control_excursion":
        d["v(vctrl)"][45000] = 1.50001
    independent = review.independent_analysis(d)
    original = review.producer.acquisition(d)
    assert independent["passed"] == (fault == "none")
    review.compare_independent(independent, original)
    if fault == "none":
        assert independent["sustained_window_start_s"] == 100e-9
        assert independent["sustained_confirmation_s"] == 200e-9
    elif fault == "missing_edge":
        assert not independent["final_two_windows_no_slip"]


def test_ordinals_tie_repeat_and_skip_are_not_phase_wrapped_away():
    ref = np.array([0.0, 10.0, 20.0, 30.0])
    fb = np.array([5.0, 6.0, 10.1, 29.0])
    assert review.monotone_ordinals(ref, fb).tolist() == [0, 1, 1, 3]


@pytest.mark.parametrize("fault", ["predicate", "ordinal", "edge", "frequency"])
def test_corrupted_recorded_analysis_rejected(fault):
    d = signal_data()
    expected = review.independent_analysis(d)
    observed = review.producer.acquisition(d)
    if fault == "predicate":
        observed["rolling_windows"][70]["checks"]["phase_range_50ps"] = False
    elif fault == "ordinal":
        observed["all_edge_pairings"][50]["reference_ordinal"] += 1
    elif fault == "edge":
        observed["feedback_edges_s"][50] += 1e-12
    elif fault == "frequency":
        observed["rolling_windows"][70]["frequency_hz"] += 1
    with pytest.raises(ValueError):
        review.compare_independent(expected, observed)


def packed_part(raw, columns=3):
    packed = lzma.compress(raw, preset=1)
    return packed, {
        "rows": len(raw) // (columns * 8),
        "bytes": len(packed),
        "sha256": hashlib.sha256(packed).hexdigest(),
        "uncompressed_bytes": len(raw),
        "uncompressed_sha256": hashlib.sha256(raw).hexdigest(),
    }


@pytest.mark.parametrize(
    "fault",
    [
        "none",
        "compressed_corruption",
        "truncated",
        "trailing_stream",
        "nan",
        "raw_hash",
        "wrong_rows",
    ],
)
def test_lossless_part_real_payload_faults(fault):
    data = np.arange(36, dtype="<f8").reshape(12, 3)
    if fault == "nan":
        data[4, 1] = np.nan
    packed, part = packed_part(data.tobytes())
    if fault == "compressed_corruption":
        packed = packed[:-1] + bytes([packed[-1] ^ 1])
    elif fault == "truncated":
        packed = packed[:-10]
        part.update(bytes=len(packed), sha256=hashlib.sha256(packed).hexdigest())
    elif fault == "trailing_stream":
        packed += lzma.compress(b"extra")
        part.update(bytes=len(packed), sha256=hashlib.sha256(packed).hexdigest())
    elif fault == "raw_hash":
        part["uncompressed_sha256"] = "0" * 64
    elif fault == "wrong_rows":
        part["rows"] += 1
    if fault == "none":
        raw, decoded = review.decode_part(packed, part, 3)
        assert raw == data.tobytes() and np.array_equal(decoded, data)
    else:
        with pytest.raises((ValueError, lzma.LZMAError)):
            review.decode_part(packed, part, 3)


def fixture(tmp_path, monkeypatch):
    original, folder = tmp_path / "original", tmp_path / "capture"
    original.mkdir()
    folder.mkdir()
    for name, text in [
        (
            "bench.cir",
            ".control\ntran 5e-12 3.4e-08 0 5e-12\nwrite wave.raw all\n.endc\n",
        ),
        ("spinit", "* exact startup\n"),
        ("circuit.spice", "* synthetic binder-only circuit\n"),
    ]:
        (original / name).write_text(text)
    monkeypatch.setattr(review.producer.previous.previous, "ORIGINAL", original)
    devices = [
        {"path": f"x{i}", "model": "npn13g2" if i < 64 else "sg13_lv_nmos"}
        for i in range(539)
    ]
    bounds = [
        dict(
            x,
            **(
                {
                    "min_settled_vce": 0.5,
                    "max_capture_vce": 1.2,
                    "max_capture_ic_per_nx": 0.002,
                }
                if x["model"] == "npn13g2"
                else {
                    "max_capture_terminal_difference": 1.2,
                    "max_capture_drain_per_um": 0.001,
                    "voltage_limit": 1.5,
                }
            ),
            passed=True,
        )
        for x in devices
    ]
    config = {
        "case": "old",
        "sources": [str(original / "circuit.spice")],
        "fixture": "synthetic-unit-control",
        "step_s": 5e-12,
        "stop_s": 34e-9,
    }
    prior = {
        "devices": devices,
        "config": config,
        "inputs": {
            str(original / "circuit.spice"): review.producer.n.common.pin(
                original / "circuit.spice"
            )
        },
    }
    for name in ["spinit", "circuit.spice"]:
        (folder / name).write_bytes((original / name).read_bytes())
    (folder / "bench.cir").write_text(
        review.producer.stream_deck((original / "bench.cir").read_text(), 5e-12, 1e-6)
    )
    for name in [
        "run.log",
        "op.raw",
        "owned-processes.json",
        "capture/capture.json",
        "capture/header.bin",
        "capture/trailer.bin",
        "capture/parts/parts.json",
    ]:
        p = folder / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text("binder-only, not native evidence\n")
    (folder / "execution.json").write_text('{"returncode":0}\n')
    config = dict(
        config,
        case="connected_physical_loop_acquisition1us",
        step_s=5e-12,
        stop_s=1e-6,
        window_s=[4e-9, 1e-6],
    )
    methods = [
        review.producer,
        review.producer.previous,
        review.producer.previous.previous,
        review.producer.runtime,
    ]
    inputs = dict(prior["inputs"])
    for p in [
        *[Path(m.__file__).resolve() for m in methods],
        folder / "bench.cir",
        folder / "spinit",
        folder / "circuit.spice",
    ]:
        inputs[str(p)] = review.producer.n.common.pin(p)
    record = {
        "status": "PASS_NATIVE_STREAM_FINITE_SCREEN",
        "devices": devices,
        "config": config,
        "inputs": inputs,
        "outputs": {
            str(p.relative_to(folder)): review.producer.n.common.pin(p)
            for p in folder.rglob("*")
            if p.is_file()
        },
        "measurement": {"passed": True},
        "safety": {
            "passed": True,
            "all_device_bounds": bounds,
            "model_geometry_range_issues": [],
        },
        "zero_source_op": True,
        "strict_numerical_diagnostics_pass": True,
        "native_off_flags": [
            "q." + x["path"] + ".qnpn13g2" for x in devices if x["model"] == "npn13g2"
        ],
    }
    return folder, prior, record


@pytest.mark.parametrize("mode", ["pass", "functional_fail", "electrical_fail"])
def test_completed_failed_screen_is_auditable_without_promoting_it(
    tmp_path, monkeypatch, mode
):
    folder, prior, record = fixture(tmp_path, monkeypatch)
    if mode == "functional_fail":
        record["measurement"]["passed"] = False
    if mode == "electrical_fail":
        record["safety"]["all_device_bounds"][0].update(
            max_capture_ic_per_nx=0.003001, passed=False
        )
        record["safety"]["passed"] = False
    if mode != "pass":
        record["status"] = "FAIL_NATIVE_STREAM_FINITE_SCREEN"
    p = folder / "result.json"
    p.write_text(json.dumps(record))
    before = p.read_bytes()
    review.bind_completed_capture(p, review.producer.n.common.sha(p), prior)
    assert p.read_bytes() == before
    assert json.loads(before)["status"] == record["status"]


@pytest.mark.parametrize(
    "fault",
    [
        "missing_source",
        "missing_output",
        "bench",
        "circuit",
        "rehashed_bench",
        "rehashed_circuit",
        "config_window",
        "forged_safe",
        "forged_status",
        "runtime_abort",
        "incomplete",
    ],
)
def test_actual_record_and_file_rejections(tmp_path, monkeypatch, fault):
    folder, prior, record = fixture(tmp_path, monkeypatch)
    if fault == "missing_source":
        record["inputs"].pop(next(iter(prior["inputs"])))
    elif fault == "missing_output":
        record["outputs"].pop("op.raw")
    elif fault in ["bench", "circuit", "rehashed_bench", "rehashed_circuit"]:
        name = "bench.cir" if "bench" in fault else "circuit.spice"
        p = folder / name
        p.write_text(p.read_text() + "* changed actual bytes\n")
        if fault.startswith("rehashed"):
            record["inputs"][str(p)] = review.producer.n.common.pin(p)
            record["outputs"][name] = review.producer.n.common.pin(p)
    elif fault == "config_window":
        record["config"]["window_s"][0] = 10e-9
    elif fault == "forged_safe":
        record["safety"]["all_device_bounds"][0]["max_capture_ic_per_nx"] = 0.00301
    elif fault == "forged_status":
        record["status"] = "FAIL_NATIVE_STREAM_FINITE_SCREEN"
    elif fault == "runtime_abort":
        (folder / "execution.json").write_text('{"returncode":1}')
        record["outputs"]["execution.json"] = review.producer.n.common.pin(
            folder / "execution.json"
        )
    elif fault == "incomplete":
        record["status"] = "RUNNING"
    p = folder / "result.json"
    p.write_text(json.dumps(record))
    with pytest.raises(ValueError):
        review.bind_completed_capture(p, review.producer.n.common.sha(p), prior)
