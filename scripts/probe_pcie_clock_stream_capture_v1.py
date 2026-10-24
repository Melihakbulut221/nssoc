#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Tiny native FIFO capture controls only; never launches the proposed1us VCO."""

import argparse
import concurrent.futures
import hashlib
import json
import lzma
import math
import os
from pathlib import Path
import re
import struct
import sys

import characterize_pcie_clock_trim_thermal_v1 as base

require = base.require
THERMAL_SHA = "663d50d2f7efd2f611792d305ce03813f8c1d0ca1f21fd0d52866adb801aa324"
RESULT_SHA = "04a1a8aea7c498633baaaaf34606df794a306dee3ee59525959e97e75bf6e1c8"
STOP = 1e-9
STEP = 0.5e-12
CHUNK_ROWS = 256


def parse_header(stream, expected):
    raw = bytearray()
    while True:
        line = stream.readline(4097)
        require(
            bool(line) and len(line) <= 4096 and len(raw) < 65536,
            "Bounded complete native raw header",
        )
        raw.extend(line)
        if line == b"Binary:\n":
            break
    text = raw.decode("ascii")
    lines = text.splitlines()

    def field(name):
        vals = [x[len(name) + 1 :].strip() for x in lines if x.startswith(name + ":")]
        require(len(vals) == 1, "Unique raw header field " + name)
        return vals[0]

    require(
        field("Flags") == "real" and field("Plotname") == "Transient Analysis",
        "Exact real transient raw format",
    )
    size = int(field("No. Variables"))
    points = int(field("No. Points"))
    require(size == len(expected) + 1 and points >= 0, "Exact native column census")
    index = lines.index("Variables:")
    table = [x.split() for x in lines[index + 1 : -1]]
    require(
        len(table) == size and all(len(x) == 3 for x in table),
        "Complete native variable table",
    )
    require(
        [int(x[0]) for x in table] == list(range(size))
        and table[0][1:] == ["time", "time"],
        "Unique ordered variable IDs",
    )
    aliases = {n: n for n in expected}
    for n in expected:
        if n.startswith("@"):
            for wrapper in ("v", "i"):
                aliases[f"{wrapper}({n})"] = n
    mapping = []
    for _, name, units in table[1:]:
        require(
            name in aliases and units in ("voltage", "current", "capacitance"),
            "Known native vector alias/units",
        )
        mapping.append(aliases[name])
    require(
        len(set(mapping)) == len(expected) and set(mapping) == set(expected),
        "Exact source-vector bijection",
    )
    return bytes(raw), dict(
        declared_points=points, columns=["time", *mapping], raw_table=table
    )


