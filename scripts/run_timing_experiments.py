#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Run checkpoint-preserving local timing experiments, never signoff acceptance.

The plan and copied scripts are immutable. An explicitly prepared handover stops
only the old controller while its existing child finishes. Heavy stages run
sequentially, with a temporary reservation of the otherwise idle supply queue.
There is no elapsed-time watchdog. A failure preserves all completed evidence.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import subprocess
import tarfile
import time

from timing_process_guard import ProcessGuardError, descendants, send_signal, snapshot

GIB = 1024 ** 3
SLACKS = ("setup_wns_ns", "hold_wns_ns", "setup_tns_ns", "hold_tns_ns")
COUNTS = ("setup_violating_endpoints", "hold_violating_endpoints",
          "slew_violations", "capacitance_violations")


def now():
    return datetime.datetime.now().astimezone().isoformat()


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n")
    temporary.replace(path)


def verify_pins(pins):
    for path, expected in pins.items():
        if not Path(path).is_file() or sha(path) != expected:
            raise RuntimeError(f"Input changed or missing: {path}")


def state_pins(path):
    path = Path(path)
    value = json.loads(path.read_text())
    for key in ("odb", "nl", "def", "sdc"):
        if (not isinstance(value.get(key), str) or not Path(value[key]).is_absolute()
                or not Path(value[key]).is_file()):
            raise RuntimeError(f"Incomplete checkpoint view {key}: {path}")
    pins = {str(path): sha(path)}

    def visit(item):
        if isinstance(item, dict):
            for child in item.values():
                visit(child)
        elif isinstance(item, list):
            for child in item:
                visit(child)
        elif isinstance(item, str) and item.startswith("/"):
            if not Path(item).is_file():
                raise RuntimeError(f"Missing referenced checkpoint file: {item}")
            pins[item] = sha(item)

    visit(value)
    return pins


def measurement(path):
    value = json.loads(Path(path).read_text())
    for key in SLACKS + COUNTS + ("area_um2", "instance_count"):
        number = value[key]
        if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number):
            raise ValueError(f"Invalid measured {key}: {number}")
        if key in COUNTS + ("instance_count",) and (number < 0 or number != int(number)):
            raise ValueError(f"Invalid count {key}: {number}")
        if key == "area_um2" and number < 0:
            raise ValueError("Negative physical area")
    return value


def no_regression(before, after):
    """A candidate cannot buy one class of timing at the cost of another."""
    return (all(after[k] >= before[k] - 1e-6 for k in SLACKS if k in before)
            and all(after[k] <= before[k] for k in COUNTS if k in before))


def improved(before, after, domain):
    return any(after[f"{domain}_{kind}_ns"] > before[f"{domain}_{kind}_ns"] + 1e-6
               for kind in ("wns", "tns"))


def eligible(before, after, source, domain):
    return no_regression(before, after) and no_regression(source, after) and improved(before, after, domain)


def setup_rates(row):
    elapsed = row["elapsed_seconds"]
    if isinstance(elapsed, bool) or not math.isfinite(elapsed) or elapsed <= 0:
        raise ValueError("A positive elapsed duration is required")
    return {kind: (row["after"][f"setup_{kind}_ns"] - row["before"][f"setup_{kind}_ns"])
            * 3600 / elapsed for kind in ("wns", "tns")}


def same_initial_measurements(first, second):
    return (all(first[k] == second[k] for k in COUNTS + ("instance_count",))
            and all(math.isclose(first[k], second[k], rel_tol=1e-12, abs_tol=1e-6)
                    for k in SLACKS + ("area_um2", "utilization_fraction")))


def choose_setup(control, batch):
    """Keep the control unless batch4 improves both measured hourly rates."""
    if not batch["eligible_estimate"]:
        return control if control["eligible_estimate"] else None
    if not control["eligible_estimate"]:
        return batch
    a, b = setup_rates(control), setup_rates(batch)
    return batch if all(b[k] > a[k] for k in a) else control


