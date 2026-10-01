#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Audit the strict tap contract from captured netlists; never run or accept LVS.

This deliberately accepts only a small, explicit SPICE/CDL subset.  Parallel
tap combination follows the pinned ordered TIE/WELL combiner.  The optional
IOVSS join is a counterfactual net union, not proof of a physical connection.
"""

import argparse
from collections import defaultdict
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re


class ContractError(ValueError):
    pass


def quantity(value):
    match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:e[+-]?\d+)?)(meg|[tgkmunpf]?)", value.lower())
    if not match:
        raise ContractError(f"Unsupported quantity: {value}")
    scale = {"": 0, "t": 12, "g": 9, "meg": 6, "k": 3, "m": -3,
             "u": -6, "n": -9, "p": -12, "f": -15}
    try:
        result = Decimal(match[1]) * Decimal(10) ** scale[match[2]]
    except InvalidOperation as exc:
        raise ContractError(value) from exc
    if not result.is_finite() or result <= 0:
        raise ContractError(f"Nonpositive/nonfinite quantity: {value}")
    return result


def parse(text):
    lines = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("*"):
            continue
        if line.startswith("+"):
            if not lines:
                raise ContractError("Orphan continuation")
            lines[-1] += " " + line[1:]
        else:
            lines.append(line)
    cells, global_nets = {}, set()
    cell = None
    for line in lines:
        words = line.lower().split()
        if words[0] == ".global":
            global_nets.update(words[1:])
        elif words[0] == ".subckt":
            if cell or len(words) < 3 or words[1] in cells:
                raise ContractError("Invalid/duplicate subcircuit")
            cell = words[1]
            cells[cell] = {"ports": words[2:], "lines": []}
            if len(set(words[2:])) != len(words[2:]):
                raise ContractError("Duplicate formal port")
        elif words[0] == ".ends":
            if not cell or (len(words) > 1 and words[1] != cell):
                raise ContractError("Mismatched .ends")
            cell = None
        elif words[0] == ".end" and cell is None:
            continue
        elif cell and not words[0].startswith("."):
            cells[cell]["lines"].append(words)
        else:
            raise ContractError(f"Unsupported directive/outside body: {line}")
    if cell:
        raise ContractError("Unclosed subcircuit")
    return cells, global_nets


def flatten_taps(text, top):
    cells, global_nets = parse(text)
    result = []
    top = top.lower()
    if top not in cells:
        raise ContractError("Missing top")

    def visit(name, nets, scope, ancestry):
        if name in ancestry:
            raise ContractError("Recursive subcircuit")
        definition = cells[name]
        if len(nets) != len(definition["ports"]):
            raise ContractError("Subcircuit terminal count mismatch")
        mapping = dict(zip(definition["ports"], nets, strict=True))

        def net(token):
            if token in mapping:
                return mapping[token]
            if token in global_nets or token.endswith("!") or token == "0":
                return token
            return scope + "/" + token

        for words in definition["lines"]:
            words = [word for word in words if word != "/"]
            params_start = next((i for i, w in enumerate(words) if "=" in w), len(words))
            terminals, params = words[:params_start], words[params_start:]
            if len(terminals) < 2:
                raise ContractError("Malformed device")
            model = terminals[-1]
            if model in {"ptap1", "ntap1"}:
                if len(terminals) != 4:
                    raise ContractError("Tap must have exactly two ordered terminals")
                values = {}
                for param in params:
                    if param.count("=") != 1:
                        raise ContractError("Malformed parameter")
                    key, value = param.split("=")
                    if key in values:
                        raise ContractError("Duplicate parameter")
                    values[key] = value
                if "a" not in values or ("p" in values) == ("perim" in values):
                    raise ContractError("Require explicit A and exactly one P/Perim")
                # Pinned custom_reader.lvs:map_resistor_params uses explicit
                # A/P ahead of legacy W/L and does not compare R for taps.
                # Accept only this known metadata; never silently drop M/S or
                # an unknown parameter that might change instance semantics.
                if set(values) - {"a", "p", "perim", "r", "w", "l"}:
                    raise ContractError("Unsupported tap parameter/multiplier")
                if ("w" in values) != ("l" in values):
                    raise ContractError("Legacy tap W/L must appear together")
                for key in ("r", "w", "l"):
                    if key in values:
                        quantity(values[key])
                area = quantity(values["a"]) * Decimal("1e12")
                perimeter = quantity(values.get("p", values.get("perim"))) * Decimal("1e6")
                result.append({"instance": scope + "/" + terminals[0], "model": model,
                               "tie": net(terminals[1]), "well": net(terminals[2]),
                               "area_um2": area, "perimeter_um": perimeter})
            elif words[0].startswith("x"):
                if model in cells:
                    if params:
                        raise ContractError("Parameterized/multiplied subcircuit is unsupported")
                    visit(model, [net(n) for n in terminals[1:-1]],
                          scope + "/" + terminals[0], ancestry + (name,))
                elif model not in {"rppd", "rhigh", "rsil", "dantenna", "dpantenna"}:
                    raise ContractError(f"Unknown X model: {model}")

    visit(top, cells[top]["ports"], top, ())
    return result


def combine(taps, aliases=None):
    aliases = aliases or {}
    grouped = defaultdict(lambda: {"area_um2": Decimal(0), "perimeter_um": Decimal(0), "instances": []})
    for tap in taps:
        key = (tap["model"], aliases.get(tap["tie"], tap["tie"]),
               aliases.get(tap["well"], tap["well"]))
        item = grouped[key]
        item["area_um2"] += tap["area_um2"]
        item["perimeter_um"] += tap["perimeter_um"]
        item["instances"].append(tap["instance"])
    return [{"model": key[0], "tie": key[1], "well": key[2], **value}
            for key, value in sorted(grouped.items())]


def audit(reference, flat, deep, top="sg13g2_IOPadVdd"):
    ref_taps = flatten_taps(reference, top)
    flat_taps = flatten_taps(flat, top)
    deep_taps = flatten_taps(deep, top)
    joined = combine(flat_taps, {"iovss$1": "iovss"})
    expected = combine(ref_taps)
    comparisons = []
    for tie in ("iovss", "vss"):
        lhs = [t for t in joined if t["model"] == "ptap1" and t["tie"] == tie]
        rhs = [t for t in expected if t["model"] == "ptap1" and t["tie"] == tie]
        if len(lhs) != 1 or len(rhs) != 1:
            raise ContractError(f"Require one combined ptap per tie: {tie}")
        comparisons.append({"tie": tie, "area_delta_um2": lhs[0]["area_um2"] - rhs[0]["area_um2"],
                            "perimeter_delta_um": lhs[0]["perimeter_um"] - rhs[0]["perimeter_um"],
                            "parameters_equal": all(lhs[0][k] == rhs[0][k] for k in ("area_um2", "perimeter_um"))})
    return {"status": "DIAGNOSTIC_ONLY_STRICT_LVS_OPEN", "reference_combined": expected,
            "flat_original": flat_taps, "deep_original": deep_taps,
            "flat_counterfactual_join": joined, "parameter_comparisons": comparisons,
            "counterfactual_assumptions": ["Only external metal connectivity changes; tap-recognition masks and extracted tap parameters remain fixed.",
                                           "TIE and WELL ordering remains unchanged; the pinned parallel combiner sums A and P.",
                                           "The iovss$1-to-iovss alias is hypothetical; this audit proves no physical join or well-net equivalence."],
            "lvs_accepted": False, "full_chip_lvs_accepted": False, "manufacturing_approval": False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("reference", "flat", "deep", "output"):
        parser.add_argument("--" + option, required=True, type=Path)
    args = parser.parse_args()
    sources = [args.reference, args.flat, args.deep, Path(__file__)]
    if args.output.resolve() in {p.resolve() for p in sources}:
        raise ContractError("Output cannot overwrite an input")
    result = audit(*(p.read_text() for p in sources[:3]))
    result["input_sha256"] = {str(p.resolve()): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources}
    with args.output.open("x") as handle:
        json.dump(result, handle, indent=2, default=lambda v: format(v, "f"))
        handle.write("\n")


if __name__ == "__main__":
    main()
