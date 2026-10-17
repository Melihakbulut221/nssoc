#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Versioned lifecycle repair: own native and publisher groups; unchanged physics."""

import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import threading
import time

import characterize_pcie_clock_trim_stream_v1 as previous

PREVIOUS_SHA = "9f405eaf9c68ed7237c06bfd0e81a25631a1417b74efd6395562086baf060982"
PREVIOUS_TEST_SHA = "660131b8022474f8bc949b69fda2a67e86bad84ac75ebab4b18ba5f987a87dc9"
base, tiny, publication = previous.base, previous.tiny, previous.publication
require, sha, atomic = previous.require, previous.sha, previous.atomic
STOP, MIN_FREE_BYTES = previous.STOP, previous.MIN_FREE_BYTES
# Exact function/class aliases: no new measurement, deck or archival algorithm.
Meter, PartQueue = previous.Meter, previous.PartQueue
long_deck, replay_local_parts = previous.long_deck, previous.replay_local_parts
FAILURE_GRACE_SECONDS = 5.0


class Cancelled(RuntimeError):
    """Only explicit failure or parent cancellation, never healthy elapsed time."""


def process_identity(pid):
    try:
        fields = Path("/proc", str(pid), "stat").read_text().rsplit(") ", 1)[1].split()
    except (FileNotFoundError, ProcessLookupError):
        return None
    return dict(
        pid=pid, state=fields[0], process_group=int(fields[2]), start_ticks=fields[19]
    )


def group_members(group):
    members = []
    for path in Path("/proc").iterdir():
        if path.name.isdigit():
            identity = process_identity(int(path.name))
            if identity and identity["process_group"] == group:
                members.append(identity)
    return sorted(members, key=lambda x: x["pid"])


