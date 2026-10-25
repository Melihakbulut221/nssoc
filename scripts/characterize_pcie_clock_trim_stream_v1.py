#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Separate continuous cold-start streaming experiment; never replaces old results."""

import argparse
from array import array
import hashlib
import json
import lzma
import math
import os
from pathlib import Path
import re
import shutil
import signal
import statistics
import struct
import subprocess
import sys
import time

import probe_pcie_clock_stream_capture_v1 as tiny
import publish_pcie_native_capture as publication

base = tiny.base
require = base.require
TINY_SHA = "13e370d57778999a1bbd97dfeeb6aaef8dbe65e6fcdd4fa0393d1b2fec985c07"
PUBLISHER_SHA = "7d974fdf1a37d987a9464c4e13dfbbc464fe01e9da6e0d147795694f1adfa03e"
STOP = 1e-6
WINDOW = 2e-9
PART_ROWS = 65536  # <=87.56 MB raw; synchronous queue has at most one part.
MIN_FREE_BYTES = 512 * 1024**2


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def atomic(path, value):
    base.driver.atomic_record(Path(path), value)


class Stats:
    """Compensated bounded-memory scalar reduction, no point decimation."""

    def __init__(self):
        self.n = 0
        self.low, self.high = math.inf, -math.inf
        self.total, self.correction = 0.0, 0.0
        self.first = self.last = None

    def add(self, x):
        require(math.isfinite(x), "Finite reduction value")
        if not self.n:
            self.first = x
        self.last = x
        self.n += 1
        self.low, self.high = min(self.low, x), max(self.high, x)
        y = x - self.correction
        total = self.total + y
        self.correction = (total - self.total) - y
        self.total = total

    @property
    def mean(self):
        require(self.n > 0, "Nonempty reduction")
        return self.total / self.n

    @property
    def absmax(self):
        return max(abs(self.low), abs(self.high))


def clock_data():
    return {n: array("d") for n in ("time", "v(clkp)", "v(clkn)")}


def add_clock(data, t, p, n):
    for key, value in zip(data, (t, p, n)):
        data[key].append(value)


