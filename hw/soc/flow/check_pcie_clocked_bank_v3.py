#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Strict native checks for the fixed VCO and eight real sampler clock branches."""

import argparse
import json
from pathlib import Path
import re

from check_ihp_drc import digest, record_result
from check_pcie_analog_bank import extracted_ports, quote, validate_lef
from check_pcie_rx_cell import execute
from make_pcie_sampler_cell import CIRCUIT, CIRCUIT_SHA256
from make_pcie_clocked_bank_v3 import COUNTS, PORTS, TOP, use_direction
from make_pcie_clock_vco import CIRCUIT as VCO_CIRCUIT, CIRCUIT_SHA256 as VCO_SHA
from prepare_ihp_drc import validate_lock, verify

APP_SHA = "d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466"
REFERENCE_FAULTS = ("sampler_load", "wrong_clock", "missing_tap", "vco_cap", "vco_pmos")
PHYSICAL_FAULTS = ("clock_open", "clock_short", "rail_23_25_short", "rail_18_25_short", "substrate_short", "vctrl_open")


def fault_reference(text, fault):
    changes = {
        "sampler_load": ("RBANK_0SAMPLER_M_RP AVDD2V5 L0_SAMPLER_MP BULK rppd w=8u l=2.12u", "RBANK_0SAMPLER_M_RP AVDD2V5 L0_SAMPLER_MP BULK rppd w=8u l=2.04u"),
        "wrong_clock": ("QBANK_2SAMPLER_M_CS L2_SAMPLER_M_SE CLOCKN L2_SAMPLER_M_TE", "QBANK_2SAMPLER_M_CS L2_SAMPLER_M_SE CLOCKP L2_SAMPLER_M_TE"),
        "missing_tap": ("RVCO_TAP0 SUB BULK ptap1 A=4p P=8u\n", ""),
        "vco_cap": ("CVCO_CP0 VCO_P0 AVSS cap_cmim w=12.2u", "CVCO_CP0 VCO_P0 AVSS cap_cmim w=12u"),
        "vco_pmos": ("MVCO_CTRL VCO_REF VCTRL AVDD2V3 VCO_NWELL sg13_hv_pmos w=32u", "MVCO_CTRL VCO_REF VCTRL AVDD2V3 VCO_NWELL sg13_hv_pmos w=31u"),
    }
    if fault not in changes:
        raise ValueError("Unknown reference fault")
    old, new = changes[fault]
    if text.count(old) != 1:
        raise ValueError("Reference fault must bind exactly once")
    return text.replace(old, new)


def mutation_source(gds, output, generated, fault):
    lines = ["import pya", "l=pya.Layout()", "l.read(" + repr(str(gds)) + ")",
             "c=l.cell(" + repr(TOP) + ")"]
    if fault == "offgrid":
        lines += ["c.shapes(l.layer(8,0)).insert(pya.DBox(2.002,2,2.102,2.1))"]
    elif fault in ("clock_open", "vctrl_open"):
        if fault == "clock_open":
            matches = [r for r in generated["clock_connections"] if r["sink"] == "L2_SAMPLER_CLKP"]
            if len(matches) != 1:
                raise ValueError("Exact clock branch missing")
            b = matches[0]["branch"]["rect_um"]
            y = (b[1]+b[3])/2
            box = (70,y-2,74,y+2)
        else:
            b = generated["ports"]["VCTRL"]["rect_um"]
            y = (b[1]+b[3])/2
            box = (3,y-2,4,y+2)
        lines += ["region=pya.Region(c.shapes(l.layer(126,0)))",
                  "region-=pya.Region(pya.DBox("+','.join(map(repr,box))+").to_itype(l.dbu))",
                  "c.shapes(l.layer(126,0)).clear()", "c.shapes(l.layer(126,0)).insert(region)"]
    elif fault == "clock_short":
        matches = [r for r in generated["routes"] if r["net"] in ("CLOCKP","CLOCKN") and r["layer"] == "TopMetal2"]
        if len(matches) != 2:
            raise ValueError("Exact clock trunks missing")
        xs = [(r["rect_um"][0]+r["rect_um"][2])/2 for r in matches]
        lines += [f"c.shapes(l.layer(134,0)).insert(pya.DBox({min(xs)!r},600,{max(xs)!r},604))"]
    elif fault in ("rail_23_25_short", "rail_18_25_short", "substrate_short"):
        names = {"rail_23_25_short":("AVDD2V3","AVDD2V5"),"rail_18_25_short":("AVDD1V8","AVDD2V5"),"substrate_short":("AVSS","SUB")}[fault]
        xs = [sum(generated["ports"][name]["rect_um"][k] for k in (0,2))/2 for name in names]
        lines += [f"c.shapes(l.layer(134,0)).insert(pya.DBox({min(xs)!r},1,{max(xs)!r},3))"]
    else:
        raise ValueError("Unknown physical fault")
    return "\n".join(lines + ["l.write(" + repr(str(output)) + ")", ""])


