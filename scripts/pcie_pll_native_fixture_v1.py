# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""All-sample native probe support; finite engineering screens, not signoff."""

import hashlib
import json
import os
from pathlib import Path
import re
import resource
import shutil
import signal
import subprocess
import sys
import time

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import characterize_pcie_pll_pfd_cp_v1 as common

CAP = 50 * 1024**2
FLOOR = 512 * 1024**2
NG = Path("/dev/shm/nssoc-ngspice47-20261004/root/usr/bin/ngspice")
OSDI = [
    Path("/dev/shm/nssoc-clock-vco-full-20261004") / name for name in common.OSDI_PINS
]
MODELS = common.PDK / "libs.tech/ngspice/models"


def graph(texts, roots):
    definitions = {}
    for text in texts.values():
        active = None
        for line in text.lower().splitlines():
            w = line.split()
            if not w or w[0].startswith("*"):
                continue
            if w[0] == ".subckt":
                assert active is None and w[1] not in definitions
                active = w[1]
                definitions[active] = (w[2:], [])
            elif w[0] == ".ends":
                assert active and (len(w) == 1 or w == [".ends", active])
                active = None
            else:
                assert active
                definitions[active][1].append(w)
        assert active is None
    rows = []

    def descend(name, path, nodes, stack=()):
        assert name not in stack
        ports, body = definitions[name]
        assert len(ports) == len(nodes)
        mapping = dict(zip(ports, nodes))
        seen = set()

        def node(n):
            return mapping.get(n, path + "." + n)

        for w in body:
            assert w[0].startswith("x") and w[0] not in seen
            seen.add(w[0])
            here = path + "." + w[0]
            if w[-1] in definitions:
                descend(w[-1], here, [node(n) for n in w[1:-1]], stack + (name,))
                continue
            models = {
                "npn13g2": 4,
                "rppd": 3,
                "cap_cmim": 2,
                "sg13_hv_pmos": 4,
                "sg13_hv_nmos": 4,
                "sg13_lv_pmos": 4,
                "sg13_lv_nmos": 4,
            }
            found = [
                (m, n) for m, n in models.items() if len(w) > n + 1 and w[n + 1] == m
            ]
            assert len(found) == 1, w
            model, n = found[0]
            params = dict(x.split("=") for x in w[n + 2 :])
            assert len(params) == len(w[n + 2 :])
            rows.append(
                dict(
                    path=here,
                    model=model,
                    nets=[node(x) for x in w[1 : n + 1]],
                    params=params,
                )
            )

    for model, name, nodes in roots:
        descend(model, name, nodes)
    assert len(rows) == len({r["path"] for r in rows})
    return rows


def vectors(rows, extra):
    result = [
        "v(" + n + ")" for n in sorted({n for r in rows for n in r["nets"]} - {"0"})
    ] + extra
    for r in rows:
        path, model = r["path"], r["model"]
        if model == "npn13g2":
            result += ["@q." + path + ".qnpn13g2[ic]", "v(" + path + ".t)"]
        elif model.startswith("sg13_"):
            result += ["@n." + path + ".n" + model + "[ids]"]
        elif model == "rppd":
            result += ["v(" + path + ".dt)"]
    assert len(result) == len(set(result))
    return result


def read_raw(path, expected, transient):
    blob = Path(path).read_bytes()
    assert len(blob) <= CAP and blob.count(b"Binary:\n") == 1
    h, p = blob.split(b"Binary:\n")
    h = h.decode()
    assert "Flags: real\n" in h
    n = int(re.search(r"No\. Variables: (\d+)\n", h)[1])
    count = int(re.search(r"No\. Points: (\d+)\n", h)[1])
    assert count > 0 and len(p) == n * count * 8
    names = []
    for i, line in enumerate(h.split("Variables:\n")[1].splitlines()):
        fields = line.split()
        assert len(fields) == 3 and fields[0] == str(i)
        names.append(fields[1])
    wanted = {"i(" + s + ")" if s.startswith("@") else s for s in expected}
    if transient:
        wanted.add("time")
    assert len(names) == len(set(names)) == n and set(names) == wanted
    a = np.frombuffer(p, dtype="<f8").reshape((count, n))
    assert np.isfinite(a).all()
    return dict(zip(names, a.T))


