# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Small synthetic checkpoints verify experimental selection and byte retention."""

import copy
import io
import json
from pathlib import Path
import signal
import subprocess
import sys
import tarfile
import time

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
import run_timing_experiments as experiments
import timing_process_guard as guard


def metrics(**updates):
    value = dict(setup_wns_ns=-5.0, hold_wns_ns=-1.0, setup_tns_ns=-4000.0,
                 hold_tns_ns=-20.0, setup_violating_endpoints=1300,
                 hold_violating_endpoints=20, slew_violations=2,
                 capacitance_violations=4, area_um2=100.0, instance_count=50,
                 utilization_fraction=.5)
    value.update(updates)
    return value


def setup_row(profile, seconds, **improvements):
    before = metrics()
    return dict(profile=profile, elapsed_seconds=seconds, before=before,
                after=metrics(**improvements), eligible_estimate=True)


def native_state(tmp_path):
    value = {}
    for name in ("odb", "nl", "def", "sdc"):
        path = tmp_path / f"soc_top.{name}"
        path.write_bytes(f"fixture {name}\n".encode())
        value[name] = str(path)
    liberty = tmp_path / "slow.lib"
    liberty.write_text("fixture library\n")
    value["lib"] = {"slow": [str(liberty)]}
    path = tmp_path / "state_out.json"
    path.write_text(json.dumps(value))
    return path, value


def test_eligibility_requires_real_progress_and_retains_source_guard():
    before = metrics()
    after = metrics(setup_wns_ns=-4.8, setup_tns_ns=-3900.0)
    assert experiments.eligible(before, after, before, "setup")
    assert not experiments.eligible(before, before, before, "setup")
    # Rebuilding global parasitics can worsen the starting point. Beating that
    # rebuilt point alone must not allow regression from the source checkpoint.
    source = metrics(setup_wns_ns=-4.5)
    assert not experiments.eligible(before, after, source, "setup")


@pytest.mark.parametrize("regression", [
    {"hold_wns_ns": -1.01}, {"hold_tns_ns": -20.1},
    {"setup_tns_ns": -4001.0}, {"setup_violating_endpoints": 1301},
    {"hold_violating_endpoints": 21}, {"slew_violations": 3},
    {"capacitance_violations": 5},
])
def test_setup_gain_cannot_hide_other_regressions(regression):
    before = metrics()
    after = metrics(setup_wns_ns=-4.0, **regression)
    assert not experiments.eligible(before, after, before, "setup")


def test_hold_candidate_must_preserve_setup():
    before = metrics()
    good = metrics(hold_wns_ns=-.8, hold_tns_ns=-15.0)
    assert experiments.eligible(before, good, before, "hold")
    bad = good | {"setup_wns_ns": -5.1}
    assert not experiments.eligible(before, bad, before, "hold")


def test_batch_selection_requires_both_hourly_rates_to_improve():
    control = setup_row("setup_baseline", 3600, setup_wns_ns=-4.8, setup_tns_ns=-3900.0)
    batch = setup_row("setup_batch4", 1800, setup_wns_ns=-4.8, setup_tns_ns=-3900.0)
    assert experiments.choose_setup(control, batch) is batch
    batch["after"]["setup_tns_ns"] = -3960.0
    assert experiments.choose_setup(control, batch) is control
    batch["after"] = copy.deepcopy(control["after"])
    batch["elapsed_seconds"] = 3600
    assert experiments.choose_setup(control, batch) is control


def test_batch_selection_never_returns_an_ineligible_candidate():
    control = setup_row("setup_baseline", 3600, setup_wns_ns=-4.8, setup_tns_ns=-3900.0)
    batch = setup_row("setup_batch4", 1800, setup_wns_ns=-4.8, setup_tns_ns=-3900.0)
    batch["eligible_estimate"] = False
    assert experiments.choose_setup(control, batch) is control
    control["eligible_estimate"] = False
    assert experiments.choose_setup(control, batch) is None
    batch["eligible_estimate"] = True
    assert experiments.choose_setup(control, batch) is batch


@pytest.mark.parametrize("elapsed", [0, -1, float("nan"), float("inf")])
def test_rate_rejects_invalid_duration(elapsed):
    row = setup_row("setup_batch4", elapsed)
    with pytest.raises(ValueError):
        experiments.setup_rates(row)


