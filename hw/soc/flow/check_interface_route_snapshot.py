#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Run one independent native deck on an authenticated interface SoC routing snapshot."""
import argparse
import hashlib
import json
import lzma
from pathlib import Path
import shutil
import subprocess
import xml.etree.ElementTree as ET

from librelane.common import Path as LanePath
from librelane.flows import SequentialFlow
from librelane.state import DesignFormat, State
from librelane.steps import KLayout, Magic, Netgen


class StagedIHPFiller(KLayout.Filler):
    """Release KLayout memory between the three native IHP fill passes."""

    def run_ihp_sg13g2(self, state_in, **kwargs):
        kwargs, env = self.extract_env(kwargs)
        env.update(PDK_ROOT=str(self.config["PDK_ROOT"]), PDK=str(self.config["PDK"]))
        current = state_in[DesignFormat.GDS]
        passes = [
            ("active-poly.gds", ("no_metal", "no_topmetal")),
            ("metal.gds", ("no_activ", "no_topmetal")),
            ("soc_top.gds", ("no_activ", "no_metal")),
        ]
        for filename, disabled in passes:
            target = Path(self.step_dir) / filename
            args = ["klayout", "-b", "-zz", "-r", str(self.config["KLAYOUT_FILLER_SCRIPT"]),
                    "-rd", f"output_file={target}"]
            for flag in disabled:
                args.extend(["-rd", flag])
            self.run_subprocess([*args, str(current)], env=env)
            if target.stat().st_size == 0:
                raise ValueError(f"Empty filled layout at {target}")
            current = target
        return {DesignFormat.GDS: LanePath(current)}, {}


CHECKS = {
    "xor": ([Magic.StreamOut, KLayout.StreamOut, KLayout.XOR], "design__xor_difference__count"),
    "magic-drc": ([Magic.StreamOut, Magic.DRC], "magic__drc_error__count"),
    "klayout-drc": ([KLayout.StreamOut, KLayout.DRC], "klayout__drc_error__count"),
    "filled-density": ([KLayout.StreamOut, StagedIHPFiller, KLayout.Density], "klayout__density_error__count"),
    "density": ([KLayout.StreamOut, KLayout.Density], "klayout__density_error__count"),
    "antenna": ([KLayout.StreamOut, KLayout.Antenna], "klayout__antenna_error__count"),
    "lvs": ([Magic.StreamOut, Magic.SpiceExtraction, Netgen.LVS], "design__lvs_error__count"),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("check", choices=CHECKS)
    parser.add_argument("--archive", required=True, type=Path)
    parser.add_argument("--receipt", required=True, type=Path)
    parser.add_argument("--pdk-root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)
    receipt = json.loads(args.receipt.read_text())
    odb = out / "soc_top.odb"
    with lzma.open(args.archive, "rb") as src, odb.open("wb") as dst:
        shutil.copyfileobj(src, dst)
    with odb.open("rb") as src:
        digest = hashlib.file_digest(src, "sha256").hexdigest()
    if digest != receipt["layout_odb_sha256"]:
        raise ValueError("Routing checkpoint digest mismatch")
    script = out / "export.tcl"
    script.write_text("read_db soc_top.odb\nwrite_def soc_top.def\n"
                      "set b [ord::get_db_block]\nset r [$b getDieArea]\n"
                      "set f [open die-area.txt w]\n"
                      "foreach side {xMin yMin xMax yMax} {puts $f [expr {double([$r $side])/[$b getDbUnitsPerMicron]}]}\nclose $f\n"
                      "write_verilog -include_pwr_gnd soc_top.pnl.v\n")
    subprocess.run(["openroad", "-exit", str(script)], cwd=out, check=True)
    pnr = Path(__file__).resolve().parents[1] / "pnr"
    original = json.loads((pnr / "config-interfaces-mbist-logicrom.json").read_text())
    config = {key: original[key] for key in ("DESIGN_NAME", "PDK", "STD_CELL_LIBRARY", "MACROS")}
    steps, metric = CHECKS[args.check]
    config["PRIMARY_GDSII_STREAMOUT_TOOL"] = "klayout" if steps[0] == KLayout.StreamOut else "magic"
    if Magic.StreamOut in steps:
        # The hard SRAM and its LEF/GDS come from the same pinned PDK tree.
        # Magic imports the real macro GDS and annotates it with its matching LEF.
        if not all(all(str(view).startswith("pdk_dir::") for view in macro[key])
                   for macro in config["MACROS"].values() for key in ("gds", "lef")):
            raise ValueError("Expected pinned PDK SRAM GDS and LEF views")
        config["DIE_AREA"] = [float(n) for n in (out / "die-area.txt").read_text().split()]
        config["MAGIC_MACRO_STD_CELL_SOURCE"] = "PDK"
    if args.check == "magic-drc":
        config["MAGIC_DRC_USE_GDS"] = False
    if args.check == "lvs":
        config["MAGIC_EXT_USE_GDS"] = False
    if args.check == "klayout-drc":
        config["KLAYOUT_DRC_OPTIONS"] = {"run_mode": "deep", "no_recommended": True}
    class SnapshotFlow(SequentialFlow):
        Steps = steps

    flow = SnapshotFlow(config, design_dir=str(pnr), pdk_root=str(args.pdk_root.resolve()))
    state = State({"def": LanePath(out / "soc_top.def"), "pnl": LanePath(out / "soc_top.pnl.v")})
    final = flow.start(with_initial_state=state, _force_run_dir=str(out / "flow"))
    value = final.metrics.get(metric)
    result = {"check": args.check, "odb_sha256": digest, "metric": metric, "value": value}
    if args.check == "filled-density":
        filled, = (out / "flow").glob("*-klayout-filler/soc_top.gds")
        with filled.open("rb") as src:
            result["filled_gds_sha256"] = hashlib.file_digest(src, "sha256").hexdigest()
    if args.check in {"klayout-drc", "density", "filled-density"}:
        report, = (out / "flow").rglob("*.klayout.lyrdb")
        groups = {}
        for _, item in ET.iterparse(report, events=("end",)):
            if item.tag != "item":
                continue
            key = (item.findtext("category"), item.findtext("cell"))
            group = groups.setdefault(key, {"items": 0, "sample": item.findtext("values/value")})
            group["items"] += 1
            item.clear()
        result["rule_cells"] = [
            {"category": category, "cell": cell, **entry}
            for (category, cell), entry in sorted(groups.items(), key=lambda row: -row[1]["items"])
        ]
    print(json.dumps(result, default=str), flush=True)
    (out / "result.json").write_text(json.dumps(result, indent=2, default=str) + "\n")
    if value is None or value != 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
