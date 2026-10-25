#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native divider v8 cap v1: unchanged strict native circuit and fault checks."""

import argparse
import ast
import os
import resource
import shutil
import signal
import subprocess
import threading
import time
from collections import Counter
from decimal import Decimal
import json
from pathlib import Path
import re

from check_ihp_drc import digest, record_result
from check_pcie_analog_bank import extracted_ports, quote, validate_lef
from make_pcie_clock_div4_v8_cap_v1 import (
    SOURCES,
    PORTS,
    TOP,
    physical_reference,
    use_direction,
    devices,
    TAPS,
)
from prepare_ihp_drc import validate_lock, verify

LIFECYCLE_SOURCE = "scripts/characterize_pcie_clock_trim_stream_v2.py"
LIFECYCLE_SHA = "39312e364fa2a788784d88f3a63845f64db25bb420e2ee5d58c07a8c805bc886"
SCRATCH_LIMIT = 80 * 1024**2
SHARED_FLOOR = 512 * 1024**2
ENTRY_FREE = 1024**3
LAUNCH_RESERVATION = 24 * 1024**2
SCRATCH_ROOTS = ()
CPU = 10


def require(value, reason):
    if not value:
        raise ValueError(reason)


def atomic(path, record):
    path = Path(path)
    temporary = path.with_name(path.name + ".tmp")
    with temporary.open("w") as stream:
        json.dump(record, stream, indent=2)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def lifecycle():
    # Import only the four exact tested lifecycle definitions, not simulation
    # producers and not their mutable shared module globals.
    root = Path(__file__).resolve().parents[3]
    source = root / LIFECYCLE_SOURCE
    require(digest(source) == LIFECYCLE_SHA, "Frozen process lifecycle")
    names = {"Cancelled", "process_identity", "group_members", "ProcessOwner"}
    selected = [
        node
        for node in ast.parse(source.read_text()).body
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names
    ]
    require(len(selected) == 4, "Exact lifecycle definitions")
    namespace = dict(
        os=os,
        Path=Path,
        threading=threading,
        signal=signal,
        subprocess=subprocess,
        time=time,
        atomic=atomic,
        require=require,
        FAILURE_GRACE_SECONDS=5.0,
    )
    exec(
        compile(ast.Module(body=selected, type_ignores=[]), str(source), "exec"),
        namespace,
    )
    return namespace


def limits():
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    resource.setrlimit(resource.RLIMIT_AS, (2 * 1024**3,) * 2)
    os.sched_setaffinity(0, {CPU})


def scratch_bytes():
    return sum(
        p.stat().st_size
        for root in SCRATCH_ROOTS
        if Path(root).exists()
        for p in Path(root).rglob("*")
        if p.is_file()
    )


def guard_resources():
    require(
        shutil.disk_usage("/dev/shm").free >= SHARED_FLOOR,
        "512MiB continuous shared scratch floor",
    )
    require(scratch_bytes() <= SCRATCH_LIMIT, "80MiB own scratch ceiling")


