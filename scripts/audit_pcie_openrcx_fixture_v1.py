#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Audit isolated straight-wire OpenRCX fixtures, not arbitrary chip SPEF.

References are the SG13G2 process specification rev1.2, table2.13 sheet
resistances (not the different snake measurements). This finite contract
checks native export topology, units, model resistance and capacitance
conservation. It does not establish capacitance accuracy, process corners,
temperature dependence, via models, RF or full-chip extraction qualification.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import re

# Ohms/square: independent process-document target and maximum, not values
# inferred from the extracted result or fitted to make the fixture pass.
SHEETS = {
    "Metal1": (0.110, 0.135),
    "Metal2": (0.088, 0.103),
    "Metal3": (0.088, 0.103),
    "Metal4": (0.088, 0.103),
    "Metal5": (0.088, 0.103),
    "TopMetal1": (0.018, 0.021),
    "TopMetal2": (0.011, 0.0145),
}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def number(text, *, positive=False):
    value = float(text)
    require(math.isfinite(value) and value >= 0, "Nonfinite/negative RC value")
    require(not positive or value > 0, "Zero resistance/dimension")
    return value


def close(actual, expected):
    # Native SPEF has approximately six significant decimal digits.
    return abs(actual - expected) <= max(1e-8, abs(expected) * 1e-5)