def capture(stream, output, expected, fifo, stop=STOP, step=STEP, supply=2.415):
    require(sys.byteorder == "little", "Pinned x86 little-endian raw format")
    output = Path(output)
    output.mkdir()
    header, meta = parse_header(stream, expected)
    (output / "header.bin").write_bytes(header)
    names = meta["columns"]
    frame = struct.Struct("<" + "d" * len(names))
    width = frame.size
    rail = names.index("v(avdd)")
    time_index = 0
    raw_hash = hashlib.sha256(header)
    payload_hash = hashlib.sha256()
    limits = {n: [math.inf, -math.inf] for n in names}
    chunks = []
    pending = bytearray()
    block = bytearray()
    rows = 0
    previous = None
    max_step = 0.0
    first_fault = None

    def save_chunk():
        if not block:
            return
        data = bytes(block)
        path = output / f"chunk-{len(chunks):04d}.bin.xz"
        packed = lzma.compress(data, preset=1)
        path.write_bytes(packed)
        chunks.append(
            dict(
                index=len(chunks),
                rows=len(data) // width,
                first_row=rows - len(data) // width,
                uncompressed_bytes=len(data),
                uncompressed_sha256=hashlib.sha256(data).hexdigest(),
                path=path.name,
                bytes=len(packed),
                sha256=hashlib.sha256(packed).hexdigest(),
            )
        )
        block.clear()

    while data := stream.read(65536):
        raw_hash.update(data)
        pending.extend(data)
        count = len(pending) // width
        for i in range(count):
            sample = bytes(pending[i * width : (i + 1) * width])
            values = frame.unpack(sample)
            t = values[time_index]
            require(all(map(math.isfinite, values)), "Finite native sample")
            if previous is None:
                require(t == 0.0, "Time0 required")
            else:
                require(0 < t - previous <= step * 1.0001, "Continuous native timestep")
                max_step = max(max_step, t - previous)
            require(t <= stop + 1e-18, "No unexpected trailing sample")
            previous = t
            rows += 1
            for n, v in zip(names, values):
                limits[n] = [min(limits[n][0], v), max(limits[n][1], v)]
            if (
                t >= 0.5e-9
                and abs(values[rail] - supply) > 1e-6
                and first_fault is None
            ):
                first_fault = t
            payload_hash.update(sample)
            block.extend(sample)
            if len(block) == CHUNK_ROWS * width:
                save_chunk()
        del pending[: count * width]
    save_chunk()
    trailer = bytes(pending)
    (output / "trailer.bin").write_bytes(trailer)
    # Exact observed ng47 nonseekable-file behavior: count rewrite lands at EOF.
    require(
        trailer == (str(rows).encode() if fifo else b""), "Exact native count trailer"
    )
    require(
        meta["declared_points"] == (0 if fifo else rows), "Declared native point count"
    )
    require(
        rows >= 1000 and previous is not None and stop <= previous <= stop + 1e-18,
        "Full bounded native completion",
    )
    result = dict(
        **meta,
        rows=rows,
        first_time_s=0.0,
        last_time_s=previous,
        max_step_s=max_step,
        all_column_ranges=limits,
        raw_sha256=raw_hash.hexdigest(),
        payload_sha256=payload_hash.hexdigest(),
        header_sha256=hashlib.sha256(header).hexdigest(),
        trailer_sha256=hashlib.sha256(trailer).hexdigest(),
        chunks=chunks,
        late_rail_fault_detected=first_fault is not None,
        first_rail_fault_s=first_fault,
        native_fifo=fifo,
        chunk_rows=CHUNK_ROWS,
        max_uncompressed_chunk_bytes=width * CHUNK_ROWS,
        read_block_bytes=65536,
    )
    (output / "capture.json").write_text(json.dumps(result, indent=2) + "\n")
    return result


def replay_chunks(root, captured):
    root = Path(root)
    total = hashlib.sha256()
    count = 0
    for i, row in enumerate(captured["chunks"]):
        require(
            row["index"] == i and row["first_row"] == count,
            "Exact ordered chunk coverage",
        )
        raw = (root / row["path"]).read_bytes()
        require(
            hashlib.sha256(raw).hexdigest() == row["sha256"], "Captured chunk changed"
        )
        data = lzma.decompress(raw)
        require(
            len(data)
            == row["uncompressed_bytes"]
            == row["rows"] * 8 * len(captured["columns"])
            and hashlib.sha256(data).hexdigest() == row["uncompressed_sha256"],
            "Exact chunk data",
        )
        total.update(data)
        count += row["rows"]
    require(
        count == captured["rows"] and total.hexdigest() == captured["payload_sha256"],
        "Complete native payload reconstruction",
    )