class ProcessOwner:
    """Spawn/registration and cancellation share one owner and one failure deadline."""

    def __init__(self, path):
        self.path = Path(path)
        self.lock = threading.RLock()
        self.cancelled = threading.Event()
        self.reason = None
        self.entries = []
        self.handlers = {}
        self.cleanup = None

    def save(self):
        with self.lock:
            atomic(
                self.path,
                dict(
                    status="CANCELLED" if self.cancelled.is_set() else "HEALTHY",
                    reason=self.reason,
                    elapsed_watchdog_seconds=None,
                    failure_grace_seconds=FAILURE_GRACE_SECONDS,
                    processes=[e["record"] for e in self.entries],
                    cleanup=self.cleanup,
                ),
            )

    def request_cancel(self, reason):
        # No raising signal handler: Popen must finish registration before cleanup.
        if self.reason is None:
            self.reason = str(reason)
        self.cancelled.set()

    def check(self):
        if self.cancelled.is_set():
            raise Cancelled(self.reason)

    def __enter__(self):
        if threading.current_thread() is threading.main_thread():
            for sig in (signal.SIGINT, signal.SIGTERM):
                self.handlers[sig] = signal.getsignal(sig)
                signal.signal(
                    sig,
                    lambda signum, frame: self.request_cancel(
                        f"Parent received {signal.Signals(signum).name}"
                    ),
                )
        self.save()
        return self

    def launch(self, kind, command, **kwargs):
        require(kind in ("native", "publisher"), "Explicit owned process kind")
        require("start_new_session" not in kwargs, "Owner controls process group")
        with self.lock:
            self.check()
            process = subprocess.Popen(command, start_new_session=True, **kwargs)
            identity = process_identity(process.pid)
            require(identity is not None, "Spawned process identity retained")
            entry = dict(
                process=process,
                record=dict(
                    kind=kind,
                    command=list(map(str, command)),
                    identity=identity,
                    process_group=process.pid,
                    status="ACTIVE",
                    returncode=None,
                ),
            )
            self.entries.append(entry)
            self.save()
            # A signal during spawn is now observed with its process registered.
            self.check()
            return process

    def complete(self, process):
        """Reap a leader; a live descendant is failure, not a successful exit."""
        code = process.wait()
        with self.lock:
            entry = next(e for e in self.entries if e["process"] is process)
            members = group_members(process.pid)
            entry["record"].update(returncode=code, members_at_leader_exit=members)
            require(
                not any(m["state"] != "Z" for m in members),
                "Owned leader exited with a live descendant",
            )
            entry["record"]["status"] = "REAPED_NO_LIVE_MEMBERS"
            self.save()
        return code

    def wait(self, process):
        while process.poll() is None:
            self.check()
            self.cancelled.wait(0.05)
        self.check()
        return self.complete(process)

    def stop_failed(self, reason):
        """Failure cleanup cannot be bypassed by observation or evidence I/O errors."""
        self.request_cancel(reason)
        with self.lock:
            if self.cleanup is not None:
                return
            start = time.monotonic()
            active = [e for e in self.entries if e["record"]["status"] == "ACTIVE"]
            self.cleanup = dict(
                reason=self.reason,
                started_monotonic=start,
                global_deadline_monotonic=start + FAILURE_GRACE_SECONDS,
                groups=[
                    dict(process_group=e["process"].pid, identity_reused=False)
                    for e in active
                ],
                recording_errors=[],
                observation_errors=[],
            )
        try:
            for entry, detail in zip(active, self.cleanup["groups"]):
                process, row = entry["process"], entry["record"]
                current = process_identity(process.pid)
                detail["identity_reused"] = (
                    current is not None
                    and current["start_ticks"] != row["identity"]["start_ticks"]
                )
                if detail["identity_reused"]:
                    continue
                detail["before"] = group_members(process.pid)
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                    detail["term_sent"] = True
                except ProcessLookupError:
                    detail["term_sent"] = False
            self.save_cleanup()
            deadline = start + FAILURE_GRACE_SECONDS
            while time.monotonic() < deadline:
                for e in active:
                    e["process"].poll()
                if not any(
                    any(m["state"] != "Z" for m in group_members(e["process"].pid))
                    for e in active
                ):
                    break
                time.sleep(min(0.01, max(0, deadline - time.monotonic())))
        except Exception as observation_error:
            # An observation failure shortens grace; it never skips group KILL.
            self.cleanup["observation_errors"].append(repr(observation_error))
        finally:
            for entry, detail in zip(active, self.cleanup["groups"]):
                process = entry["process"]
                if detail["identity_reused"]:
                    continue
                try:
                    # Entire group even when its leader already exited.
                    os.killpg(process.pid, signal.SIGKILL)
                    detail["kill_sent"] = True
                except ProcessLookupError:
                    detail["kill_sent"] = False
                finally:
                    entry["record"].update(
                        status="FAILURE_REAPED", returncode=process.wait()
                    )
                try:
                    detail["immediate_after_kill"] = group_members(process.pid)
                except Exception as observation_error:
                    self.cleanup["observation_errors"].append(repr(observation_error))
            self.cleanup["finished_monotonic"] = time.monotonic()
            self.save_cleanup()

    def save_cleanup(self):
        # Evidence I/O is never allowed to prevent KILL/reap after a failure.
        try:
            self.save()
        except Exception as error:
            self.cleanup["recording_errors"].append(repr(error))

    def __exit__(self, kind, error, traceback):
        try:
            if error is not None or self.cancelled.is_set():
                self.stop_failed(error or self.reason)
                self.save_cleanup()
            else:
                try:
                    self.save()
                except BaseException as recording_error:
                    self.stop_failed(recording_error)
                    raise
        finally:
            for sig, handler in self.handlers.items():
                signal.signal(sig, handler)


def publisher_record(path, receipt):
    record = json.loads(Path(receipt).read_text())
    require(
        record["status"] == "PASS_IMMUTABLE_RELEASE_ROUNDTRIPS"
        and len(record["assets"]) == 1,
        "Complete single-part publication",
    )
    return record["assets"][0]


class OwnedPublisher:
    def __init__(self, owner):
        self.owner = owner

    def __call__(self, path, receipt):
        require(
            sha(Path(publication.__file__)) == previous.PUBLISHER_SHA,
            "Frozen publisher",
        )
        self.owner.check()
        with receipt.with_suffix(".log").open("x") as log:
            process = self.owner.launch(
                "publisher",
                [
                    sys.executable,
                    str(Path(publication.__file__)),
                    "--out",
                    str(receipt),
                    str(path),
                ],
                stdout=log,
                stderr=subprocess.STDOUT,
            )
            require(self.owner.wait(process) == 0, "Actual publication nonzero exit")
        return publisher_record(path, receipt)