class Meter:
    """Every sample contributes to safety; only bounded clock windows retained."""

    def __init__(self, columns, hbts, case, stop=STOP):
        require(
            stop >= 12e-9 and abs(stop / WINDOW - round(stop / WINDOW)) < 1e-6,
            "Complete2ns windows and original4-to12ns history",
        )
        require(
            len(columns) == len(set(columns))
            and set(columns) == {"time", *base.prior.vectors(hbts)},
            "Exact complete metrology vector census",
        )
        self.columns, self.hbts, self.case, self.stop = columns, hbts, case, stop
        self.index = {n: i for i, n in enumerate(columns)}
        self.full = {n: Stats() for n in columns}
        self.active = {n: Stats() for n in columns}
        self.vce_full = {n: Stats() for n in hbts}
        self.vce_active = {n: Stats() for n in hbts}
        self.switch = {
            f"xtsw{s}{b}": {
                k: Stats() for k in ("vgs", "vgd", "vds", "active_vds", "plate")
            }
            for s in range(3)
            for b in range(2)
        }
        self.rail_error = {"0": 0.0, "1": 0.0}
        self.common, self.power = Stats(), Stats()
        self.thermal = [n for n in columns if n.endswith((".t)", ".dt)"))]
        require(len(self.thermal) == len(hbts) + 23, "All53 native thermal nodes")
        self.final_clock, self.history = clock_data(), clock_data()
        self.windows, self.wi, self.last_row = [], 0, None
        self._new_window()

    def _new_window(self):
        self.wstart = self.wi * WINDOW
        self.wend = min((self.wi + 1) * WINDOW, self.stop)
        self.wclock = clock_data()
        self.wthermal = {n: Stats() for n in self.thermal}

    def _window_add(self, row):
        ix = self.index
        add_clock(
            self.wclock,
            min(row[ix["time"]], self.stop),
            row[ix["v(clkp)"]],
            row[ix["v(clkn)"]],
        )
        for n, s in self.wthermal.items():
            s.add(row[ix[n]])

    def _close_window(self):
        value = base.clock_window(self.wclock, self.wstart, self.wend)
        elapsed = self.wclock["time"][-1] - self.wclock["time"][0]
        value["thermal_nodes"] = {
            n: dict(
                start_v=s.first,
                end_v=s.last,
                min_v=s.low,
                max_v=s.high,
                mean_v=s.mean,
                signed_rate_v_per_ns=(s.last - s.first) / elapsed * 1e-9,
            )
            for n, s in self.wthermal.items()
        }
        self.windows.append(value)

    def push(self, row):
        require(
            len(row) == len(self.columns) and all(map(math.isfinite, row)),
            "Complete finite metrology sample",
        )
        ix, t = self.index, row[self.index["time"]]
        prev = None if self.last_row is None else self.last_row[ix["time"]]
        require(
            (prev is None and t == 0)
            or (prev is not None and 0 < t - prev <= self.case["step_s"] * 1.00001),
            "Continuous time0 metrology",
        )
        require(
            t <= self.stop + 4 * math.ulp(self.stop), "No data after fixed endpoint"
        )
        # Native binary endpoint rounding only; raw time and every value stay intact.
        classified_t = min(t, self.stop)
        active = t >= 4e-9

        def v(net):
            if net == "avss":
                return 0.0
            name = net if net in ("avdd", "clkp", "clkn") else "xosc." + net
            return row[ix["v(" + name + ")"]]

        for n, value in zip(self.columns, row):
            self.full[n].add(value)
            if active:
                self.active[n].add(value)
        for name, ((collector, _, emitter), _) in self.hbts.items():
            value = v(collector) - v(emitter)
            self.vce_full[name].add(value)
            if active:
                self.vce_active[name].add(value)
        for stage in range(3):
            for bit in range(2):
                d, s, g = (
                    row[ix[f"v(xosc.tp{stage}{bit}p)"]],
                    row[ix[f"v(xosc.tp{stage}{bit}n)"]],
                    row[ix[f"v(trim{bit})"]],
                )
                stats = self.switch[f"xtsw{stage}{bit}"]
                for key, value in (("vgs", g - s), ("vgd", g - d), ("vds", d - s)):
                    stats[key].add(value)
                if active:
                    stats["active_vds"].add(d - s)
                    stats["plate"].add((d + s) / 2)
        if active:
            for bit in range(2):
                target = (
                    self.case["supply"]
                    if self.case["code"] > bit and not self.case.get("trim_fault")
                    else 0
                )
                self.rail_error[str(bit)] = max(
                    self.rail_error[str(bit)], abs(row[ix[f"v(trim{bit})"]] - target)
                )
            self.common.add((v("clkp") + v("clkn")) / 2)
            self.power.add(-v("avdd") * row[ix["i(vdd)"]])
        if 4e-9 <= classified_t <= 12e-9:
            add_clock(self.history, classified_t, v("clkp"), v("clkn"))
        if self.stop - 8e-9 <= classified_t <= self.stop:
            add_clock(self.final_clock, classified_t, v("clkp"), v("clkn"))
        while t > self.wend and self.wend < self.stop:
            self._close_window()
            self.wi += 1
            self._new_window()
            if prev == self.wstart:
                self._window_add(self.last_row)
        self._window_add(row)
        self.last_row = row

    def finish(self):
        require(
            self.last_row is not None
            and self.stop
            <= self.last_row[self.index["time"]]
            <= self.stop + 4 * math.ulp(self.stop),
            "Full final metrology endpoint required",
        )
        self._close_window()
        require(
            len(self.windows) == round(self.stop / WINDOW),
            "Every consecutive2ns window",
        )
        devices = {}
        for n, (_, nx) in self.hbts.items():
            ic = f"@q.xosc.{n}.qnpn13g2[ic]"
            ib = f"@q.xosc.{n}.qnpn13g2[ib]"
            thermal = f"v(xosc.{n}.t)"
            f, a = self.full, self.active
            devices[n] = dict(
                nx=nx,
                full_capture_max_vce_v=self.vce_full[n].high,
                full_capture_max_abs_ic_a=f[ic].absmax,
                full_capture_thermal_node_min_v=f[thermal].low,
                full_capture_thermal_node_max_v=f[thermal].high,
                min_vce_v=self.vce_active[n].low,
                max_vce_v=self.vce_active[n].high,
                max_abs_ic_a=a[ic].absmax,
                mean_ic_a=a[ic].mean,
                mean_ib_a=a[ib].mean,
                max_abs_ib_a=a[ib].absmax,
                thermal_node_min_v=a[thermal].low,
                thermal_node_max_v=a[thermal].high,
            )
        switches = {}
        for stage in range(3):
            for bit in range(2):
                n = f"xtsw{stage}{bit}"
                d, s, g = (
                    self.full[f"v(xosc.tp{stage}{bit}p)"],
                    self.full[f"v(xosc.tp{stage}{bit}n)"],
                    self.full[f"v(trim{bit})"],
                )
                stats = self.switch[n]
                switches[n] = dict(
                    expected_on=self.case["code"] > bit
                    and not self.case.get("trim_fault"),
                    full_gate_min_v=g.low,
                    full_gate_max_v=g.high,
                    full_drain_min_v=d.low,
                    full_source_min_v=s.low,
                    full_drain_max_v=d.high,
                    full_source_max_v=s.high,
                    full_max_abs_vgs_v=stats["vgs"].absmax,
                    full_max_abs_vgd_v=stats["vgd"].absmax,
                    full_max_abs_vds_v=stats["vds"].absmax,
                    full_max_abs_ids_a=self.full[
                        f"@n.xosc.{n}.nsg13_hv_nmos[ids]"
                    ].absmax,
                    full_max_abs_idb_a=self.full[
                        f"@n.xosc.{n}.nsg13_hv_nmos[idb]"
                    ].absmax,
                    full_max_abs_isb_a=self.full[
                        f"@n.xosc.{n}.nsg13_hv_nmos[isb]"
                    ].absmax,
                    active_max_abs_vds_v=stats["active_vds"].absmax,
                    active_mean_plate_v=stats["plate"].mean,
                )
        limits = base.old.LIMITS
        checks = dict(
            headroom=all(
                d["min_vce_v"] >= limits["min_vce_v"] for d in devices.values()
            ),
            maximum_vce=all(
                d["max_vce_v"] <= limits["max_vce_v"] for d in devices.values()
            ),
            current_density=all(
                d["max_abs_ic_a"] < d["nx"] * limits["max_collector_a_per_emitter"]
                for d in devices.values()
            ),
            full_capture_maximum_vce=all(
                d["full_capture_max_vce_v"] <= limits["max_vce_v"]
                for d in devices.values()
            ),
            full_capture_current_density=all(
                d["full_capture_max_abs_ic_a"]
                < d["nx"] * limits["max_collector_a_per_emitter"]
                for d in devices.values()
            ),
            switch_terminal_voltage=all(
                min(x["full_gate_min_v"], x["full_drain_min_v"], x["full_source_min_v"])
                >= -0.05
                and max(
                    x["full_gate_max_v"],
                    x["full_drain_max_v"],
                    x["full_source_max_v"],
                    x["full_max_abs_vgs_v"],
                    x["full_max_abs_vgd_v"],
                    x["full_max_abs_vds_v"],
                )
                <= 3.3
                for x in switches.values()
            ),
            native_trim_gate_rails=max(self.rail_error.values()) <= 1e-10,
        )
        final = base.clock_window(self.final_clock, self.stop - 8e-9, self.stop)
        history = base.clock_window(self.history, 4e-9, 12e-9)
        conv = convergence(self.windows, self.stop)
        return dict(
            rows=self.full["time"].n,
            full_capture_window_s=[0.0, self.stop],
            raw_final_time_s=self.last_row[self.index["time"]],
            endpoint_classification_tolerance_s=4 * math.ulp(self.stop),
            operating_window_s=[4e-9, self.stop],
            devices=devices,
            switches=switches,
            trim_gate_rail_error_v=self.rail_error,
            mean_common_mode_v=self.common.mean,
            mean_supply_power_w=self.power.mean,
            safety_checks=checks,
            original_4_to12ns_clock_window=history,
            final_clock_window=final,
            consecutive2ns_windows=self.windows,
            convergence=conv,
            all_column_ranges={n: [s.low, s.high] for n, s in self.full.items()},
            limited_thermal_screen_pass=all(checks.values())
            and final["functional_pass"]
            and conv["converged"],
            prior_failures_superseded=False,
            frequency_lock_or_pcie_acceptance=False,
        )


