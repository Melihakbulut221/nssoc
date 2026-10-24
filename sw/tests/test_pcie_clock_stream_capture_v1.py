# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
import copy
import io
import math
from pathlib import Path
import struct
import sys
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import probe_pcie_clock_stream_capture_v1 as p  # noqa: E402


def raw(fifo=False, fault=False):
    rows = []
    for i in range(2001):
        t = i * 0.5e-12
        rail = 2.415 * min(1, t / 0.5e-9)
        if fault and t > 0.75e-9:
            rail = 0
        rows.append((t, rail, math.sin(i / 30)))
    head = f"Title: tiny\nDate: test\nCommand: ngspice-47\nPlotname: Transient Analysis\nFlags: real\nNo. Variables: 3\nNo. Points: {0 if fifo else len(rows)}\nVariables:\n0 time time\n1 v(avdd) voltage\n2 v(x) voltage\nBinary:\n".encode()
    body = b"".join(struct.pack("<3d", *r) for r in rows)
    return head + body + (str(len(rows)).encode() if fifo else b"")


def test_exact_file_fifo_binary_identity_and_late_fault(tmp_path):
    results = []
    for fifo in (False, True):
        r = p.capture(
            io.BytesIO(raw(fifo)), tmp_path / str(fifo), ["v(avdd)", "v(x)"], fifo
        )
        p.replay_chunks(tmp_path / str(fifo), r)
        results.append(r)
        assert not r["late_rail_fault_detected"] and r["rows"] == 2001
        assert (
            len(r["chunks"]) == 8 and r["max_uncompressed_chunk_bytes"] == 256 * 3 * 8
        )
    assert results[0]["payload_sha256"] == results[1]["payload_sha256"]
    r = p.capture(
        io.BytesIO(raw(True, True)), tmp_path / "fault", ["v(avdd)", "v(x)"], True
    )
    assert 0.75e-9 < r["first_rail_fault_s"] < 0.751e-9
    assert r["late_rail_fault_detected"]


@pytest.mark.parametrize(
    "mutation",
    [
        "count",
        "missing_count",
        "junk",
        "truncated",
        "time_reverse",
        "not_time0",
        "infinite",
        "wrong_column",
        "duplicate_id",
        "complex",
        "missing_header",
        "duplicate_field",
    ],
)
def test_corrupt_stream_fails_closed(tmp_path, mutation):
    data = raw(True)
    head, body = data.split(b"Binary:\n", 1)
    if mutation == "count":
        body = body[:-4] + b"2000"
    elif mutation == "missing_count":
        body = body[:-4]
    elif mutation == "junk":
        body += b"extra"
    elif mutation == "truncated":
        body = body[:-29]
    elif mutation == "time_reverse":
        body = body[:24] + struct.pack("<d", 0) + body[32:]
    elif mutation == "not_time0":
        body = struct.pack("<d", 1e-20) + body[8:]
    elif mutation == "infinite":
        body = body[:8] + struct.pack("<d", float("inf")) + body[16:]
    elif mutation == "wrong_column":
        head = head.replace(b"v(x)", b"v(other)")
    elif mutation == "duplicate_id":
        head = head.replace(b"2 v(x)", b"1 v(x)")
    elif mutation == "complex":
        head = head.replace(b"Flags: real", b"Flags: complex")
    elif mutation == "missing_header":
        head = head.replace(b"No. Points: 0\n", b"")
    elif mutation == "duplicate_field":
        head += b"No. Points: 0\n"
    with pytest.raises((ValueError, UnicodeDecodeError)):
        p.capture(
            io.BytesIO(head + b"Binary:\n" + body),
            tmp_path / "bad",
            ["v(avdd)", "v(x)"],
            True,
        )


