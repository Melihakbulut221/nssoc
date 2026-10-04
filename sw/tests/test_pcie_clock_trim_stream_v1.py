# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import copy
import io
import json
import math
from pathlib import Path
import struct
import sys
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import characterize_pcie_clock_trim_stream_v1 as m  # noqa: E402


def context():
    case = dict(m.base.cases()[0], step_s=6e-12)
    hbts = m.base.driver.contract(m.base.circuit(case), 4)
    return case, hbts, ["time", *m.base.prior.vectors(hbts)]


@pytest.fixture(scope="module")
def data():
    case, hbts, cols = context()
    data = {n: [] for n in cols}
    for i in range(2001):
        t = i * 6e-12
        ramp = min(1, t / 0.5e-9)
        row = {n: 0.0 for n in cols}
        row["time"] = t
        for n in cols[1:]:
            if n.endswith((".t)", ".dt)")):
                v = t * 1e9 * 0.005
            elif n.endswith("[ic]"):
                v = 1e-4 * ramp
            elif n.endswith("[ib]"):
                v = 1e-6 * ramp
            elif n in ("v(avdd)", "v(trim0)", "v(trim1)"):
                v = case["supply"] * ramp
            elif n.startswith("v(xosc.tp") or n == "v(xosc.tmid)":
                v = 1.2 * ramp
            elif n in [
                "v(xosc." + x + ")"
                for x in ("p0", "n0", "p1", "n1", "p2", "n2", "bo_p", "bo_n")
            ]:
                v = 1.8 * ramp
            elif n.startswith("v("):
                v = 0.7 * ramp
            else:
                v = 0.0
            row[n] = v
        row["v(clkp)"] = (1.2 + 0.3 * math.sin(2 * math.pi * 8e9 * t)) * ramp
        row["v(clkn)"] = (1.2 - 0.3 * math.sin(2 * math.pi * 8e9 * t)) * ramp
        for n in cols:
            data[n].append(row[n])
    return case, hbts, data


def reduced(case, hbts, data):
    meter = m.Meter(list(data), hbts, case, 12e-9)
    for row in zip(*data.values()):
        meter.push(row)
    return meter.finish()


def same(a, b):
    if isinstance(a, dict):
        assert a.keys() == b.keys()
        for k in a:
            same(a[k], b[k])
    elif isinstance(a, (list, tuple)):
        assert len(a) == len(b)
        for x, y in zip(a, b):
            same(x, y)
    elif isinstance(a, float):
        assert math.isclose(a, b, rel_tol=1e-12, abs_tol=1e-14)
    else:
        assert a == b


def test_stream_reductions_match_frozen_full_array_algorithms(data):
    case, hbts, full = data
    actual = reduced(case, hbts, full)
    expected = m.base.prior.measure(full, hbts, case)
    for name in (
        "devices",
        "switches",
        "trim_gate_rail_error_v",
        "mean_common_mode_v",
        "mean_supply_power_w",
    ):
        same(actual[name], expected[name])
    assert actual["safety_checks"] == {
        k: v
        for k, v in expected["checks"].items()
        if k not in m.base.driver.FUNCTIONAL_CHECKS
    }
    same(actual["final_clock_window"], m.base.clock_window(full, 4e-9, 12e-9))
    assert all(actual["safety_checks"].values())
    for i, w in enumerate(actual["consecutive2ns_windows"]):
        start, end = i * m.WINDOW, min((i + 1) * m.WINDOW, 12e-9)
        same(
            {k: v for k, v in w.items() if k != "thermal_nodes"},
            m.base.clock_window(full, start, end),
        )
        lo, hi = m.base.indices(full, start, end)
        for n, stats in w["thermal_nodes"].items():
            vals = full[n][lo:hi]
            same(
                stats,
                dict(
                    start_v=vals[0],
                    end_v=vals[-1],
                    min_v=min(vals),
                    max_v=max(vals),
                    mean_v=m.statistics.mean(vals),
                    signed_rate_v_per_ns=(vals[-1] - vals[0])
                    / (full["time"][hi - 1] - full["time"][lo])
                    * 1e-9,
                ),
            )


@pytest.mark.parametrize("kind", ["late_vce", "late_ic", "late_switch", "late_rail"])
def test_real_late_sample_cannot_escape_fulltime_safety(data, kind):
    case, hbts, original = data
    full = copy.deepcopy(original)
    if kind == "late_vce":
        full["v(clkp)"][-3] = -3.0
    elif kind == "late_ic":
        full["@q.xosc.xref.qnpn13g2[ic]"][-3] = 1.0
    elif kind == "late_switch":
        full["v(xosc.tp00p)"][-3] = 4.0
    else:
        full["v(trim1)"][-3] = 0.0
    actual = reduced(case, hbts, full)
    assert not all(actual["safety_checks"].values())
    assert not actual["limited_thermal_screen_pass"]