def execute(command, directory, label):
    require(
        sorted(os.sched_getaffinity(0)) == [CPU], "Owned physical work assigned CPU"
    )
    require(shutil.disk_usage("/dev/shm").free >= ENTRY_FREE, "1GiB shared entry floor")
    require(
        scratch_bytes() + LAUNCH_RESERVATION <= SCRATCH_LIMIT,
        "80MiB own scratch with24MiB launch reserve",
    )
    environment = {
        k: v
        for k, v in os.environ.items()
        if k not in ("GH_TOKEN", "GITHUB_TOKEN", "PYTHONPATH", "PYTHONHOME")
    }
    start = time.monotonic()
    ns = lifecycle()
    owner_path = directory / (label + ".owned.json")
    require(not owner_path.exists(), "Fresh owned process receipt")
    with ns["ProcessOwner"](owner_path) as owner:
        with (directory / (label + ".log")).open("x") as log:
            process = owner.launch(
                "native",
                list(map(str, command)),
                stdout=log,
                stderr=subprocess.STDOUT,
                env=environment,
                preexec_fn=limits,
            )
            while process.poll() is None:
                owner.check()
                guard_resources()
                owner.cancelled.wait(0.25)
            owner.check()
            code = owner.complete(process)
            owner.check()
            guard_resources()
    # A stop raised inside complete/save/__exit__ must not be discarded when
    # the lifecycle context restores signal handlers. Likewise a fast child
    # must pass resource guards after its final bytes and owner receipt exist.
    owner.check()
    guard_resources()
    return dict(
        command=list(map(str, command)),
        returncode=code,
        seconds=time.monotonic() - start,
        memory_limit_bytes=2 * 1024**3,
        elapsed_watchdog=None,
        log_sha256=digest(directory / (label + ".log")),
        lifecycle_source_sha256=LIFECYCLE_SHA,
        process_owner_sha256=digest(owner_path),
    )


APP_SHA = "d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466"
REFERENCE_FAULTS = (
    "limiter_load",
    "feedback",
    "limiter_nx",
    "feedforward_mim",
    "seed_asymmetry",
    "missing_tap",
    "supply_swap",
    "conditioner_pullup",
)
PHYSICAL_FAULTS = (
    "clock_open",
    "output_short",
    "rails_short",
    "feedback_open",
    "row_trunk_open",
    "row_trunk_short",
)


def fault_reference(text, fault):
    changes = {
        "limiter_load": (
            "RDIV__XLRP DIV_AVDD DIV__LP BULK rppd w=8u l=4.4u",
            "RDIV__XLRP DIV_AVDD DIV__LP BULK rppd w=8u l=4u",
        ),
        "feedback": (
            "QDIV__XSECOND__XM__XDP DIV__XSECOND__MN QN",
            "QDIV__XSECOND__XM__XDP DIV__XSECOND__MN QP",
        ),
        "limiter_nx": (
            "QDIV__XLP DIV__LN DIV__BIP DIV__LT BULK npn13G2 Nx=2",
            "QDIV__XLP DIV__LN DIV__BIP DIV__LT BULK npn13G2 Nx=1",
        ),
        "feedforward_mim": (
            "CDIV__XCP DIV__LP DIV__CKP cap_cmim w=20u",
            "CDIV__XCP DIV__LP DIV__CKP cap_cmim w=18u",
        ),
        "seed_asymmetry": (
            "CDIV__XSECOND__XSEEDP DIV__XSECOND__MP AVSS cap_cmim w=2.2u",
            "CDIV__XSECOND__XSEEDP DIV__XSECOND__MP AVSS cap_cmim w=2u",
        ),
        "missing_tap": ("RTAP0 SUB BULK ptap1 A=4p P=8u\n", ""),
        "supply_swap": (
            "RDIV__XSECOND__XBIAS DIV_AVDD",
            "RDIV__XSECOND__XBIAS AVSS",
        ),
        "conditioner_pullup": (
            "RDIV__XFIRST__XUP DIV_AVDD DIV__XFIRST__CKP BULK rppd w=1u l=4u",
            "RDIV__XFIRST__XUP DIV_AVDD DIV__XFIRST__CKP BULK rppd w=1u l=6.4u",
        ),
    }
    if fault not in changes:
        raise ValueError("Unknown exact reference fault")
    a, b = changes[fault]
    if text.count(a) != 1:
        raise ValueError("Fault must bind exactly once: " + fault)
    return text.replace(a, b)


