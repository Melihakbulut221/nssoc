#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Actual 437-device loaded /80 prerequisite; no ideal internal clock or PLL claim.

The frozen VCO includes all 889R/765C and 13 finite contacts. Divider and CMOS
feedback retain their frozen schematic devices, without a physical RC claim.
Every native sample is retained losslessly, including every device observation.
"""

import argparse
import concurrent.futures
import copy
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import subprocess
import sys
import time
import zlib

import numpy as np
import characterize_pcie_pll_loop_v1 as old
import characterize_pcie_pll_loop_stream_v2 as stream
import diagnose_pcie_vco_v6_powered_v1 as physical

n = old.n
life = stream.previous.life
require = stream.previous.require
ROOT = old.ROOT
SOURCE = ROOT / "hw/soc/analog/pcie/pll_feedback_vco_v6_wire_v1.spice"
TOP = "nssoc_pll_feedback_vco_v6_wire_v1"
HYBRID = Path("/dev/shm/nssoc-vco-v4-mim-v6-local-v1-hybrid-01")
PINS = {
    "hybrid-open.spice": "37673a8cba095790d53b477db96cda8c782e94166a52b3998c92203d7649805b",
    "composition.json": "619ac16d7bb31a5a25b594c768bb551b232439d736745697b79923beb8811ff1",
}
METHOD_PINS = {
    "characterize_pcie_pll_loop_v1.py": "f2e8fe57309ee15bb73dffc4954720b635842db333f8df81799ddb29e45f0737",
    "characterize_pcie_pll_loop_stream_v2.py": "79de51fcd210e1141b187a3fc83546e9933b5d5c6c36a9d0bc85aa6a69d2da9d",
    "diagnose_pcie_vco_v6_powered_v1.py": "bddafbf3a3ae9beaa9bbb4e212675bf4496e2b73220b2c08b00c88299622c87b",
    "pcie_pll_native_fixture_v1.py": "ba483cc0a740db3c774225ef2c42cb0a41cf56311050512217ec588ab2172223",
}
OBS = ["time"] + [
    f"v({x})"
    for x in (
        "clkp",
        "clkn",
        "qp",
        "qn",
        "fb",
        "xchain.xfb.clk",
        "xchain.xfb.f0",
        "xchain.xfb.f1",
        "xchain.xfb.count",
        "xchain.xfb.xcount.q0",
        "xchain.xfb.xcount.q1",
    )
]
OWN_LIMIT = 80 * 1024**2
RECEIPT_RESERVE = 2 * 1024**2
FLOOR = 512 * 1024**2
FAULTS = {
    "disconnect_divider_clock": ("XDIV clkp clkn", "XDIV clkp clkp"),
    "wrong_feedback_modulus": ("XD2N q2b q1 q0 d2b", "XD2N q2b q1 q1 d2b"),
}


def topology(text):
    """Only exact physical connections, no substituted behavioral clock."""
    expected = [
        f".subckt {TOP} vctrl clearb clkp clkn qp qn fb fbbar vco_avdd div_avdd core_vdd avss sub body_substrate wire_cref",
        "XOSC vco_avdd avss clkn clkp sub vctrl body_substrate wire_cref nssoc_vco_local_hybrid_open_v2",
        "XDIV clkp clkn qp qn div_avdd avss sub nssoc_clock_div4_hbt_v5",
        "XFB qp qn clearb fb fbbar div_avdd core_vdd avss sub nssoc_pll_feedback_div20_v2",
        f".ends {TOP}",
    ]
    require(
        [x for x in text.splitlines() if x and not x.startswith("*")] == expected,
        "Exact source-bound real feedback topology",
    )


def config(vctrl=0.6, fault=""):
    require(vctrl in (0.6, 0.85) and fault in ("", *FAULTS), "Predeclared probe")
    for name, digest in METHOD_PINS.items():
        require(
            n.common.sha(ROOT / "scripts" / name) == digest, "Frozen method " + name
        )
    for name, digest in PINS.items():
        require(n.common.sha(HYBRID / name) == digest, "Exact physical VCO " + name)
    c = old.chain_config()
    old_rows = n.graph(
        {Path(p).name: Path(p).read_text() for p in c["sources"]}, c["roots"]
    )
    texts = {
        Path(p).name: Path(p).read_text()
        for p in c["sources"]
        if Path(p).name not in ("clock_vco_hbt_v4.spice", "pll_feedback_chain_v1.spice")
    }
    topology(SOURCE.read_text())
    texts[SOURCE.name] = SOURCE.read_text()
    texts["hybrid-open.spice"] = (HYBRID / "hybrid-open.spice").read_text()
    if fault:
        filename = (
            SOURCE.name
            if fault == "disconnect_divider_clock"
            else old.counter.CIRCUIT.name
        )
        before, after = FAULTS[fault]
        require(
            texts[filename].count(before) == 1, "One actual device connection fault"
        )
        texts[filename] = texts[filename].replace(before, after)
    # Native parser traverses unchanged /4 and /20; physical VCO rows are bound
    # directly to their already validated native composition, never inferred.
    rows = [r for r in old_rows if not r["path"].startswith("xchain.xosc.")]
    if fault == "disconnect_divider_clock":
        rows = [
            dict(r, nets=["clkp" if x == "clkn" else x for x in r["nets"]])
            if r["path"].startswith("xchain.xdiv.")
            else r
            for r in rows
        ]
    if fault == "wrong_feedback_modulus":
        feedback = n.graph(
            {old.counter.CIRCUIT.name: texts[old.counter.CIRCUIT.name]},
            [
                (
                    old.counter.TOP,
                    "xchain.xfb",
                    ["qp", "qn", "clearb", "fb", "fbbar", "dvdd", "cvdd", "0", "0"],
                )
            ],
        )
        rows = [r for r in rows if not r["path"].startswith("xchain.xfb.")] + feedback
    comp = json.loads((HYBRID / "composition.json").read_text())
    ports = dict(
        zip(
            [x.lower() for x in comp["ports"]],
            ["avdd", "0", "clkn", "clkp", "0", "vctrl", "body_substrate", "wire_cref"],
        )
    )
    for item in comp["records"]:
        words = item["line"].lower().split()
        count = len(item["terminals"])
        require(
            words[count + 1] == item["model"].lower(), "Native device model binding"
        )
        rows.append(
            dict(
                path="xchain.xosc." + words[0],
                model=words[count + 1],
                nets=[ports.get(x, "xchain.xosc." + x) for x in words[1 : count + 1]],
                params=dict(x.split("=") for x in words[count + 2 :]),
            )
        )
    require(
        len(rows) == 437 and len({r["path"] for r in rows}) == 437, "All437 devices"
    )
    require(sum(r["model"] == "npn13g2" for r in rows) == 64, "All64 HBT")
    require(
        sum(r["model"] in ("ptap1", "ntap1") for r in rows) == 13,
        "All13 finite contacts",
    )
    hybrid_lines = texts["hybrid-open.spice"].splitlines()
    require(
        sum(x.startswith("R") for x in hybrid_lines) == 889, "All889 wire resistors"
    )
    require(
        sum(x.startswith("C") for x in hybrid_lines) == 765, "All765 wire capacitors"
    )
    c.update(
        case="loaded_physical_vco_v6_div80",
        vctrl=vctrl,
        fault=fault,
        physical_vco_records=62,
        divider_schematic_records=375,
        contact_records=13,
        wire_resistors=889,
        wire_capacitors=765,
        window_s=[4e-9, 34e-9],
        step_s=5e-12,
        stop_s=34e-9,
    )
    c["fixture"] = [x.replace("500p .85", f"500p {vctrl:.2g}") for x in c["fixture"]]
    c["fixture"] += [
        "VBODY body_substrate 0 0",
        "VWREF wire_cref 0 0",
        "CLOAD_CLKP clkp 0 50f",
        "CLOAD_CLKN clkn 0 50f",
    ]
    c["extra_vectors"] += ["i(vbody)", "i(vwref)"]
    c["roots"] = [
        (
            TOP,
            "xchain",
            [
                "vctrl",
                "clearb",
                "clkp",
                "clkn",
                "qp",
                "qn",
                "fb",
                "fbbar",
                "avdd",
                "dvdd",
                "cvdd",
                "0",
                "0",
                "body_substrate",
                "wire_cref",
            ],
        )
    ]
    return c, rows, texts


def measurement(data, c):
    r = old.measure_chain(data, c)
    r["vctrl_external_v"] = c["vctrl"]
    return r


class Meter(stream.Meter):
    """Frozen424 device screens plus explicit13 contact terminal-voltage screens."""

    def __init__(self, columns, rows, c):
        self.contacts = [r for r in rows if r["model"] in ("ptap1", "ntap1")]
        super().__init__(columns, [r for r in rows if r not in self.contacts], c, OBS)
        self.contact_max = {r["path"]: 0.0 for r in self.contacts}

    def push(self, block):
        super().push(block)
        for row in self.contacts:
            values = [
                block[:, self.names.index(f"v({x})")]
                if x != "0"
                else np.zeros(len(block))
                for x in row["nets"]
            ]
            self.contact_max[row["path"]] = max(
                self.contact_max[row["path"]], float(abs(values[0] - values[1]).max())
            )

    def finish(self):
        safety, data, grid = super().finish()
        for row in self.contacts:
            vmax = self.contact_max[row["path"]]
            safety["all_device_bounds"].append(
                dict(
                    path=row["path"],
                    model=row["model"],
                    max_capture_terminal_difference=vmax,
                    voltage_limit=3.3,
                    inferred_ohmic_peak_a=vmax / float(row["params"]["r"]),
                    contact_current_qualified=False,
                    passed=vmax <= 3.3,
                )
            )
        safety["passed"] = safety["passed"] and all(
            r["passed"] for r in safety["all_device_bounds"]
        )
        require(len(safety["all_device_bounds"]) == 437, "Every device screen retained")
        return safety, data, grid


def guard(folder, pending=0):
    free = shutil.disk_usage("/dev/shm").free
    used = physical.owned_size(folder)
    # Include all this experiment's attempts, so a failed probe is not free space.
    used += sum(
        physical.regular_size(x)
        for x in Path("/dev/shm").glob("nssoc-vco-v6-feedback-*")
        if x != folder
    )
    require(free - pending >= FLOOR, "Shared512MiB reserve")
    require(
        used + pending + RECEIPT_RESERVE <= OWN_LIMIT, "Own80MiB final-drain reserve"
    )
    return free, used


def capture(source, out, rows, c):
    expected = n.vectors(rows, c["extra_vectors"])
    header, meta = life.tiny.parse_header(source, expected)
    require(
        meta["declared_points"] == 0 and sys.byteorder == "little", "NativeFIFO format"
    )
    meter = Meter(meta["columns"], rows, c)
    width = len(meta["columns"]) * 8
    pending, whole, payload = bytearray(), hashlib.sha256(header), hashlib.sha256()
    compressor = zlib.compressobj(level=6, wbits=31)
    raw_bytes = len(header)
    with (out / "wave.raw.gz").open("xb", buffering=0) as dst:

        def write(blob):
            guard(out, len(blob))
            dst.write(blob)

        write(compressor.compress(header))
        while raw := source.read(65536):
            whole.update(raw)
            raw_bytes += len(raw)
            write(compressor.compress(raw))
            pending.extend(raw)
            count = len(pending) // width
            if count:
                blob = bytes(pending[: count * width])
                payload.update(blob)
                meter.push(np.frombuffer(blob, "<f8").reshape(count, -1))
                del pending[: count * width]
        write(compressor.flush())
    require(
        bytes(pending) == str(meter.count).encode(), "Exact native sample-count trailer"
    )
    safety, data, grid = meter.finish()
    # Independent gzip readback proves every byte survived the transport.
    digest, total = hashlib.sha256(), 0
    with gzip.open(out / "wave.raw.gz", "rb") as src:
        while part := src.read(1024**2):
            digest.update(part)
            total += len(part)
    require(
        total == raw_bytes and digest.hexdigest() == whole.hexdigest(),
        "Lossless gzip all-byte replay",
    )
    return dict(
        columns=meta["columns"],
        raw_table=meta["raw_table"],
        rows=meter.count,
        values=meter.count * len(meta["columns"]),
        raw_bytes=raw_bytes,
        raw_sha256=whole.hexdigest(),
        payload_sha256=payload.hexdigest(),
        safety=safety,
        measurement=measurement(data, c),
        time_grid=grid,
        compression_readback=True,
    )


def deck(c, rows, texts):
    lines = ["Actual437-device physical VCOv6 loaded /80 prerequisite"]
    lines += [
        f'.lib "{n.MODELS}/corner{k}.lib" {v}'
        for k, v in [
            ("HBT", "hbt_typ"),
            ("RES", "res_typ"),
            ("CAP", "cap_typ"),
            ("MOShv", "mos_tt"),
            ("MOSlv", "mos_tt"),
        ]
    ]
    lines += [f'.include "{p}"' for p in texts]
    lines += [".temp 27", ".options reltol=1e-4 abstol=1e-12", *c["fixture"]]
    for model, path, ports in c["roots"]:
        lines.append(path + " " + " ".join(ports) + " " + model)
    lines += [
        f".tran {c['step_s']:.12g} {c['stop_s']:.12g} 0 {c['step_s']:.12g}",
        ".control",
    ]
    lines += ["pre_osdi " + str(x) for x in n.OSDI]
    lines += [
        "set filetype=binary",
        "save " + " ".join(n.vectors(rows, c["extra_vectors"])),
    ]
    for r in rows:
        if r["model"] == "npn13g2":
            name = "q." + r["path"] + ".qnpn13g2"
            lines += [
                f"alter @{name}[off] = 1",
                "echo NSSOC_NATIVE_FLAG_BEGIN " + name,
                "show " + name + " : off",
                "echo NSSOC_NATIVE_FLAG_END",
            ]
    lines += [
        "op",
        "write op.raw all",
        "run stream.fifo",
        "setplot",
        "display",
        "rusage space",
        "quit",
        ".endc",
        ".end",
        "",
    ]
    return "\n".join(lines)


def native_limit():
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3,) * 2)
    resource.setrlimit(resource.RLIMIT_FSIZE, (45 * 1024**2,) * 2)
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    os.sched_setaffinity(0, {10})


def run_native(out, rows, c):
    fifo = out / "stream.fifo"
    os.mkfifo(fifo)
    keep = os.open(fifo, os.O_RDWR)
    reader = fifo.open("rb")
    env = {
        k: v
        for k, v in os.environ.items()
        if k
        not in ("GH_TOKEN", "GITHUB_TOKEN", "LD_PRELOAD", "PYTHONPATH", "PYTHONHOME")
    }
    env.update(SPICE_SCRIPTS=str(out), RAYON_NUM_THREADS="1", OMP_NUM_THREADS="1")
    start, proc, pool = time.monotonic(), None, None
    free_min, own_peak = guard(out)
    affinity = None

    def close_keep():
        nonlocal keep
        if keep is not None:
            os.close(keep)
            keep = None

    with life.ProcessOwner(out / "owned-processes.json") as owner:
        try:
            with (out / "run.log").open("x") as log:
                proc = owner.launch(
                    "native",
                    [str(n.NG), "-n", "-b", "bench.cir"],
                    cwd=out,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    preexec_fn=native_limit,
                )
                affinity = sorted(os.sched_getaffinity(proc.pid))
                require(affinity == [10], "Actual native CPU10 affinity")
                pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)

                def consume():
                    try:
                        with reader:
                            return capture(reader, out, rows, c)
                    except BaseException as error:
                        owner.request_cancel(error)
                        raise

                future = pool.submit(consume)
                while True:
                    if future.done():
                        result = future.result()
                    owner.check()
                    free, used = guard(out)
                    free_min, own_peak = min(free_min, free), max(own_peak, used)
                    if proc.poll() is not None:
                        close_keep()
                        require(proc.returncode == 0, "Native nonzero exit")
                        if future.done():
                            result = future.result()
                            owner.complete(proc)
                            break
                    owner.cancelled.wait(0.1)
        except BaseException as error:
            owner.stop_failed(error)
            close_keep()
            raise
        finally:
            close_keep()
            if pool is not None:
                pool.shutdown(wait=True)
            reader.close()
            n.common.atomic(
                out / "execution.json",
                dict(
                    returncode=None if proc is None else proc.poll(),
                    elapsed_seconds=time.monotonic() - start,
                    elapsed_watchdog_seconds=None,
                    address_space_limit_bytes=2 * 1024**3,
                    actual_affinity=affinity,
                    min_shared_free_bytes=free_min,
                    max_own_bytes=own_peak,
                ),
            )
    fifo.unlink()
    return result


def run(out, vctrl, fault=""):
    c, rows, texts = config(vctrl, fault)
    require(
        not out.exists() and out.resolve().is_relative_to("/dev/shm"),
        "Fresh RAM output",
    )
    require(shutil.disk_usage("/dev/shm").free >= 1024**3, "Native1GiB entry floor")
    _, owned = guard(out)
    require(owned + 24 * 1024**2 < OWN_LIMIT, "24MiB launch headroom")
    require(n.common.sha(n.NG) == n.common.NG47_SHA, "Exact ng47")
    require(
        {p.name: n.common.sha(p) for p in n.OSDI} == n.common.OSDI_PINS, "Exact OSDIs"
    )
    inventory = {p.name: n.common.sha(p) for p in sorted(n.MODELS.glob("*.lib"))}
    require(
        hashlib.sha256(
            json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        == n.common.MODEL_INVENTORY_SHA,
        "Exact PDK model inventory",
    )
    out.mkdir()
    for name, text in texts.items():
        (out / name).write_text(text)
    (out / "spinit").write_text("set num_threads=1\n")
    (out / "bench.cir").write_text(deck(c, rows, texts))
    paths = [
        SOURCE,
        *[HYBRID / x for x in PINS],
        n.NG,
        *n.OSDI,
        *n.MODELS.glob("*.lib"),
        *[Path(p) for p in c["sources"]],
        *[Path(p) for p in stream.previous.method_inventory()],
        *out.iterdir(),
    ]
    pins = {str(p.resolve()): n.common.pin(p) for p in paths}
    record = dict(
        status="RUNNING",
        inputs=pins,
        config=c,
        devices=rows,
        raw_estimate_bytes=int(34e-9 / 5e-12 + 32)
        * (len(n.vectors(rows, c["extra_vectors"])) + 1)
        * 8,
        limits="Finite27C loaded /80; no PLL lock, full divider RC, substrate spreading, PVT, jitter, BER, or foundry qualification.",
    )
    n.common.atomic(out / "result.json", record)
    try:
        record.update(run_native(out, rows, c))
        # Same 64 actual native OFF readbacks, zero-source OP and strict clean-log gate.
        record.update(stream.previous.startup_proof(out, dict(devices=rows, config=c)))
        require(
            all(n.common.pin(p) == pin for p, pin in pins.items()),
            "All inputs unchanged after native",
        )
        good = record["safety"]["passed"] and record["measurement"]["passed"]
        record["status"] = (
            "PASS_NATIVE_LOADED_FEEDBACK_SCREEN"
            if good
            else "FAIL_NATIVE_LOADED_FEEDBACK_SCREEN"
        )
        record["accepted_actual_fault"] = bool(
            fault and record["safety"]["passed"] and not record["measurement"]["passed"]
        )
    except BaseException as error:
        record.update(status="ERROR_NATIVE_OR_CAPTURE", error=repr(error))
        raise
    finally:
        record["outputs"] = {
            str(p.relative_to(out)): n.common.pin(p)
            for p in out.rglob("*")
            if p.is_file() and p.name != "result.json"
        }
        n.common.atomic(out / "result.json", record)
    return record


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--vctrl", type=float, choices=[0.6, 0.85], default=0.6)
    ap.add_argument("--fault", choices=list(FAULTS), default="")
    a = ap.parse_args()
    r = run(a.out, a.vctrl, a.fault)
    print(r["status"])
    return (
        0
        if r["status"] == "PASS_NATIVE_LOADED_FEEDBACK_SCREEN"
        or r["accepted_actual_fault"]
        else 1
    )


if __name__ == "__main__":
    raise SystemExit(main())