def test_state_pins_cover_every_native_referenced_view(tmp_path):
    path, value = native_state(tmp_path)
    pins = experiments.state_pins(path)
    expected = {str(path), *(value[key] for key in ("odb", "nl", "def", "sdc")), value["lib"]["slow"][0]}
    assert set(pins) == expected
    experiments.verify_pins(pins)
    Path(value["odb"]).write_text("changed checkpoint")
    with pytest.raises(RuntimeError, match="changed or missing"):
        experiments.verify_pins(pins)


@pytest.mark.parametrize("missing", ["odb", "nl", "def", "sdc", "lib"])
def test_missing_native_view_is_rejected(tmp_path, missing):
    path, value = native_state(tmp_path)
    target = value["lib"]["slow"][0] if missing == "lib" else value[missing]
    Path(target).unlink()
    with pytest.raises(RuntimeError, match="checkpoint"):
        experiments.state_pins(path)


def test_relative_required_view_cannot_escape_pin_inventory(tmp_path, monkeypatch):
    path, value = native_state(tmp_path)
    value["odb"] = "soc_top.odb"
    path.write_text(json.dumps(value))
    monkeypatch.chdir(tmp_path)
    with pytest.raises(RuntimeError):
        experiments.state_pins(path)


def resume_fixture(tmp_path):
    state, views = native_state(tmp_path)
    log = tmp_path / "openroad-resizertimingpostgrt.log"
    log.write_text("ALL_32_HARD_MACRO_MASTERS_LOCATIONS_ORIENTATIONS_PRESERVED\n"
                   "CHUNK_SETUP_WNS_BEGIN\nworst slack max -4.7\nCHUNK_SETUP_WNS_END\n"
                   "CHUNK_HOLD_WNS_BEGIN\nworst slack min -1.8\nCHUNK_HOLD_WNS_END\n"
                   "COMPLETE_CHECKPOINT_REQUIRES_FRESH_ROUTING_RCX_STA_AND_EQUIVALENCE\n")
    proof = dict(state=str(state), output_sha256=experiments.state_pins(state),
                 original_exit=dict(state="Z", exit_status_raw=0),
                 metrics=dict(setup_wns_ns=-4.7, hold_wns_ns=-1.8),
                 log_sha256=experiments.sha(log))
    proof_path = tmp_path / "proof.json"
    experiments.write_json(proof_path, proof)
    result = tmp_path / "previous.json"
    experiments.write_json(result, dict(status="FAILED_LAST_COMPLETE_CHECKPOINT_PRESERVED",
                                       old_controller_retired=True, baseline=proof,
                                       reservations=[dict(released=True)]))
    resume = dict(proof=str(proof_path), proof_sha256=experiments.sha(proof_path),
                  previous_result=str(result), previous_result_sha256=experiments.sha(result),
                  previous_controller=dict(pid=99999999, birth="10", boot_id="fixture"))
    return resume, proof, views


def test_completed_baseline_can_resume_without_old_live_controller(tmp_path, monkeypatch):
    resume, proof, _ = resume_fixture(tmp_path)
    monkeypatch.setattr(experiments, "snapshot", lambda _: None)
    assert experiments.resume_verified_checkpoint(resume) == proof


@pytest.mark.parametrize("defect", ["proof", "view", "log", "metrics", "reservation", "exit", "live"])
def test_resume_rejects_changed_or_unreleased_evidence(tmp_path, monkeypatch, defect):
    resume, proof, views = resume_fixture(tmp_path)
    monkeypatch.setattr(experiments, "snapshot", lambda _: None)
    if defect == "proof":
        Path(resume["proof"]).write_text("changed")
    elif defect == "view":
        Path(views["odb"]).write_text("changed")
    elif defect == "log":
        (tmp_path / "openroad-resizertimingpostgrt.log").write_text("changed")
    elif defect == "live":
        monkeypatch.setattr(experiments, "snapshot", lambda _: resume["previous_controller"] | dict(state="S"))
    else:
        previous = json.loads(Path(resume["previous_result"]).read_text())
        if defect == "reservation":
            previous["reservations"][0]["released"] = False
        else:
            if defect == "metrics":
                proof["metrics"]["setup_wns_ns"] = 0.0
            else:
                proof["original_exit"]["exit_status_raw"] = 256
            previous["baseline"] = proof
            experiments.write_json(resume["proof"], proof)
            resume["proof_sha256"] = experiments.sha(resume["proof"])
        experiments.write_json(resume["previous_result"], previous)
        resume["previous_result_sha256"] = experiments.sha(resume["previous_result"])
    with pytest.raises(RuntimeError):
        experiments.resume_verified_checkpoint(resume)