def capture_stream(
    stream, output, expected, hbts, case, prefix, *, publisher, **kwargs
):
    result = previous.capture_stream(
        stream, output, expected, hbts, case, prefix, publisher=publisher, **kwargs
    )
    result["live_release_publication"] = type(publisher) is OwnedPublisher
    result["lifecycle_revision"] = "v2_native_and_publication_groups"
    atomic(Path(output) / "capture.json", result)
    return result


def verify_parent(parent):
    require(sha(previous.__file__) == PREVIOUS_SHA, "Frozen v1 producer")
    prior, pins = previous.verify_parent(parent)
    pins[str(Path(__file__).resolve())] = sha(__file__)
    return prior, pins


def native_wait(runtime, folder, log, consume):
    """Healthy wait has no elapsed bound; failure owns both process trees."""
    rx = base.driver.parent.init.startup.s.rx.rx
    folder, log = Path(folder), Path(log)
    fifo = folder / "stream.fifo"
    os.mkfifo(fifo)
    keepalive = os.open(fifo, os.O_RDWR)
    # Open before any failure can close keepalive; even an unscheduled reader
    # must later observe EOF instead of blocking forever in FIFO open().
    reader_stream = fifo.open("rb")
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("GH_TOKEN", "GITHUB_TOKEN", "LD_PRELOAD")
    }
    env.update(
        SPICE_SCRIPTS=str(folder.parent), RAYON_NUM_THREADS="1", OMP_NUM_THREADS="1"
    )
    command = [str(runtime), "-n", "-b", "bench.cir"]
    start = time.monotonic()
    lifecycle = dict(
        status="STARTING",
        command=command,
        elapsed_watchdog_seconds=None,
        capture_error=None,
        explicit_failure_grace_seconds=FAILURE_GRACE_SECONDS,
    )
    process, pool = None, None

    def close_keepalive():
        nonlocal keepalive
        if keepalive is not None:
            os.close(keepalive)
            keepalive = None

    with ProcessOwner(folder / "owned-processes.json") as owner:
        try:
            with log.open("x") as stdout:
                process = owner.launch(
                    "native",
                    command,
                    cwd=folder,
                    env=env,
                    stdout=stdout,
                    stderr=subprocess.STDOUT,
                    preexec_fn=rx.resource_limit,
                )
                lifecycle.update(
                    status="RUNNING", pid=process.pid, process_group=process.pid
                )
                atomic(folder / "native-process.json", lifecycle)
                pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)

                def reader():
                    try:
                        with reader_stream as stream:
                            return consume(stream, owner)
                    except BaseException as error:
                        lifecycle["capture_error"] = repr(error)
                        owner.request_cancel(error)
                        raise

                future = pool.submit(reader)
                while True:
                    # Prefer original consumer error over its cancellation signal.
                    if future.done():
                        captured = future.result()
                    owner.check()
                    code = process.poll()
                    if code is not None:
                        close_keepalive()
                        require(code == 0, "Actual native nonzero exit")
                        if future.done():
                            returncode = owner.complete(process)
                            break
                    owner.cancelled.wait(0.05)
        except BaseException as error:
            lifecycle["error"] = repr(error)
            # Terminate both native and uploader BEFORE joining the consumer.
            owner.stop_failed(error)
            close_keepalive()
            raise
        finally:
            close_keepalive()
            if pool is not None:
                pool.shutdown(wait=True)
            reader_stream.close()
            lifecycle.update(
                status="EXITED",
                returncode=None if process is None else process.poll(),
                elapsed_seconds=time.monotonic() - start,
            )
            atomic(folder / "native-process.json", lifecycle)
    fifo.unlink()
    return captured, dict(
        command=command,
        returncode=returncode,
        elapsed_seconds=time.monotonic() - start,
        address_space_limit_bytes=rx.MEMORY_LIMIT,
        cpu_affinity_count=1,
        elapsed_watchdog_seconds=None,
        explicit_failure_grace_seconds=FAILURE_GRACE_SECONDS,
        native_and_publishers_owned=True,
        terminated_on_capture_error_or_cancellation_only=True,
    )


