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
    name = re.sub(r"^.*/hw/soc/rtl/pcie/", "", name)
    name = re.sub(r"_reg$", "", name)
    return name


def group(name):
    """Register name without bit and array indices."""
    return re.sub(r"\s*\[\d+\]", "", name).strip()


def ends(path, want="pcie_clk_i"):
    """Endpoint slacks of one path group (recovery checks are "asynchronous")."""
    rows, current = [], None
    if not path.exists():
        return rows
    for line in path.read_text().splitlines():
        if " group " in line and line.startswith(("max_delay", "min_delay")):
            current = line.split()[-1]
            continue
        m = END.match(line.strip())
        if m and current == want:
            rows.append((register(m.group(1)), float(m.group(5))))
    return rows


def full(path, want="pcie_clk_i"):
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
        elif line.startswith("Path Group:"):
            cur["group"] = line.split()[-1]
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
    return [p for p in paths if p.get("group") == want]


def logic_levels(cells):
    """Cells after the launch flop, and the same without buffers/inverters."""
    rest = cells[1:]
    return len(rest), sum(1 for c in rest if not re.match(r"sg13g2_(buf|inv|dlygate)", c))


def main(out):
    out = Path(out)
    for stage in ("synth", "placed", "sized", "repaired"):
        for corner in ("typ", "slow"):
            if not (out / f"{stage}_r2r_end_{corner}.rpt").exists():
                continue
            print(f"== stage {stage} corner {corner}")
            for kind, label in (("r2r", "register to register"), ("all", "all pcie_clk_i paths")):
                rows = ends(out / f"{stage}_{kind}_end_{corner}.rpt")
                if not rows:
                    print(f"{label}: no paths")
                    continue
                neg = [s for _, s in rows if s < 0]
                print(f"{label}: worst {min(s for _, s in rows):.3f} ns, "
                      f"TNS {sum(neg):.2f} ns, violating endpoints {len(neg)} of {len(rows)} reported")
            if stage == "synth":
                continue
            groups = defaultdict(list)
            for name, slack in ends(out / f"{stage}_r2r_end_{corner}.rpt"):
                if slack < 0:
                    groups[group(name)].append(slack)
            print("violating register-to-register endpoints by register (worst, count):")
            for g, s in sorted(groups.items(), key=lambda kv: min(kv[1]))[:30]:
                print(f"  {min(s):8.3f} {len(s):5d}  {g}")
            core = full(out / f"{stage}_core_full_{corner}.rpt")
            if core:
                crow = ends(out / f"{stage}_core_end_{corner}.rpt")
                neg = [s for _, s in crow if s < 0]
                print(f"without link status startpoints: worst {min(s for _, s in crow):.3f} ns, "
                      f"TNS {sum(neg):.2f} ns, violating endpoints {len(neg)}")
                print("  worst path per endpoint register (slack, cells, logic cells, start -> end):")
                seen = set()
                for p in core:
                    g = group(register(p.get("end", "?")))
                    if g in seen:
                        continue
                    seen.add(g)
                    n, m = logic_levels(p["cells"])
                    print(f"  {p['slack']:8.3f} {n:3d} {m:3d}  {register(p['start'])} -> {register(p.get('end', '?'))}")
                    if len(seen) >= 40:
                        break
                depth = sorted((logic_levels(p["cells"]) for p in core), reverse=True)[:1]
                print(f"  deepest of {len(core)} worst-endpoint paths: cells, logic cells {depth}")
            print("worst register-to-register paths (slack, arrival, cells, logic cells, start -> end):")
            for p in full(out / f"{stage}_r2r_full_{corner}.rpt")[:6]:
                n, m = logic_levels(p["cells"])
                nets = [x for x in p["nets"] if x != group(register(p["start"]))][:10]
                print(f"  {p['slack']:8.3f} {p['arrival']:7.3f} {n:3d} {m:3d}  "
                      f"{register(p['start'])} -> {register(p.get('end', '?'))}")
                print(f"           via {', '.join(nets)}")
            for p in full(out / f"{stage}_all_full_{corner}.rpt")[:3]:
                n, m = logic_levels(p["cells"])
                print(f"  any-path {p['slack']:8.3f} {n:3d} {m:3d}  {register(p['start'])} -> {register(p.get('end', '?'))}")
            hold = ends(out / f"{stage}_hold_end_{corner}.rpt")
            if hold:
                print(f"hold worst {min(s for _, s in hold):.3f} ns")
            rec = ends(out / f"{stage}_all_end_{corner}.rpt", "asynchronous")
            if rec:
                print(f"recovery (asynchronous group) worst {min(s for _, s in rec):.3f} ns, "
                      f"violating {sum(1 for _, s in rec if s < 0)}")


if __name__ == "__main__":
    main(sys.argv[1])