def mock_publish(path, receipt):
    asset = dict(
        name=path.name,
        bytes=path.stat().st_size,
        sha256=m.sha(path),
        authenticated_roundtrip=True,
        anonymous_roundtrip=True,
        url="https://example.invalid/unit-control-only",
    )
    receipt.write_text(json.dumps(dict(unit_control_only=True, asset=asset)))
    return asset


def native_raw(data, count=None, trailer=None):
    cols = list(data)
    rows = len(data["time"])
    names = ["time"] + [f"v({x})" if x.startswith("@") else x for x in cols[1:]]
    header = f"Title: synthetic\nPlotname: Transient Analysis\nFlags: real\nNo. Variables: {len(cols)}\nNo. Points: {0 if count is None else count}\nVariables:\n"
    header += (
        "\n".join(
            f"{i} {n} {'time' if i == 0 else 'voltage'}" for i, n in enumerate(names)
        )
        + "\nBinary:\n"
    )
    payload = b"".join(
        struct.pack("<" + "d" * len(cols), *r) for r in zip(*data.values())
    )
    return (
        header.encode() + payload + (str(rows).encode() if trailer is None else trailer)
    )


def test_complete_capture_queue_has_every_point_and_does_not_decimate(tmp_path, data):
    case, hbts, full = data
    out = tmp_path / "capture"
    result = m.capture_stream(
        io.BytesIO(native_raw(full)),
        out,
        m.base.prior.vectors(hbts),
        hbts,
        case,
        "unit-native",
        stop=12e-9,
        publisher=mock_publish,
        rows_per_part=256,
        reclaim=False,
        min_free_bytes=0,
    )
    ledger = json.loads((out / "parts/parts.json").read_text())
    assert ledger["queue_capacity"] == 1 and len(ledger["parts"]) == 8
    assert sum(p["rows"] for p in ledger["parts"]) == 2001
    payload = b"".join(
        m.lzma.decompress((out / "parts" / p["name"]).read_bytes())
        for p in ledger["parts"]
    )
    assert m.hashlib.sha256(payload).hexdigest() == result["payload_sha256"]
    assert result["status"] == "PASS_COMPLETE_CAPTURE"


@pytest.mark.parametrize(
    "fault", ["count", "trailer", "truncated", "gap", "nonfinite", "unknown_vector"]
)
def test_corrupt_stream_rejected_and_partial_capture_preserved(tmp_path, data, fault):
    case, hbts, full = data
    full = copy.deepcopy(full)
    if fault == "gap":
        full["time"][100] += case["step_s"] * 0.5
    if fault == "nonfinite":
        full["v(clkp)"][100] = math.nan
    raw = native_raw(
        full,
        count=1 if fault == "count" else None,
        trailer=b"wrong" if fault == "trailer" else None,
    )
    if fault == "truncated":
        raw = raw[:-1500]
    if fault == "unknown_vector":
        raw = raw.replace(b"v(clkp)", b"v(blkp)")
    out = tmp_path / "capture"
    with pytest.raises(ValueError):
        m.capture_stream(
            io.BytesIO(raw),
            out,
            m.base.prior.vectors(hbts),
            hbts,
            case,
            "unit-native",
            stop=12e-9,
            publisher=mock_publish,
            rows_per_part=256,
            reclaim=False,
            min_free_bytes=0,
        )
    assert not (out / "capture.json").exists()


@pytest.mark.parametrize(
    "fault",
    [
        "wrong_digest",
        "missing_auth",
        "missing_anon",
        "late_mutation",
        "publisher_error",
        "missing_receipt",
    ],
)
def test_failed_publication_retains_exact_part_and_never_advances(tmp_path, fault):
    def bad(path, receipt):
        asset = mock_publish(path, receipt)
        if fault == "wrong_digest":
            asset["sha256"] = "0" * 64
        elif fault == "missing_auth":
            asset["authenticated_roundtrip"] = False
        elif fault == "missing_anon":
            asset["anonymous_roundtrip"] = False
        elif fault == "late_mutation":
            path.write_bytes(b"changed")
        elif fault == "publisher_error":
            raise RuntimeError("Actual control publication failure")
        else:
            receipt.unlink()
        return asset

    q = m.PartQueue(tmp_path / "parts", "unit-failure", ["time"], bad, 1, True, 0)
    with pytest.raises((ValueError, RuntimeError)):
        q.append(struct.pack("<d", 0.0))
    assert len(q.parts) == 1 and q.parts[0]["status"] == "PUBLICATION_FAILED"
    assert (q.root / q.parts[0]["name"]).exists()
    assert not q.ledger.get("status", "").startswith("PASS")