def audit(path, geometry, *, coupling=False):
    data = Path(path).read_bytes()
    text = data.decode()
    for literal in ("*R_UNIT 1 OHM", "*C_UNIT 1 PF", "*T_UNIT 1 NS"):
        require(
            len(re.findall(r"(?m)^" + re.escape(literal) + r"\s*$", text)) == 1,
            "Missing/ambiguous native SPEF units: " + literal,
        )
    require('"PIN_CAP NONE"' in text, "Fixture excludes cell pin capacitance")
    require(
        text.count("*NAME_MAP") == 1 and text.count("*PORTS") == 1,
        "Exact name/port sections",
    )
    names = {}
    for line in text.split("*NAME_MAP", 1)[1].split("*PORTS", 1)[0].splitlines():
        if not line.strip():
            continue
        words = line.split()
        require(len(words) == 2 and re.fullmatch(r"\*\d+", words[0]), "Name map")
        require(
            words[0] not in names and words[1] not in names.values(), "Duplicate name"
        )
        names[words[0]] = words[1]
    expected = {row["net"]: row for row in geometry}
    require(
        len(expected) == len(geometry) and set(names.values()) == set(expected),
        "Exact expected net census",
    )
    ports = {}
    owners = {}
    for net, row in expected.items():
        require(
            len(row["ports"]) == 2 and len(set(row["ports"])) == 2,
            "Two distinct terminals",
        )
        for port, direction in zip(row["ports"], ("I", "O")):
            require(port not in ports, "Shared/duplicated expected terminal")
            ports[port] = direction
            owners[port] = net
    raw_ports = [
        line.split()
        for line in text.split("*PORTS", 1)[1].split("*D_NET", 1)[0].splitlines()
        if line.strip()
    ]
    require(
        all(len(x) == 2 for x in raw_ports)
        and len(raw_ports) == len(ports)
        and dict(raw_ports) == ports,
        "Exact terminal/direction census",
    )
    observed = {}
    coupled = {}
    for block in text.split("*D_NET ")[1:]:
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        require(
            lines[-1] == "*END" and lines.count("*END") == 1, "Truncated/trailing net"
        )
        ident, total = lines[0].split()
        require(
            ident in names and names[ident] not in observed, "Missing/duplicate net"
        )
        net = names[ident]
        row = expected[net]
        sections = {}
        section = None
        for line in lines[1:-1]:
            if line in ("*CONN", "*CAP", "*RES"):
                require(line not in sections, "Duplicate section")
                section = line
                sections[section] = []
            else:
                require(section is not None, "Missing net section")
                sections[section].append(line.split())
        require(set(sections) == {"*CONN", "*CAP", "*RES"}, "Complete RC net sections")
        conn = sections["*CONN"]
        require(
            len(conn) == 2 and all(len(x) == 3 and x[0] == "*P" for x in conn),
            "Only the two actual fixture terminals",
        )
        require(
            {x[1]: x[2] for x in conn} == {p: ports[p] for p in row["ports"]},
            "Terminal binding changed",
        )
        resistance = sections["*RES"]
        require(
            len(resistance) == 1 and len(resistance[0]) == 4,
            "Straight fixture must remain one connected RC segment",
        )
        r = resistance[0]
        require(
            r[0] == "1" and set(r[1:3]) == set(row["ports"]),
            "Broken resistor terminals",
        )
        actual_r = number(r[3], positive=True)
        width = number(row["width_um"], positive=True)
        length = number(row["length_um"], positive=True)
        nominal, maximum = SHEETS[row["layer"]]
        # OpenRCX uses the full native rectangle including the half-width at
        # each end. This checks that exported model convention explicitly;
        # it is not proof of center-to-center terminal resistance accuracy.
        expected_r = nominal * (length + width) / width
        require(
            close(actual_r, expected_r),
            "Resistance disagrees with original geometry/process target",
        )
        caps = sections["*CAP"]
        require(len(caps) >= 2, "Missing ground capacitance")
        grounds = {}
        edges = set()
        serialized = 0.0
        for index, cap in enumerate(caps, 1):
            require(cap[0] == str(index) and len(cap) in (3, 4), "Capacitance row")
            value = number(cap[-1], positive=True)
            serialized += value
            if len(cap) == 3:
                require(
                    cap[1] in row["ports"] and cap[1] not in grounds,
                    "Ground-C terminal",
                )
                grounds[cap[1]] = value
            else:
                require(
                    coupling and all(p in owners for p in cap[1:3]),
                    "Unexpected coupling terminal",
                )
                a, b = sorted(cap[1:3])
                require(
                    owners[a] != owners[b] and net in (owners[a], owners[b]),
                    "Coupling ownership",
                )
                require((a, b) not in edges, "Duplicate coupling entry")
                edges.add((a, b))
                coupled.setdefault((a, b), []).append((net, value))
        require(set(grounds) == set(row["ports"]), "Both endpoint ground capacitances")
        require(
            close(serialized, number(total, positive=True)),
            "Declared/serialized capacitance mismatch",
        )
        observed[net] = dict(
            resistance_ohm=actual_r,
            expected_target_ohm=expected_r,
            maximum_sheet_reference_ohm=maximum * (length + width) / width,
            declared_cap_pf=float(total),
            ground_cap_pf=sum(grounds.values()),
        )
    require(set(observed) == set(expected), "Missing complete net")
    require(bool(coupled) == coupling, "Expected coupling presence")
    for (a, b), entries in coupled.items():
        require(
            len(entries) == 2
            and {x[0] for x in entries} == {owners[a], owners[b]}
            and close(entries[0][1], entries[1][1]),
            "Coupling reciprocity",
        )
    return dict(
        status="PASS_FINITE_WIRE_EXPORT_CONTRACT",
        nets=observed,
        unique_coupling_pf=sum(v[0][1] for v in coupled.values()),
        unique_coupling_edges=len(coupled),
        input_sha256=hashlib.sha256(data).hexdigest(),
        scope=__doc__,
        qualified_rc=False,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--spef", type=Path, required=True)
    parser.add_argument("--geometry", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--coupling", action="store_true")
    args = parser.parse_args()
    if args.out.exists():
        parser.error("Use a fresh evidence file")
    try:
        result = audit(
            args.spef, json.loads(args.geometry.read_text()), coupling=args.coupling
        )
    except (ValueError, KeyError, IndexError) as exc:
        result = dict(status="FAIL", error=str(exc), qualified_rc=False)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    print(result["status"])
    return int(result["status"] == "FAIL")


if __name__ == "__main__":
    raise SystemExit(main())
