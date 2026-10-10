# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""The proof gate must wait for the real producer and reject missing evidence."""
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import verify_completed_pipeline as runner


def write_state(path, status, **values):
    row = dict(status=status, input_sha256={"input": "hash"}, **values)
    (path / "result.json").write_text(json.dumps(row))
    return row


def test_wait_beyond_old_thirteen_hour_limit(tmp_path):
    write_state(tmp_path, "RUNNING_POSTROUTE_TIMING_REPAIR_CANDIDATE")
    elapsed = 0

    def tick(seconds):
        nonlocal elapsed
        elapsed += seconds
        if elapsed == 50000:
            write_state(tmp_path, runner.READY, returncode=0)

    row = runner.wait_for_producer(tmp_path, {"input": "hash"}, 4, "5",
                                   alive=lambda *_: True, sleep=tick)
    assert elapsed > 46800 and row["returncode"] == 0


@pytest.mark.parametrize("status,code", [("ERROR", 1), ("UNKNOWN", 0), (runner.READY, 1)])
def test_rejects_failed_or_unknown_producer(tmp_path, status, code):
    write_state(tmp_path, status, returncode=code)
    with pytest.raises(ValueError):
        runner.wait_for_producer(tmp_path, {"input": "hash"}, 4, "5")


def test_dead_producer_does_not_wait_forever(tmp_path):
    write_state(tmp_path, "RUNNING_POSTROUTE_TIMING_REPAIR_CANDIDATE")
    with pytest.raises(RuntimeError, match="exited or PID was reused"):
        runner.wait_for_producer(tmp_path, {"input": "hash"}, 4, "5", alive=lambda *_: False)


def test_final_write_exit_race(tmp_path):
    write_state(tmp_path, "RUNNING_POSTROUTE_TIMING_REPAIR_CANDIDATE")

    def exits(*_):
        write_state(tmp_path, runner.READY, returncode=0)
        return False

    assert runner.wait_for_producer(tmp_path, {"input": "hash"}, 4, "5", alive=exits)["returncode"] == 0


@pytest.mark.parametrize("state,birth,expected", [("S", "123", True), ("Z", "123", False), ("R", "124", False)])
def test_pid_reuse_and_zombie_rejected(tmp_path, state, birth, expected):
    process = tmp_path / "4"
    process.mkdir()
    (process / "stat").write_text("4 (producer (name)) " + " ".join([state] + ["0"] * 18 + [birth]))
    assert runner.process_alive(4, "123", tmp_path) is expected
    assert not runner.process_alive(5, "123", tmp_path)


def test_changed_producer_inventory_rejected(tmp_path):
    write_state(tmp_path, runner.READY, returncode=0)
    with pytest.raises(ValueError, match="inventory changed"):
        runner.producer_state(tmp_path, {"input": "different"})


def test_in_place_final_write_can_finish(tmp_path, monkeypatch):
    (tmp_path / "result.json").write_text("{")
    monkeypatch.setattr(runner.time, "sleep", lambda _: write_state(tmp_path, runner.READY, returncode=0))
    assert runner.producer_state(tmp_path, {"input": "hash"})["returncode"] == 0


def test_persistently_malformed_result_rejected(tmp_path, monkeypatch):
    (tmp_path / "result.json").write_text("{")
    monkeypatch.setattr(runner.time, "sleep", lambda _: None)
    with pytest.raises(json.JSONDecodeError):
        runner.producer_state(tmp_path, {"input": "hash"})


def test_changed_input_bytes_rejected(tmp_path):
    source = tmp_path / "source"
    source.write_bytes(b"original")
    pins = {str(source): runner.digest(source)}
    runner.verify_pins(pins)
    source.write_bytes(b"changed")
    with pytest.raises(ValueError, match="Changed proof input"):
        runner.verify_pins(pins)
    with pytest.raises(ValueError, match="Missing input hashes"):
        runner.verify_pins({})


@pytest.mark.parametrize("defect", [None, "escape", "symlink", "missing_macro", "liberty"])
def test_completed_producer_requires_own_netlist_and_libraries(tmp_path, defect):
    producer = tmp_path / "producer"
    final = producer / "run/final"
    final.mkdir(parents=True)
    netlist = final / "soc.nl.v"
    netlist.write_text("module soc_top; endmodule")
    foreign = tmp_path / "foreign.v"
    foreign.write_text("module foreign; endmodule")
    if defect == "escape":
        netlist = foreign
    if defect == "symlink":
        netlist.unlink()
        netlist.symlink_to(foreign)
    lib = tmp_path / "stdcell.lib"
    lib.write_text("library(test) {}")
    (final / "state.json").write_text(json.dumps({"nl": str(netlist)}))
    cfg = dict(MACROS={"sp": {"instances": list(range(30))}, "dp": {"instances": [1, 2]}},
               LIB={"nom_slow_1p08V_125C": [str(lib)]})
    if defect == "missing_macro": cfg["MACROS"]["sp"]["instances"].pop()
    if defect == "liberty": lib.unlink()
    (producer / "run/resolved.json").write_text(json.dumps(cfg))
    if defect:
        with pytest.raises(ValueError): runner.completed_inputs(producer)
    else:
        after, actual_lib, _ = runner.completed_inputs(producer)
        assert after == netlist and actual_lib == lib