def deck(parent_deck, target, fault):
    require(target in ("reference.raw", "stream.fifo"), "Owned fixed output path")
    text = parent_deck
    old = "tran 5e-13 40n 0 5e-13"
    require(
        text.count(old) == 1 and text.count(".control") == 1, "Exact original transient"
    )
    text = text.replace(".control", ".tran 5e-13 1n 0 5e-13\n.control", 1)
    text = text.replace(old, f"run {target}\nsetplot\ndisplay\nrusage space")
    lines = text.splitlines()
    waves = [line for line in lines if line.startswith("wrdata wave.dat ")]
    require(len(waves) == 1, "One original waveform writer")
    text = text.replace(waves[0] + "\n", "")
    if fault:
        source = "VDD avdd 0 PWL(0 0 5e-10 2.415)"
        require(text.count(source) == 1, "Exact original rail")
        text = text.replace(
            source, "VDD avdd 0 PWL(0 0 5e-10 2.415 7.5e-10 2.415 7.51e-10 0)"
        )
    require(
        text.count("alter @q.xosc.") == 30
        and not re.search(r"(?im)^\s*(reset|resume)\b|\buic\b|^\s*\.ic\b", text),
        "One continuous unchanged native startup",
    )
    return text


def native_log(log, captured, hbts):
    require(base.old.diagnostics(log)["clean"], "Clean native execution required")
    flags = base.driver.flags(log, hbts)
    require(
        [int(n) for n in re.findall(r"No\. of Data Rows\s*:\s*(\d+)", log)]
        == [1, captured["rows"]],
        "OP/native-stream row counts",
    )
    require(
        re.search(r"(?m)^Current op1\s", log)
        and not re.search(r"(?m)^\s*(?:Current )?tran\d+\b", log),
        "No retained transient plot",
    )
    displayed = re.findall(r"(?m)^\s+(\S+)\s*:\s+\S+, real, (\d+) long", log)
    expected_names = []
    for name in captured["columns"][1:]:
        expected_names.append(
            name[2:-1]
            if name.startswith("v(")
            else name[2:-1] + "#branch"
            if name.startswith("i(")
            else name
        )
    require(
        len(displayed) == len(expected_names)
        and set(name for name, _ in displayed) == set(expected_names)
        and {length for _, length in displayed} == {"1"},
        "Only exact1-point OP vectors retained",
    )
    peak = re.findall(r"Maximum ngspice program size =\s*([0-9.]+) MB", log)
    require(len(peak) == 1 and float(peak[0]) < 128, "Bounded tiny native program size")
    return dict(
        flags=flags,
        native_peak_mb=float(peak[0]),
        retained_plot="op1_only",
        retained_vector_length=1,
    )