def convergence(windows, stop):
    require(
        len(windows) == round(stop / WINDOW)
        and all(
            w["declared_window_s"] == [i * WINDOW, min((i + 1) * WINDOW, stop)]
            for i, w in enumerate(windows)
        ),
        "Complete fixed trajectory",
    )
    tail = windows[-4:]
    fs = [w["frequency_hz"] for w in tail]
    keys = set(tail[0]["thermal_nodes"])
    require(
        len(keys) == 53 and all(set(w["thermal_nodes"]) == keys for w in windows),
        "Every thermal state/window",
    )
    valid = all(f is not None and math.isfinite(f) and f > 0 for f in fs)
    span = (max(fs) - min(fs)) / statistics.mean(fs) * 1e6 if valid else None
    rates = {
        n: [abs(w["thermal_nodes"][n]["signed_rate_v_per_ns"]) for w in tail]
        for n in sorted(keys)
    }
    checks = dict(
        final_four_frequency_means_within100ppm=span is not None
        and span <= base.FREQUENCY_SPAN_PPM,
        all_final_thermal_rates_within_limit=all(
            v[-1] <= base.THERMAL_RATE_V_PER_NS for v in rates.values()
        ),
        all_final_thermal_rates_nonincreasing=all(
            all(
                b <= a + base.RATE_INCREASE_TOLERANCE_V_PER_NS for a, b in zip(v, v[1:])
            )
            for v in rates.values()
        ),
    )
    return dict(
        declared_window_s=[stop - 8e-9, stop],
        frequency_span_ppm=span,
        max_final_thermal_rate_v_per_ns=max(v[-1] for v in rates.values()),
        rates_by_node_v_per_ns=rates,
        checks=checks,
        converged=all(checks.values()),
        scope="Finite endpoint-average2ns thermal slopes, not instantaneous derivative or infinite-time equilibrium",
    )


