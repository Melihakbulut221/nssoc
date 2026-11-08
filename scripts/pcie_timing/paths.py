# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Summarise the PCIe packet-domain OpenSTA reports written by run.sh.

For each corner: worst slack, total negative slack and violating endpoint
count, the violating endpoints grouped by RTL register, and the worst
paths with their logic depth (cells after the launch flop) and the named
nets they pass through.
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

OUT_PINS = {"X", "Y", "Q", "Q_N", "L_HI", "L_LO"}
ROW = re.compile(r"^\s*(-?[\d.]+)\s+(-?[\d.]+)\s+([\^v])\s+(\S+)\s+\((\S+)\)")
NET = re.compile(r"^\s*(?:\d+\s+)?(?:[\d.]+\s+)?(\S+)\s+\(net\)")
END = re.compile(r"^(\S+)\s+\((\S+)\)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)")


def register(pin):
    name = pin.rsplit("/", 1)[0].replace("\\", "")
    name = re.sub(r"_reg$", "", name)
    return name


def group(name):
    """Register name without bit and array indices."""
    return re.sub(r"\s*\[\d+\]", "", name).strip()


def ends(path):
    rows = []
    if not path.exists():
        return rows
    for line in path.read_text().splitlines():
        m = END.match(line.strip())
        if m:
            rows.append((register(m.group(1)), float(m.group(5))))
    return rows


def full(path):
    paths, cur = [], None
    if not path.exists():
        return paths
    for line in path.read_text().splitlines():
        if line.startswith("Startpoint:"):
            cur = {"start": line.split()[1], "cells": [], "nets": [], "slack": None, "arrival": None}
            paths.append(cur)
        elif cur is None:
            continue
        elif line.startswith("Endpoint:"):
            cur["end"] = line.split()[1]
        elif "data arrival time" in line and cur["arrival"] is None:
            cur["arrival"] = float(line.split()[0])
        elif "slack" in line and "(" in line:
            cur["slack"] = float(line.split()[0])
        elif cur["arrival"] is None:
            m = ROW.match(line)
            if m:
                pin = m.group(4).rsplit("/", 1)[-1]
                if pin in OUT_PINS:
                    cur["cells"].append(m.group(5))
                continue
            n = NET.match(line)
            if n and not n.group(1).startswith(("_", "$")):
                nm = group(n.group(1).replace("\\", ""))
                if nm not in cur["nets"]:
                    cur["nets"].append(nm)
    return paths


def main(out):
    out = Path(out)
    for corner in ("typ", "slow"):
        print(f"== corner {corner}")
        for kind, label in (("r2r", "register to register"), ("all", "all pcie_clk_i paths")):
            rows = ends(out / f"{kind}_end_{corner}.rpt")
            if not rows:
                print(f"{label}: no report")
                continue
            neg = [s for _, s in rows if s < 0]
            print(f"{label}: worst {min(s for _, s in rows):.3f} ns, "
                  f"TNS {sum(neg):.2f} ns, violating endpoints {len(neg)} of {len(rows)} reported")
        groups = defaultdict(list)
        for name, slack in ends(out / f"r2r_end_{corner}.rpt"):
            if slack < 0:
                groups[group(name)].append(slack)
        print("violating register-to-register endpoints by register (worst, count):")
        for g, s in sorted(groups.items(), key=lambda kv: min(kv[1]))[:30]:
            print(f"  {min(s):8.3f} {len(s):5d}  {g}")
        print("worst register-to-register paths (slack, arrival, levels, start -> end, named nets):")
        for p in full(out / f"r2r_full_{corner}.rpt")[:25]:
            levels = max(len(p["cells"]) - 1, 0)
            nets = [n for n in p["nets"] if n != group(register(p["start"]))][:8]
            print(f"  {p['slack']:8.3f} {p['arrival']:7.3f} {levels:3d}  "
                  f"{register(p['start'])} -> {register(p.get('end', '?'))}")
            print(f"           via {', '.join(nets)}")
        for p in full(out / f"all_full_{corner}.rpt")[:3]:
            levels = max(len(p["cells"]) - 1, 0)
            print(f"  any-path {p['slack']:8.3f} {levels:3d}  {register(p['start'])} -> {register(p.get('end', '?'))}")
        hold = ends(out / f"hold_end_{corner}.rpt")
        if hold:
            print(f"hold worst {min(s for _, s in hold):.3f} ns")


if __name__ == "__main__":
    main(sys.argv[1])