def mutation_source(gds, output, generated, fault):
    lines = [
        "import pya",
        "l=pya.Layout()",
        "l.read(" + repr(str(gds)) + ")",
        "c=l.cell(" + repr(TOP) + ")",
    ]
    if fault == "offgrid":
        lines += ["c.shapes(l.layer(8,0)).insert(pya.DBox(2.002,2,2.102,2.1))"]
    elif fault in ("row_trunk_open", "row_trunk_short"):
        p = generated["peripheral_trunks"]["DIV__S1P"]
        n = generated["peripheral_trunks"]["DIV__S1N"]
        lower = max(p["lower_y_um"], n["lower_y_um"])
        upper = min(p["upper_y_um"], n["upper_y_um"])
        if upper - lower < 10:
            raise ValueError("Actual cross-row differential clock trunks required")
        dx, dy = generated["origin_translation_um"]
        y = round((lower + upper) / 2 / 0.005) * 0.005 + dy
        x = p["x_um"] + dx
        if fault == "row_trunk_open":
            lines += [
                "region=pya.Region(c.shapes(l.layer(50,0)))",
                f"region-=pya.Region(pya.DBox({x - 0.8!r},{y - 0.1!r},{x + 0.8!r},{y + 0.1!r}).to_itype(l.dbu))",
                "c.shapes(l.layer(50,0)).clear()",
                "c.shapes(l.layer(50,0)).insert(region)",
            ]
        else:
            xn = n["x_um"] + dx
            lines += [
                f"c.shapes(l.layer(50,0)).insert(pya.DBox({min(x, xn) - 0.1!r},{y - 0.3!r},{max(x, xn) + 0.1!r},{y + 0.3!r}))"
            ]
    elif fault == "feedback_open":
        rows = [
            r
            for r in generated["routes"]
            if r.get("device") == "DIV__XSECOND__XM__XDP" and r.get("net") == "QN"
        ]
        if len(rows) != 1:
            raise ValueError("Exact toggle feedback route required")
        r = rows[0]
        coords = [float(v) for v in re.findall(r"-?\d+(?:\.\d+)?", r["actual_pin_um"])]
        if len(coords) != 4:
            raise ValueError("Native contact rectangle required")
        x = (
            round(((coords[0] + coords[2]) / 2 + r["escape_lane_um"]) / 2 / 0.005)
            * 0.005
        )
        dx, dy = generated["origin_translation_um"]
        x += dx
        y = r["escape_y_um"] + dy
        lines += [
            "region=pya.Region(c.shapes(l.layer(30,0)))",
            f"region-=pya.Region(pya.DBox({x - 0.1!r},{y - 0.3!r},{x + 0.1!r},{y + 0.3!r}).to_itype(l.dbu))",
            "c.shapes(l.layer(30,0)).clear()",
            "c.shapes(l.layer(30,0)).insert(region)",
        ]
    elif fault == "clock_open":
        b = generated["ports"]["CLKP"]["rect_um"]
        y = (b[1] + b[3]) / 2
        edge = generated["bbox_um"][2]
        if b[2] != edge or b[0] != edge - 2:
            raise ValueError("Exact right-edge clock input required")
        lines += [
            "region=pya.Region(c.shapes(l.layer(67,0)))",
            f"region-=pya.Region(pya.DBox({edge - 4!r},{y - 2!r},{edge - 3!r},{y + 2!r}).to_itype(l.dbu))",
            "c.shapes(l.layer(67,0)).clear()",
            "c.shapes(l.layer(67,0)).insert(region)",
        ]
    elif fault in ("output_short", "rails_short"):
        names = ("QP", "QN") if fault == "output_short" else ("DIV_AVDD", "AVSS")
        ys = [
            sum(generated["ports"][n]["rect_um"][k] for k in (1, 3)) / 2 for n in names
        ]
        x = sum(generated["ports"][names[0]]["rect_um"][k] for k in (0, 2)) / 2
        lines += [
            f"c.shapes(l.layer(67,0)).insert(pya.DBox({x - 0.5!r},{min(ys)!r},{x + 0.5!r},{max(ys)!r}))"
        ]
    else:
        raise ValueError("Unknown exact physical fault")
    return "\n".join(lines + ["l.write(" + repr(str(output)) + ")", ""])


