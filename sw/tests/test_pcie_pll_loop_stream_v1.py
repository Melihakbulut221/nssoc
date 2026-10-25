# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual parser, bound, late-fault and process-owner rejection controls."""

import io
import json
import os
from pathlib import Path
import signal
import sys
import time

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))
import characterize_pcie_pll_loop_stream_v1 as m


def fixture():
    rows = [
        dict(path="xh", model="npn13g2", nets=["c", "b", "e", "0"], params={"nx": "2"}),
        dict(
            path="xm",
            model="sg13_lv_nmos",
            nets=["d", "g", "0", "0"],
            params=dict(w="2u", l=".13u", ng="1", m="1"),
        ),
        dict(
            path="xr", model="rppd", nets=["c", "d", "0"], params=dict(w="1u", l="1u")
        ),
    ]
    names = ["time", *m.n.vectors(rows, [])]
    a = np.zeros((1001, len(names)))
    a[:, 0] = np.linspace(0, 10e-9, len(a))
    for name, value in {
        "v(c)": 1,
        "v(b)": 0.7,
        "v(d)": 1,
        "v(g)": 1.2,
        "@q.xh.qnpn13g2[ic]": 0.004,
        "@n.xm.nsg13_lv_nmos[ids]": 0.001,
    }.items():
        a[:, names.index(name)] = value
    return names, rows, a, dict(step_s=10e-12, stop_s=10e-9, window_s=[4e-9, 10e-9])


def reduce(a, names, rows, config):
    meter = m.Meter(names, rows, config, observations=["time"])
    for block in np.array_split(a, 23):
        meter.push(block)
    return meter.finish()[0]


def test_stream_extrema_equal_full_frozen_formulas():
    names, rows, a, c = fixture()
    actual = reduce(a, names, rows, c)
    expected = m.n.safety(dict(zip(m.data_names(names), a.T)), rows, c["window_s"])
    assert actual == expected and actual["passed"]


@pytest.mark.parametrize(
    "name,value",
    [
        ("@q.xh.qnpn13g2[ic]", 0.00601),
        ("v(c)", 1.60001),
        ("v(c)", 0.39999),
        ("v(g)", 1.50001),
        ("@n.xm.nsg13_lv_nmos[ids]", 0.00401),
        ("v(d)", -3.31),
    ],
)
def test_late_actual_observation_fault_never_lost(name, value):
    names, rows, a, c = fixture()
    a[-2, names.index(name)] = value
    assert not reduce(a, names, rows, c)["passed"]


def test_startup_lower_headroom_not_claimed_but_upper_bound_kept():
    names, rows, a, c = fixture()
    a[:100, names.index("v(c)")] = 0
    assert reduce(a, names, rows, c)["passed"]
    a[4, names.index("v(c)")] = 1.7
    assert not reduce(a, names, rows, c)["passed"]


def test_geometry_range_cannot_be_averaged_away():
    names, rows, a, c = fixture()
    rows[1]["params"]["w"] = "32u"
    assert not reduce(a, names, rows, c)["passed"]


@pytest.mark.parametrize(
    "fault", ["nan", "duplicate", "gap", "early_end", "late_end", "missing_settled"]
)
def test_capture_time_or_nonfinite_rejected(fault):
    names, rows, a, c = fixture()
    if fault == "nan":
        a[-1, 1] = np.nan
    elif fault == "duplicate":
        a[50, 0] = a[49, 0]
    elif fault == "gap":
        a = np.delete(a, 50, axis=0)
    elif fault == "early_end":
        a = a[:-1]
    elif fault == "late_end":
        a[-1, 0] += 17 * np.spacing(c["stop_s"])
    else:
        c["window_s"] = [20e-9, 30e-9]
    with pytest.raises(ValueError):
        reduce(a, names, rows, c)


