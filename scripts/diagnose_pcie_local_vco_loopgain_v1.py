#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Source-bound static DC and conditional differential-return diagnostic.

Added L/C/test sources are diagnostic boundaries, never a physical design repair.
All native device models, intrinsic parameters, full wire R/C and finite contacts
remain. Opening both base paths does not prove global multiloop stability.
"""

import argparse
import cmath
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import tarfile
import time

import diagnose_pcie_local_vco_powered_v1 as p

h = p.h
ROOT = Path(__file__).resolve().parents[1]
POWERED_SHA = "f6f5a07ec912646c98c0cff776f3001eb5f9a2addd7bf2dbe3a99f703132ff82"
CAPSULE_SHA = "f96718bbff6e5c546635d48b81332ee033cd6b557af2e60230fcebca111ddc52"
VCTRLS = (0.4, 0.6, 0.85, 1.0, 1.2, 1.5)
KINDS = ("intact", "break", "break_small", "break_large", "mid_suppressed")


def last_native_voltages(archive, mode, row):
    name = f"native/nssoc-vco-v4-local-powered-01/{mode}/wave.dat.gz"
    digest = hashlib.sha256()
    count = 0
    with archive.extractfile(name) as f:
        for block in iter(lambda: f.read(1024**2), b""):
            digest.update(block)
            count += len(block)
    h.require(
        dict(bytes=count, sha256=digest.hexdigest()) == row["stream"]["compressed"],
        "Compressed source wave changed",
    )
    digest = hashlib.sha256()
    count = 0
    with gzip.GzipFile(fileobj=archive.extractfile(name)) as f:
        header = f.readline()
        digest.update(header)
        count += len(header)
        names = header.decode().split()
        for raw in f:
            digest.update(raw)
            count += len(raw)
            last = raw.decode().split()
    h.require(
        digest.hexdigest() == row["stream"]["raw_sha256"]
        and count == row["stream"]["raw_bytes"],
        "Full native source wave changed",
    )
    h.require(len(last) == len(names), "Native hint vector census")
    values = {
        n.lower(): float(v) for n, v in zip(names[1:], last[1:]) if n.startswith("v(")
    }
    h.require(all(math.isfinite(v) for v in values.values()), "Nonfinite native hints")
    return values


def topology(original, ids, node, kind):
    h.require(kind in KINDS, "Unknown diagnostic")
    lines = original.splitlines()
    changes = []
    if kind != "intact":
        scale = {"break_small": 0.1, "break_large": 10}.get(kind, 1)
        for side, sign in [("P", 1), ("N", -1)]:
            name = side + "0"
            indices = [
                i
                for i, line in enumerate(lines)
                if line.startswith(f"XD{ids[name]:04d} ")
            ]
            h.require(len(indices) == 1, "Missing exact stage-zero device")
            idx = indices[0]
            tokens = lines[idx].split()
            old = node(name, "B")
            h.require(tokens[2] == old, "Actual named base differs")
            new = "diag_" + side + "_base"
            tokens[2] = new
            lines[idx] = " ".join(tokens)
            added = [
                f"LDIAG_{side} {old} {new} {scale:.17g}",
                f"CDIAG_{side} {new} diag_{side}_drive {scale * 1e-6:.17g}",
                f"VDIAG_{side} diag_{side}_drive 0 DC 0 AC {sign * 0.5}",
            ]
            lines[-2:-2] = added
            changes.append(
                dict(device=name, original_base=old, new_base=new, added=added)
            )
        if kind == "mid_suppressed":
            # Deliberately suppress the second stage differential AC input while
            # retaining the exact DC circuit. This is an actual native fault test.
            lines[-2:-2] = [f"CDIAG_SUPPRESS {node('P1', 'B')} {node('N1', 'B')} 1u"]
    text = "\n".join(lines) + "\n"
    verify_topology(original, text, changes, kind, node)
    return text, changes


def verify_topology(original, actual, changes, kind, node):
    rows = h.statements(actual)
    wanted = h.statements(original)
    actual_native = [
        r[:] for r in rows if not r[0].startswith(("LDIAG_", "CDIAG_", "VDIAG_"))
    ]
    for change in changes:
        hits = [r for r in actual_native if len(r) > 2 and r[2] == change["new_base"]]
        h.require(len(hits) == 1, "Diagnostic base anchor census")
        hits[0][2] = change["original_base"]
    h.require(actual_native == wanted, "Intrinsic device/wire/body topology changed")
    extras = [r for r in rows if r[0].startswith(("LDIAG_", "CDIAG_", "VDIAG_"))]
    expected = [line.split() for change in changes for line in change["added"]]
    if kind == "mid_suppressed":
        expected.append(["CDIAG_SUPPRESS", node("P1", "B"), node("N1", "B"), "1u"])
    h.require(extras == expected, "Diagnostic boundary changed")


def read_table(path, names, ac=False):
    lines = path.read_text().splitlines()
    expected = [x for n in names for x in ((n, n) if ac else (n,))]
    h.require(lines[0].split()[1:] == expected, "Native vector identity/order differs")
    result = []
    for line in lines[1:]:
        values = [float(x) for x in line.split()]
        h.require(
            len(values) == len(expected) + 1 and all(math.isfinite(x) for x in values),
            "Incomplete/nonfinite native table",
        )
        result.append(
            (
                values[0],
                [complex(*values[i : i + 2]) for i in range(1, len(values), 2)]
                if ac
                else values[1:],
            )
        )
    if ac:
        h.require(
            len(result) == 289
            and result[0][0] == 1e7
            and math.isclose(result[-1][0], 4e10, rel_tol=1e-12)
            and all(a[0] < b[0] for a, b in zip(result, result[1:]))
            and all(
                math.isclose(row[0], 1e7 * 4000 ** (i / 288), rel_tol=1e-12)
                for i, row in enumerate(result)
            ),
            "AC frequency coverage changed",
        )
    else:
        h.require(len(result) == 1, "OP row census")
    return result


def op_screen(values, contract):
    rows = []
    for d in contract["hbts"]:
        vce = values[d["C"]] - values[d["E"]]
        current = abs(values[d["current"]]) / d["Nx"]
        rows.append(
            dict(
                id=d["id"],
                vce=vce,
                current_per_emitter_a=current,
                pass_bounds=0.4 <= vce <= 1.6 and current <= 0.003,
            )
        )
    h.require(len(rows) == 30, "Missing HBT DC safety census")
    return dict(
        all30_dc_bounds_pass=all(r["pass_bounds"] for r in rows),
        hbts=rows,
        scope="Static DC only; no transient, startup, all-device SOA or PVT acceptance.",
    )


def ac_measure(rows):
    data = []
    for frequency, values in rows:
        injection = values[-2] - values[-1]
        h.require(abs(injection) > 0.9, "Differential drive collapsed")
        ret = (values[0] - values[3]) / injection
        stages = []
        for j in range(3):
            z = 6 * j
            vin = injection if j == 0 else values[z] - values[z + 3]
            vout = values[z + 1] - values[z + 4]
            # Suppression control intentionally destroys the middle input.
            gain = vout / vin if abs(vin) > 1e-14 else None
            stages.append(
                dict(
                    gain=abs(gain) if gain is not None else None,
                    phase_deg=math.degrees(cmath.phase(gain))
                    if gain is not None
                    else None,
                    input_abs=abs(vin),
                    output_abs=abs(vout),
                )
            )
        data.append(
            dict(
                frequency_hz=frequency,
                real=ret.real,
                imag=ret.imag,
                gain=abs(ret),
                phase_deg=math.degrees(cmath.phase(ret)),
                stages=stages,
            )
        )
    crossings = []
    for a, b in zip(data, data[1:]):
        if a["imag"] * b["imag"] < 0:
            weight = -a["imag"] / (b["imag"] - a["imag"])
            value = a["real"] + weight * (b["real"] - a["real"])
            crossings.append(
                dict(
                    frequency_hz=a["frequency_hz"]
                    + weight * (b["frequency_hz"] - a["frequency_hz"]),
                    return_real=value,
                    positive_feedback_phase=value > 0,
                    interpolation="Linear complex-value interpolation between preserved adjacent samples",
                    endpoints=[a, b],
                )
            )
    return dict(
        samples=data,
        zero_imaginary_crossings=crossings,
        near_8GHz=min(data, key=lambda r: abs(r["frequency_hz"] - 8e9)),
        near_zero_phase=min(data, key=lambda r: abs(r["phase_deg"])),
        conditional_only=True,
    )


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    b = ROOT / "hw/soc/out/pcie-vco-v4-local-wire-20261004"
    oldroot = Path("/dev/shm/nssoc-vco-v4-local-powered-01")
    hybridroot = Path("/dev/shm/nssoc-vco-v4-local-hybrid-01")
    archivepath = b / "local-vco-v4-wire-native.tar.xz"
    h.require(
        h.pin(archivepath)["sha256"] == CAPSULE_SHA
        and h.pin(Path(p.__file__))["sha256"] == POWERED_SHA,
        "Frozen capture/producer changed",
    )
    old = json.loads((oldroot / "result.json").read_text())
    h.require(
        all(h.pin(k) == v for k, v in old["inputs"].items()),
        "Original native input changed",
    )
    comp = json.loads((hybridroot / "composition.json").read_text())
    anchors = json.loads((b / "anchors.json").read_text())
    binding = json.loads((b / "source-native-bijection.json").read_text())
    ids = {d["source_name"]: d["native_id"] for d in binding["devices"]}
    devices = {d["native_id"]: d for d in comp["records"]}
    mapping = p.physical_to_ideal(comp, anchors)
    hybrid = (hybridroot / "hybrid-open.spice").read_text()
    with tarfile.open(archivepath) as archive:
        hints = {
            c["mode"]: last_native_voltages(archive, c["mode"], c) for c in old["cases"]
        }
    ng = Path("/dev/shm/nssoc-ngspice47-20261004/root/usr/bin/ngspice")
    plan = [
        dict(mode=mode, kind=kind, vctrl=0.85)
        for mode in ("intrinsic_only", "distributed_wire")
        for kind in KINDS
    ]
    plan += [
        dict(mode="distributed_wire", kind=kind, vctrl=v)
        for v in VCTRLS
        if v != 0.85
        for kind in ("intact", "break")
    ]
    args.out.mkdir(exist_ok=False)
    result = dict(
        status="RUNNING",
        inputs={
            str(x): h.pin(x)
            for x in [
                Path(__file__),
                Path(p.__file__),
                Path(h.__file__),
                archivepath,
                oldroot / "result.json",
                b / "source-native-bijection.json",
                b / "anchors.json",
                hybridroot / "composition.json",
                hybridroot / "hybrid-open.spice",
            ]
        },
        cases=[],
        plan=plan,
        full_pex_qualified=False,
        transient_confirmation=False,
        conditional_not_multiloop_stability_proof=True,
        documentation=[
            "https://nmg.gitlab.io/ngspice-manual/analysesandoutputcontrol_batchmode/analyses/op_operatingpointanalysis.html",
            "https://nmg.gitlab.io/ngspice-manual/analysesandoutputcontrol_batchmode/analyses/ac_small-signalacanalysis.html",
        ],
        assumptions=dict(
            avdd=2.3,
            temp_c=27,
            output_each_f=50e-15,
            body_substrate_and_wire_cref="Separate external ideal0V references",
            nodesets="Actual last12ns voltages released after initialization; not clamped or forced",
            DC="Independent static equilibrium including native self-heating; not12ns operating trajectory",
        ),
    )

    def save():
        temp = args.out / "result.tmp"
        temp.write_text(json.dumps(result, indent=2) + "\n")
        temp.replace(args.out / "result.json")

    for index, case in enumerate(plan):
        mode, kind = case["mode"], case["kind"]
        root = args.out / f"{index:02d}_{mode}_{kind}_{case['vctrl']}"
        root.mkdir()

        def node(name, term):
            n = next(
                t["node"]
                for t in devices[ids[name]]["terminals"]
                if t["terminal"] == term
            )
            return mapping.get(n, n) if mode == "intrinsic_only" else n

        def expr(n):
            return "v(" + (n if n in comp["ports"] else "xbank." + n) + ")"

        original = p.circuit(comp, hybrid, mapping, mode)
        text, changes = topology(original, ids, node, kind)
        (root / "bank.spice").write_text(text)
        contract = json.loads((oldroot / mode / "contract.json").read_text())
        vectors = contract["vectors"] + (
            [expr("diag_P_base"), expr("diag_N_base")] if kind != "intact" else []
        )
        acvectors = [
            expr(node(side + str(i), term))
            for i in range(3)
            for side in ("P", "N")
            for term in ("B", "C", "E")
        ]
        if kind != "intact":
            acvectors += [expr("diag_P_base"), expr("diag_N_base")]
        init = dict(hints[mode])
        for c in changes:
            init[expr(c["new_base"]).lower()] = init[expr(c["original_base"]).lower()]
        parentbench = (oldroot / mode / "bench.cir").read_text().splitlines()
        deck = (
            ["Native static DC/conditional differential return diagnostic"]
            + [x for x in parentbench if x.startswith(".lib ")]
            + [
                '.include "bank.spice"',
                ".temp 27",
                ".options reltol=1e-4 abstol=1e-12 keepopinfo",
            ]
        )
        rails = dict(
            AVDD=2.3, VCTRL=case["vctrl"], AVSS=0, SUB=0, BODY_SUBSTRATE=0, WIRE_CREF=0
        )
        deck += [f"Vs_{n.lower()} {n} 0 DC {v}" for n, v in rails.items()] + [
            "CLOAD_CLKP CLKP 0 50f",
            "CLOAD_CLKN CLKN 0 50f",
            "XBANK " + " ".join(comp["ports"]) + " nssoc_vco_local_hybrid_open_v1",
        ]
        deck += (
            [f".nodeset {n}={v:.17g}" for n, v in init.items()]
            + [".control"]
            + [x for x in parentbench if x.startswith("pre_osdi ")]
            + ["set wr_singlescale", "set wr_vecnames", "set numdgt=16"]
        )
        deck += [
            "save " + " ".join(vectors[i : i + 40]) for i in range(0, len(vectors), 40)
        ] + ["op", "wrdata op.dat " + " ".join(vectors)]
        if kind != "intact":
            deck += [
                "ac dec 80 10MEG 40G",
                "wrdata ac.dat " + " ".join(acvectors),
                "setplot op2",
                "wrdata ac-op.dat " + " ".join(vectors),
            ]
        deck += [
            "echo NSSOC_DIFFERENTIAL_DIAGNOSTIC_COMPLETE",
            "quit",
            ".endc",
            ".end",
            "",
        ]
        (root / "bench.cir").write_text("\n".join(deck))
        (root / "spinit").write_text("* Explicit native OSDI only\n")
        row = dict(
            case,
            status="RUNNING",
            changes=changes,
            dc_vectors=vectors,
            ac_vectors=acvectors,
        )
        result["cases"].append(row)
        save()
        proc = None
        start = time.monotonic()
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("GH_TOKEN", "GITHUB_TOKEN", "PYTHONPATH", "PYTHONHOME")
        }
        env.update(SPICE_SCRIPTS=str(root), OMP_NUM_THREADS="1")
        try:
            with (root / "native.log").open("w") as log:
                proc = subprocess.Popen(
                    [str(ng), "-n", "-b", "bench.cir"],
                    cwd=root,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    preexec_fn=p.limits,
                    start_new_session=True,
                )
                while proc.poll() is None:
                    h.require(
                        p.shared_free() > 512 * 1024**2
                        and p.owned_size(args.out) < 80 * 1024**2,
                        "Resource floor",
                    )
                    time.sleep(0.25)
            h.require(proc.returncode == 0, "Native exit failed")
            log = (root / "native.log").read_text()
            h.require(
                log.count("NSSOC_DIFFERENTIAL_DIAGNOSTIC_COMPLETE") == 1,
                "Native completion missing",
            )
            h.require(
                not any(
                    t in log.lower()
                    for t in (
                        "error:",
                        "no such plot",
                        "no such vector",
                        "timestep too small",
                        "singular matrix",
                    )
                ),
                "Native API/incomplete analysis",
            )
            row["warning_lines"] = [
                x
                for x in log.splitlines()
                if any(t in x.lower() for t in ("warning", "nan", "failed"))
            ]
            row["numerical_clean"] = not row["warning_lines"]
            op = dict(zip(vectors, read_table(root / "op.dat", vectors)[0][1]))
            row["op"] = op
            row["dc_safety"] = op_screen(op, contract)
            if kind != "intact":
                acop = dict(zip(vectors, read_table(root / "ac-op.dat", vectors)[0][1]))
                row["ac_op"] = acop
                row["ac_dc_safety"] = op_screen(acop, contract)
                row["conditional_return"] = ac_measure(
                    read_table(root / "ac.dat", acvectors, True)
                )
            row["status"] = "COMPLETE_DIAGNOSTIC_NOT_ACCEPTANCE"
        except Exception as e:
            row.update(status="FAIL_PRESERVED", error=type(e).__name__ + ": " + str(e))
        finally:
            if proc:
                p.stop_owned(proc)
            row.update(
                returncode=proc.returncode if proc else None,
                seconds=time.monotonic() - start,
                outputs={q.name: h.pin(q) for q in root.iterdir() if q.is_file()},
            )
            save()
        print(index, mode, kind, case["vctrl"], row["status"], flush=True)
        if row["status"] == "FAIL_PRESERVED":
            break
    h.require(
        all(h.pin(k) == v for k, v in result["inputs"].items()),
        "Frozen diagnosis input changed",
    )
    result["status"] = (
        "COMPLETE_DIAGNOSTIC_WITH_EXPLICIT_NUMERICAL_DISPOSITIONS"
        if len(result["cases"]) == len(plan)
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