def test_native_run_directory_created_before_spawn_and_never_reused(tmp_path, monkeypatch):
    state, _ = native_state(tmp_path)
    campaign = object.__new__(experiments.Campaign)
    campaign.directory = tmp_path
    campaign.root = tmp_path
    campaign.plan = dict(app="native-app", pdk_root="pdk", method_sha256={})
    campaign.record = dict(stages=[])
    monkeypatch.setattr(campaign, "reserve_resources", lambda: None)
    monkeypatch.setattr(campaign, "release_resources", lambda: None)
    monkeypatch.setattr(campaign, "save", lambda **kw: None)
    calls = []

    def stop_before_native(command, **kwargs):
        run = Path(command[command.index("--force-run-dir") + 1])
        assert run.is_dir()
        calls.append(command)
        raise RuntimeError("Reached native boundary with existing run directory")

    monkeypatch.setattr(experiments.subprocess, "Popen", stop_before_native)
    with pytest.raises(RuntimeError, match="Reached native boundary"):
        campaign.run_stage("critical_xnor", str(state), {})
    with pytest.raises(FileExistsError):
        campaign.run_stage("critical_xnor", str(state), {})
    assert len(calls) == 1


def test_archive_roundtrip_preserves_all_bytes(tmp_path):
    directory = tmp_path / "checkpoint"
    (directory / "nested").mkdir(parents=True)
    contents = {"state.json": b'{"fixture":true}\n', "nested/odb": bytes(range(256)) * 4,
                "empty.log": b""}
    for name, data in contents.items():
        (directory / name).write_bytes(data)
    receipt = experiments.archive_directory(directory)
    assert receipt["roundtrip_verified"] is True and not directory.exists()
    assert set(receipt["inventory"]) == set(contents)
    assert Path(receipt["archive"]).is_file()
    experiments.restore_directory(receipt)
    assert {name: (directory / name).read_bytes() for name in contents} == contents
    with pytest.raises(RuntimeError, match="Unsafe checkpoint restoration"):
        experiments.restore_directory(receipt)


def test_archive_does_not_delete_unverified_source(tmp_path, monkeypatch):
    directory = tmp_path / "checkpoint"
    directory.mkdir()
    source = directory / "odb"
    source.write_bytes(b"original bytes")

    def changed_during_archive(_pins):
        source.write_bytes(b"new bytes after compression")
        raise RuntimeError("Synthetic concurrent source change")

    monkeypatch.setattr(experiments, "verify_pins", changed_during_archive)
    with pytest.raises(RuntimeError, match="concurrent source change"):
        experiments.archive_directory(directory)
    assert source.read_bytes() == b"new bytes after compression"
    assert directory.with_suffix(".tar.gz").exists()


def test_archive_refuses_symlink(tmp_path):
    directory = tmp_path / "checkpoint"
    directory.mkdir()
    target = tmp_path / "external"
    target.write_bytes(b"must remain")
    (directory / "reference").symlink_to(target)
    with pytest.raises(RuntimeError, match="symlink"):
        experiments.archive_directory(directory)
    assert target.read_bytes() == b"must remain" and directory.exists()


def test_restore_refuses_modified_archive_before_creating_directory(tmp_path):
    directory = tmp_path / "checkpoint"
    directory.mkdir()
    (directory / "odb").write_bytes(b"fixture")
    receipt = experiments.archive_directory(directory)
    with Path(receipt["archive"]).open("ab") as stream:
        stream.write(b"tampered")
    with pytest.raises(RuntimeError, match="Unsafe checkpoint restoration"):
        experiments.restore_directory(receipt)
    assert not directory.exists()


def test_restore_refuses_path_traversal(tmp_path):
    archive = tmp_path / "unsafe.tar.gz"
    name = "../escaped"
    with tarfile.open(archive, "w:gz") as stream:
        member = tarfile.TarInfo("checkpoint/" + name)
        member.size = 1
        stream.addfile(member, io.BytesIO(b"x"))
    receipt = dict(path=str(tmp_path / "checkpoint"), archive=str(archive),
                   sha256=experiments.sha(archive), inventory={name: {"bytes": 1, "sha256": "unused"}})
    with pytest.raises(RuntimeError, match="Unsafe checkpoint archive member"):
        experiments.restore_directory(receipt)
    assert not (tmp_path / "escaped").exists()