def test_deck_transport_only_and_declared_changes():
    text = (m.ORIGINAL / "bench.cir").read_text()
    new = m.stream_deck(text, 2.5e-12, 400e-9)
    restored = new.replace(".tran 2.5e-12 4e-07 0 2.5e-12\n", "").replace(
        "run stream.fifo\nsetplot\ndisplay\nrusage space\n",
        "tran 5e-12 3.4e-08 0 5e-12\nwrite wave.raw all\n",
    )
    assert restored == text
    for bad in [
        text.replace("write wave.raw all", "write truncated.raw all"),
        text + ".control\n",
    ]:
        with pytest.raises(ValueError):
            m.stream_deck(bad, 5e-12, 34e-9)
    with pytest.raises(ValueError):
        m.stream_deck(text, 20e-12, 34e-9)


def test_settling_detects_slip_frequency_and_phase_drift():
    t = np.arange(0, 400.005e-9, 5e-12)

    def data(period, shift=0):
        return dict(
            time=t,
            **{
                "v(reference)": 2.5 * (np.sin(2 * np.pi * (t - 4e-9) / 10e-9) > 0),
                "v(fb)": 2.5 * (np.sin(2 * np.pi * (t - 4e-9 - shift) / period) > 0),
                "v(vctrl)": np.ones(len(t)),
            },
        )

    assert m.settling(data(10e-9))["passed"]
    assert not m.settling(data(10.05e-9))["passed"]
    bad = data(10e-9)
    bad["v(fb)"][(t > 251e-9) & (t < 264e-9)] = 0
    assert not m.settling(bad)["passed"]
    bad = data(10e-9)
    bad["v(vctrl)"][-100:] = 1.51
    assert not m.settling(bad)["passed"]


@pytest.mark.parametrize("leader_exit", [False, True])
def test_adapter_failure_kills_native_and_ignoring_publisher(
    tmp_path, monkeypatch, leader_exit
):
    """Real separate process groups, exact late-write deadline; no SPICE here."""
    native = tmp_path / "native"
    native.write_text(
        '#!/usr/bin/env python3\nimport time\nf=open("stream.fifo","wb",buffering=0)\nf.write(b"ready")\ntime.sleep(60)\n'
    )
    native.chmod(0o755)
    monkeypatch.setattr(m.n, "NG", native)
    # Resource guard is unchanged; pytest's own fixture remains well below cap.
    marker = tmp_path / "late-marker"
    identity = tmp_path / "identity.json"
    deadline = time.monotonic() + 8
    child = (
        "import os,signal,time,json; from pathlib import Path; "
        "signal.signal(signal.SIGTERM,signal.SIG_IGN); "
        f"Path({str(identity)!r}).write_text(json.dumps({{'pid':os.getpid(),'deadline':{deadline!r}}})); "
        f"time.sleep(max(0,{deadline!r}-time.monotonic())); Path({str(marker)!r}).write_text('escaped')"
    )
    command = [sys.executable, "-c", child]
    if leader_exit:
        command = [
            sys.executable,
            "-c",
            f"import subprocess; subprocess.Popen({command!r})",
        ]

    def consume(stream, owner):
        assert stream.read(5) == b"ready"
        owner.launch("publisher", command)
        until = time.monotonic() + 3
        while not identity.exists() and time.monotonic() < until:
            time.sleep(0.01)
        assert identity.exists()
        raise RuntimeError("actual publication failure")

    with pytest.raises(RuntimeError, match="actual publication failure"):
        m.native_wait(tmp_path, consume)
    child_pid = json.loads(identity.read_text())["pid"]
    until = time.monotonic() + 1
    while time.monotonic() < until:
        found = m.life.process_identity(child_pid)
        if found is None or found["state"] == "Z":
            break
        time.sleep(0.01)
    assert found is None or found["state"] == "Z"
    time.sleep(max(0, deadline + 0.1 - time.monotonic()))
    assert not marker.exists()
    ledger = json.loads((tmp_path / "owned-processes.json").read_text())
    assert ledger["status"] == "CANCELLED"
    assert (
        json.loads((tmp_path / "execution.json").read_text())["returncode"] is not None
    )