def run(parent, output):
    parent, output = Path(parent).resolve(), Path(output).resolve()
    require(
        base.old.sha(Path(base.__file__)) == THERMAL_SHA
        and base.old.sha(parent / "result.json") == RESULT_SHA,
        "Exact frozen parent",
    )
    require(
        not output.exists() and output.is_relative_to(Path("/dev/shm")),
        "Fresh RAM output",
    )
    prior = json.loads((parent / "result.json").read_text())
    pins = prior["source_sha256"].copy()
    pins[str(parent / "result.json")] = RESULT_SHA
    pins[str(Path(__file__).resolve())] = base.old.sha(Path(__file__))
    require(
        all(base.old.sha(Path(p)) == h for p, h in pins.items()),
        "Original sources/runtime/models unchanged",
    )
    row = prior["cases"][0]
    folder = parent / row["case"]["name"]
    olddeck = (folder / "bench.cir").read_text()
    circuit = (folder / base.prior.FILE).read_text()
    require(
        base.old.sha(folder / "bench.cir") == row["outputs"]["bench.cir"]
        and base.old.sha(folder / base.prior.FILE) == base.PRIOR_CIRCUIT_SHA,
        "Exact native circuit/deck",
    )
    pins[str(folder / "bench.cir")] = base.old.sha(folder / "bench.cir")
    pins[str(folder / base.prior.FILE)] = base.PRIOR_CIRCUIT_SHA
    hbts = base.driver.contract(circuit, 4)
    expected = base.prior.vectors(hbts)
    runtime = next(Path(p) for p in pins if Path(p).name == "ngspice")
    output.mkdir()
    (output / "producer.py").write_bytes(Path(__file__).read_bytes())
    (output / "spinit").write_text(base.driver.parent.init.SPINIT)
    record = dict(
        status="RUNNING",
        source_sha256=pins,
        cases=[],
        scope="One-nanosecond capture-backend continuity and latefault controls, not oscillator/thermal/PCIe acceptance.",
    )
    save = lambda: base.driver.atomic_record(output / "result.json", record)
    prev = os.environ.get("SPICE_SCRIPTS")
    os.environ["SPICE_SCRIPTS"] = str(output)
    save()
    try:
        for fault in (False, True):
            for fifo in (False, True):
                label = ("latefault" if fault else "normal") + (
                    "_fifo" if fifo else "_file"
                )
                d = output / label
                d.mkdir()
                (d / base.prior.FILE).write_text(circuit)
                (d / "bench.cir").write_text(
                    deck(olddeck, "stream.fifo" if fifo else "reference.raw", fault)
                )
                item = dict(name=label, latefault=fault, fifo=fifo)
                record["cases"].append(item)
                save()
                command = [str(runtime), "-n", "-b", "bench.cir"]
                if fifo:
                    pipe = d / "stream.fifo"
                    os.mkfifo(pipe)
                    keepalive = os.open(pipe, os.O_RDWR)
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:

                        def consume():
                            with pipe.open("rb") as f:
                                return capture(f, d / "chunks", expected, True)

                        future = pool.submit(consume)
                        try:
                            item["execution"] = (
                                base.driver.parent.init.startup.s.rx.execute(
                                    command, d, d / "run.log"
                                )
                            )
                        finally:
                            os.close(keepalive)
                        item["capture"] = future.result(timeout=5)
                    pipe.unlink()
                else:
                    item["execution"] = base.driver.parent.init.startup.s.rx.execute(
                        command, d, d / "run.log"
                    )
                    with (d / "reference.raw").open("rb") as f:
                        item["capture"] = capture(f, d / "chunks", expected, False)
                item["native"] = native_log(
                    (d / "run.log").read_text(), item["capture"], hbts
                )
                item["initial_op"] = base.driver.parent.init.startup.initial_op(
                    d / "initial-op.dat", expected
                )
                require(
                    max(map(abs, item["initial_op"].values())) <= 1e-10,
                    "Exact zero initial OP",
                )
                require(
                    item["capture"]["late_rail_fault_detected"] == fault,
                    "Actual latefault detection",
                )
                if fault:
                    require(
                        0.75e-9 < item["capture"]["first_rail_fault_s"] < 0.752e-9,
                        "Real latefault timing",
                    )
                replay_chunks(d / "chunks", item["capture"])
                item["reconstructed"] = True
                item["outputs"] = {
                    str(p.relative_to(d)): base.old.sha(p)
                    for p in d.rglob("*")
                    if p.is_file()
                }
                save()
        for i in (0, 2):
            a, b = record["cases"][i : i + 2]
            require(
                a["capture"]["payload_sha256"] == b["capture"]["payload_sha256"]
                and a["capture"]["rows"] == b["capture"]["rows"]
                and a["capture"]["raw_table"] == b["capture"]["raw_table"],
                "Byte-identical continuous native file/FIFO trajectory",
            )
            require(a["initial_op"] == b["initial_op"], "Same original OP")
        require(
            all(base.old.sha(Path(p)) == h for p, h in pins.items()),
            "Inputs changed during probe",
        )
        record.update(
            status="PASS_TINY_NATIVE_STREAMING_CAPTURE",
            full_1us_oscillator_executed=False,
            source_bytes_unchanged=True,
        )
        save()
    except BaseException as e:
        record.update(status="ERROR", error=repr(e))
        save()
        raise
    finally:
        if prev is None:
            os.environ.pop("SPICE_SCRIPTS", None)
        else:
            os.environ["SPICE_SCRIPTS"] = prev
    return record


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("parent", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    a = p.parse_args()
    return int(run(a.parent, a.out)["status"] != "PASS_TINY_NATIVE_STREAMING_CAPTURE")


if __name__ == "__main__":
    raise SystemExit(main())