def archive_directory(path):
    """Lossless local checkpoint packing; never remove unverified bytes."""
    path = Path(path)
    archive = path.with_suffix(".tar.gz")
    if archive.exists():
        raise FileExistsError(archive)
    inventory = {}
    for item in path.rglob("*"):
        if item.is_symlink():
            raise RuntimeError(f"Unexpected checkpoint symlink: {item}")
        if item.is_file():
            inventory[str(item.relative_to(path))] = {"bytes": item.stat().st_size, "sha256": sha(item)}
    if not inventory:
        raise ValueError("Empty checkpoint")
    with tarfile.open(archive, "w:gz", compresslevel=1) as output:
        for name in sorted(inventory):
            output.add(path / name, arcname=str(Path(path.name) / name), recursive=False)
    seen = set()
    with tarfile.open(archive, "r|gz") as source:
        for member in source:
            name = str(Path(member.name).relative_to(path.name))
            if not member.isfile() or name not in inventory or name in seen:
                raise RuntimeError("Unexpected archive member")
            entry = inventory[name]
            if member.size != entry["bytes"] or hashlib.file_digest(source.extractfile(member), "sha256").hexdigest() != entry["sha256"]:
                raise RuntimeError("Checkpoint archive round trip failed")
            seen.add(name)
    if seen != set(inventory):
        raise RuntimeError("Incomplete checkpoint archive")
    verify_pins({str(path / n): v["sha256"] for n, v in inventory.items()})
    receipt = dict(path=str(path), archive=str(archive), sha256=sha(archive), inventory=inventory,
                   roundtrip_verified=True, recorded=now())
    write_json(archive.with_suffix(".json"), receipt)
    shutil.rmtree(path)
    return receipt


def restore_directory(receipt):
    path, archive = Path(receipt["path"]), Path(receipt["archive"])
    if path.exists() or sha(archive) != receipt["sha256"]:
        raise RuntimeError("Unsafe checkpoint restoration")
    path.mkdir()
    seen = set()
    with tarfile.open(archive, "r|gz") as source:
        for member in source:
            name = str(Path(member.name).relative_to(path.name))
            if not member.isfile() or ".." in Path(name).parts or name not in receipt["inventory"] or name in seen:
                raise RuntimeError("Unsafe checkpoint archive member")
            target = path / name
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("xb") as output:
                shutil.copyfileobj(source.extractfile(member), output)
            entry = receipt["inventory"][name]
            if target.stat().st_size != entry["bytes"] or sha(target) != entry["sha256"]:
                raise RuntimeError("Restored checkpoint differs")
            seen.add(name)
    if seen != set(receipt["inventory"]):
        raise RuntimeError("Restored checkpoint incomplete")


def resource_sample(root):
    data = dict(line.split(":", 1) for line in Path("/proc/meminfo").read_text().splitlines())
    return dict(available_memory_bytes=int(data["MemAvailable"].split()[0]) * 1024,
                free_disk_bytes=shutil.disk_usage(root).free)


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (8 * GIB,) * 2)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.nice(10)