def validate_expanded_devices(text):
    records = []
    for line in text.splitlines():
        if line.startswith("+"):
            records[-1] += " " + line[1:]
        elif line.strip() and not line.startswith("*"):
            records.append(line)
    rows = [r.split() for r in records if not r.startswith(".")]
    hbts = [r for r in rows if r[0].startswith("Q")]
    expanded = []
    for row in hbts:
        if len(row) != 10 or row[5] != "npn13G2":
            raise ValueError("Native HBT syntax")
        p = dict(v.split("=") for v in row[6:])
        if set(p) != {"we", "le", "Nx", "m"} or p["we"] != "70n" or p["le"] != "900n":
            raise ValueError("Native HBT geometry")
        nx, mult = int(p["Nx"]), int(p["m"])
        if nx not in (1, 2, 4) or mult != 1:
            raise ValueError("No merged or multiplied divider HBT permitted")
        expanded.append(nx)
    expected = [
        r["nx"]
        for r in devices(Path(__file__).resolve().parents[3])
        if r["kind"] == "hbt"
    ]
    if len(hbts) != 34 or Counter(expanded) != Counter(expected):
        raise ValueError("Exact 34 HBT census")
    if len(rows) != 74:
        raise ValueError("Exact 73 primitives plus one parallel finite tap class")
    for model, count, index, allowed in [
        ("rppd", 33, 4, {"w", "l", "ps", "b", "m"}),
        ("cap_cmim", 6, 3, {"w", "l", "A", "P", "m"}),
    ]:
        selected = [row for row in rows if len(row) > index and row[index] == model]
        if len(selected) != count:
            raise ValueError("Exact native " + model + " census")
        measured_geometry = []
        for row in selected:
            parts = row[index + 1 :]
            p = dict(value.split("=") for value in parts)
            if len(parts) != len(p):
                raise ValueError("Duplicate extracted passive field")
            if (
                set(p) != allowed
                or p["m"] != "1"
                or (model == "rppd" and (p["b"] != "0" or p["ps"] != "0u"))
            ):
                raise ValueError("Exact unmultiplied straight native passive device")

            def quantity(value, suffix):
                if not re.fullmatch(r"[0-9]+(?:\.[0-9]+)?" + suffix, value):
                    raise ValueError(
                        "Exact native positive geometry with declared unit"
                    )
                result = Decimal(value[:-1])
                if result <= 0:
                    raise ValueError("Positive finite native passive geometry")
                return result

            w, length = quantity(p["w"], "u"), quantity(p["l"], "u")
            measured_geometry.append((w, length))
            if model == "cap_cmim" and (
                quantity(p["A"], "p") != w * length
                or quantity(p["P"], "u") != 2 * (w + length)
            ):
                raise ValueError("Exact native MIM area and perimeter from actual W/L")
        kind = "resistor" if model == "rppd" else "capacitor"
        expected_geometry = [
            (Decimal(str(r["width_um"])), Decimal(str(r["length_um"])))
            for r in devices(Path(__file__).resolve().parents[3])
            if r["kind"] == kind
        ]
        if Counter(measured_geometry) != Counter(expected_geometry):
            raise ValueError(
                "All extracted passive W/L geometries equal frozen circuit"
            )
    taps = [r for r in rows if r[0].startswith("R") and len(r) >= 4 and r[3] == "ptap1"]
    if (
        len(taps) != 1
        or taps[0][1] != "SUB"
        or taps[0][2] in PORTS
        or taps[0][4:] != [f"A={TAPS * 4}p", f"P={TAPS * 8}u"]
    ):
        raise ValueError("Exact 18 finite substrate contacts required")