def lef_script(pdk, lef, generated):
    box = generated["bbox_um"]
    lines = ["read_lef " + quote(pdk / "libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef"),
             "read_lef " + quote(lef), "set master [[ord::get_db] findMaster " + TOP + "]",
             'if {$master eq "NULL"} {error "Clocked bank master missing"}',
             f'if {{[$master getWidth] != {round(box[2]*1000)} || [$master getHeight] != {round(box[3]*1000)}}} {{error "Clocked bank outline changed"}}',
             'if {[llength [$master getMTerms]] != 54} {error "Analog terminal census changed"}']
    if set(generated["ports"]) != set(PORTS):
        raise ValueError("Clocked bank LEF pin census differs")
    for name in PORTS:
        use, direction = use_direction(name)
        coords = " ".join(str(round(v*1000)) for v in generated["ports"][name]["rect_um"])
        metal = generated["ports"][name]["layer"]
        lines += ["set term [$master findMTerm " + name + "]",
                  'if {$term eq "NULL"} {error "Clocked bank terminal missing"}',
                  'if {[$term getIoType] ne "' + direction + '" || [$term getSigType] ne "' + use + '"} {error "Clocked bank terminal type differs"}',
                  'set boxes {}; foreach pin [$term getMPins] {foreach box [$pin getGeometry] {lappend boxes [list [[$box getTechLayer] getName] [$box xMin] [$box yMin] [$box xMax] [$box yMax]]}}',
                  'if {$boxes ne {{' + metal + ' ' + coords + '}}} {error "Clocked bank terminal geometry differs"}']
    lines += ['set obs {}; foreach box [$master getObstructions] {lappend obs [[$box getTechLayer] getName]}',
              'if {[lsort -unique $obs] ne {Metal1 Metal2 Metal3 Metal4 Metal5 TopMetal1 TopMetal2}} {error "Clocked bank blockage layer census changed"}',
              'puts PASS_NATIVE_ANALOG_BANK_LEF_ONLY']
    return "\n".join(lines) + "\n"