def release_part(path, receipt):
    """One immutable part, both remote byte roundtrips; never overwrite an asset."""
    require(sha(Path(publication.__file__)) == PUBLISHER_SHA, "Frozen publisher")
    subprocess.run(
        [
            sys.executable,
            str(Path(publication.__file__)),
            "--out",
            str(receipt),
            str(path),
        ],
        check=True,
    )
    record = json.loads(Path(receipt).read_text())
    require(
        record["status"] == "PASS_IMMUTABLE_RELEASE_ROUNDTRIPS"
        and len(record["assets"]) == 1,
        "Complete single-part publication",
    )
    return record["assets"][0]


class PartQueue:
    """Synchronous one-part queue; uploader backpressure blocks native FIFO writes."""

    def __init__(
        self,
        root,
        prefix,
        columns,
        publisher=release_part,
        rows_per_part=PART_ROWS,
        reclaim=True,
        min_free_bytes=MIN_FREE_BYTES,
    ):
        self.root = Path(root)
        self.root.mkdir()
        require(
            re.fullmatch(r"[a-z0-9][a-z0-9-]{4,110}", prefix),
            "Safe unique asset prefix",
        )
        require(1 <= rows_per_part <= PART_ROWS, "Bounded part size")
        self.prefix, self.columns, self.publisher = prefix, columns, publisher
        self.rows_per_part, self.reclaim, self.min_free = (
            rows_per_part,
            reclaim,
            min_free_bytes,
        )
        self.width = len(columns) * 8
        self.pending = bytearray()
        self.rows, self.parts = 0, []
        self.hash = hashlib.sha256()
        self.ledger = dict(
            status="RUNNING",
            queue_capacity=1,
            columns=columns,
            parts=self.parts,
            prefix=prefix,
            rows_per_part=rows_per_part,
            no_decimation=True,
        )
        self._save()

    def _save(self):
        atomic(self.root / "parts.json", self.ledger)

    def append(self, sample):
        require(len(sample) == self.width, "Complete native frame")
        self.hash.update(sample)
        self.pending.extend(sample)
        self.rows += 1
        if len(self.pending) == self.width * self.rows_per_part:
            self.flush()

    def flush(self):
        if not self.pending:
            return
        require(
            shutil.disk_usage(self.root).free >= self.min_free,
            "Preserve free-space reserve before publication",
        )
        raw = bytes(self.pending)
        index = len(self.parts)
        path = self.root / f"{self.prefix}-part{index:05d}.bin.xz"
        require(not path.exists(), "Never replace a part")
        packed = lzma.compress(raw, preset=1)
        path.write_bytes(packed)
        row = dict(
            index=index,
            first_row=self.rows - len(raw) // self.width,
            rows=len(raw) // self.width,
            name=path.name,
            uncompressed_bytes=len(raw),
            uncompressed_sha256=hashlib.sha256(raw).hexdigest(),
            bytes=len(packed),
            sha256=hashlib.sha256(packed).hexdigest(),
            status="AWAITING_PUBLICATION",
        )
        self.parts.append(row)
        self._save()
        receipt = self.root / f"publication-{index:05d}.json"
        try:
            asset = self.publisher(path, receipt)
            require(
                asset["name"] == path.name
                and asset["bytes"] == row["bytes"]
                and asset["sha256"] == row["sha256"]
                and asset["authenticated_roundtrip"] is True
                and asset["anonymous_roundtrip"] is True,
                "Exact two-path part roundtrip",
            )
            require(
                path.stat().st_size == row["bytes"] and sha(path) == row["sha256"],
                "Part changed while publishing",
            )
            require(receipt.is_file(), "Persistent publication evidence")
            row.update(
                status="PUBLIC_VERIFIED",
                asset=asset,
                receipt_sha256=sha(receipt),
                local_state="PRESENT",
            )
            self._save()
            if self.reclaim:
                path.unlink()
                row["local_state"] = "REMOVED_EXACT_PUBLIC_DUPLICATE"
                self._save()
            self.pending.clear()
        except BaseException as error:
            row.update(status="PUBLICATION_FAILED", error=repr(error))
            self.ledger["status"] = "ERROR_PART_RETAINED"
            self._save()
            raise

    def finish(self):
        self.flush()
        require(
            all(x["status"] == "PUBLIC_VERIFIED" for x in self.parts),
            "No unpublished part",
        )
        count = 0
        for i, p in enumerate(self.parts):
            require(
                p["index"] == i and p["first_row"] == count,
                "Unique ordered complete part coverage",
            )
            count += p["rows"]
        require(count == self.rows, "Every captured row belongs to one part")
        self.ledger.update(
            status="PASS_PUBLISHED_PARTS",
            rows=self.rows,
            payload_sha256=self.hash.hexdigest(),
        )
        self._save()
        return self.ledger


