#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native full retimed CDR PD484 DRC/LVS and actual reference/geometry fault controls."""

import argparse
import json
from pathlib import Path
import sys, re

sys.path.insert(0, str(Path.cwd() / "hw/soc/flow"))

from check_ihp_drc import digest, record_result
from prepare_ihp_drc import validate_lock, verify
from check_pcie_rx_cell import execute
from check_pcie_analog_bank import extracted_ports

TOP = "nssoc_cdr_pd484_input_drive_v10"
sys.path.insert(0,str(Path.cwd()/"scripts"))
from cdr_retimed_input_drive_v10_parent_plan import build
PORTS = build()["ports"]

APP_SHA = "d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466"


def reference_fault(text, name):
    if name in ('old_sampler_input_width','old_retime_width','old_retime_mim'):
        lines=text.splitlines(keepends=True);hits=[]
        targets={f'R{tag}_{pin}' for tag in ('sa','sb','sc','sd') for pin in ('IP','IN','BP','BN')}
        for i,line in enumerate(lines):
            f=line.split()
            if not f:continue
            hit=(name=='old_sampler_input_width' and f[0]in targets) or (name=='old_retime_width' and f[0].startswith(('Rac_','Rbd_')) and 'rppd'in f) or (name=='old_retime_mim' and f[0].startswith(('Cac_','Cbd_')) and 'cap_cmim'in f)
            if not hit:continue
            before,after=(' w=7.2u l=7.2u ',' w=3.6u l=3.6u ')if name=='old_retime_mim'else(' w=4u ',' w=1u ')
            assert line.count(before)==1
            lines[i]=line.replace(before,after);hits.append(i)
        assert len(hits)=={'old_sampler_input_width':16,'old_retime_width':8,'old_retime_mim':4}[name]
        return ''.join(lines)
    if name=='old_data_header_length':
        lines=text.splitlines(keepends=True)
        hits=[i for i,l in enumerate(lines)if l.split()and l.split()[0]in ('Rda_D4','Rdc_D4')]
        assert len(hits)==2
        for i in hits:
            assert ' rppd w=8u l=2.4u ' in lines[i]
            lines[i]=lines[i].replace(' l=2.4u ',' l=2u ')
        return ''.join(lines)
    lines=text.splitlines(keepends=True);hits=[i for i,l in enumerate(lines)if l.startswith('Q')]
    assert len(hits)==116
    i=hits[0]if name=='wrong_finger_count'else hits[1]
    if name=='wrong_finger_count':
        match=re.search(r'Nx=(\d+)',lines[i]);assert match
        lines[i]=lines[i][:match.start()]+"Nx="+str(int(match.group(1))+1)+lines[i][match.end():]
    elif name=='missing_hbt':lines[i]=''
    else:raise ValueError(name)
    return ''.join(lines)


def geometry_script(gds, target, fault):
    data = json.loads((gds.parent / "result.json").read_text())
    ports = {
        n: list(map(float, re.findall(r"-?\d+(?:\.\d+)?", v)))
        for n, v in data["ports"].items()
    }
    assert all(len(v) == 4 for v in ports.values())
    ys = {n: (v[1] + v[3]) / 2 for n, v in ports.items()}
    return f"""import pya
L=pya.Layout();L.read({str(gds)!r});top=L.cell({TOP!r});assert top is not None
fault={fault!r};ys={ys!r}
if fault=='offgrid':top.transform(pya.Trans(1,0))
elif fault=='q_open':
    li=L.layer(134,0);before=pya.Region(top.shapes(li));y=ys['vip'];cut=pya.Region(pya.DBox(5,y-2.2,7,y+2.2).to_itype(L.dbu));after=before-cut;assert before.area()!=after.area();top.shapes(li).clear();top.shapes(li).insert(after)
elif fault=='rail_short':
    top.shapes(L.layer(134,0)).insert(pya.DBox(2.5,min(ys['avdd'],ys['avss'])-.7,3,max(ys['avdd'],ys['avss'])+.7))
else:raise ValueError(fault)
L.write({str(target)!r})
"""


