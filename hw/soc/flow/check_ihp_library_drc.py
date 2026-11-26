# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Check an unmodified PDK SRAM or standard-cell GDS with the interface DRC deck."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

from librelane.common import Path as LanePath
from librelane.flows import SequentialFlow
from librelane.state import State
from librelane.steps import KLayout


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("check", choices=["library-sram", "library-stdcell"])
    parser.add_argument("--pdk-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    if args.check == "library-sram":
        lib, top = "sg13g2_sram", "RM_IHPSG13_1P_2048x64_c2_bm_bist"
    else:
        lib, top = "sg13g2_stdcell", "sg13g2_fill_1"
    root = args.pdk_root.resolve()
    gds = root / "ihp-sg13g2/libs.ref" / lib / "gds" / ((top if args.check == "library-sram" else lib) + ".gds")
    with gds.open("rb") as src:
        digest = hashlib.file_digest(src, "sha256").hexdigest()
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=False)

    class LibraryDRC(SequentialFlow):
        Steps = [KLayout.DRC]

    cfg = {"DESIGN_NAME": top, "PDK": "ihp-sg13g2", "STD_CELL_LIBRARY": "sg13g2_stdcell",
           "KLAYOUT_DRC_OPTIONS": {"run_mode": "deep", "no_recommended": True}}
    flow = LibraryDRC(cfg, design_dir=str(out), pdk_root=str(root))
    final = flow.start(with_initial_state=State({"gds": LanePath(gds)}),
                       _force_run_dir=str(out / "flow"))
    count = final.metrics["klayout__drc_error__count"]
    report, = (out / "flow").rglob("*.klayout.lyrdb")
    groups = Counter((item.findtext("category"), item.findtext("cell"))
                     for item in ET.parse(report).iter("item"))
    result = {"top": top, "gds": str(gds), "sha256": digest, "count": int(count),
              "rule_cells": [[*key, n] for key, n in groups.most_common()]}
    print(json.dumps(result), flush=True)
    (out / "result.json").write_text(json.dumps(result, indent=2) + "\n")
    if count != 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
