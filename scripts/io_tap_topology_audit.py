#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Read-only, ordered IO Vss reference contract and coherent-view audit.

The expected diode maps follow IHP commit 1a29eb4980d520d9ce7273593dc1599310cb81a9
and issue 714; they are independent of extracted device values. No geometry,
schematic or deck is edited. Matching this contract is not an LVS pass.
"""

import argparse
import hashlib
import json
from pathlib import Path
import re

from io_tap_contract_audit import ContractError, parse

TOP = "sg13g2_iopadvss"
RAILS = {"iovdd": "POWER", "iovss": "GROUND", "vdd": "POWER", "vss": "GROUND"}
CHILD_MAPS = {
    "sg13g2_dcndiode": {"anode": "iovss", "cathode": "vss", "guard": "iovdd"},
    "sg13g2_dcpdiode": {"anode": "vss", "cathode": "iovdd", "guard": "iovss"},
}
VIEW_BASE = "ihp-sg13g2/libs.ref/sg13g2_io"
REPO = "https://github.com/IHP-GmbH/IHP-Open-PDK"


def file_identity(path):
    path = Path(path)
    size = path.stat().st_size
    blob = hashlib.sha1(f"blob {size}\0".encode())
    sha = hashlib.sha256()
    with path.open("rb") as stream:
        while data := stream.read(1024 * 1024):
            blob.update(data)
            sha.update(data)
    if path.stat().st_size != size:
        raise ContractError("View changed while being read")
    return {"bytes": size, "git_blob_sha1": blob.hexdigest(), "sha256": sha.hexdigest()}


def verify_view(path, metadata, commit, extension):
    if not re.fullmatch("[0-9a-f]{40}", commit) or extension not in {"gds", "cdl", "lef"}:
        raise ContractError("Require a pinned commit and supported view")
    expected_path = f"{VIEW_BASE}/{extension}/sg13g2_io.{extension}"
    if (metadata.get("path") != expected_path
            or metadata.get("html_url") != f"{REPO}/blob/{commit}/{expected_path}"):
        raise ContractError("View metadata has a different version/path")
    identity = file_identity(path)
    if identity["bytes"] != metadata.get("size") or identity["git_blob_sha1"] != metadata.get("sha"):
        raise ContractError("View bytes do not belong to the pinned library version")
    return identity


def bind_call(formals, actuals):
    if len(formals) != len(actuals) or len(set(formals)) != len(formals):
        raise ContractError("Ambiguous formal/actual pin mapping")
    return dict(zip(formals, actuals, strict=True))


def migration_indices(old_formals, new_formals):
    if len(set(old_formals)) != len(old_formals) or set(old_formals) != set(new_formals):
        raise ContractError("Cannot permute different/duplicate port sets")
    if len(set(new_formals)) != len(new_formals):
        raise ContractError("Duplicate destination formal")
    return [old_formals.index(port) for port in new_formals]


def lef_contract(text):
    macro = re.compile(r"^\s*MACRO\s+sg13g2_IOPadVss\s*$", re.I | re.M)
    starts = list(macro.finditer(text))
    if len(starts) != 1:
        raise ContractError("Require exactly one Vss LEF macro")
    tail = text[starts[0].end():]
    end = re.search(r"^\s*END\s+sg13g2_IOPadVss\s*$", tail, re.I | re.M)
    if not end:
        raise ContractError("Unclosed Vss LEF macro")
    body = tail[:end.start()]
    if re.search(r"^\s*MACRO\s", body, re.I | re.M):
        raise ContractError("Nested LEF macro")
    pins = {}
    for item in re.finditer(r"^\s*PIN\s+(\S+)\s*$", body, re.I | re.M):
        name = item[1].lower()
        if name in pins:
            raise ContractError("Duplicate LEF pin")
        remainder = body[item.end():]
        closing = re.search(r"^\s*END\s+" + re.escape(item[1]) + r"\s*$", remainder, re.I | re.M)
        if not closing:
            raise ContractError("Unclosed LEF pin")
        pin = remainder[:closing.start()]
        if re.search(r"^\s*PIN\s", pin, re.I | re.M):
            raise ContractError("Nested LEF pin")
        properties = {}
        for prop in ("DIRECTION", "USE"):
            values = re.findall(r"^\s*" + prop + r"\s+(\S+)\s*;\s*$", pin, re.I | re.M)
            if len(values) != 1:
                raise ContractError("Missing/ambiguous LEF pin property")
            properties[prop.lower()] = values[0].upper()
        pins[name] = properties
    if set(pins) != set(RAILS):
        raise ContractError("Vss LEF pin set differs from four separate rails")
    for name, role in RAILS.items():
        if pins[name] != {"direction": "INOUT", "use": role}:
            raise ContractError("LEF rail direction/role mismatch")
    return {"pins": pins, "macro_body_sha256": hashlib.sha256(body.encode()).hexdigest()}


def selected_topology_cells(cdl):
    """Keep exact target bodies; unrelated empty .PARAM/gallery is not a model.

    The raw library remains byte-pinned. No declaration or directive inside
    any selected cell is removed; the shared strict parser validates it.
    """
    wanted = {TOP, *CHILD_MAPS}
    selected, seen = [], set()
    active = None
    for raw in cdl.splitlines():
        words = raw.lower().split()
        if words and words[0] == ".subckt":
            if active is not None or len(words) < 2:
                raise ContractError("Nested/malformed subcircuit")
            active = words[1]
            if active in wanted:
                if active in seen:
                    raise ContractError("Duplicate selected subcircuit")
                seen.add(active)
                selected.append(raw)
        elif words and words[0] == ".ends":
            if active is None or (len(words) > 1 and words[1] != active):
                raise ContractError("Mismatched subcircuit end")
            if active in wanted:
                selected.append(raw)
            active = None
        elif active in wanted:
            selected.append(raw)
    if active is not None or seen != wanted:
        raise ContractError("Missing/unclosed selected subcircuit")
    cells, _ = parse("\n".join(selected))
    return cells


def audit(cdl, lef):
    cells = selected_topology_cells(cdl)
    if TOP not in cells or set(cells[TOP]["ports"]) != set(RAILS):
        raise ContractError("Vss CDL needs exactly the four named rails")
    children = {}
    for child, expected in CHILD_MAPS.items():
        if child not in cells or set(cells[child]["ports"]) != set(expected):
            raise ContractError("Diode formal interface differs")
        matches = []
        for words in cells[TOP]["lines"]:
            tokens = [word for word in words if word != "/"]
            if child in tokens:
                if (tokens[-1] != child or not tokens[0].startswith("x")
                        or any("=" in token for token in tokens)):
                    raise ContractError("Unsupported parameterized diode instance")
                actual_map = bind_call(cells[child]["ports"], tokens[1:-1])
                matches.append({"instance": tokens[0], "formal_order": cells[child]["ports"],
                                "actual_order": tokens[1:-1], "actual_map": actual_map,
                                "expected_map": expected, "contract_matches": actual_map == expected})
        if len(matches) != 1:
            raise ContractError("Require exactly one instance of each IO diode")
        children[child] = matches[0]
    lef_result = lef_contract(lef)
    good = all(item["contract_matches"] for item in children.values())
    return {"status": "REFERENCE_TOPOLOGY_MATCH" if good else "REFERENCE_TOPOLOGY_MISMATCH",
            "top": TOP, "formal_order": cells[TOP]["ports"], "children": children,
            "lef": lef_result, "reference_topology_matches": good,
            "authority": REPO + "/commit/1a29eb4980d520d9ce7273593dc1599310cb81a9",
            "scope": "Named schematic diode terminals and LEF rail interface only; no physical connectivity, tap A/P or LVS acceptance.",
            "physical_parent_connection_proven": False, "lvs_accepted": False,
            "full_chip_lvs_accepted": False, "manufacturing_approval": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for field in ("cdl", "lef", "output"):
        parser.add_argument("--" + field, type=Path, required=True)
    args = parser.parse_args()
    inputs = [args.cdl, args.lef, Path(__file__), Path(__file__).with_name("io_tap_contract_audit.py")]
    if args.output.resolve() in {p.resolve() for p in inputs}:
        raise ContractError("Output cannot overwrite an input")
    result = audit(args.cdl.read_text(), args.lef.read_text())
    result["input_sha256"] = {str(p.resolve()): file_identity(p)["sha256"] for p in inputs}
    with args.output.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")


if __name__ == "__main__":
    main()