def test_part_reclaimed_only_after_persisted_two_path_receipt(tmp_path):
    order = []

    def publish(path, receipt):
        assert path.exists() and not order
        order.append("publication")
        return mock_publish(path, receipt)

    q = m.PartQueue(tmp_path / "parts", "unit-reclaim", ["time"], publish, 1, True, 0)
    q.append(struct.pack("<d", 0.0))
    assert order == ["publication"] and not (q.root / q.parts[0]["name"]).exists()
    assert q.parts[0]["local_state"] == "REMOVED_EXACT_PUBLIC_DUPLICATE"
    assert q.finish()["status"] == "PASS_PUBLISHED_PARTS"


def test_queue_backpressure_blocks_before_second_part(tmp_path):
    seen = []

    def wait(path, receipt):
        time.sleep(0.02)
        seen.append(path.name)
        return mock_publish(path, receipt)

    q = m.PartQueue(tmp_path / "parts", "unit-block", ["time"], wait, 1, False, 0)
    before = time.monotonic()
    q.append(struct.pack("<d", 0.0))
    assert time.monotonic() - before >= 0.02 and len(seen) == 1 and len(q.parts) == 1
    q.append(struct.pack("<d", 1.0))
    assert len(seen) == 2


@pytest.mark.parametrize("fault", ["early_exit", "consumer_failure"])
def test_control_process_lifetime_is_complete_or_stopped_on_actual_failure(
    tmp_path, fault
):
    root = tmp_path / "native"
    root.mkdir()
    runtime = root / "writer"
    text = "#!/usr/bin/python3\nimport pathlib\n"
    if fault == "early_exit":
        text += "raise SystemExit(7)\n"
    else:
        text += 'with open("stream.fifo","wb",buffering=0) as f:\n while True:f.write(b"x"*65536)\n'
    runtime.write_text(text)
    runtime.chmod(0o700)

    def fail(stream):
        if fault == "early_exit":
            assert stream.read(1) == b""
            raise ValueError("Actual early process exit")
        assert stream.read(10) == b"x" * 10
        raise ValueError("Actual parser control rejection")

    with pytest.raises(ValueError):
        m.native_wait(runtime, root, root / "run.log", fail)
    receipt = json.loads((root / "native-process.json").read_text())
    assert receipt["status"] == "EXITED" and receipt["returncode"] != 0
    assert receipt["elapsed_watchdog_seconds"] is None and receipt["capture_error"]
    assert not Path("/proc", str(receipt["pid"])).exists()


def test_long_deck_changes_only_duration_recording_and_retains_native_initialization():
    parent = Path("/dev/shm/nssoc-clock-trim-thermal40-v1")
    if not parent.exists():
        pytest.skip("Optional exact native parent")
    record, pins = m.verify_parent(parent)
    assert len(record["cases"]) == 2 and len(pins) > 90
    for row in record["cases"]:
        text = (parent / row["case"]["name"] / "bench.cir").read_text()
        changed = m.long_deck(text, row["case"]["step_s"])
        assert (
            changed.count("alter @q.xosc.") == 30
            and changed.count("run stream.fifo") == 1
        )
        assert changed.count("op\n") == 1 and "wrdata initial-op.dat" in changed
        assert "1u 0 " in changed and "reset" not in changed and "uic" not in changed


@pytest.mark.parametrize(
    "status,code",
    [
        ("PASS_LIMITED1US_THERMAL_SCREEN", 0),
        ("FAIL_LIMITED1US_THERMAL_SCREEN", 1),
        ("ERROR_INCOMPLETE", 1),
        ("RUNNING", 1),
    ],
)
def test_cli_only_completed_pair_pass_exits_zero(monkeypatch, status, code):
    monkeypatch.setattr(m, "run", lambda *_: {"status": status})
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "method",
            "--parent",
            "/tmp/p",
            "--out",
            "/tmp/o",
            "--release-prefix",
            "unit-test",
        ],
    )
    assert m.main() == code