def capture_stream(
    stream,
    output,
    expected,
    hbts,
    case,
    prefix,
    stop=STOP,
    publisher=release_part,
    rows_per_part=PART_ROWS,
    reclaim=True,
    min_free_bytes=MIN_FREE_BYTES,
):
    require(sys.byteorder == "little", "Pinned x86 binary format")
    output = Path(output)
    output.mkdir()
    header, meta = tiny.parse_header(stream, expected)
    require(meta["declared_points"] == 0, "Native nonseekable zero-count header")
    (output / "header.bin").write_bytes(header)
    meter = Meter(meta["columns"], hbts, case, stop)
    queue = PartQueue(
        output / "parts",
        prefix,
        meta["columns"],
        publisher,
        rows_per_part,
        reclaim,
        min_free_bytes,
    )
    decoder = struct.Struct("<" + "d" * len(meta["columns"]))
    pending, raw_hash = bytearray(), hashlib.sha256(header)
    try:
        while data := stream.read(65536):
            raw_hash.update(data)
            pending.extend(data)
            count = len(pending) // decoder.size
            for i in range(count):
                sample = bytes(pending[i * decoder.size : (i + 1) * decoder.size])
                meter.push(decoder.unpack(sample))
                queue.append(sample)
            del pending[: count * decoder.size]
        trailer = bytes(pending)
        (output / "trailer.bin").write_bytes(trailer)
        require(
            trailer == str(queue.rows).encode(), "Exact completed native count trailer"
        )
        measurement = meter.finish()
        ledger = queue.finish()
        result = dict(
            **meta,
            rows=queue.rows,
            stop_s=stop,
            step_s=case["step_s"],
            raw_sha256=raw_hash.hexdigest(),
            payload_sha256=ledger["payload_sha256"],
            header_sha256=sha(output / "header.bin"),
            trailer_sha256=sha(output / "trailer.bin"),
            ledger_sha256=sha(output / "parts/parts.json"),
            measurement=measurement,
            status="PASS_COMPLETE_CAPTURE",
            live_release_publication=publisher is release_part,
            semantic_screen_pass=measurement["limited_thermal_screen_pass"],
        )
        atomic(output / "capture.json", result)
        return result
    except BaseException as error:
        atomic(
            output / "failure.json",
            dict(
                status="INCOMPLETE_OR_INVALID_CAPTURE",
                error=repr(error),
                observed_rows=queue.rows,
                completed_parts=len(queue.parts),
            ),
        )
        raise