def test_prerequisite_rejects_forged_status_or_hash(tmp_path):
    p = tmp_path / "gate.json"
    p.write_text(json.dumps(dict(status="FAIL_NATIVE_STREAM_FINITE_SCREEN")))
    with pytest.raises(ValueError):
        m.bind_receipt(p, m.n.common.sha(p), "PASS_NATIVE_STREAM_FINITE_SCREEN")
    with pytest.raises(ValueError):
        m.bind_receipt(p, "0" * 64, "FAIL_NATIVE_STREAM_FINITE_SCREEN")


def test_columns_bijection_rejects_duplicate():
    names, rows, a, c = fixture()
    with pytest.raises(ValueError):
        m.Meter(names + [names[-1]], rows, c, observations=["time"])


def test_actual_complete_stream_parser_and_final_sample_safety(tmp_path, monkeypatch):
    """Real binary decoder/queue; synthetic circuit observation, not native proof."""
    prior = json.loads((m.ORIGINAL / "result.json").read_text())
    columns = ["time", *m.n.vectors(prior["devices"], prior["config"]["extra_vectors"])]
    a = np.zeros((3, len(columns)))
    a[:, 0] = [0, 5e-12, 10e-12]
    # A late current observation must survive decoder/queue boundaries.
    column = next(
        i for i, s in enumerate(columns) if s.startswith("@q.") and "[ic]" in s
    )
    a[-1, column] = 0.1
    header = (
        "Title: test\nPlotname: Transient Analysis\nFlags: real\n"
        f"No. Variables: {len(columns)}\nNo. Points: 0\nVariables:\n"
        + "".join(
            f"{i}\t{s}\t"
            + ("time" if i == 0 else "current" if s.startswith("@") else "voltage")
            + "\n"
            for i, s in enumerate(columns)
        )
        + "Binary:\n"
    ).encode()
    raw = header + a.astype("<f8").tobytes() + b"3"
    config = dict(
        prior["config"], step_s=5e-12, stop_s=10e-12, window_s=[5e-12, 10e-12]
    )
    monkeypatch.setattr(
        m, "measurements", lambda data, config: dict(parser_only=True, passed=False)
    )

    def publisher(path, receipt):
        # Unit transport substitute, explicitly neither live nor native evidence.
        receipt.write_text("{}")
        return dict(
            name=path.name,
            **m.n.common.pin(path),
            authenticated_roundtrip=True,
            anonymous_roundtrip=True,
        )

    good = m.capture(
        io.BytesIO(raw),
        tmp_path / "good",
        prior,
        config,
        "unit-parser-only",
        publisher,
        rows_per_part=2,
    )
    assert good["rows"] == 3 and not good["safety"]["passed"]
    observed = next(
        x for x in good["safety"]["all_device_bounds"] if x["model"] == "npn13g2"
    )
    assert observed["max_capture_ic_per_nx"] > 0.003
    for label, body in [
        ("trailer", raw[:-1] + b"2"),
        ("partial", raw[:-4]),
        ("variable", raw.replace(b"\tv(clkp)\t", b"\tv(wrong)\t", 1)),
    ]:
        with pytest.raises((ValueError, AssertionError)):
            m.capture(
                io.BytesIO(body),
                tmp_path / label,
                prior,
                config,
                "unit-parser-only",
                publisher,
                rows_per_part=2,
            )


def test_prerequisite_output_mutation_rejected(tmp_path):
    evidence = tmp_path / "capture.json"
    evidence.write_text('{"rows": 7}')
    p = tmp_path / "result.json"
    p.write_text(
        json.dumps(
            dict(
                status="PASS_NATIVE_STREAM_FINITE_SCREEN",
                outputs={"capture.json": m.n.common.pin(evidence)},
            )
        )
    )
    digest = m.n.common.sha(p)
    assert m.bind_receipt(p, digest, "PASS_NATIVE_STREAM_FINITE_SCREEN")
    evidence.write_text('{"rows": 6}')
    with pytest.raises(ValueError, match="output drift"):
        m.bind_receipt(p, digest, "PASS_NATIVE_STREAM_FINITE_SCREEN")