@pytest.mark.parametrize(
    "mutation",
    ["omitted", "duplicate", "reorder", "changed_chunk", "wrong_hash", "wrong_rows"],
)
def test_chunk_inventory_requires_unique_exhaustive_original_bytes(tmp_path, mutation):
    r = p.capture(
        io.BytesIO(raw(True)), tmp_path / "capture", ["v(avdd)", "v(x)"], True
    )
    r = copy.deepcopy(r)
    if mutation == "omitted":
        r["chunks"].pop(3)
    elif mutation == "duplicate":
        r["chunks"].insert(1, copy.deepcopy(r["chunks"][0]))
    elif mutation == "reorder":
        r["chunks"][0], r["chunks"][1] = r["chunks"][1], r["chunks"][0]
    elif mutation == "changed_chunk":
        (tmp_path / "capture" / r["chunks"][0]["path"]).write_bytes(b"bad")
    elif mutation == "wrong_hash":
        r["payload_sha256"] = "0" * 64
    elif mutation == "wrong_rows":
        r["chunks"][0]["rows"] -= 1
    with pytest.raises(ValueError):
        p.replay_chunks(tmp_path / "capture", r)


def test_only_duration_backend_and_one_external_fault_change():
    root = Path("/dev/shm/nssoc-clock-trim-thermal40-v1")
    if not root.exists():
        pytest.skip("Optional exact local parent")
    original = (root / "fast_code2_v1.00_halfstep/bench.cir").read_text()
    normal = p.deck(original, "reference.raw", False)
    fifo = p.deck(original, "stream.fifo", False)
    assert normal.replace("reference.raw", "stream.fifo") == fifo
    assert p.deck(original, "reference.raw", True) == normal.replace(
        "VDD avdd 0 PWL(0 0 5e-10 2.415)",
        "VDD avdd 0 PWL(0 0 5e-10 2.415 7.5e-10 2.415 7.51e-10 0)",
    )
    assert (
        normal.count("alter @q.xosc.") == 30
        and normal.count("op\n") == 1
        and normal.count("run reference.raw") == 1
    )
    assert ".tran 5e-13 1n 0 5e-13" in normal
    assert "reset" not in normal and "resume" not in normal and "uic" not in normal


def test_no_partial_stream_can_report_complete_even_with_valid_prefix(tmp_path):
    source = raw(True)
    head, body = source.split(b"Binary:\n", 1)
    short = head + body[: 1000 * 24] + b"1000"
    with pytest.raises(ValueError):
        p.capture(io.BytesIO(short), tmp_path / "short", ["v(avdd)", "v(x)"], True)


def native_log_fixture():
    # Native display does not pad long device-vector names before its colon.
    return (
        "No. of Data Rows : 1\nNo. of Data Rows : 2001\nCurrent op1\n"
        "    avdd : voltage, real, 1 long\n"
        "    vdd#branch : current, real, 1 long\n"
        "    @q.xosc.xftnd3.qnpn13g2[ic]: current, real, 1 long\n"
        "Maximum ngspice program size = 30.109 MB\n"
    )


def test_native_retained_op_log_accepts_actual_long_name_format():
    captured = dict(
        rows=2001,
        columns=["time", "v(avdd)", "i(vdd)", "@q.xosc.xftnd3.qnpn13g2[ic]"],
    )
    result = p.native_log(native_log_fixture(), captured, [])
    assert result["retained_vector_length"] == 1
    assert result["native_peak_mb"] == 30.109


@pytest.mark.parametrize(
    "old,new",
    [
        ("2001", "2000"),
        ("Current op1", "Current tran1"),
        ("avdd :", "other :"),
        ("1 long", "2001 long"),
        ("30.109 MB", "128 MB"),
        ("Current op1", "Current op1\nWarning: invalid state"),
    ],
)
def test_native_plot_memory_claim_rejects_wrong_actual_log(old, new):
    captured = dict(
        rows=2001,
        columns=["time", "v(avdd)", "i(vdd)", "@q.xosc.xftnd3.qnpn13g2[ic]"],
    )
    with pytest.raises(ValueError):
        p.native_log(native_log_fixture().replace(old, new), captured, [])


@pytest.mark.parametrize(
    "status,code",
    [("PASS_TINY_NATIVE_STREAMING_CAPTURE", 0), ("RUNNING", 1), ("ERROR", 1)],
)
def test_cli_only_exact_completed_success_exits_zero(monkeypatch, status, code):
    monkeypatch.setattr(p, "run", lambda *_: {"status": status})
    monkeypatch.setattr(sys, "argv", ["probe", "--parent", "/tmp/p", "--out", "/tmp/o"])
    assert p.main() == code