def replay_local_parts(root, ledger):
    """Verify local retained parts before independent numeric/stream replay."""
    root = Path(root)
    require(ledger["status"] == "PASS_PUBLISHED_PARTS", "Complete part ledger")
    payload, count = hashlib.sha256(), 0
    for index, part in enumerate(ledger["parts"]):
        require(
            part["index"] == index
            and part["first_row"] == count
            and part["name"] == f"{ledger['prefix']}-part{index:05d}.bin.xz",
            "Unique ordered part identity",
        )
        path = root / part["name"]
        require(
            path.stat().st_size == part["bytes"] and sha(path) == part["sha256"],
            "Compressed part changed",
        )
        raw = lzma.decompress(path.read_bytes())
        require(
            len(raw)
            == part["uncompressed_bytes"]
            == part["rows"] * len(ledger["columns"]) * 8
            and hashlib.sha256(raw).hexdigest() == part["uncompressed_sha256"],
            "Decoded part changed",
        )
        payload.update(raw)
        count += part["rows"]
        yield raw
    require(
        count == ledger["rows"] and payload.hexdigest() == ledger["payload_sha256"],
        "Every original native row exactly once",
    )


def long_deck(original, step):
    old = f"tran {step:.12g} 40n 0 {step:.12g}"
    require(
        original.count(old) == 1 and original.count(".control") == 1,
        "Exact original40ns analysis",
    )
    text = original.replace(
        ".control", f".tran {step:.12g} 1u 0 {step:.12g}\n.control", 1
    )
    text = text.replace(old, "run stream.fifo\nsetplot\ndisplay\nrusage space")
    writers = [
        line for line in text.splitlines() if line.startswith("wrdata wave.dat ")
    ]
    require(len(writers) == 1, "One historical fullwave writer")
    text = text.replace(writers[0] + "\n", "")
    require(
        text.count("alter @q.xosc.") == 30
        and not re.search(r"(?im)^\s*(reset|resume)\b|\buic\b|^\s*\.ic\b", text),
        "Exact native initialization and continuous analysis",
    )
    return text