class Campaign:
    def __init__(self, directory):
        self.directory = Path(directory).resolve()
        self.plan = json.loads((self.directory / "plan.json").read_text())
        self.root = Path(self.plan["root"])
        self.result = self.directory / "result.json"
        if self.result.exists():
            raise RuntimeError("Existing campaign: inspect it, never launch a duplicate")
        self.record = dict(status="VERIFYING_PLAN", recorded=now(), plan_sha256=sha(self.directory / "plan.json"),
                           stages=[], reservations=[], timing_accepted=False, manufacturing_approval=False)
        self.supply_reserved = False
        self.active_child = None
        self.active_groups = set()
        self.active_run = None
        self.save()

    def save(self, **updates):
        self.record.update(updates, recorded=now())
        write_json(self.result, self.record)

    def handover(self):
        plan = self.plan
        old, child = plan["old_controller"], plan["old_child"]
        # Only the old controller is stopped. Its separate-session child runs.
        parent = snapshot(old["pid"])
        if parent is None or parent["state"] != "T":
            raise RuntimeError("Prepared old controller is no longer paused")
        descendants(old)  # Includes exact root identity validation.
        while True:
            current = snapshot(child["pid"])
            if current is None or current["birth"] != child["birth"] or current["parent"] != old["pid"]:
                raise RuntimeError("Lost child exit evidence during handover")
            if current["state"] == "Z":
                if current["exit_status_raw"] != 0:
                    raise RuntimeError(f"Original LibreLane child failed: {current}")
                break
            self.save(status="WAITING_FOR_ORIGINAL_CHECKPOINT", original_child=current,
                      resources=resource_sample(self.root))
            time.sleep(30)
        live = [p for p in descendants(old) if p["pid"] != child["pid"] and p["state"] != "Z"]
        if live:
            raise RuntimeError(f"Original child still has active descendants: {live}")
        verify_pins(plan["handover_input_sha256"])
        step = Path(plan["checkpoint_step"])
        log = (step / "openroad-resizertimingpostgrt.log").read_text()
        for marker in ("ALL_32_HARD_MACRO_MASTERS_LOCATIONS_ORIENTATIONS_PRESERVED",
                       "COMPLETE_CHECKPOINT_REQUIRES_FRESH_ROUTING_RCX_STA_AND_EQUIVALENCE"):
            if marker not in log:
                raise RuntimeError(f"Original checkpoint incomplete: {marker}")
        values = {}
        for kind in ("SETUP", "HOLD"):
            start, end = f"CHUNK_{kind}_WNS_BEGIN", f"CHUNK_{kind}_WNS_END"
            if log.count(start) != 1 or log.count(end) != 1:
                raise RuntimeError("Non-unique original slack markers")
            part = log.split(start)[1].split(end)[0]
            match = re.fullmatch(r"\s*worst slack (?:min|max)\s+(-?[0-9]+(?:\.[0-9]+)?)\s*", part)
            if match is None:
                raise RuntimeError("Unparseable original slack")
            values[f"{kind.lower()}_wns_ns"] = float(match[1])
        state = step / "state_out.json"
        pins = state_pins(state)
        proof = dict(recorded=now(), original_exit=current, input_sha256=plan["handover_input_sha256"],
                     output_sha256=pins, metrics=values, state=str(state), log_sha256=sha(step / "openroad-resizertimingpostgrt.log"),
                     scope="Verified completed global-estimate checkpoint; no final timing acceptance")
        write_json(self.directory / "baseline-verified.json", proof)
        self.save(status="ORIGINAL_CHECKPOINT_VERIFIED", baseline=proof)
        # Queue TERM while stopped, then let the pending default termination run.
        # A bare CONT would erroneously let the old controller launch its next job.
        send_signal(old, signal.SIGTERM, allowed_states={"T"})
        send_signal(old, signal.SIGCONT, allowed_states={"T"})
        for _ in range(100):
            parent = snapshot(old["pid"])
            if parent is None or parent["state"] == "Z":
                break
            time.sleep(0.05)
        else:
            raise RuntimeError("Original controller did not terminate")
        self.save(old_controller_retired=True)
        prior = Path(plan["previous_checkpoint_directory"])
        if any(Path(p).is_relative_to(prior) for p in pins):
            self.save(previous_checkpoint_retained="New state still references old views")
        else:
            self.save(previous_checkpoint_archive=archive_directory(prior))
        return str(state), values

    def reserve_resources(self):
        supply = self.plan["supply_controller"]
        while True:
            verify_pins(self.plan["method_sha256"])
            if sha(self.directory / "plan.json") != self.record["plan_sha256"]:
                raise RuntimeError("Immutable campaign plan changed")
            sample = resource_sample(self.root)
            if sample["available_memory_bytes"] < 5 * GIB or sample["free_disk_bytes"] < GIB:
                self.save(status="WAITING_FOR_LOCAL_RESOURCES", resources=sample)
                time.sleep(30)
                continue
            current = snapshot(supply["pid"])
            if current is None or current["state"] == "Z":
                # Fail closed: a disappeared supplier could have left an orphan.
                raise RuntimeError("Supply controller disappeared; review resources before restarting")
            supply_result = json.loads(Path(self.plan["supply_result"]).read_text())
            idle = (supply_result["status"] == "WAITING_FOR_LOCAL_RESOURCES"
                    and all(stage.get("status") == "EXITED" for stage in supply_result.get("stages", [])))
            if not idle or descendants(supply):
                self.save(status="WAITING_FOR_SUPPLY_JOB", supply_status=supply_result["status"], resources=sample)
                time.sleep(30)
                continue
            send_signal(supply, signal.SIGSTOP, allowed_states={"S", "R"})
            self.supply_reserved = True
            self.record["reservations"].append(dict(recorded=now(), controller=supply, released=False))
            self.save(status="RESERVING_IDLE_SUPPLY_QUEUE")
            for _ in range(500):
                current = snapshot(supply["pid"])
                if current is None or current["birth"] != supply["birth"]:
                    raise RuntimeError("Supply identity changed while reserving")
                if current["state"] == "T":
                    break
                time.sleep(0.01)
            else:
                raise RuntimeError("Supply did not stop; reservation unproved")
            # Recheck after the stop: it might have forked between checks.
            supply_result = json.loads(Path(self.plan["supply_result"]).read_text())
            if (descendants(supply) or supply_result["status"] != "WAITING_FOR_LOCAL_RESOURCES"
                    or any(stage.get("status") != "EXITED" for stage in supply_result.get("stages", []))):
                self.release_resources()
                time.sleep(30)
                continue
            sample = resource_sample(self.root)
            if sample["available_memory_bytes"] >= 5 * GIB and sample["free_disk_bytes"] >= GIB:
                return
            self.release_resources()

    def release_resources(self):
        if self.supply_reserved:
            if self.active_child is not None:
                if isinstance(self.active_child, subprocess.Popen):
                    if self.active_child.poll() is None:
                        self.save(reservation_release_deferred="Experiment child still active; monitor must retain reservation")
                        return
                    self.active_child = None
            if self.active_child is not None:
                current = snapshot(self.active_child["pid"])
                if current is not None and current["birth"] == self.active_child["birth"] and current["state"] != "Z":
                    self.save(reservation_release_deferred="Experiment child still active; monitor must retain reservation")
                    return
            # A failed LibreLane parent may leave a reparented OpenROAD child.
            # Inspect the launched process groups and stage-specific commands,
            # including workers whose wrapper created another process group.
            survivors = self.stage_survivors()
            if survivors:
                self.save(reservation_release_deferred="Experiment workers remain active", active_workers=survivors)
                return
            send_signal(self.plan["supply_controller"], signal.SIGCONT, allowed_states={"T"})
            self.supply_reserved = False
            self.record["reservations"][-1].update(released=True, released_at=now())
            self.save()

    def stage_survivors(self):
        if self.active_run is None:
            return []
        found = []
        for entry in Path("/proc").iterdir():
            if not entry.name.isdigit() or int(entry.name) == os.getpid():
                continue
            try:
                current = snapshot(int(entry.name))
            except ProcessGuardError:
                # Other users' processes may deny cmdline access. A known
                # stage group is still detectable through its public stat.
                try:
                    fields = (entry / "stat").read_text().rsplit(") ", 1)[1].split()
                except FileNotFoundError:
                    continue
                if int(fields[2]) in self.active_groups:
                    raise RuntimeError("Cannot inspect a known experiment worker")
                continue
            if current is not None and current["state"] != "Z":
                if (current["group"] in self.active_groups
                        or any(str(self.active_run) in arg for arg in current["command"])):
                    found.append(current)
        return found

    def run_stage(self, profile, state, source):
        self.reserve_resources()
        row = dict(profile=profile, input_state=state, input_sha256=state_pins(state), status="PREPARED")
        self.record["stages"].append(row)
        run = self.directory / profile
        self.active_run = run
        self.active_groups = set()
        env = os.environ.copy()
        env.update(NSSOC_TIMING_EXPERIMENT_PROFILE=profile,
                   NSSOC_TIMING_PROFILE_SCRIPT=str(self.directory / "methods/timing_repair_experiment.tcl"),
                   NSSOC_CRITICAL_PLACEMENT_SCRIPT=str(self.directory / "methods/critical_xnor_placement.tcl"))
        cmd = [self.plan["app"], "python", str(self.directory / "methods/timing_experiment_flow.py"),
               "--flow", "TimingExperiments", "--manual-pdk", "--pdk-root", self.plan["pdk_root"],
               "--pdk", "ihp-sg13g2", "--force-run-dir", str(run),
               "--from", "OpenROAD.ResizerTimingPostGRT", "--to", "OpenROAD.ResizerTimingPostGRT",
               "--with-initial-state", state, str(self.directory / "config.json")]
        row["command"] = cmd
        try:
            verify_pins(row["input_sha256"])
            verify_pins(self.plan["method_sha256"])
            self.save(status="RUNNING_EXPERIMENT")
            start = time.monotonic()
            with (self.directory / f"{profile}.log").open("x") as log:
                child = subprocess.Popen(cmd, cwd=self.root, env=env, stdout=log, stderr=subprocess.STDOUT,
                                         start_new_session=True, preexec_fn=limits)
                self.active_child = child
                self.active_groups.add(child.pid)
                child_identity = snapshot(child.pid)
                row.update(status="RUNNING", child=child_identity, started=now())
                self.save()
                while child.poll() is None:
                    current = snapshot(child.pid)
                    if current is not None and current["state"] != "Z":
                        if child_identity is not None and current["birth"] != child_identity["birth"]:
                            raise RuntimeError("Experiment child identity changed")
                        workers = descendants(current)
                        self.active_groups.update(p["group"] for p in workers)
                        row["last_workers"] = workers
                        self.save()
                    time.sleep(30)
                code = child.returncode
                self.active_child = None
                survivors = self.stage_survivors()
                if survivors:
                    raise RuntimeError(f"Experiment left live workers; retain reservation: {survivors}")
            row.update(returncode=code, elapsed_seconds=time.monotonic() - start, completed=now())
            if code:
                row["status"] = "FAILED_PRESERVED"
                self.save()
                return row
            verify_pins(row["input_sha256"])
            verify_pins(self.plan["method_sha256"])
            steps = list(run.glob("*-openroad-resizertimingpostgrt"))
            if len(steps) != 1:
                raise RuntimeError("Missing or ambiguous experiment output")
            step = steps[0]
            log = (step / "openroad-resizertimingpostgrt.log").read_text()
            for marker in (f"EXPERIMENT_COMPLETE_REQUIRES_ROUTING_RCX_STA_EQUIVALENCE {profile}",
                           "ALL_32_HARD_MACRO_MASTERS_LOCATIONS_ORIENTATIONS_PRESERVED",
                           "EXPERIMENT_NATIVE_TIMING_CONSTRAINTS_BYTE_IDENTICAL"):
                if log.count(marker) != 1:
                    raise RuntimeError(f"Missing unique experiment completion marker: {marker}")
            before, after = measurement(step / "experiment-before.json"), measurement(step / "experiment-after.json")
            output = step / "state_out.json"
            row.update(status="COMPLETE_ESTIMATE_ONLY", before=before, after=after,
                       output_state=str(output), output_sha256=state_pins(output))
            domain = "hold" if profile == "hold_guarded" else "setup"
            row["eligible_estimate"] = eligible(before, after, source, domain)
            if profile.startswith("setup_"):
                row["setup_gain_per_hour"] = setup_rates(row)
            self.save()
            return row
        finally:
            self.release_resources()

    def pack_stage(self, row, selected_state):
        run = self.directory / row["profile"]
        if not run.exists():
            return
        pins = state_pins(selected_state)
        if any(Path(p).is_relative_to(run) for p in pins):
            return
        row["archive"] = archive_directory(run)
        self.save()

    def run(self):
        try:
            verify_pins(self.plan["method_sha256"])
            state, metrics = self.handover()
            selected = None
            for profile in ("critical_xnor", "hold_guarded"):
                row = self.run_stage(profile, state, metrics)
                if row.get("eligible_estimate"):
                    old_selected = selected
                    state, metrics, selected = row["output_state"], row["after"], row
                    if old_selected:
                        self.pack_stage(old_selected, state)
                else:
                    self.pack_stage(row, state)
                self.save(selected_estimated_state=state, selected_estimated_metrics=metrics)
            shared_state, shared_metrics = state, metrics
            control = self.run_stage("setup_baseline", shared_state, shared_metrics)
            if control["status"] != "COMPLETE_ESTIMATE_ONLY":
                raise RuntimeError("Control failed; no valid setup A/B comparison")
            self.pack_stage(control, shared_state)
            batch = self.run_stage("setup_batch4", shared_state, shared_metrics)
            if batch["status"] != "COMPLETE_ESTIMATE_ONLY":
                raise RuntimeError("Batch4 failed; no valid setup A/B comparison")
            if (control["input_sha256"] != batch["input_sha256"]
                    or not same_initial_measurements(control["before"], batch["before"])):
                raise RuntimeError("Setup A/B did not have identical inputs and initial measurements")
            chosen = choose_setup(control, batch)
            if chosen is not None:
                if "archive" in chosen:
                    self.pack_stage(batch, shared_state)
                    restore_directory(chosen["archive"])
                state, metrics = chosen["output_state"], chosen["after"]
            if selected:
                self.pack_stage(selected, state)
            for row in (control, batch):
                self.pack_stage(row, state)
            status = ("EXPERIMENTS_FINISHED_WITH_FAILED_METHODS" if any(row["status"] == "FAILED_PRESERVED" for row in self.record["stages"])
                      else "EXPERIMENTS_COMPLETE_REQUIRES_INDEPENDENT_REVIEW")
            self.save(status=status,
                      selected_estimated_state=state, selected_estimated_metrics=metrics,
                      selected_output_sha256=state_pins(state),
                      selected_setup_profile=chosen["profile"] if chosen else None,
                      batch4_faster_on_both_setup_rates=bool(chosen is batch and control["eligible_estimate"]),
                      next="Verify raw results; selected estimates still require equivalence, route, qualified RC and physical checks.")
        except BaseException as error:
            self.save(status="FAILED_LAST_COMPLETE_CHECKPOINT_PRESERVED", error=repr(error))
            raise
        finally:
            self.release_resources()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    Campaign(args.directory).run()


if __name__ == "__main__":
    main()