def validate_lvs(step, text, positive):
    audit = step["audit"]
    if positive:
        if (
            audit["status"] != "PASS within comparison scope"
            or step["audit_execution"]["returncode"] != 0
            or extracted_ports(text, TOP) != set(PORTS)
            or len(audit["circuits"]) != 1
            or audit["circuits"][0]["layout_devices_recursive"] != 74
            or audit["circuits"][0]["schematic_devices_recursive"] != 74
        ):
            raise ValueError("Strict standalone divider native topology/census differs")
        validate_expanded_devices(text)
    elif audit["status"] != "FAIL" or step["audit_execution"]["returncode"] != 1:
        raise ValueError("Native negative accepted")
    elif step["name"] == "clock_open":
        if extracted_ports(text, TOP) != set(PORTS) - {"CLKP"}:
            raise ValueError("Exact missing CLKP input")
    elif audit["circuit_status_counts"].get("NoMatch", 0) < 1:
        raise ValueError("Unrelated native rejection")


def lef_script(pdk, lef, generated):
    box = generated["bbox_um"]
    lines = [
        "read_lef " + quote(pdk / "libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef"),
        "read_lef " + quote(lef),
        "set master [[ord::get_db] findMaster " + TOP + "]",
        'if {$master eq "NULL"} {error "Divider master missing"}',
        f'if {{[$master getWidth] != {round(box[2] * 1000)} || [$master getHeight] != {round(box[3] * 1000)}}} {{error "Divider outline changed"}}',
        'if {[llength [$master getMTerms]] != 7} {error "Analog terminal census changed"}',
    ]
    if set(generated["ports"]) != set(PORTS):
        raise ValueError("Divider LEF pin census differs")
    for name in PORTS:
        use, direction = use_direction(name)
        coords = " ".join(
            str(round(v * 1000)) for v in generated["ports"][name]["rect_um"]
        )
        lines += [
            "set term [$master findMTerm " + name + "]",
            'if {$term eq "NULL"} {error "Divider terminal missing"}',
            'if {[$term getIoType] ne "'
            + direction
            + '" || [$term getSigType] ne "'
            + use
            + '"} {error "Divider terminal type differs"}',
            "set boxes {}; foreach pin [$term getMPins] {foreach box [$pin getGeometry] {lappend boxes [list [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]]}}",
            "if {$boxes ne {{Metal5 "
            + coords
            + '}}} {error "Divider terminal geometry differs"}',
        ]
    lines += [
        "set obs {}; foreach box [$master getObstructions] {lappend obs [[$box getTechLayer] getName]}",
        'if {[lsort -unique $obs] ne {Metal1 Metal2 Metal3 Metal4 Metal5 TopMetal1 TopMetal2}} {error "Divider blockage layer census changed"}',
        "foreach term [$master getMTerms] {foreach pin [$term getMPins] {foreach pb [$pin getGeometry] {foreach ob [$master getObstructions] {",
        'if {[[$pb getTechLayer] getName] eq [[$ob getTechLayer] getName] && [$pb xMin] < [$ob xMax] && [$ob xMin] < [$pb xMax] && [$pb yMin] < [$ob yMax] && [$ob yMin] < [$pb yMax]} {error "Divider pin obstruction overlap"}',
        "}}}}",
        "puts PASS_NATIVE_ANALOG_BANK_LEF_ONLY",
    ]
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("layout", "pdk", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument(
        "--generate",
        action="store_true",
        help="Generate a fresh standalone layout in an owned native process first",
    )
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    out, layout, pdk = args.out.resolve(), args.layout.resolve(), args.pdk.resolve()
    if out.exists() or not (
        out.is_relative_to(root / "hw/soc/out")
        or out.is_relative_to(Path("/dev/shm"))
        and out.name.startswith("nssoc-div4-")
    ):
        parser.error("Fresh project or /dev/shm/nssoc-div4- directory required")
    require(
        not (layout == out or out.is_relative_to(layout) or layout.is_relative_to(out)),
        "Separate non-overlapping physical directories",
    )
    global SCRATCH_ROOTS
    SCRATCH_ROOTS = (out, layout)
    app = root / "hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage"
    if digest(app) != APP_SHA or any(digest(root / p) != h for p, h in SOURCES.items()):
        raise ValueError("Divider circuit or native runtime changed")
    require(digest(root / LIFECYCLE_SOURCE) == LIFECYCLE_SHA, "Frozen lifecycle source")
    generation = None
    if args.generate:
        require(not layout.exists(), "Fresh standalone generation directory")
        # The generator independently restricts --out, pins all native PCell
        # and source inputs, and keeps prior geometry unchanged.
        out.mkdir(parents=True)
        generation = execute(
            [
                app,
                "python",
                root / "hw/soc/flow/make_pcie_clock_div4_v8_cap_v1.py",
                "--pdk",
                pdk,
                "--out",
                layout,
            ],
            out,
            "generation",
        )
        require(generation["returncode"] == 0, "Native generation completed")
    generated = json.loads((layout / "result.json").read_text())
    gds, schematic = layout / (TOP + ".gds"), layout / "schematic.cir"
    if schematic.read_text() != physical_reference(root):
        raise ValueError("Physical reference differs from frozen Divider")
    pins = {Path(k): v for k, v in generated["input_sha256"].items()}
    for name, expected in generated["output_sha256"].items():
        if digest(layout / name) != expected:
            raise ValueError("Generated physical view changed")
        pins[layout / name] = expected
    methods = [
        "check_pcie_clock_div4_v7.py",
        "check_pcie_clock_div4_v7_v2.py",
        "make_pcie_clock_div4_v7.py",
        "make_pcie_clock_div4_v8_cap_v1.py",
        "check_pcie_clock_div4_v7_power_v2.py",
        "check_pcie_clock_div4_v8_cap_v1.py",
        "audit_pcie_clock_div4_v8_cap_v1.py",
        "audit_pcie_clock_div4_v7_power_v3.py",
        "check_pcie_rx_cell.py",  # Indirect import through check_pcie_analog_bank.
        "check_pcie_analog_bank.py",
        "make_pcie_analog_bank.py",
        "make_pcie_rx_cell.py",
        "make_pcie_rx_cell_v2.py",
        "check_ihp_drc.py",
        "prepare_ihp_drc.py",
        "audit_klayout_lvs.py",
    ]
    for path in [
        app,
        root / LIFECYCLE_SOURCE,
        layout / "result.json",
        Path("/dev/shm/nssoc-div4-v7-compact-v2-layout-01/nssoc_clock_div4_v7_compact_v2_layout.gds"),
        Path("/dev/shm/nssoc-div4-v7-compact-v2-layout-01/result.json"),
        pdk / "libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef",
        *(root / "hw/soc/flow" / name for name in methods),
    ]:
        pins[path] = digest(path)
    for typ in ("drc", "lvs"):
        path = root / f"hw/soc/pnr/ihp-{typ}.lock.json"
        lock = json.loads(path.read_text())
        validate_lock(lock)
        if lock["commit"] != "5e6d592e4002946a4616f798c357f0f3c06cf3b6":
            raise ValueError("Native deck revision changed")
        pins[path] = digest(path)
        for row in lock["files"]:
            path = root / f"hw/soc/tools/ihp-{typ}-5e6d592" / row["path"]
            verify(path.read_bytes(), row)
            pins[path] = row["sha256"]
    if any(not p.is_file() or digest(p) != h for p, h in pins.items()):
        raise ValueError("Physical source changed before validation")
    out.mkdir(parents=True, exist_ok=args.generate)
    record = dict(
        status="RUNNING",
        inputs={str(p): h for p, h in pins.items()},
        generation_execution=generation,
        resource_contract=dict(
            cpu=10,
            child_address_space=2 * 1024**3,
            own_scratch=SCRATCH_LIMIT,
            shared_floor=SHARED_FLOOR,
            entry_free=ENTRY_FREE,
            launch_reservation=LAUNCH_RESERVATION,
            healthy_elapsed_watchdog=None,
            failure_grace_seconds=5.0,
        ),
        steps=[],
        phy_complete=False,
        qualified_pex=False,
        manufacturing_approval=False,
        scope="Actual standalone divider v8 cap v1 connectivity and main-rule screen only; no extracted division, qualified RC, PLL or chip integration acceptance.",
    )

    def save():
        (out / "result.json").write_text(json.dumps(record, indent=2) + "\n")

    try:
        save()
        geometry = out / "power-geometry.json"
        record["power_geometry_execution"] = execute(
            [
                app,
                "python",
                root / "hw/soc/flow/audit_pcie_clock_div4_v8_cap_v1.py",
                "--baseline",
                "/dev/shm/nssoc-div4-v7-compact-v2-layout-01",
                "--pdk",
                pdk,
                "--layout",
                layout,
                "--out",
                geometry,
            ],
            out,
            "power-geometry",
        )
        require(
            record["power_geometry_execution"]["returncode"] == 0,
            "Actual two-cap geometry delta and all remaining intrinsic geometry verified",
        )
        record["power_geometry_audit"] = json.loads(geometry.read_text())
        require(
            record["power_geometry_audit"]["status"]
            == "PASS_ACTUAL_CAP24_TWO_MIM_DELTA_POWER_AND_SIX_GEOMETRY_CONTROLS",
            "Exact real geometry comparison and negative controls",
        )
        save()
        for name in (
            "drc",
            "offgrid",
            "lvs",
            "lvs_flat",
            *REFERENCE_FAULTS,
            *PHYSICAL_FAULTS,
        ):
            directory = out / name
            directory.mkdir()
            step = dict(name=name)
            record["steps"].append(step)
            save()
            physical, reference = gds, schematic
            if name == "offgrid" or name in PHYSICAL_FAULTS:
                physical = directory / "wrong.gds"
                script = directory / "mutate.py"
                script.write_text(mutation_source(gds, physical, generated, name))
                step["mutation_execution"] = execute(
                    [app, "python", script], directory, "mutation"
                )
                if step["mutation_execution"]["returncode"] != 0 or digest(
                    physical
                ) == digest(gds):
                    raise ValueError("Physical fault did not bind")
            if name in REFERENCE_FAULTS:
                reference = directory / "wrong.cir"
                reference.write_text(fault_reference(schematic.read_text(), name))
            drc = name in ("drc", "offgrid")
            entry = root / (
                "hw/soc/tools/ihp-drc-5e6d592/ihp-sg13g2/libs.tech/klayout/tech/drc/ihp-sg13g2.drc"
                if drc
                else "hw/soc/tools/ihp-lvs-5e6d592/ihp-sg13g2/libs.tech/klayout/tech/lvs/sg13g2.lvs"
            )
            options = [
                "input=" + str(physical),
                "topcell=" + TOP,
                "log=" + str(directory / "deck.log"),
                "run_mode=flat" if name == "lvs_flat" else "run_mode=deep",
            ]
            options += (
                [
                    "report=" + str(directory / "drc.lyrdb"),
                    "threads=2",
                    "no_recommended=False",
                    "precheck_drc=False",
                ]
                if drc
                else [
                    "schematic=" + str(reference),
                    "report=" + str(directory / "result.lvsdb"),
                    "target_netlist=" + str(directory / "extracted.cir"),
                    "thr=2",
                ]
            )
            command = [app, "klayout", "-b", "-zz", "-r", entry]
            for option in options:
                command += ["-rd", option]
            step["execution"] = execute(command, directory, "run")
            if step["execution"]["returncode"] != 0:
                raise ValueError("Native deck did not complete")
            if drc:
                measurement = record_result(directory, TOP, 0, pins)
                step["measurement"], step["status"] = measurement, measurement["status"]
                if (
                    measurement["category_count"] != 560
                    or "KLayout DRC run for tables 'main' completed"
                    not in (directory / "run.log").read_text()
                ):
                    raise ValueError("Native main rule census incomplete")
                if name == "drc" and measurement["status"] != "PASS":
                    raise ValueError("Divider main DRC failed")
                if name == "offgrid" and (
                    measurement["status"] != "FAIL"
                    or measurement["categories"].get("metal1_drw_Offgrid", 0) < 1
                ):
                    raise ValueError("Physical DRC fault was accepted")
            else:
                step["audit_execution"] = execute(
                    [
                        app,
                        "python",
                        root / "hw/soc/flow/audit_klayout_lvs.py",
                        directory / "result.lvsdb",
                        "--top",
                        TOP,
                        "--deck-log",
                        directory / "deck.log",
                        "--output",
                        directory / "audit.json",
                    ],
                    directory,
                    "audit",
                )
                step["audit"] = json.loads((directory / "audit.json").read_text())
                step["status"] = step["audit"]["status"]
                validate_lvs(
                    step,
                    (directory / "extracted.cir").read_text(),
                    name in ("lvs", "lvs_flat"),
                )
            save()
            print(name, step["status"], flush=True)
        for negative in (None, "missing_pin", "blocked_pin"):
            directory = out / ("lef_" + negative if negative else "lef")
            directory.mkdir()
            view = layout / (TOP + ".lef")
            if negative == "missing_pin":
                text, count = re.subn(
                    r"  PIN CLKP\n.*?  END CLKP\n", "", view.read_text(), flags=re.S
                )
                if count != 1:
                    raise ValueError("LEF fault did not bind")
                view = directory / "wrong.lef"
                view.write_text(text)
            if negative == "blocked_pin":
                pin = generated["ports"]["CLKP"]["rect_um"]
                obstruction = (
                    "      RECT " + " ".join(f"{value:.3f}" for value in pin) + " ;\n"
                )
                text = view.read_text()
                if text.count("  OBS\n") != 1:
                    raise ValueError("LEF obstruction insertion did not bind")
                text = text.replace(
                    "  OBS\n", "  OBS\n    LAYER Metal5 ;\n" + obstruction, 1
                )
                view = directory / "wrong.lef"
                view.write_text(text)
            script = directory / "inspect.tcl"
            script.write_text(lef_script(pdk, view, generated))
            execution = execute([app, "openroad", "-exit", script], directory, "native")
            log = (directory / "native.log").read_text()
            if negative == "blocked_pin":
                if (
                    execution["returncode"] == 0
                    or "PASS_NATIVE_ANALOG_BANK_LEF_ONLY" in log
                    or len(
                        re.findall(
                            r"^Error: inspect\.tcl, \d+ Divider pin obstruction overlap$",
                            log,
                            re.M,
                        )
                    )
                    != 1
                ):
                    raise ValueError(
                        "Blocked clock-pin LEF negative failed incorrectly"
                    )
            else:
                validate_lef(execution["returncode"], log, bool(negative))
            record["steps"].append(
                dict(
                    name=directory.name,
                    execution=execution,
                    status="EXPECTED_REJECTION" if negative else "PASS",
                )
            )
            save()
        if any(digest(p) != h for p, h in pins.items()):
            raise ValueError("Physical inputs changed during native validation")
        record["status"] = (
            "PASS_DIV4_V8_CAP_V1_STANDALONE_MAIN_DRC_STRICT_DEEP_FLAT_LVS_LEF_NEGATIVE_CONTROLS_ONLY"
        )
        record["outputs"] = {
            str(p.relative_to(out)): digest(p)
            for p in sorted(out.rglob("*"))
            if p.is_file() and p != out / "result.json"
        }
        save()
    except BaseException as error:
        record.update(status="FAILED_OR_INCOMPLETE", error=repr(error))
        save()
        raise


if __name__ == "__main__":
    main()