def validate_lvs(step, text, positive):
    audit = step["audit"]
    if positive:
        if (audit["status"] != "PASS within comparison scope" or step["audit_execution"]["returncode"] != 0 or
                extracted_ports(text, TOP) != set(PORTS) or len(audit["circuits"]) != 1 or
                audit["circuits"][0]["layout_devices_recursive"] != 200 or
                audit["circuits"][0]["schematic_devices_recursive"] != 200):
            raise ValueError("Positive clocked bank LVS/port/device census did not pass")
    elif audit["status"] != "FAIL" or step["audit_execution"]["returncode"] != 1:
        raise ValueError("Native clocked bank negative was accepted")
    elif step["name"] == "vctrl_open":
        if extracted_ports(text, TOP) != set(PORTS) - {"VCTRL"}:
            raise ValueError("Clock open did not bind the exact missing boundary port")
    elif audit["circuit_status_counts"].get("NoMatch", 0) < 1:
        raise ValueError("Native clocked bank fault failed for an unrelated reason")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("layout", "pdk", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[3]
    out, layout, pdk = args.out.resolve(), args.layout.resolve(), args.pdk.resolve()
    if out.exists() or not (out.is_relative_to(root / "hw/soc/out") or
                           out.is_relative_to(Path("/dev/shm")) and out.name.startswith("nssoc-clocked-")):
        parser.error("Fresh project or /dev/shm/nssoc-clocked- directory required")
    generated = json.loads((layout / "result.json").read_text())
    if generated["primitive_counts"] != COUNTS or len(generated["clock_connections"]) != 8:
        raise ValueError("Exact clocked parent primitive/branch census differs")
    app = root / "hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage"
    if digest(app) != APP_SHA or digest(root / CIRCUIT) != CIRCUIT_SHA256 or digest(root / VCO_CIRCUIT) != VCO_SHA:
        raise ValueError("Clocked bank circuit or native runtime changed")
    gds, schematic = layout / (TOP + ".gds"), layout / "schematic.cir"
    pins = {Path(k): v for k, v in generated["input_sha256"].items()}
    for name, expected in generated["output_sha256"].items():
        if digest(layout / name) != expected:
            raise ValueError("Generated physical view changed")
        pins[layout / name] = expected
    methods = ["check_pcie_clocked_bank_v3.py", "make_pcie_clocked_bank_v3.py", "make_pcie_analog_bank_v2.py", "make_pcie_clock_vco.py", "make_pcie_sampler_cell.py", "check_pcie_rx_cell.py",
               "check_pcie_analog_bank.py", "make_pcie_analog_bank.py", "make_pcie_rx_cell.py",
               "make_pcie_rx_cell_v2.py", "check_ihp_drc.py", "prepare_ihp_drc.py", "audit_klayout_lvs.py"]
    for path in [app, layout / "result.json", pdk / "libs.ref/sg13g2_stdcell/lef/sg13g2_tech.lef",
                 *(root / "hw/soc/flow" / name for name in methods)]:
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
    out.mkdir(parents=True)
    record = dict(status="RUNNING", inputs={str(p): h for p, h in pins.items()}, steps=[],
                  phy_complete=False, qualified_pex=False, manufacturing_approval=False,
                  clock_fanout_qualified=False, post_layout_8ghz_qualified=False, main_chip_integrated=False,
                  scope="Fixed VCO to four RX/sampler lanes over eight real clock branches; isolated 1.8/2.5/2.3 V rails. Main-rule screen only; no fanout/RF/timing, PLL/CDR locking or main-chip acceptance.")

    def save():
        (out / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    try:
        save()
        for name in ("drc", "offgrid", "lvs", "lvs_flat", *REFERENCE_FAULTS, *PHYSICAL_FAULTS):
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
                step["mutation_execution"] = execute([app, "python", script], directory, "mutation")
                if step["mutation_execution"]["returncode"] != 0 or digest(physical) == digest(gds):
                    raise ValueError("Physical fault did not bind")
            if name in REFERENCE_FAULTS:
                reference = directory / "wrong.cir"
                reference.write_text(fault_reference(schematic.read_text(), name))
            drc = name in ("drc", "offgrid")
            entry = root / ("hw/soc/tools/ihp-drc-5e6d592/ihp-sg13g2/libs.tech/klayout/tech/drc/ihp-sg13g2.drc" if drc else
                            "hw/soc/tools/ihp-lvs-5e6d592/ihp-sg13g2/libs.tech/klayout/tech/lvs/sg13g2.lvs")
            options = ["input=" + str(physical), "topcell=" + TOP, "log=" + str(directory / "deck.log"), "run_mode=flat" if name == "lvs_flat" else "run_mode=deep"]
            options += ["report=" + str(directory / "drc.lyrdb"), "threads=2", "no_recommended=False", "precheck_drc=False"] if drc else [
                "schematic=" + str(reference), "report=" + str(directory / "result.lvsdb"),
                "target_netlist=" + str(directory / "extracted.cir"), "thr=2"]
            command = [app, "klayout", "-b", "-zz", "-r", entry]
            for option in options:
                command += ["-rd", option]
            step["execution"] = execute(command, directory, "run")
            if step["execution"]["returncode"] != 0:
                raise ValueError("Native deck did not complete")
            if drc:
                measurement = record_result(directory, TOP, 0, pins)
                step["measurement"], step["status"] = measurement, measurement["status"]
                if measurement["category_count"] != 560 or "KLayout DRC run for tables 'main' completed" not in (directory / "run.log").read_text():
                    raise ValueError("Native main rule census incomplete")
                if name == "drc" and measurement["status"] != "PASS":
                    raise ValueError("Clocked bank main DRC failed")
                if name == "offgrid" and (measurement["status"] != "FAIL" or measurement["categories"].get("metal1_drw_Offgrid", 0) < 1):
                    raise ValueError("Physical DRC fault was accepted")
            else:
                step["audit_execution"] = execute([app, "python", root / "hw/soc/flow/audit_klayout_lvs.py",
                                                    directory / "result.lvsdb", "--top", TOP,
                                                    "--deck-log", directory / "deck.log", "--output", directory / "audit.json"], directory, "audit")
                step["audit"] = json.loads((directory / "audit.json").read_text())
                step["status"] = step["audit"]["status"]
                validate_lvs(step, (directory / "extracted.cir").read_text(), name in ("lvs", "lvs_flat"))
            save()
            print(name, step["status"], flush=True)
        for negative in (False, True):
            directory = out / ("lef_missing_pin" if negative else "lef")
            directory.mkdir()
            view = layout / (TOP + ".lef")
            if negative:
                text, count = re.subn(r"  PIN VCTRL\n.*?  END VCTRL\n", "", view.read_text(), flags=re.S)
                if count != 1:
                    raise ValueError("LEF fault did not bind")
                view = directory / "wrong.lef"
                view.write_text(text)
            script = directory / "inspect.tcl"
            script.write_text(lef_script(pdk, view, generated))
            execution = execute([app, "openroad", "-exit", script], directory, "native")
            validate_lef(execution["returncode"], (directory / "native.log").read_text(), negative)
            record["steps"].append(dict(name=directory.name, execution=execution,
                                         status="EXPECTED_REJECTION" if negative else "PASS"))
            save()
        if any(digest(p) != h for p, h in pins.items()):
            raise ValueError("Physical inputs changed during native validation")
        record["status"] = "PASS_CLOCKED_BANK_V3_MAIN_DRC_STRICT_DEEP_FLAT_LVS_LEF_AND_THIRTEEN_NEGATIVE_CONTROLS_ONLY"
        record["outputs"] = {str(p.relative_to(out)): digest(p) for p in sorted(out.rglob("*"))
                               if p.is_file() and p != out / "result.json"}
        save()
    except BaseException as error:
        record.update(status="FAILED_OR_INCOMPLETE", error=repr(error))
        save()
        raise


if __name__ == "__main__":
    main()