def run(layout, out, app):
    root = Path.cwd()
    layout, out, app = layout.resolve(), out.resolve(), app.resolve()
    if out.exists() or not out.is_relative_to(root / "hw/soc/out"):
        raise ValueError("Use a fresh project output directory")
    if digest(app) != APP_SHA:
        raise ValueError("Native tool archive changed")
    generated = json.loads((layout / "result.json").read_text())
    pins = {Path(p): h for p, h in generated["inputs"].items()}
    pins.update({layout / name: h for name, h in generated["outputs"].items()})
    methods = [
        "make_pcie_sampler_cell.py",
        "check_ihp_drc.py",
        "prepare_ihp_drc.py",
        "check_pcie_rx_cell.py",
        "audit_klayout_lvs.py",
        "check_pcie_analog_bank.py",
    ]
    pins.update({p:digest(p)for p in [root/"scripts/generate_cdr_retimed_input_drive_v10_parent.py",root/"scripts/cdr_retimed_input_drive_v10_parent_plan.py"]})
    pins.update(
        {
            p: digest(p)
            for p in [
                app,
                Path(__file__).resolve(),
                layout / "result.json",
                *[root / "hw/soc/flow" / n for n in methods],
            ]
        }
    )
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
    if any(digest(p) != h for p, h in pins.items()):
        raise ValueError("Layout source changed")
    out.mkdir()
    record = dict(
        status="RUNNING",
        inputs={str(p): h for p, h in pins.items()},
        steps={},
        serial_phy_complete=False,
        main_chip_integrated=False,
        qualified_pex=False,
    )

    def save():
        (out / "result.json").write_text(json.dumps(record, indent=2) + "\n")

    save()
    try:
        for name in (
            "drc",
            "lvs",
            "lvs_flat",
            "old_sampler_input_width",
            "old_retime_width",
            "old_retime_mim",
            "old_data_header_length",
            "wrong_finger_count",
            "missing_hbt",
            "q_open",
            "rail_short",
            "offgrid",
        ):
            directory = out / name
            directory.mkdir()
            gds, schematic = layout / (TOP + ".gds"), layout / "schematic.cir"
            step = {}
            record["steps"][name] = step
            if name in ("old_sampler_input_width", "old_retime_width", "old_retime_mim", "old_data_header_length", "wrong_finger_count", "missing_hbt"):
                target = directory / "fault.cir"
                target.write_text(reference_fault(schematic.read_text(), name))
                schematic = target
            if name in ("q_open", "rail_short", "offgrid"):
                target = directory / "fault.gds"
                script = directory / "fault.py"
                script.write_text(geometry_script(gds, target, name))
                step["mutation"] = execute(
                    [app, "python", script], directory, "mutation"
                )
                if step["mutation"]["returncode"] != 0 or digest(gds) == digest(target):
                    raise ValueError("Physical fault did not execute")
                gds = target
            drc = name in ("drc", "offgrid")
            typ = "drc" if drc else "lvs"
            suffix = "drc/ihp-sg13g2.drc" if drc else "lvs/sg13g2.lvs"
            entry = (
                root
                / f"hw/soc/tools/ihp-{typ}-5e6d592/ihp-sg13g2/libs.tech/klayout/tech"
                / suffix
            )
            options = [
                "input=" + str(gds),
                "topcell=" + TOP,
                "log=" + str(directory / "deck.log"),
                "run_mode=" + ("flat" if name == "lvs_flat" else "deep"),
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
                    "schematic=" + str(schematic),
                    "report=" + str(directory / "result.lvsdb"),
                    "target_netlist=" + str(directory / "extracted.cir"),
                    "thr=2",
                    "no_simplify=true",
                    "top_lvl_pins=true",
                ]
            )
            command = [app, "klayout", "-b", "-zz", "-r", entry]
            for option in options:
                command += ["-rd", option]
            step["execution"] = execute(command, directory, "run")
            if step["execution"]["returncode"] != 0:
                raise ValueError("Native deck did not complete")
            if drc:
                result = record_result(directory, TOP, 0, pins)
                step["measurement"] = result
                expected = "PASS" if name == "drc" else "FAIL"
                if result["status"] != expected or result["category_count"] != 560:
                    raise ValueError("DRC verdict or rule coverage differs")
                if name == "offgrid" and not any(
                    "metal1_drw_Offgrid" in c for c in result["categories"]
                ):
                    raise ValueError("Offgrid fault rejected for wrong reason")
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
                result = json.loads((directory / "audit.json").read_text())
                step["audit"] = result
                positive = name in ("lvs", "lvs_flat")
                if positive:
                    if (
                        result["status"] != "PASS within comparison scope"
                        or step["audit_execution"]["returncode"] != 0
                        or result["extraction_diagnostics"]
                        or result["circuit_status_counts"] != {"Match": 1}
                    ):
                        raise ValueError("Strict transistor comparison failed")
                    if len(result["circuits"]) != 1 or any(
                        result["circuits"][0][key] != 484
                        for key in (
                            "layout_devices_recursive",
                            "schematic_devices_recursive",
                        )
                    ):
                        raise ValueError("Physical device census differs")
                    from collections import Counter
                    census=Counter()
                    for line in (directory / "extracted.cir").read_text().lower().splitlines():
                        f=line.split()
                        if not f or f[0][0] not in "qmr c".replace(" ", ""):
                            continue
                        models=[m for m in ("npn13g2","sg13_lv_nmos","rppd","cap_cmim","ptap1") if m in f]
                        assert len(models)==1, ("Unexpected extracted primitive",line)
                        census[models[0]]+=1
                    assert dict(census)==build()["primitive_census"], census
                    step["native_primitive_census"]=dict(census)
                    if extracted_ports(
                        (directory / "extracted.cir").read_text(), TOP
                    ) != set(PORTS):
                        raise ValueError("Physical port census differs")
                elif (
                    result["status"] != "FAIL"
                    or step["audit_execution"]["returncode"] != 1
                    or "Deck explicitly reported a mismatch" not in result["reasons"]
                ):
                    raise ValueError("Native fault not rejected by actual comparison")
            step["status"] = (
                "PASS"
                if name in ("drc", "lvs", "lvs_flat")
                else "REJECTED_EXPECTED_FAULT"
            )
            save()
            print(name, step["status"], flush=True)
        if any(digest(p) != h for p, h in pins.items()):
            raise ValueError("Inputs changed during verification")
        record["status"] = "PASS_NATIVE_PDK_CDR_PD484_DRC_LVS_AND_FAULT_CONTROLS"
    except Exception as error:
        record.update(status="FAIL", error=repr(error))
        save()
        raise
    save()
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("layout", "out", "app"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    run(args.layout, args.out, args.app)


if __name__ == "__main__":
    main()
