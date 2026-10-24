#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Lossless native streaming of the unchanged 539-device loop; finite screens only.

No internal ideal clock/divider/detector or control clamp is introduced. Native
physics uses the exact original bench except transient stop/step and FIFO output.
The unchanged 3 mA/Nx HBT limit gates a tighter startup before a longer experiment.
Public single-part roundtrips precede removal; healthy execution has no timeout.
"""

import argparse
import concurrent.futures
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import sys
import tarfile
import time
import urllib.request

import numpy as np
import characterize_pcie_pll_loop_v2 as loop
import characterize_pcie_clock_trim_stream_v2 as life

n = loop.n
ROOT = Path(__file__).resolve().parents[1]
ORIGINAL = Path("/dev/shm/nssoc-pll-connected-loop-v1-startup01")
ORIGINAL_SHA = "ace7d843add5b275a15bc341a26caec5b844260cf0811600fa8305c40a341bc4"
PUBLIC = (
    ROOT
    / "hw/soc/out/pcie-pll-loop-20261004/pcie-pll-connected-loop-20261004-v1-startup01-parts.json"
)
FLOOR = 512 * 1024**2
CAP = 50 * 1024**2
PART_BYTES = 16 * 1024**2
PINS = {
    "characterize_pcie_clock_trim_stream_v2.py": "39312e364fa2a788784d88f3a63845f64db25bb420e2ee5d58c07a8c805bc886",
    "characterize_pcie_clock_trim_stream_v1.py": "9f405eaf9c68ed7237c06bfd0e81a25631a1417b74efd6395562086baf060982",
    "probe_pcie_clock_stream_capture_v1.py": "13e370d57778999a1bbd97dfeeb6aaef8dbe65e6fcdd4fa0393d1b2fec985c07",
    "characterize_pcie_pll_loop_v2.py": "bc94a96bd34fc73f2d2e1587ecf3e382637793bedf08578358acd14270ec095e",
    "pcie_pll_native_fixture_v1.py": "ba483cc0a740db3c774225ef2c42cb0a41cf56311050512217ec588ab2172223",
}
OBSERVATIONS = (
    ["time"]
    + [
        f"v({s})"
        for s in (
            "clkp",
            "clkn",
            "qp",
            "qn",
            "fb",
            "reference",
            "up",
            "down",
            "vctrl",
            "xloop.xchain.xfb.clk",
            "xloop.xchain.xfb.f0",
            "xloop.xchain.xfb.f1",
            "xloop.xchain.xfb.count",
            "xloop.xchain.xfb.xcount.q0",
            "xloop.xchain.xfb.xcount.q1",
        )
    ]
    + [
        f"i(@n.xloop.xdet.xcp.x{p}enable.nsg13_hv_{m}mos[ids])"
        for p, m in [("p", "p"), ("n", "n")]
    ]
)


def require(value, reason):
    if not value:
        raise ValueError(reason)


def method_inventory():
    """Every loaded local Python dependency, including lifecycle/parser helpers."""
    return sorted(
        {
            str(Path(mod.__file__).resolve())
            for mod in list(sys.modules.values())
            if getattr(mod, "__file__", None)
            and Path(mod.__file__).resolve().is_relative_to(ROOT / "scripts")
        }
    )


def verify_parent():
    loop.verify()
    for name, digest in PINS.items():
        require(
            n.common.sha(ROOT / "scripts" / name) == digest, "Frozen method " + name
        )
    require(
        n.common.sha(ORIGINAL / "result.json") == ORIGINAL_SHA, "Sealed native parent"
    )
    prior = json.loads((ORIGINAL / "result.json").read_text())
    require(len(prior["devices"]) == 539, "Exact native device census")
    for path, pin in prior["inputs"].items():
        require(n.common.pin(path) == pin, "Parent input drift: " + path)
    for name, pin in prior["outputs"].items():
        if name != "wave.raw":
            require(
                n.common.pin(ORIGINAL / name) == pin, "Parent output drift: " + name
            )
    return prior


def stream_deck(original, step, stop):
    require(
        step in (5e-12, 2.5e-12) and stop in (34e-9, 400e-9), "Declared finite analyses"
    )
    old = "tran 5e-12 3.4e-08 0 5e-12\nwrite wave.raw all\n"
    require(
        original.count(old) == 1 and original.count(".control\n") == 1,
        "Exact parent analysis",
    )
    new = original.replace(
        ".control\n", f".tran {step:.12g} {stop:.12g} 0 {step:.12g}\n.control\n"
    )
    return new.replace(old, "run stream.fifo\nsetplot\ndisplay\nrusage space\n")


def data_names(columns):
    return ["i(" + name + ")" if name.startswith("@") else name for name in columns]


class Meter:
    """Block extrema use the frozen all-device formulas without sample thinning."""

    def __init__(self, columns, rows, config, observations=OBSERVATIONS):
        self.names = data_names(columns)
        require(len(set(self.names)) == len(self.names), "Unique columns")
        self.rows, self.config = rows, config
        self.indices = [self.names.index(x) for x in observations]
        self.observations = observations
        self.saved, self.bounds = [], None
        self.geometry = None
        self.count, self.last, self.max_dt = 0, None, 0.0
        self.minima = np.full(len(columns), np.inf)
        self.maxima = np.full(len(columns), -np.inf)
        self.settled_seen = False

    def push(self, block):
        require(
            block.ndim == 2 and block.shape[1] == len(self.names) and len(block),
            "Complete row block",
        )
        require(np.isfinite(block).all(), "All native observations finite")
        t = block[:, 0]
        require(
            (self.count != 0 or t[0] == 0) and (self.last is None or t[0] > self.last),
            "Time origin/continuity",
        )
        delta = np.diff(t if self.last is None else np.r_[self.last, t])
        require(np.all(delta > 0), "Strict native time ordering")
        if len(delta):
            self.max_dt = max(self.max_dt, float(delta.max()))
        require(
            self.max_dt <= self.config["step_s"] * (1 + 1e-5),
            "Native maximum time step",
        )
        require(
            t[-1] <= self.config["stop_s"] + 16 * np.spacing(self.config["stop_s"]),
            "No samples after endpoint",
        )
        data = dict(zip(self.names, block.T))
        settled = (t >= self.config["window_s"][0]) & (t <= self.config["window_s"][1])
        window = (
            self.config["window_s"] if settled.any() else [float(t[0]), float(t[-1])]
        )
        result = n.safety(data, self.rows, window)
        require(
            self.geometry is None
            or self.geometry == result["model_geometry_range_issues"],
            "Geometry drift",
        )
        self.geometry = result["model_geometry_range_issues"]
        if self.bounds is None:
            self.bounds = copy.deepcopy(result["all_device_bounds"])
            for item in self.bounds:
                if "min_settled_vce" in item and not settled.any():
                    item["min_settled_vce"] = float("inf")
        else:
            for old, new in zip(self.bounds, result["all_device_bounds"]):
                require(
                    old["path"] == new["path"] and old["model"] == new["model"],
                    "Device identity",
                )
                for key in old:
                    if key.startswith("max_capture_"):
                        old[key] = max(old[key], new[key])
                    elif key == "min_settled_vce" and settled.any():
                        old[key] = min(old[key], new[key])
        self.settled_seen |= bool(settled.any())
        self.minima = np.minimum(self.minima, block.min(axis=0))
        self.maxima = np.maximum(self.maxima, block.max(axis=0))
        self.saved.append(block[:, self.indices].copy())
        self.count += len(t)
        self.last = float(t[-1])

    def finish(self):
        require(self.count >= 2 and self.settled_seen, "Actual settled capture")
        distance = abs(self.last - self.config["stop_s"]) / np.spacing(
            self.config["stop_s"]
        )
        require(distance <= 16, "Exact finite endpoint within 16 binary64 ULP")
        for item in self.bounds:
            if item["model"] == "npn13g2":
                item["passed"] = (
                    item["min_settled_vce"] >= 0.4
                    and item["max_capture_vce"] <= 1.6
                    and item["max_capture_ic_per_nx"] <= 0.003
                )
            else:
                item["passed"] = (
                    item["max_capture_terminal_difference"] <= item["voltage_limit"]
                    and item.get("max_capture_drain_per_um", 0) <= 0.002
                )
        safety = dict(
            passed=not self.geometry and all(x["passed"] for x in self.bounds),
            all_device_bounds=self.bounds,
            model_geometry_range_issues=self.geometry,
            foundry_soa_qualification=False,
        )
        data = dict(zip(self.observations, np.concatenate(self.saved).T))
        grid = dict(
            first_s=0.0,
            last_s=self.last,
            endpoint_ulp_distance=float(distance),
            endpoint_ulp_limit=16,
            largest_interval_s=self.max_dt,
            raw_samples_changed=False,
        )
        return safety, data, grid


def measurements(data, config):
    if config["stop_s"] == 34e-9:
        return loop.measure(data, config)
    observed = dict(data)
    for key, value in data.items():
        if key.startswith("v(xloop.xchain."):
            observed[key.replace("v(xloop.xchain.", "v(xchain.", 1)] = value
    result = loop.base.measure_chain(observed, config)
    result.pop("vctrl_external_v")
    result.pop("closed_pll")
    result["settling"] = settling(data)
    result["passed"] &= result["settling"]["passed"]
    result["lock_demonstrated"] = False
    return result


def settling(data):
    """Predeclared finite edge screens; no full lock/noise/stationarity claim."""
    t = data["time"]
    refs = np.array(n.common.crossings(t, data["v(reference)"], 1.25))
    feedback = np.array(n.common.crossings(t, data["v(fb)"], 1.25))
    windows = []
    for a, b in ((200e-9, 300e-9), (300e-9, 400e-9)):
        fb = feedback[(feedback >= a) & (feedback < b)]
        period = np.diff(fb)
        frequency = 1 / float(period.mean()) if len(period) else None
        indices = [int(np.argmin(abs(refs - x))) for x in fb] if len(refs) else []
        phases = [float(x - refs[i]) for x, i in zip(fb, indices)]
        no_slip = (
            len(fb) >= 9
            and len(indices) == len(fb)
            and all(j == i + 1 for i, j in zip(indices, indices[1:]))
            and all(abs(p) < 5e-9 for p in phases)
        )
        phase_span = max(phases) - min(phases) if phases else None
        mask = (t >= a) & (t <= b)
        control = [
            float(data["v(vctrl)"][mask].min()),
            float(data["v(vctrl)"][mask].max()),
        ]
        checks = dict(
            frequency_100ppm=frequency is not None
            and abs(frequency / 1e8 - 1) <= 100e-6,
            unique_successive_reference_no_slip=no_slip,
            phase_range_50ps=phase_span is not None and phase_span <= 50e-12,
            control_development_window=0.4 <= control[0] <= control[1] <= 1.5,
        )
        windows.append(
            dict(
                interval_s=[a, b],
                frequency_hz=frequency,
                reference_indices=indices,
                phase_s=phases,
                phase_span_s=phase_span,
                control_range_v=control,
                checks=checks,
            )
        )
    # Adjacent windows may not each independently reuse/skip a reference edge.
    joined = [i for w in windows for i in w["reference_indices"]]
    cross = len(joined) >= 18 and all(b == a + 1 for a, b in zip(joined, joined[1:]))
    return dict(
        passed=cross and all(all(w["checks"].values()) for w in windows),
        windows=windows,
        cross_window_no_slip=cross,
        scope="Two finite 100 ns windows, not lock/jitter/PVT/thermal or foundry qualification",
    )


def capture(stream, output, prior, config, prefix, publisher, *, rows_per_part=None):
    output.mkdir()
    expected = n.vectors(prior["devices"], config["extra_vectors"])
    header, meta = life.tiny.parse_header(stream, expected)
    require(
        meta["declared_points"] == 0 and sys.byteorder == "little",
        "Actual nonseekable native format",
    )
    (output / "header.bin").write_bytes(header)
    width = len(meta["columns"]) * 8
    part_rows = PART_BYTES // width if rows_per_part is None else rows_per_part
    require(1 <= part_rows <= PART_BYTES // width, "Part bound")
    queue = life.PartQueue(
        output / "parts", prefix, meta["columns"], publisher, part_rows, True, FLOOR
    )
    meter = Meter(meta["columns"], prior["devices"], config)
    pending, whole = bytearray(), hashlib.sha256(header)
    try:
        while raw := stream.read(65536):
            whole.update(raw)
            pending.extend(raw)
            count = len(pending) // width
            if count:
                payload = bytes(pending[: count * width])
                meter.push(np.frombuffer(payload, "<f8").reshape(count, -1))
                for offset in range(0, len(payload), width):
                    queue.append(payload[offset : offset + width])
                del pending[: count * width]
        trailer = bytes(pending)
        (output / "trailer.bin").write_bytes(trailer)
        require(trailer == str(queue.rows).encode(), "Exact native count trailer")
        safety, data, grid = meter.finish()
        ledger = queue.finish()
        result = dict(
            status="PASS_COMPLETE_CAPTURE",
            **meta,
            rows=queue.rows,
            values=queue.rows * len(meta["columns"]),
            safety=safety,
            time_grid=grid,
            measurement=measurements(data, config),
            raw_sha256=whole.hexdigest(),
            payload_sha256=ledger["payload_sha256"],
        )
        n.common.atomic(output / "capture.json", result)
        return result
    except BaseException as error:
        # Preserve incomplete samples too; no cleanup without a public proof.
        retention_error = None
        try:
            (output / "unpublished-tail.bin").write_bytes(queue.pending)
            (output / "unparsed-tail.bin").write_bytes(pending)
        except BaseException as failed_write:
            retention_error = repr(failed_write)
        n.common.atomic(
            output / "failure.json",
            dict(
                status="ERROR_CAPTURE",
                error=repr(error),
                observed_rows=queue.rows,
                retention_error=retention_error,
            ),
        )
        raise


def guard(folder):
    free = shutil.disk_usage("/dev/shm").free
    require(free >= FLOOR, "Shared 512 MiB floor")
    used = sum(p.stat().st_size for p in folder.rglob("*") if p.is_file())
    require(used <= CAP, "Own 50 MiB capture ceiling")
    return free, used


def native_limit():
    resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
    resource.setrlimit(resource.RLIMIT_FSIZE, (45 * 1024**2, 45 * 1024**2))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})


def native_wait(folder, consume):
    """Frozen group owner; changed limit/env and explicit artifact resource guard."""
    fifo = folder / "stream.fifo"
    os.mkfifo(fifo)
    keepalive = os.open(fifo, os.O_RDWR)
    reader_stream = fifo.open("rb")
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("GH_TOKEN", "GITHUB_TOKEN", "LD_PRELOAD")
    }
    env.update(SPICE_SCRIPTS=str(folder), RAYON_NUM_THREADS="1", OMP_NUM_THREADS="1")
    command = [str(n.NG), "-n", "-b", "bench.cir"]
    start = time.monotonic()
    process, pool = None, None
    minimum, peak = guard(folder)
    pipe_stalls = []

    def close_keepalive():
        nonlocal keepalive
        if keepalive is not None:
            os.close(keepalive)
            keepalive = None

    with life.ProcessOwner(folder / "owned-processes.json") as owner:
        try:
            with (folder / "run.log").open("x") as log:
                process = owner.launch(
                    "native",
                    command,
                    cwd=folder,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    preexec_fn=native_limit,
                )
                pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)

                def reader():
                    try:
                        with reader_stream as stream:
                            return consume(stream, owner)
                    except BaseException as error:
                        owner.request_cancel(error)
                        raise

                future = pool.submit(reader)
                while True:
                    if future.done():
                        captured = future.result()
                    owner.check()
                    free, used = guard(folder)
                    minimum, peak = min(minimum, free), max(peak, used)
                    try:
                        wchan = Path(f"/proc/{process.pid}/wchan").read_text().strip()
                    except (FileNotFoundError, ProcessLookupError):
                        wchan = None
                    if (
                        wchan in ("anon_pipe_write", "pipe_write")
                        and len(pipe_stalls) < 16
                    ):
                        pipe_stalls.append(
                            dict(elapsed_s=time.monotonic() - start, wchan=wchan)
                        )
                    code = process.poll()
                    if code is not None:
                        close_keepalive()
                        require(code == 0, "Native nonzero exit")
                        if future.done():
                            code = owner.complete(process)
                            break
                    owner.cancelled.wait(0.05)
        except BaseException as error:
            owner.stop_failed(error)
            close_keepalive()
            raise
        finally:
            close_keepalive()
            if pool is not None:
                pool.shutdown(wait=True)
            reader_stream.close()
            n.common.atomic(
                folder / "execution.json",
                dict(
                    returncode=None if process is None else process.poll(),
                    elapsed_seconds=time.monotonic() - start,
                    elapsed_watchdog_seconds=None,
                    address_space_limit_bytes=1024**3,
                    min_free_bytes=minimum,
                    max_own_artifact_bytes=peak,
                    native_and_publisher_groups_owned=True,
                    observed_native_pipe_backpressure=pipe_stalls,
                ),
            )
    fifo.unlink()
    return captured


def startup_proof(folder, prior):
    log = (folder / "run.log").read_text()
    bad = [
        line
        for line in log.splitlines()
        if re.search(
            r"warning|error|failed|singular|timestep too small|gmin stepping|source stepping",
            line,
            re.I,
        )
    ]
    require(not bad and "ngspice-47 done" in log, "Strict clean native diagnostics")
    flags = [
        "q." + r["path"] + ".qnpn13g2"
        for r in prior["devices"]
        if r["model"] == "npn13g2"
    ]
    observed = re.findall(
        r"(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$", log
    )
    require(
        [x[0] for x in observed] == flags and len(flags) == 64,
        "Exact 64 native OFF devices",
    )
    for name, body in observed:
        require(
            re.findall(r"(?m)^\s*device\s+(\S+)\s*$", body) == [name[:21]]
            and re.findall(r"(?m)^\s*off\s+([01])\s*$", body) == ["1"],
            "Native OFF readback",
        )
    op = n.read_raw(
        folder / "op.raw",
        n.vectors(prior["devices"], prior["config"]["extra_vectors"]),
        False,
    )
    require(
        all(len(v) == 1 and abs(v[0]) <= 1e-10 for v in op.values()),
        "Exact finite zero-source OP",
    )
    return dict(zero_source_op=True, native_off_flags=flags, clean_diagnostics=True)


def bind_receipt(path, digest, expected_status):
    require(n.common.sha(path) == digest, "Externally pinned prerequisite")
    record = json.loads(Path(path).read_text())
    require(record["status"] == expected_status, "Actual prerequisite status")
    for source, pin in record.get("inputs", {}).items():
        require(n.common.pin(source) == pin, "Prerequisite input drift")
    for name, pin in record.get("outputs", {}).items():
        require(
            n.common.pin(Path(path).parent / name) == pin, "Prerequisite output drift"
        )
    return record


def run(out, prefix, step, stop, reference, reference_sha, gate=None, gate_sha=None):
    prior = verify_parent()
    reference_record = bind_receipt(
        reference, reference_sha, "PASS_ORIGINAL_PUBLIC_RAW_REPLAY"
    )
    if step == 2.5e-12 or stop == 400e-9:
        required = bind_receipt(gate, gate_sha, "PASS_NATIVE_STREAM_FINITE_SCREEN")
        target_step = 5e-12 if stop == 34e-9 else 2.5e-12
        require(
            required["config"]["stop_s"] == 34e-9
            and required["config"]["step_s"] == target_step,
            "Actual shorter/transport prerequisite",
        )
        require(
            required["safety"]["passed"] and required["measurement"]["passed"],
            "No safety waiver",
        )
        if stop == 34e-9:
            require(
                required["original_payload_and_measurements_equal"] is True,
                "Exact native FIFO control",
            )
    require(
        not out.exists() and out.resolve().is_relative_to("/dev/shm"),
        "Fresh RAM output",
    )
    require(shutil.disk_usage("/dev/shm").free >= FLOOR + CAP, "Entry reserve")
    out.mkdir()
    config = copy.deepcopy(prior["config"])
    config.update(step_s=step, stop_s=stop, window_s=[4e-9, stop])
    for source in config["sources"]:
        shutil.copyfile(ORIGINAL / Path(source).name, out / Path(source).name)
    (out / "spinit").write_bytes((ORIGINAL / "spinit").read_bytes())
    (out / "bench.cir").write_text(
        stream_deck((ORIGINAL / "bench.cir").read_text(), step, stop)
    )
    paths = (
        list(prior["inputs"])
        + [str(ROOT / "scripts" / name) for name in PINS]
        + [__file__, str(reference)]
    )
    if gate:
        paths.append(str(gate))
    paths += method_inventory() + [str(p) for p in out.iterdir()]
    pins = {str(Path(p).resolve()): n.common.pin(p) for p in paths}
    record = dict(
        status="RUNNING",
        inputs=pins,
        config=config,
        devices=prior["devices"],
        parent_result_sha256=ORIGINAL_SHA,
        unchanged_physical_devices=539,
        scope="Finite nominal schematic loop; not PLL lock, PVT, jitter, thermal equilibrium, layout or foundry SOA",
    )
    n.common.atomic(out / "result.json", record)
    try:
        captured = native_wait(
            out,
            lambda stream, owner: capture(
                stream,
                out / "capture",
                prior,
                config,
                prefix,
                life.OwnedPublisher(owner),
            ),
        )
        record.update(captured)
        record.update(startup_proof(out, prior))
        record["original_payload_and_measurements_equal"] = None
        if step == 5e-12 and stop == 34e-9:
            equality = all(
                captured[k] == reference_record[k]
                for k in (
                    "payload_sha256",
                    "safety",
                    "measurement",
                    "time_grid",
                    "rows",
                )
            )
            require(
                equality,
                "Actual streaming native must exactly reproduce original payload and reductions",
            )
            record["original_payload_and_measurements_equal"] = True
        require(
            all(n.common.pin(p) == pin for p, pin in pins.items()),
            "Post-native immutable inputs",
        )
        record["status"] = (
            "PASS_NATIVE_STREAM_FINITE_SCREEN"
            if captured["safety"]["passed"] and captured["measurement"]["passed"]
            else "FAIL_NATIVE_STREAM_FINITE_SCREEN"
        )
    except BaseException as error:
        record.update(status="ERROR_NATIVE_OR_STREAM_CAPTURE", error=repr(error))
        raise
    finally:
        record["outputs"] = {
            str(p.relative_to(out)): n.common.pin(p)
            for p in out.rglob("*")
            if p.is_file() and p.name != "result.json"
        }
        n.common.atomic(out / "result.json", record)
    return record


def replay_original(out):
    prior = verify_parent()
    entry_pins = {
        str(Path(p).resolve()): n.common.pin(p)
        for p in [
            __file__,
            PUBLIC,
            ORIGINAL / "result.json",
            *[ROOT / "scripts" / name for name in PINS],
            *method_inventory(),
        ]
    }
    require(not out.exists(), "Fresh replay receipt")
    ledger = json.loads(PUBLIC.read_text())
    require(
        ledger["native_result"] == n.common.pin(ORIGINAL / "result.json")
        and ledger["whole_raw"] == prior["outputs"]["wave.raw"],
        "Original public bridge",
    )
    whole, payload = hashlib.sha256(), hashlib.sha256()
    pending, offset, meter, width = bytearray(), 0, None, None
    for index, part in enumerate(ledger["parts"]):
        a, manifest = part["asset"], part["manifest"]
        require(
            a["authenticated_roundtrip"] and a["anonymous_roundtrip"],
            "Sealed publication",
        )
        with urllib.request.urlopen(
            urllib.request.Request(
                a["url"], headers={"User-Agent": "nssoc-pll-stream-replay"}
            ),
            timeout=120,
        ) as response:
            packed = response.read(8 * 1024**2 + 1)
        require(
            len(packed) == a["bytes"]
            and hashlib.sha256(packed).hexdigest() == a["sha256"],
            "Compressed source part",
        )
        with tarfile.open(fileobj=io.BytesIO(packed)) as archive:
            raw = archive.extractfile("wave.bin").read()
            require(
                json.load(archive.extractfile("part.json")) == manifest, "Part identity"
            )
        require(
            manifest["index"] == index
            and manifest["offset"] == offset
            and len(raw) == manifest["bytes"]
            and hashlib.sha256(raw).hexdigest() == manifest["sha256"],
            "Exact original raw part",
        )
        whole.update(raw)
        offset += len(raw)
        pending.extend(raw)
        if meter is None:
            require(b"Binary:\n" in pending, "Original header in first part")
            h, rest = bytes(pending).split(b"Binary:\n", 1)
            header = h + b"Binary:\n"
            _, meta = life.tiny.parse_header(
                io.BytesIO(header),
                n.vectors(prior["devices"], prior["config"]["extra_vectors"]),
            )
            require(meta["declared_points"] > 0, "Original seekable count")
            pending = bytearray(rest)
            meter = Meter(meta["columns"], prior["devices"], prior["config"])
            width = len(meta["columns"]) * 8
        count = len(pending) // width
        body = bytes(pending[: count * width])
        payload.update(body)
        meter.push(np.frombuffer(body, "<f8").reshape(count, -1))
        del pending[: count * width]
    require(
        not pending
        and dict(bytes=offset, sha256=whole.hexdigest()) == ledger["whole_raw"],
        "Complete original raw without thinning",
    )
    safety, data, grid = meter.finish()
    require(meter.count == meta["declared_points"], "Original full count")
    require(
        safety == prior["safety"]
        and grid == prior["time_grid"]
        and loop.base.measure(data, prior["config"]) == prior["measurement"],
        "All frozen original scalar reductions exact",
    )
    record = dict(
        status="PASS_ORIGINAL_PUBLIC_RAW_REPLAY",
        original_result=n.common.pin(ORIGINAL / "result.json"),
        original_authoritative_status=prior["status"],
        original_raw=ledger["whole_raw"],
        rows=meter.count,
        values=meter.count * len(meta["columns"]),
        payload_sha256=payload.hexdigest(),
        safety=safety,
        time_grid=grid,
        measurement=loop.measure(data, prior["config"]),
        inputs=entry_pins,
        public_parts=len(ledger["parts"]),
        no_native_execution=True,
    )
    verify_parent()
    require(
        all(n.common.pin(p) == pin for p, pin in entry_pins.items()),
        "Replay method/input drift",
    )
    n.common.atomic(out, record)
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--replay-original", action="store_true")
    p.add_argument("--prefix")
    p.add_argument("--step-ps", type=float, choices=[5, 2.5])
    p.add_argument("--stop-ns", type=float, choices=[34, 400])
    p.add_argument("--reference", type=Path)
    p.add_argument("--reference-sha")
    p.add_argument("--gate", type=Path)
    p.add_argument("--gate-sha")
    a = p.parse_args()
    if a.replay_original:
        r = replay_original(a.out)
    else:
        require(
            all(
                x is not None
                for x in (a.prefix, a.step_ps, a.stop_ns, a.reference, a.reference_sha)
            ),
            "Explicit native contract",
        )
        r = run(
            a.out,
            a.prefix,
            {5: 5e-12, 2.5: 2.5e-12}[a.step_ps],
            {34: 34e-9, 400: 400e-9}[a.stop_ns],
            a.reference,
            a.reference_sha,
            a.gate,
            a.gate_sha,
        )
    print(r["status"])
    return 0 if r["status"].startswith("PASS_") else 1


if __name__ == "__main__":
    raise SystemExit(main())