def run(parent, output, prefix):
    parent, output = Path(parent).resolve(), Path(output).resolve()
    prior, pins = verify_parent(parent)
    require(
        not output.exists() and output.is_relative_to(Path("/dev/shm")),
        "Fresh RAM output",
    )
    require(
        shutil.disk_usage("/dev/shm").free >= 1024 * 1024**2,
        "Initial1GiB free-space gate",
    )
    runtime = next(Path(p) for p in pins if Path(p).name == "ngspice")
    output.mkdir()
    (output / "producer.py").write_bytes(Path(__file__).read_bytes())
    (output / "spinit").write_text(base.driver.parent.init.SPINIT)
    record = dict(
        status="RUNNING",
        source_sha256=pins,
        cases=[],
        stop_s=STOP,
        declared_final_window_s=[STOP - 8e-9, STOP],
        fixed_step_pair_s=[0.5e-12, 0.25e-12],
        no_full_wave_resident_plot=True,
        queue_capacity=1,
        scope="Finite cold-start thermal screen; no PCIe/PLL/frequency-lock/fullPEX acceptance",
    )
    atomic(output / "result.json", record)
    try:
        for index, original in enumerate(prior["cases"]):
            case = original["case"]
            folder = output / case["name"]
            folder.mkdir()
            src = parent / case["name"]
            circuit = (src / base.prior.FILE).read_text()
            (folder / base.prior.FILE).write_text(circuit)
            (folder / "bench.cir").write_text(
                long_deck((src / "bench.cir").read_text(), case["step_s"])
            )
            hbts = base.driver.contract(circuit, 4)
            expected = base.prior.vectors(hbts)
            row = dict(case=case, status="NATIVE_RUNNING")
            record["cases"].append(row)
            atomic(output / "result.json", record)
            cap, execution = native_wait(
                runtime,
                folder,
                folder / "run.log",
                lambda f, owner: capture_stream(
                    f,
                    folder / "capture",
                    expected,
                    hbts,
                    case,
                    f"{prefix}-s{index}",
                    publisher=OwnedPublisher(owner),
                ),
            )
            row.update(capture=cap, execution=execution, measurement=cap["measurement"])
            require(
                cap["live_release_publication"] is True,
                "Production requires live release retention",
            )
            row["native"] = tiny.native_log((folder / "run.log").read_text(), cap, hbts)
            row["initial_op"] = base.driver.parent.init.startup.initial_op(
                folder / "initial-op.dat", expected
            )
            require(
                max(map(abs, row["initial_op"].values())) <= 1e-10,
                "Exact zero-source initialOP",
            )
            require(
                all(sha(p) == h for p, h in pins.items()),
                "All inputs rechecked after actual native completion",
            )
            row.update(
                status="COMPLETE",
                outputs={
                    str(p.relative_to(folder)): sha(p)
                    for p in folder.rglob("*")
                    if p.is_file()
                },
            )
            atomic(output / "result.json", record)
        record["pair_agreement"] = base.pair_agreement(record["cases"])
        passed = (
            all(
                x["measurement"]["limited_thermal_screen_pass"] for x in record["cases"]
            )
            and record["pair_agreement"]["pass_pair"]
        )
        record["status"] = (
            "PASS_LIMITED1US_THERMAL_SCREEN"
            if passed
            else "FAIL_LIMITED1US_THERMAL_SCREEN"
        )
        record["prior_failures_superseded"] = False
        record["all_inputs_rechecked"] = True
        atomic(output / "result.json", record)
    except BaseException as error:
        record.update(status="ERROR_INCOMPLETE", error=repr(error))
        atomic(output / "result.json", record)
        raise
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--release-prefix", required=True)
    args = parser.parse_args()
    return int(
        run(args.parent, args.out, args.release_prefix)["status"]
        != "PASS_LIMITED1US_THERMAL_SCREEN"
    )


if __name__ == "__main__":
    raise SystemExit(main())