def test_live_orphan_in_stage_group_prevents_supply_resume(tmp_path, monkeypatch):
    pidfile = tmp_path / "synthetic-worker.pid"
    program = ("import subprocess,sys;from pathlib import Path;"
               "p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'],"
               "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);"
               f"Path({str(pidfile)!r}).write_text(str(p.pid))")
    launcher = subprocess.Popen([sys.executable, "-c", program], start_new_session=True,
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    worker = None
    try:
        assert launcher.wait(timeout=5) == 0
        worker = guard.snapshot(int(pidfile.read_text()))
        assert worker is not None and worker["state"] != "Z"
        assert worker["group"] == launcher.pid and worker["parent"] != launcher.pid
        campaign = experiments.Campaign.__new__(experiments.Campaign)
        campaign.active_run = tmp_path / "isolated-fixture-stage"
        campaign.active_groups = {launcher.pid}
        campaign.active_child = None
        campaign.supply_reserved = True
        campaign.plan = {"supply_controller": {"fixture": "never signal a real queue"}}
        campaign.record = {"reservations": [{"released": False}]}
        campaign.save = lambda **updates: campaign.record.update(updates)
        calls = []
        monkeypatch.setattr(experiments, "send_signal", lambda *args, **kwargs: calls.append(args))
        assert worker["pid"] in {item["pid"] for item in campaign.stage_survivors()}
        campaign.release_resources()
        assert not calls and campaign.supply_reserved is True
        assert campaign.record["reservation_release_deferred"] == "Experiment workers remain active"
        assert campaign.record["reservations"][0]["released"] is False
    finally:
        if launcher.poll() is None:
            launcher.terminate()
            launcher.wait(timeout=5)
        if worker is None and pidfile.exists():
            worker = guard.snapshot(int(pidfile.read_text()))
        if worker is not None:
            current = guard.snapshot(worker["pid"])
            if current is not None and current["state"] != "Z":
                # Signal only the exact synthetic worker; never the PGID.
                identity = {key: worker[key] for key in ("pid", "birth", "command", "group", "boot_id")}
                guard.send_signal(identity, signal.SIGTERM)
                deadline = time.monotonic() + 5
                while time.monotonic() < deadline:
                    current = guard.snapshot(worker["pid"])
                    if current is None or current["state"] == "Z":
                        break
                    time.sleep(.01)
                else:
                    raise AssertionError("Synthetic orphan survived guarded termination")


@pytest.mark.parametrize("changed_metric", [None, "capacitance_violations", "utilization_fraction"])
def test_setup_comparison_ignores_profile_label_but_checks_measurements(tmp_path, monkeypatch, changed_metric):
    campaign = experiments.Campaign.__new__(experiments.Campaign)
    campaign.directory = tmp_path
    campaign.result = tmp_path / "result.json"
    campaign.plan = {"method_sha256": {}}
    campaign.record = {"stages": []}
    campaign.handover = lambda: ("source-state", metrics())
    campaign.pack_stage = lambda row, state: None
    campaign.release_resources = lambda: None
    monkeypatch.setattr(experiments, "state_pins", lambda state: {state: "fixture digest"})

    def run_stage(profile, state, source):
        row = dict(profile=profile, input_sha256={"source-state": "same digest"},
                   status="COMPLETE_ESTIMATE_ONLY", elapsed_seconds=3600,
                   before=metrics(profile=profile), after=metrics(),
                   eligible_estimate=False, output_state=f"{profile}-state")
        if profile.startswith("setup_"):
            row.update(eligible_estimate=True, after=metrics(setup_wns_ns=-4.8, setup_tns_ns=-3900.0))
        if profile == "setup_batch4":
            row["elapsed_seconds"] = 1800
            if changed_metric is not None:
                row["before"][changed_metric] += 1
        campaign.record["stages"].append(row)
        return row

    campaign.run_stage = run_stage
    if changed_metric is not None:
        with pytest.raises(RuntimeError, match="identical inputs and initial measurements"):
            campaign.run()
        assert campaign.record["status"] == "FAILED_LAST_COMPLETE_CHECKPOINT_PRESERVED"
    else:
        campaign.run()
        assert campaign.record["selected_setup_profile"] == "setup_batch4"
        assert campaign.record["status"] == "EXPERIMENTS_COMPLETE_REQUIRES_INDEPENDENT_REVIEW"
