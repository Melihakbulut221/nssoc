#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""One explicit predeclared powered62-device diagnostic, retaining actual wire RC.

No elapsed-time cancellation. Explicit external ideal BODY_SUBSTRATE/WIRE_CREF
sources are testbench assumptions, not physical substrate attachment or full PEX.
All62 intrinsic devices remain present; actual native VCO generates its output clock.
"""

import argparse
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import re
import resource
import signal
import subprocess
import threading
import time
import zlib

import build_pcie_local_vco_hybrid_v6 as h

INPUT_PINS = {
    "hybrid": "ba97b052bf8a33fd3cac1124421ac27ee708cde308e4a77e7860ac70a1c28d02",
    "composition": "c1d53928e86ae8b3b860306a54e810c22eb1798cb7e22c36a717dd29e411353b",
    "anchors": "c941e16a3dac449a8a6594bf4fabc475cc45fff4ab21d9132659002b929ee9ad",
    "source_binding": "7db2a9e4dbae77facc6e1e7cf827a0c554b8f71fa23362f4ff09903e354769a3",
    "rc_review": "b66e7867d83f4fd7384b7f581fba257efd6f802766d456f9b96285e61140a830",
}
METHOD_SHA = "ab2962f0c47cc89029866761992bfdd87ab1d5649920b8bc8edaa1c54bbe5a3f"
NG_SHA = "eaca52dad06845779fed4f50420a6a0cf4a32776e6a572432275f350002b87b8"
STOP = 12e-9
STEP = 1e-12
BEGIN = 6e-9
OWN_LIMIT = 80 * 1024**2
SHARED_RESERVE = 512 * 1024**2
RECEIPT_RESERVE = 2 * 1024**2
LAUNCH_HEADROOM = 24 * 1024**2
STREAM_CHUNK = 1024**2
# All newly owned wire/precision/hybrid scratch, excluding symlink targets and
# immutable shared source GDS/PDK/native tools. Explicit historical roots count.
OWN_ROOTS = [
    "/dev/shm/nssoc-magic-cap-precision-v3-build",
    "/dev/shm/nssoc-bank-wire-cap-precision-v3-01",
    "/dev/shm/nssoc-bank-wire-rc-actual-v1-01",
    "/dev/shm/nssoc-bank-wire-rc-v1-01",
    "/dev/shm/nssoc-bank-wire-rc-v1-02",
    "/dev/shm/nssoc-bank-wire-rc-geometry-v1",
    "/dev/shm/nssoc-bank-wire-port-loss-v1",
    "/dev/shm/nssoc-cap-precision-v3-regressions",
    "/dev/shm/nssoc-cap-precision-v3-regressions-recorded",
    "/dev/shm/nssoc-cap-precision-v3-mutants",
    "/dev/shm/nssoc-bank-hybrid-v1-01",
    "/dev/shm/nssoc-bank-wire-transfer-v1-01",
    "/dev/shm/nssoc-bank-wire-transfer-v1-02",
    "/dev/shm/nssoc-bank-wire-transfer-v1-final",
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def physical_to_ideal(composition, anchors):
    public = {
        a["wire_component"]: a["detail"]["name"]
        for a in anchors["anchors"]
        if a["kind"] == "PUBLIC_PORT_REFERENCE"
    }
    mapping = {}
    for a in anchors["anchors"]:
        if a["kind"] != "INTRINSIC_DEVICE_TERMINAL_REFERENCE":
            continue
        native = "w_" + a["label"]
        component = a["wire_component"]
        mapping[native] = public.get(component, f"ideal_c{component:03d}")
    h.require(len(mapping) == 145, "Ideal reference terminal census")
    nodes = {
        n for d in composition["records"] for n in [t["node"] for t in d["terminals"]]
    }
    h.require(
        nodes - set(mapping) == {"BODY_SUBSTRATE", "body_well_2"},
        "Unexpected nonmetal reference",
    )
    return mapping


def circuit(composition, hybrid_text, mapping, mode):
    h.require(
        mode in ("intrinsic_only", "distributed_wire"), "Unsupported comparison mode"
    )
    if mode == "distributed_wire":
        return hybrid_text
    lines = [
        "* Deliberate ideal-wire reference; NO physical RC acceptance.",
        ".subckt nssoc_vco_local_hybrid_open_v2 " + " ".join(composition["ports"]),
    ]
    for d in composition["records"]:
        tokens = d["line"].split()
        count = len(d["terminals"])
        tokens[1 : 1 + count] = [mapping.get(n, n) for n in tokens[1 : 1 + count]]
        lines.append(" ".join(tokens))
    lines += [".ends nssoc_vco_local_hybrid_open_v2", ""]
    h.require(len(lines) == 66, "Ideal reference dropped intrinsic device")
    return "\n".join(lines)


def node_expression(node, ports, mapping, mode):
    if mode == "intrinsic_only":
        node = mapping.get(node, node)
    return "v(" + (node if node in ports else "xbank." + node) + ")"


def vector_contract(comp, mapping, mode, binding):
    ports = comp["ports"]
    hbts = []
    extras = set()
    ids = {r["source_name"]: r["native_id"] for r in binding["devices"]}
    by = {r["native_id"]: r for r in comp["records"]}

    def expr(node):
        return node_expression(node, ports, mapping, mode)

    def terminal(name, term):
        matches = [
            t["node"] for t in by[ids[name]]["terminals"] if t["terminal"] == term
        ]
        h.require(len(matches) == 1, "Exact source terminal missing")
        return expr(matches[0])

    for d in comp["records"]:
        terms = {r["terminal"]: r["node"] for r in d["terminals"]}
        if d["model"] == "npn13G2":
            row = dict(
                id=d["native_id"],
                Nx=int(d["native_parameters"]["Nx"]),
                current=f"@q.xbank.xd{d['native_id']:04d}.qnpn13g2[ic]",
            )
            row.update({n: expr(terms[n]) for n in ("C", "B", "E")})
            hbts.append(row)
            extras.add(f"v(xbank.xd{d['native_id']:04d}.t)")
        elif d["model"] == "rppd":
            extras.add(f"v(xbank.xd{d['native_id']:04d}.dt)")
        elif d["model"] == "sg13_hv_pmos":
            extras.add(f"@n.xbank.xd{d['native_id']:04d}.nsg13_hv_pmos[ids]")
            extras.update(expr(n) for n in terms.values())
    pairs = [["v(CLKP)", "v(CLKN)"], [terminal("FP", "E"), terminal("FN", "E")]]
    pairs += [[terminal(f"P{i}", "C"), terminal(f"N{i}", "C")] for i in range(3)]
    vectors = sorted(
        {v for d in hbts for v in (d["C"], d["B"], d["E"], d["current"])}
        | {v for p in pairs for v in p}
        | {f"v({p})" for p in ports}
        | extras
        | {"i(vs_avdd)", "i(vs_vctrl)"}
    )
    h.require(len(hbts) == 30, "All30 native HBT bounds required")
    return dict(
        vectors=vectors,
        hbts=hbts,
        clock_inputs=[],
        clock_drivers=pairs,
        sampler_outputs=[],
        signal_names=[
            "public_clock",
            "native_output_emitters",
            "ring0",
            "ring1",
            "ring2",
        ],
    )


def deck(comp, contract, models, osdis, vctrl=0.85):
    h.require(vctrl in (0.4, 0.6, 0.85), "Predeclared VCTRL point required")
    lines = [
        "Local-routed62-device VCOv4 powered diagnostic; explicit ideal external body and wire references"
    ]
    lines += [
        f'.lib "{models}/corner{k}.lib" {c}'
        for k, c in [
            ("HBT", "hbt_typ"),
            ("RES", "res_typ"),
            ("MOShv", "mos_tt"),
            ("CAP", "cap_typ"),
        ]
    ]
    lines += ['.include "bank.spice"', ".temp 27", ".options reltol=1e-4 abstol=1e-12"]
    rails = dict(AVDD=2.3, VCTRL=vctrl, AVSS=0, SUB=0, BODY_SUBSTRATE=0, WIRE_CREF=0)
    for name, value in rails.items():
        lines.append(f"Vs_{name.lower()} {name} 0 PWL(0 0 500p {value})")
    for name in ("CLKP", "CLKN"):
        lines.append(f"CLOAD_{name} {name} 0 50f")
    h.require(
        set(rails) | {"CLKP", "CLKN"} == set(comp["ports"]), "External contract differs"
    )
    lines += [
        "XBANK " + " ".join(comp["ports"]) + " nssoc_vco_local_hybrid_open_v2",
        ".control",
    ]
    lines += ["pre_osdi " + str(p) for p in osdis]
    for d in contract["hbts"]:
        name = f"q.xbank.xd{d['id']:04d}.qnpn13g2"
        lines += [
            f"alter @{name}[off]=1",
            f"echo NSSOC_FLAG_BEGIN {name}",
            f"show {name} : off",
            "echo NSSOC_FLAG_END",
        ]
    vectors = contract["vectors"]
    lines += ["set wr_singlescale", "set wr_vecnames", "set numdgt=16"]
    lines += [
        "save " + " ".join(vectors[i : i + 40]) for i in range(0, len(vectors), 40)
    ]
    lines += [
        "op",
        "wrdata initial-op.dat " + " ".join(vectors),
        f"tran {STEP:.14g} {STOP:.14g} 0 {STEP:.14g}",
        "wrdata wave.fifo " + " ".join(vectors),
        "echo NSSOC_POWERED_VCO_COMPLETE",
        "quit",
        ".endc",
        ".end",
        "",
    ]
    return "\n".join(lines)


def limits():
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3,) * 2)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))


def regular_size(root):
    return (
        sum(
            p.stat().st_size
            for p in root.rglob("*")
            if p.is_file() and not p.is_symlink()
        )
        if root.exists()
        else 0
    )


def owned_size(out):
    roots = set(map(Path, OWN_ROOTS)) | {out}
    for pattern in (
        "nssoc-vco-v4-*",
        "nssoc-power-overlay-*",
        "nssoc-magic-area-product-v4-*",
        "nssoc-area-v4-*",
    ):
        roots.update(Path("/dev/shm").glob(pattern))
    roots = {
        p
        for p in roots
        if p.is_dir() and not any(p != q and p.is_relative_to(q) for q in roots)
    }
    return sum(regular_size(p) for p in roots)


def shared_free():
    stat = os.statvfs("/dev/shm")
    return stat.f_bavail * stat.f_frsize


def stream_wave(fifo, compressed, record, out):
    """Budget actual gzip bytes before every write, including post-exit flush."""
    digest = hashlib.sha256()
    raw_bytes = 0
    compressor = zlib.compressobj(level=6, wbits=31)  # Standard gzip, not custom codec.
    record.update(
        chunk_raw_limit=STREAM_CHUNK,
        receipt_reserve_bytes=RECEIPT_RESERVE,
        peak_owned_bytes=0,
        min_shared_free_bytes=shared_free(),
    )

    def write_bounded(dst, payload):
        size, free = owned_size(out), shared_free()
        if size + len(payload) + RECEIPT_RESERVE > OWN_LIMIT:
            record["resource_stop"] = "OWN_80MIB_FINAL_DRAIN_RESERVE"
        elif free - len(payload) < SHARED_RESERVE:
            record["resource_stop"] = "SHARED_512MIB_FINAL_DRAIN_RESERVE"
        if record.get("resource_stop"):
            raise ValueError(record["resource_stop"])
        if payload:
            dst.write(payload)
        size, free = owned_size(out), shared_free()
        record["peak_owned_bytes"] = max(record["peak_owned_bytes"], size)
        record["min_shared_free_bytes"] = min(record["min_shared_free_bytes"], free)
        if size + RECEIPT_RESERVE > OWN_LIMIT or free < SHARED_RESERVE:
            record["resource_stop"] = "RESOURCE_CHANGED_DURING_CAPTURE_WRITE"
            raise ValueError(record["resource_stop"])

    try:
        # Buffered read deliberately waits for a whole bounded chunk or EOF.
        # The final short chunk may arrive after native exit; it uses the same
        # budget checks, and the keeper is closed before waiting for EOF.
        with fifo.open("rb") as src, compressed.open("wb", buffering=0) as dst:
            while chunk := src.read(STREAM_CHUNK):
                digest.update(chunk)
                raw_bytes += len(chunk)
                write_bounded(dst, compressor.compress(chunk))
                record.update(raw_bytes=raw_bytes)
            write_bounded(dst, compressor.flush(zlib.Z_FINISH))
        record.update(
            complete=True, raw_sha256=digest.hexdigest(), compressed=h.pin(compressed)
        )
    except Exception as error:
        record["error"] = repr(error)


def wave_measure(path, contract):
    columns = ["time", *contract["vectors"]]
    index = {n: i for i, n in enumerate(columns)}
    peak = [
        [math.inf, -math.inf]
        for _ in contract["clock_inputs"]
        + contract["clock_drivers"]
        + contract["sampler_outputs"]
    ]
    pairs = (
        contract["clock_inputs"]
        + contract["clock_drivers"]
        + contract["sampler_outputs"]
    )
    crossings = [[] for _ in pairs]
    bjt_bounds = {
        d["id"]: dict(
            min_vce=math.inf, max_vce=-math.inf, peak_abs_current_per_emitter_a=0.0
        )
        for d in contract["hbts"]
    }
    full_max_vce = -math.inf
    full_min_vce = math.inf
    previous = None
    samples = 0
    active = 0
    first = None
    last = None
    max_gap = 0
    with gzip.open(path, "rt") as file:
        h.require(
            file.readline().split() == columns, "Wave vector order/identity differs"
        )
        for line in file:
            row = [float(v) for v in line.split()]
            h.require(
                len(row) == len(columns) and all(math.isfinite(v) for v in row),
                "Nonfinite/incomplete waveform",
            )
            t = row[0]
            samples += 1
            first = t if first is None else first
            if previous is not None:
                h.require(t > last, "Wave time order")
                max_gap = max(max_gap, t - last)
                h.require(
                    t - last <= STEP * (1 + 1e-8), "Native timestep gap exceeds recipe"
                )
            for d in contract["hbts"]:
                v = row[index[d["C"]]] - row[index[d["E"]]]
                full_max_vce = max(full_max_vce, v)
                full_min_vce = min(full_min_vce, v)
            if t >= BEGIN:
                active += 1
                for j, (a, b) in enumerate(pairs):
                    value = row[index[a]] - row[index[b]]
                    peak[j][0] = min(peak[j][0], value)
                    peak[j][1] = max(peak[j][1], value)
                    if previous is not None and last >= BEGIN:
                        old = previous[index[a]] - previous[index[b]]
                        if old <= 0 < value:
                            crossings[j].append(
                                last + (t - last) * (-old) / (value - old)
                            )
                for d in contract["hbts"]:
                    vce = row[index[d["C"]]] - row[index[d["E"]]]
                    bound = bjt_bounds[d["id"]]
                    bound["min_vce"] = min(bound["min_vce"], vce)
                    bound["max_vce"] = max(bound["max_vce"], vce)
                    bound["peak_abs_current_per_emitter_a"] = max(
                        bound["peak_abs_current_per_emitter_a"],
                        abs(row[index[d["current"]]]) / d["Nx"],
                    )
            previous, last = row, t
    h.require(
        first is not None
        and first <= 1e-12
        and last >= STOP * (1 - 1e-8)
        and active > 900,
        "Incomplete waveform time coverage",
    )
    signals = []
    for pair, extrema, edges in zip(pairs, peak, crossings):
        periods = [b - a for a, b in zip(edges, edges[1:])]
        signals.append(
            dict(
                vectors=pair,
                minimum_differential_v=extrema[0],
                maximum_differential_v=extrema[1],
                rising_edges=len(edges),
                mean_frequency_hz=len(periods) / sum(periods) if periods else None,
                rising_edge_times=edges,
            )
        )
    return dict(
        samples=samples,
        active_samples=active,
        time_start=first,
        time_end=last,
        max_time_gap=max_gap,
        operating_window_start_s=BEGIN,
        signals=signals,
        hbt_bounds=bjt_bounds,
        min_vce=min(b["min_vce"] for b in bjt_bounds.values()),
        max_vce=max(b["max_vce"] for b in bjt_bounds.values()),
        peak_abs_current_per_emitter_a=max(
            b["peak_abs_current_per_emitter_a"] for b in bjt_bounds.values()
        ),
        screen_bounds=dict(
            min_vce=0.4, max_vce=1.6, max_collector_current_per_emitter_a=0.003
        ),
        full_time_min_vce=full_min_vce,
        full_time_max_vce=full_max_vce,
        scope="Finite12ns diagnostic with6ns post-startup bounds; no synchronous-bit/BER/CDR or full-PVT acceptance",
    )


def audit_native(root, contract):
    log = (root / "native.log").read_text()
    h.require(log.count("NSSOC_POWERED_VCO_COMPLETE") == 1, "Missing native completion")
    sections = re.findall(r"NSSOC_FLAG_BEGIN (\S+)\n(.*?)NSSOC_FLAG_END", log, re.S)
    expected = [f"q.xbank.xd{d['id']:04d}.qnpn13g2" for d in contract["hbts"]]
    h.require([n for n, _ in sections] == expected, "Native OFF flag census")
    for name, block in sections:
        h.require(
            re.findall(r"^\s*off\s+(\S+)\s*$", block, re.M) == ["1"],
            "Native OFF flag value",
        )
        h.require(
            re.findall(r"^\s*device\s+(\S+)\s*$", block, re.M) == [name[:21]],
            "Native OFF device identity",
        )
    initial = (root / "initial-op.dat").read_text().splitlines()
    h.require(
        len(initial) == 2 and initial[0].split()[1:] == contract["vectors"],
        "Initial OP vector coverage",
    )
    values = [float(v) for v in initial[1].split()]
    h.require(
        len(values) == len(contract["vectors"]) + 1
        and all(math.isfinite(v) and abs(v) < 1e-10 for v in values),
        "Initial zero OP failed",
    )
    diagnostics = [
        line
        for line in log.splitlines()
        if re.search(
            r"warning|error|failed|singular|timestep too small|nan", line, re.I
        )
    ]
    return dict(
        initial_op_max_abs=max(map(abs, values)),
        native_off_flags=len(expected),
        numerical_diagnostics=diagnostics,
        numerical_clean=not diagnostics,
        metrics=wave_measure(root / "wave.dat.gz", contract),
    )


def stop_owned(proc):
    """Only owned resource/error/cancel cleanup; never elapsed cancellation."""
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        proc.wait()
        return
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        proc.poll()  # Reap the group leader promptly, also when it ignores TERM.
        try:
            os.killpg(proc.pid, 0)
        except ProcessLookupError:
            proc.wait()
            return
        time.sleep(0.05)
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait()


def run_native(root, ngspice, out, save, row):
    fifo = root / "wave.fifo"
    os.mkfifo(fifo)
    # Parent keeper prevents a reader-open deadlock when a native process aborts
    # before wrdata. It is noninheritable; close after all owned writers stop.
    keeper = os.open(fifo, os.O_RDWR | os.O_NONBLOCK)
    stream = row["stream"]
    stream.setdefault("raw_bytes", 0)
    proc = None
    reader = threading.Thread(
        target=stream_wave, args=(fifo, root / "wave.dat.gz", stream, out), daemon=True
    )
    reader.start()
    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("GH_TOKEN", "GITHUB_TOKEN", "PYTHONPATH", "PYTHONHOME")
    }
    env["SPICE_SCRIPTS"] = str(root.resolve())
    env["OMP_NUM_THREADS"] = "1"
    start = time.monotonic()
    reason = None
    try:
        with (root / "native.log").open("w") as log:
            proc = subprocess.Popen(
                [str(ngspice.resolve()), "-n", "-b", "bench.cir"],
                cwd=root,
                env=env,
                preexec_fn=limits,
                stdout=log,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            row["pid"] = proc.pid
            save()
            while proc.poll() is None:
                free = shared_free()
                size = owned_size(out)
                row["resources"].append(
                    dict(
                        elapsed_s=time.monotonic() - start,
                        shared_free=free,
                        own_scratch=size,
                        stream_raw_bytes=stream.get("raw_bytes", 0),
                    )
                )
                if free < SHARED_RESERVE:
                    reason = "SHARED_512MIB_RESERVE"
                elif size + RECEIPT_RESERVE > OWN_LIMIT:
                    reason = "OWN_80MIB_SCRATCH_LIMIT"
                elif stream.get("error"):
                    reason = "WAVE_CAPTURE_ERROR"
                if reason:
                    break
                save()
                time.sleep(2)
    finally:
        if proc is not None:
            stop_owned(proc)
        os.close(keeper)
        # Native writer is reaped and keeper closed, so EOF drains the reader.
        # Owned native process group is reaped; close the keeper and finish
        # the bounded final compression instead of abandoning healthy drain.
        reader.join()
        if reader.is_alive():
            row["collector_failure"] = "WAVE_COLLECTOR_DID_NOT_DRAIN"
        fifo.unlink()
        final_size, final_free = owned_size(out), shared_free()
        row["post_drain_resources"] = dict(
            owned_bytes=final_size,
            shared_free_bytes=final_free,
            receipt_reserve_bytes=RECEIPT_RESERVE,
        )
        if stream.get("resource_stop"):
            reason = stream["resource_stop"]
        elif final_size + RECEIPT_RESERVE > OWN_LIMIT:
            reason = "OWN_80MIB_POST_DRAIN_RESERVE"
        elif final_free < SHARED_RESERVE:
            reason = "SHARED_512MIB_POST_DRAIN_RESERVE"
        row.update(
            returncode=proc.returncode if proc else None,
            elapsed_seconds=time.monotonic() - start,
            resource_stop=reason,
        )
    h.require(not reader.is_alive(), "Wave collector failed to drain after native reap")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    for key in [*INPUT_PINS, "model_receipt", "ngspice", "pdk", "osdi_root", "out"]:
        ap.add_argument("--" + key.replace("_", "-"), type=Path, required=True)
    ap.add_argument(
        "--mode", choices=("intrinsic_only", "distributed_wire"), required=True
    )
    ap.add_argument("--vctrl", type=float, choices=(0.4, 0.6, 0.85), required=True)
    a = ap.parse_args()
    for name, digest in INPUT_PINS.items():
        h.require(
            h.pin(getattr(a, name))["sha256"] == digest,
            "Frozen local " + name + " differs",
        )
    h.require(
        h.pin(Path(h.__file__))["sha256"] == METHOD_SHA
        and h.pin(a.ngspice)["sha256"] == NG_SHA,
        "Builder/runtime source changed",
    )
    rc = json.loads(a.rc_review.read_text())
    h.require(
        rc["status"] == "PASS_WIRE_GRAPH_AND_COLLAPSED_C_ONLY"
        and rc["geometry_probes"] == 151
        and rc["physical_wire_components"] == 20,
        "Native complete compact RC required",
    )
    h.require(
        rc["inputs"][str(a.anchors)] == h.pin(a.anchors), "RC/anchor evidence differs"
    )
    comp = json.loads(a.composition.read_text())
    anchors = json.loads(a.anchors.read_text())
    binding = json.loads(a.source_binding.read_text())
    hybrid = a.hybrid.read_text()
    h.require(
        binding["status"]
        == "PASS_FULL62_DEVICE_SOURCE_LOCATION_AND_NAMED_NET_BIJECTION",
        "Full named source topology required",
    )
    h.require(
        len(comp["records"]) == 62
        and comp["finite_contacts"] == 13
        and comp["body_well_terminals"] == 56,
        "Intrinsic census differs",
    )
    models = a.pdk / "libs.tech/ngspice/models"
    osdis = [a.osdi_root / n for n in ("r3_cmc.osdi", "psp103.osdi", "psp103_nqs.osdi")]
    receipt = json.loads(a.model_receipt.read_text())
    for p in [*models.glob("*.lib"), *osdis]:
        h.require(
            str(p) in receipt["inputs"] and h.pin(p) == receipt["inputs"][str(p)],
            "Original native model/OSDI differs",
        )
    a.out.mkdir(parents=True, exist_ok=False)
    mapping = physical_to_ideal(comp, anchors)
    inputs = {
        str(p): h.pin(p)
        for p in [
            Path(__file__),
            Path(h.__file__),
            *[getattr(a, k) for k in INPUT_PINS],
            a.model_receipt,
            a.ngspice,
            *models.glob("*.lib"),
            *osdis,
        ]
    }
    result = dict(
        status="RUNNING",
        inputs=inputs,
        cases=[],
        full_pex_qualified=False,
        elapsed_cancellation=False,
        controller_resources=dict(
            owned_limit_bytes=OWN_LIMIT,
            shared_reserve_bytes=SHARED_RESERVE,
            receipt_reserve_bytes=RECEIPT_RESERVE,
            preflight_headroom_bytes=LAUNCH_HEADROOM,
            stream_chunk_bytes=STREAM_CHUNK,
            final_drain_checked=True,
        ),
        body_reference_assumption="BODY_SUBSTRATE and WIRE_CREF separately held at ideal0V externally. All56 intrinsic body/well identities and13 finite contacts retained. No inferred body spreading R.",
        intrinsic_devices=62,
        wire_resistors=553,
        wire_capacitors=563,
        assumptions=dict(
            vdd=2.3,
            vctrl=a.vctrl,
            temp_c=27,
            load_each_f=50e-15,
            ramp_s=0.5e-9,
            stop_s=STOP,
            maxstep_s=STEP,
            operating_window_s=[BEGIN, STOP],
            clock="Actual native VCO; no periodic source/kick/clamp",
        ),
        scope="Finite explicitly selected nominal-temperature bias/mode diagnostic only. Same62 actual devices/finite contacts, ideal-wires versus validated full coupled wireRC; not RF/noise/long thermal/PLL/PVT qualification.",
    )

    def save():
        p = a.out / "result.tmp"
        payload = (json.dumps(result, indent=2) + "\n").encode()
        h.require(
            2 * len(payload) <= RECEIPT_RESERVE,
            "Receipt and atomic temporary file exceed reserved bytes",
        )
        h.require(
            owned_size(a.out) + len(payload) <= OWN_LIMIT,
            "Receipt would exceed declared owned scratch",
        )
        h.require(
            shared_free() - len(payload) >= SHARED_RESERVE,
            "Receipt would cross declared shared reserve",
        )
        p.write_bytes(payload)
        p.replace(a.out / "result.json")

    save()
    for mode in (a.mode,):
        h.require(
            shared_free() > SHARED_RESERVE + LAUNCH_HEADROOM
            and owned_size(a.out) + LAUNCH_HEADROOM <= OWN_LIMIT,
            "Resource reserve unavailable",
        )
        root = a.out / mode
        root.mkdir()
        contract = vector_contract(comp, mapping, mode, binding)
        (root / "contract.json").write_text(json.dumps(contract, indent=2) + "\n")
        (root / "bank.spice").write_text(circuit(comp, hybrid, mapping, mode))
        (root / "bench.cir").write_text(deck(comp, contract, models, osdis, a.vctrl))
        (root / "spinit").write_text("* Explicit native OSDI model loading only.\n")
        row = dict(mode=mode, status="RUNNING", stream={}, resources=[])
        result["cases"].append(row)
        save()
        try:
            run_native(root, a.ngspice, a.out, save, row)
            h.require(
                row["returncode"] == 0 and row["resource_stop"] is None,
                "Native process/resource failure",
            )
            h.require(
                row["stream"].get("complete") is True
                and not row["stream"].get("error"),
                "Lossless waveform incomplete",
            )
            row["audit"] = audit_native(root, contract)
            metrics = row["audit"]["metrics"]
            row["failed_hbts"] = [
                int(k)
                for k, v in metrics["hbt_bounds"].items()
                if v["min_vce"] < 0.4
                or v["max_vce"] > 1.6
                or v["peak_abs_current_per_emitter_a"] > 0.003
            ]
            row["postsettling_hbt_bounds_pass"] = not row["failed_hbts"]
            row["all_time_upper_vce_pass"] = metrics["full_time_max_vce"] <= 1.6
            signal = metrics["signals"][0]
            row["finite_output_clock_screen_pass"] = (
                signal["rising_edges"] >= 10
                and signal["minimum_differential_v"] <= -0.3
                and signal["maximum_differential_v"] >= 0.3
            )
            row["status"] = "COMPLETE_DIAGNOSTIC_NOT_ACCEPTANCE"
        except BaseException as e:
            row.update(status="FAIL_PRESERVED", error=type(e).__name__ + ": " + str(e))
            save()
            if not isinstance(e, Exception):
                raise
        row["outputs"] = {p.name: h.pin(p) for p in root.iterdir() if p.is_file()}
        save()
        if row["status"] == "FAIL_PRESERVED":
            break
    h.require(
        all(h.pin(p) == v for p, v in inputs.items()),
        "Frozen powered source/input changed",
    )
    result["status"] = (
        "COMPLETE_SINGLE_MODE_DIAGNOSTIC_NOT_ACCEPTANCE"
        if len(result["cases"]) == 1
        and all(
            c["status"] == "COMPLETE_DIAGNOSTIC_NOT_ACCEPTANCE" for c in result["cases"]
        )
        else "FAIL_PRESERVED"
    )
    save()
    print(result["status"])
    if result["status"] == "FAIL_PRESERVED":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