@pytest.mark.parametrize("ulps", [1, 4, 5, 10])
def test_only_four_ulp_native_endpoint_classification_retains_raw_sample(data, ulps):
    case, hbts, original = data
    full = copy.deepcopy(original)
    full["time"][-1] = 12e-9 + ulps * math.ulp(12e-9)
    if ulps <= 4:
        value = reduced(case, hbts, full)
        assert value["raw_final_time_s"] == full["time"][-1]
        assert value["all_column_ranges"]["time"][1] == full["time"][-1]
        assert value["rows"] == len(full["time"])
        assert value["final_clock_window"]["actual_samples_s"][-1] == 12e-9
    else:
        with pytest.raises(ValueError, match="endpoint"):
            reduced(case, hbts, full)


@pytest.mark.parametrize(
    "fault",
    [
        "changed_compressed",
        "changed_raw_pin",
        "omit",
        "duplicate",
        "reorder",
        "wrong_union",
    ],
)
def test_offline_part_replay_rejects_corrupt_and_incomplete_artifact(tmp_path, fault):
    q = m.PartQueue(
        tmp_path / "parts", "unit-replay", ["time"], mock_publish, 1, False, 0
    )
    q.append(struct.pack("<d", 0.0))
    q.append(struct.pack("<d", 1.0))
    ledger = q.finish()
    assert b"".join(m.replay_local_parts(q.root, ledger)) == struct.pack(
        "<dd", 0.0, 1.0
    )
    ledger = copy.deepcopy(ledger)
    if fault == "changed_compressed":
        (q.root / ledger["parts"][0]["name"]).write_bytes(b"corrupted")
    elif fault == "changed_raw_pin":
        ledger["parts"][0]["uncompressed_sha256"] = "0" * 64
    elif fault == "omit":
        ledger["parts"].pop()
    elif fault == "duplicate":
        ledger["parts"].append(ledger["parts"][0])
    elif fault == "reorder":
        ledger["parts"].reverse()
    else:
        ledger["payload_sha256"] = "0" * 64
    with pytest.raises(ValueError):
        b"".join(m.replay_local_parts(q.root, ledger))


@pytest.mark.parametrize("mode", ["ignores_term", "leader_exits_first"])
def test_failed_process_group_cannot_write_after_return(tmp_path, mode):
    # The original immediate /proc observation failed under a real scheduler race.
    # Retain its exact source outside collection; use actual identity and latewrite.
    import test_pcie_clock_trim_stream_shutdown_v2 as shutdown

    result = shutdown.control(tmp_path / "native", mode == "leader_exits_first")
    assert result["exact_child_nonexecuting"] and result["marker_absent"]
    assert result["marker_checked_monotonic"] >= result["marker_deadline_monotonic"]


def test_actual_parent_sigint_cleans_ignoring_native_group(tmp_path):
    import os
    import signal
    import subprocess

    root = tmp_path / "native"
    root.mkdir()
    runtime = root / "writer"
    runtime.write_text(
        '#!/usr/bin/python3\nimport signal,time,pathlib\nsignal.signal(signal.SIGTERM,signal.SIG_IGN)\nwith open("stream.fifo","wb",buffering=0) as f:f.write(b"x")\npathlib.Path("writer-ready").write_text("ready")\ntime.sleep(7)\npathlib.Path("late-write").write_text("UNSAFE")\n'
    )
    runtime.chmod(0o700)
    controller = tmp_path / "controller.py"
    controller.write_text(
        "import sys,pathlib\nsys.path.insert(0,"
        + repr(str(Path(m.__file__).parent))
        + ")\nimport characterize_pcie_clock_trim_stream_v1 as m\nf=pathlib.Path("
        + repr(str(root))
        + ')\nm.native_wait(f/"writer",f,f/"run.log",lambda stream:stream.read())\n'
    )
    with (tmp_path / "controller.log").open("wb") as output:
        child = subprocess.Popen(
            [sys.executable, str(controller)],
            stdout=output,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        try:
            until = time.monotonic() + 3
            while not (root / "writer-ready").exists() and time.monotonic() < until:
                time.sleep(0.01)
            assert (root / "writer-ready").exists()
            child.send_signal(signal.SIGINT)
            assert child.wait(timeout=8) != 0
            receipt = json.loads((root / "native-process.json").read_text())
            assert receipt["status"] == "EXITED" and receipt["returncode"] != 0
            assert "KeyboardInterrupt" in receipt["error"]
            assert (
                not (root / "late-write").exists()
                and not Path("/proc", str(receipt["pid"])).exists()
            )
        finally:
            if child.poll() is None:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
            if (root / "native-process.json").exists():
                pg = json.loads((root / "native-process.json").read_text()).get(
                    "process_group"
                )
                if pg:
                    try:
                        os.killpg(pg, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