def verify_parent(parent):
    parent = Path(parent).resolve()
    require(
        sha(Path(tiny.__file__)) == TINY_SHA
        and sha(Path(base.__file__)) == tiny.THERMAL_SHA
        and sha(Path(publication.__file__)) == PUBLISHER_SHA
        and sha(parent / "result.json") == tiny.RESULT_SHA,
        "Frozen tiny/thermal/parent/publisher identity",
    )
    prior = json.loads((parent / "result.json").read_text())
    pins = dict(prior["source_sha256"])
    for p in (
        Path(tiny.__file__),
        Path(__file__),
        Path(publication.__file__),
        parent / "result.json",
    ):
        pins[str(p.resolve())] = sha(p)
    require(
        all(sha(p) == h for p, h in pins.items()),
        "All original sources/model/runtime pins",
    )
    for row in prior["cases"]:
        d = parent / row["case"]["name"]
        for name in ("bench.cir", base.prior.FILE):
            require(
                sha(d / name) == row["outputs"][name], "Prior exact deck/circuit input"
            )
            pins[str(d / name)] = sha(d / name)
        require(
            sha(d / base.prior.FILE) == base.PRIOR_CIRCUIT_SHA,
            "Unchanged exact native circuit",
        )
    require(
        [x["case"] for x in prior["cases"]] == base.cases(),
        "Exact inherited precision pair",
    )
    return prior, pins


def stop_failed_group(process):
    """Bound only failure/cancellation cleanup; healthy simulation is unlimited."""
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        pass
    finally:
        # The leader may already have exited while a descendant ignored TERM.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def native_wait(runtime, folder, log, consume):
    """Actual completion or bounded group cleanup after explicit failure/cancel."""
    import concurrent.futures

    rx = base.driver.parent.init.startup.s.rx.rx
    fifo = folder / "stream.fifo"
    os.mkfifo(fifo)
    keepalive = os.open(fifo, os.O_RDWR)
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
        explicit_failure_grace_seconds=5,
    )
    process_record = folder / "native-process.json"
    process = None

    def close_keepalive():
        nonlocal keepalive
        if keepalive is not None:
            os.close(keepalive)
            keepalive = None

    try:
        with (
            log.open("x") as stdout,
            concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool,
        ):
            process = subprocess.Popen(
                command,
                cwd=folder,
                env=env,
                stdout=stdout,
                stderr=subprocess.STDOUT,
                preexec_fn=rx.resource_limit,
                start_new_session=True,
            )
            lifecycle.update(
                status="RUNNING", pid=process.pid, process_group=process.pid
            )
            atomic(process_record, lifecycle)

            def reader():
                try:
                    with fifo.open("rb") as stream:
                        return consume(stream)
                except BaseException as error:
                    lifecycle["capture_error"] = repr(error)
                    stop_failed_group(process)
                    raise

            future = pool.submit(reader)
            try:
                returncode = process.wait()  # No healthy elapsed watchdog.
                close_keepalive()
                captured = future.result()
                require(returncode == 0, "Actual native nonzero exit")
            except BaseException as error:
                lifecycle["error"] = repr(error)
                stop_failed_group(process)
                close_keepalive()
                raise
            finally:
                lifecycle.update(
                    status="EXITED",
                    returncode=process.poll(),
                    elapsed_seconds=time.monotonic() - start,
                )
                atomic(process_record, lifecycle)
    finally:
        close_keepalive()
        if process is not None and process.poll() is None:
            stop_failed_group(process)
    fifo.unlink()
    return captured, dict(
        command=command,
        returncode=returncode,
        elapsed_seconds=time.monotonic() - start,
        address_space_limit_bytes=rx.MEMORY_LIMIT,
        cpu_affinity_count=1,
        elapsed_watchdog_seconds=None,
        explicit_failure_grace_seconds=5,
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
                lambda f: capture_stream(
                    f, folder / "capture", expected, hbts, case, f"{prefix}-s{index}"
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