def safety(data, rows, window):
    t = data["time"]
    mask = (t >= window[0]) & (t <= window[1])
    result = []
    range_issues = []

    def value(node):
        return data["v(" + node + ")"] if node != "0" else np.zeros_like(t)

    for r in rows:
        model, path = r["model"], r["path"]
        if model == "npn13g2":
            nx = int(r["params"]["nx"])
            assert 1 <= nx <= 10
            c, b, e, _ = map(value, r["nets"])
            vce = c - e
            ic = data["i(@q." + path + ".qnpn13g2[ic])"]
            item = dict(
                path=path,
                model=model,
                min_settled_vce=float(vce[mask].min()),
                max_capture_vce=float(vce.max()),
                max_capture_ic_per_nx=float(abs(ic).max()) / nx,
            )
            item["passed"] = (
                item["min_settled_vce"] >= 0.4
                and item["max_capture_vce"] <= 1.6
                and item["max_capture_ic_per_nx"] <= 0.003
            )
        elif model.startswith("sg13_"):
            params = r["params"]
            assert params["w"].endswith("u") and params["l"].endswith("u")
            w, l = (float(params[n][:-1]) for n in ("w", "l"))
            lv = "_lv_" in model
            assert params["ng"] == params["m"] == "1"
            if not (
                (0.15 if lv else 0.3) <= w <= 10
                and (0.13 if lv else 0.4 if "pmos" in model else 0.45) <= l <= 10
            ):
                range_issues.append(
                    dict(path=path, model=model, width_um=w, length_um=l)
                )
            values = list(map(value, r["nets"]))
            amps = data["i(@n." + path + ".n" + model + "[ids])"]
            item = dict(
                path=path,
                model=model,
                max_capture_terminal_difference=float(
                    max(abs(a - b).max() for a in values for b in values)
                ),
                max_capture_drain_per_um=float(abs(amps).max()) / w,
                voltage_limit=1.5 if lv else 3.3,
            )
            item["passed"] = (
                item["max_capture_terminal_difference"] <= item["voltage_limit"]
                and item["max_capture_drain_per_um"] <= 0.002
            )
        elif model in ("rppd", "cap_cmim"):
            a, b = (value(x) for x in r["nets"][:2])
            item = dict(
                path=path,
                model=model,
                max_capture_terminal_difference=float(abs(a - b).max()),
                voltage_limit=3.3,
            )
            item["passed"] = item["max_capture_terminal_difference"] <= 3.3
        else:
            raise ValueError("No safety contract for " + model)
        result.append(item)
    return dict(
        passed=not range_issues and all(r["passed"] for r in result),
        all_device_bounds=result,
        model_geometry_range_issues=range_issues,
        foundry_soa_qualification=False,
    )


def validate_time_grid(t, stop, step):
    """Retain the native final timestamp; classify only <=16 binary64 ULP drift."""
    assert len(t) >= 2 and np.isfinite(t).all()
    distance = abs(float(t[-1]) - stop) / np.spacing(stop)
    assert t[0] == 0 and distance <= 16
    assert np.all(np.diff(t) > 0)
    assert np.diff(t).max() <= step * (1 + 1e-5)
    return dict(
        first_s=float(t[0]),
        last_s=float(t[-1]),
        endpoint_ulp_distance=float(distance),
        endpoint_ulp_limit=16,
        largest_interval_s=float(np.diff(t).max()),
        raw_samples_changed=False,
    )


def run(config, out, producer, measurement):
    out = Path(out)
    assert (
        common.sha(common.__file__)
        == "013c213cb2dc4dd3bef97124a107fbd06b6897340c4be9c517717c5ab8fef5b9"
    )
    assert not out.exists() and out.resolve().is_relative_to(Path("/dev/shm"))
    assert shutil.disk_usage("/dev/shm").free >= FLOOR + CAP
    assert common.sha(NG) == common.NG47_SHA
    assert {p.name: common.sha(p) for p in OSDI} == common.OSDI_PINS
    inventory = {p.name: common.sha(p) for p in sorted(MODELS.glob("*.lib"))}
    assert (
        hashlib.sha256(
            json.dumps(inventory, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        == common.MODEL_INVENTORY_SHA
    )
    texts = {Path(p).name: Path(p).read_text() for p in config["sources"]}
    assert len(texts) == len(config["sources"])
    rows = graph(texts, config["roots"])
    names = vectors(rows, config["extra_vectors"])
    out.mkdir()
    for name, text in texts.items():
        (out / name).write_text(text)
    (out / "spinit").write_text("set num_threads=1\n")
    (out / "config.json").write_text(json.dumps(config, indent=2) + "\n")
    lines = ["Bounded native feedback prerequisite probe"]
    for kind, corner in [
        ("HBT", "hbt_typ"),
        ("RES", "res_typ"),
        ("CAP", "cap_typ"),
        ("MOShv", "mos_tt"),
        ("MOSlv", "mos_tt"),
    ]:
        lines.append(f'.lib "{MODELS}/corner{kind}.lib" {corner}')
    lines += (
        ['.include "' + n + '"' for n in texts]
        + [".temp 27", ".options reltol=1e-4 abstol=1e-12"]
        + config["fixture"]
    )
    for model, name, nodes in config["roots"]:
        lines.append(name + " " + " ".join(nodes) + " " + model)
    lines += (
        [".control"]
        + ["pre_osdi " + str(p) for p in OSDI]
        + ["set filetype=binary", "save " + " ".join(names)]
    )
    flags = []
    for r in rows:
        if r["model"] == "npn13g2":
            path = "q." + r["path"] + ".qnpn13g2"
            flags.append(path)
            lines += [
                "alter @" + path + "[off] = 1",
                "echo NSSOC_NATIVE_FLAG_BEGIN " + path,
                "show " + path + " : off",
                "echo NSSOC_NATIVE_FLAG_END",
            ]
    lines += [
        "op",
        "write op.raw all",
        f"tran {config['step_s']:.12g} {config['stop_s']:.12g} 0 {config['step_s']:.12g}",
        "write wave.raw all",
        "quit",
        ".endc",
        ".end",
    ]
    (out / "bench.cir").write_text("\n".join(lines) + "\n")
    paths = [
        Path(__file__),
        Path(producer),
        Path(common.__file__),
        NG,
        *OSDI,
        *MODELS.glob("*.lib"),
        *[Path(p) for p in config["sources"]],
        *[Path(p) for p in config.get("method_inputs", [])],
        *out.iterdir(),
    ]
    pins = {str(p.resolve()): common.pin(p) for p in paths}
    record = dict(
        status="RUNNING",
        config=config,
        inputs=pins,
        devices=rows,
        measurement_scope="Finite source-bound schematic experiment; no closed-loop or foundry signoff.",
    )
    common.atomic(out / "result.json", record)

    def cap():
        resource.setrlimit(resource.RLIMIT_AS, (1024**3, 1024**3))
        resource.setrlimit(resource.RLIMIT_FSIZE, (45 * 1024**2, 45 * 1024**2))
        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
        os.sched_setaffinity(0, {min(os.sched_getaffinity(0))})

    env = {
        k: v
        for k, v in os.environ.items()
        if k not in ("GH_TOKEN", "GITHUB_TOKEN", "LD_PRELOAD")
    }
    env.update(SPICE_SCRIPTS=str(out), OMP_NUM_THREADS="1")
    process = None
    start = time.monotonic()
    minimum = shutil.disk_usage("/dev/shm").free
    try:
        with (out / "run.log").open("x") as log:
            process = subprocess.Popen(
                [str(NG), "-n", "-b", "bench.cir"],
                cwd=out,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                preexec_fn=cap,
                start_new_session=True,
            )
            while process.poll() is None:
                minimum = min(minimum, shutil.disk_usage("/dev/shm").free)
                assert minimum >= FLOOR
                assert (
                    sum(p.stat().st_size for p in out.iterdir() if p.is_file()) <= CAP
                )
                time.sleep(0.1)
        record["execution"] = dict(
            returncode=process.returncode,
            elapsed_s=time.monotonic() - start,
            min_free_bytes=minimum,
            address_space_cap_bytes=1024**3,
            elapsed_watchdog=None,
        )
        assert process.returncode == 0
        log = (out / "run.log").read_text()
        record["diagnostics"] = [
            s
            for s in log.splitlines()
            if re.search(
                r"warning|error|failed|singular|timestep too small|gmin stepping|source stepping",
                s,
                re.I,
            )
        ]
        assert not record["diagnostics"] and "ngspice-47 done" in log
        observed = re.findall(
            r"(?ms)^NSSOC_NATIVE_FLAG_BEGIN (\S+)\n(.*?)^NSSOC_NATIVE_FLAG_END\s*$", log
        )
        assert [r[0] for r in observed] == flags
        for name, body in observed:
            assert re.findall(r"(?m)^\s*device\s+(\S+)\s*$", body) == [name[:21]]
            assert re.findall(r"(?m)^\s*off\s+([01])\s*$", body) == ["1"]
        op = read_raw(out / "op.raw", names, False)
        assert all(len(v) == 1 and abs(v[0]) <= 1e-10 for v in op.values())
        data = read_raw(out / "wave.raw", names, True)
        t = data["time"]
        record["time_grid"] = validate_time_grid(t, config["stop_s"], config["step_s"])
        record["safety"] = safety(data, rows, config["window_s"])
        record["measurement"] = measurement(data, config)
        record["zero_source_op"] = True
        record["actual_off_flags"] = flags
        assert all(common.pin(p) == h for p, h in pins.items())
        record["status"] = (
            "PASS_NATIVE_FINITE_EXPERIMENT"
            if record["safety"]["passed"] and record["measurement"]["passed"]
            else "FAIL_NATIVE_FINITE_EXPERIMENT"
        )
    except BaseException as error:
        record.update(status="ERROR_NATIVE_OR_CAPTURE", error=repr(error))
        raise
    finally:
        if process is not None and process.poll() is None:
            os.killpg(process.pid, signal.SIGKILL)
            process.wait()
        record["outputs"] = {
            p.name: common.pin(p)
            for p in out.iterdir()
            if p.is_file() and p.name != "result.json"
        }
        common.atomic(out / "result.json", record)
    return record
