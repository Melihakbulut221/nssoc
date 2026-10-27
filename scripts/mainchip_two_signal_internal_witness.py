#!/usr/bin/env python3
"""Disabled source derivation and strict diagnostic witness interpretation.

No engine/build/route launch occurs here. A complete parse is a diagnostic only.
The native observer must be separately compiled/qualified at the pinned source.
"""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

SOURCE = "dcf36133a369abc8f3c5e5738cd4d82e4903c0e0"
ORIGINAL_SHA = "fa5c6c23a992648c5282ed99ecb03a92bee9187dd55b9630809a5da41f18a3f5"
NAMES = ("net36993", "net459", "clknet_5_29__leaf_u_ibex.clk")
STAGES = ("imported", "before_dr", "after_dr", "after_writer")
MAX_BYTES = 64 * 1024 * 1024
MAX_ROWS = 200000
MAX_MATERIAL = 10000
ROOT = Path(__file__).resolve().parent.parent
PRIMARY = "docs/evidence/mainchip-two-signal-current-readback-bounded-diagnosis-20261028-primary/TritonRoute.cpp"
HEADER = "hw/soc/flow/MainchipInternalWitness.h"
METHOD = "scripts/mainchip-two-signal-internal-witness-methods.json"

def require(ok, reason):
    if not ok:
        raise ValueError(reason)

def sha(value):
    return hashlib.sha256(value).hexdigest()

def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()

def source_edits():
    call = '  mainchip_witness::observe(getDesign(), db_, "{stage}", !distributed_ && !router_cfg_->SINGLE_STEP_DR);\n'
    return [
        ('#include "drt/TritonRoute.h"\n',
         '#include "drt/TritonRoute.h"\n#include "MainchipInternalWitness.h"\n'),
        ('  initDesign();\n  bool has_routable_nets = false;\n',
         '  initDesign();\n' + call.format(stage="imported") + '  bool has_routable_nets = false;\n'),
        ('  dr();\n  if (!router_cfg_->SINGLE_STEP_DR) {\n    endFR();\n  }\n',
         call.format(stage="before_dr") + '  dr();\n' + call.format(stage="after_dr")
         + '  if (!router_cfg_->SINGLE_STEP_DR) {\n    endFR();\n'
         + '  ' + call.format(stage="after_writer") + '  }\n'),
    ]

def derive(original):
    require(sha(original) == ORIGINAL_SHA, "Original router source hash mismatch")
    text = original.decode()
    for old, new in source_edits():
        require(text.count(old) == 1 and new not in text, "Router insertion anchor mismatch")
        text = text.replace(old, new)
    rebuilt = text
    for old, new in reversed(source_edits()):
        require(rebuilt.count(new) == 1, "Router reversal anchor mismatch")
        rebuilt = rebuilt.replace(new, old)
    require(rebuilt.encode() == original, "Router reversible bytes mismatch")
    return text.encode()

def pairs(items):
    result = {}
    for key, value in items:
        require(key not in result, "Duplicate JSON key")
        result[key] = value
    return result

def integer(value, reason, minimum=None):
    require(type(value) is int and (minimum is None or value >= minimum), reason)
    return value

def rect(value):
    require(type(value) is list and len(value) == 4, "Invalid rectangle schema")
    for v in value:
        integer(v, "Invalid rectangle integer")
    require(value[0] < value[2] and value[1] < value[3], "Nonpositive rectangle")
    return tuple(value)

def keys(row, expected):
    require(type(row) is dict and set(row) == set(expected.split()), "Unexpected witness row fields")

def sequence(rows, key, reason):
    require([r[key] for r in rows] == list(range(len(rows))), reason)

def parse_stage(data, stage):
    require(type(data) is bytes and 0 < len(data) <= MAX_BYTES, "Witness byte budget")
    require(data.endswith(b"\n"), "Truncated witness line")
    lines = data.splitlines()
    require(2 <= len(lines) <= MAX_ROWS, "Witness row budget")
    rows = [json.loads(line, object_pairs_hook=pairs) for line in lines]
    head, tail = rows[0], rows[-1]
    keys(head, "kind schema stage source dbu ordinary_nets special_nets native_nets")
    require(head["kind"] == "stage" and type(head["schema"]) is int and head["schema"] == 1
            and head["stage"] == stage and head["source"] == SOURCE, "Witness stage/source mismatch")
    integer(head["dbu"], "Invalid DBU", 1)
    require(all(type(head[k]) is int for k in ("ordinary_nets", "special_nets", "native_nets"))
            and (head["ordinary_nets"], head["special_nets"], head["native_nets"])
            == (143818, 2, 143820), "Witness census mismatch")
    keys(tail, "kind records_before_complete")
    require(tail == {"kind": "complete", "records_before_complete": len(rows) - 1}
            and type(tail["records_before_complete"]) is int, "Incomplete witness stage")
    position = 1
    nets = {}
    for name in NAMES:
        row = rows[position]; position += 1
        keys(row, "kind name fixed sigtype native_oid native_class terminal_count")
        require(row["kind"] == "net" and row["name"] == name, "Witness net order/identity mismatch")
        fixed = name == NAMES[2]
        require(type(row["fixed"]) is bool and row["fixed"] == fixed
                and row["native_class"] == ("FIXED" if fixed else "ROUTED"), "Witness fixed state mismatch")
        require(row["sigtype"] == ("CLOCK" if fixed else "SIGNAL"), "Witness signal type mismatch")
        integer(row["native_oid"], "Invalid native net OID", 1)
        integer(row["terminal_count"], "Invalid terminal count", 1)
        require(row["terminal_count"] == {NAMES[0]: 9, NAMES[1]: 5, NAMES[2]: 8}[name], "Target terminal count mismatch")
        groups = {"internal": [], "native": [], "raw": []}
        rank = -1
        while position < len(rows) - 1 and rows[position].get("kind") != "end_net":
            item = rows[position]; position += 1
            kind = item.get("kind")
            require(kind in groups and item.get("net") == name, "Witness material ownership mismatch")
            current_rank = {"internal": 0, "raw": 1, "native": 2}[kind]
            require(current_rank >= rank, "Witness material ordering mismatch")
            rank = current_rank
            groups[kind].append(item)
            if kind == "raw":
                keys(item, "kind net ordinal opcode data")
                integer(item["ordinal"], "Invalid raw ordinal", 0)
                integer(item["opcode"], "Invalid opcode", 0)
                require(item["opcode"] <= 255, "Invalid opcode")
                integer(item["data"], "Invalid raw operand")
            else:
                rect(item["rect"])
                integer(item["ordinal"], "Invalid material ordinal", 0)
                integer(item["component"], "Invalid component ordinal", 0)
                l = item["layer"]
                count = 3 if kind == "internal" else 2
                require(type(l) is list and len(l) == count and type(l[-1]) is str
                        and l[-1] and l[-1].isascii(), "Invalid layer identity")
                for v in l[:-1]:
                    integer(v, "Invalid layer number", 0)
                require(l[-2] > 0, "Invalid native layer OID")
                if kind == "native":
                    keys(item, "kind net ordinal component shape_id layer rect")
                    integer(item["shape_id"], "Invalid shape ID", 0)
                else:
                    keys(item, "kind net container ordinal component part layer rect primitive")
                    require(item["container"] in ("shape", "patch", "via"), "Unsupported internal container")
                    p = item["primitive"]
                    require(type(p) is list, "Invalid primitive")
                    if item["container"] == "shape":
                        require(item["part"] == "segment" and item["component"] == 0 and len(p) == 9,
                                "Invalid segment primitive")
                        for v in p: integer(v, "Invalid segment integer")
                        require((p[0] == p[2] or p[1] == p[3]) and p[4] > 0 and min(p[6], p[8]) >= 0,
                                "Invalid segment geometry")
                        r = ((p[0]-p[6], p[1]-p[4]//2, p[2]+p[8], p[3]+p[4]//2)
                             if p[1] == p[3] and p[0] != p[2]
                             else (p[0]-p[4]//2, p[1]-p[6], p[2]+p[4]//2, p[3]+p[8]))
                        require(tuple(item["rect"]) == r, "Segment bbox/primitive mismatch")
                    elif item["container"] == "patch":
                        require(item["part"] == "patch" and item["component"] == 0 and len(p) == 3,
                                "Invalid patch primitive")
                        integer(p[0], "Invalid patch origin"); integer(p[1], "Invalid patch origin")
                        r = rect(p[2])
                        require(tuple(item["rect"]) == (r[0]+p[0], r[1]+p[1], r[2]+p[0], r[3]+p[1]),
                                "Patch bbox/primitive mismatch")
                    else:
                        require(item["part"] in ("lower", "cut", "upper") and len(p) == 3
                                and type(p[0]) is str and p[0], "Invalid via primitive")
                        integer(p[1], "Invalid via origin"); integer(p[2], "Invalid via origin")
        require(position < len(rows) - 1, "Missing net completion")
        end = rows[position]; position += 1
        keys(end, "kind name internal_records native_records raw_pairs")
        require(end == {"kind": "end_net", "name": name,
                        "internal_records": len(groups["internal"]), "native_records": len(groups["native"]),
                        "raw_pairs": len(groups["raw"])}
                and all(type(end[k]) is int for k in ("internal_records", "native_records", "raw_pairs")),
                "Net completion count mismatch")
        require(all(groups[k] for k in groups), "Empty selected net evidence")
        require(max(len(groups["internal"]), len(groups["native"])) <= MAX_MATERIAL, "Material budget")
        sequence(groups["raw"], "ordinal", "Raw opcode sequence mismatch")
        for container in ("shape", "patch", "via"):
            material = [r for r in groups["internal"] if r["container"] == container]
            ids = sorted(set(r["ordinal"] for r in material))
            require(ids == list(range(len(ids))), "Internal ordinal gap")
            for ordinal in ids:
                component = [r for r in material if r["ordinal"] == ordinal]
                sequence(component, "component", "Internal component sequence mismatch")
                if container == "via":
                    require([r["part"] for r in component] == sorted([r["part"] for r in component],
                            key={"lower": 0, "cut": 1, "upper": 2}.get)
                            and set(r["part"] for r in component) == {"lower", "cut", "upper"}
                            and len({canonical(r["primitive"]) for r in component}) == 1,
                            "Incomplete via components")
        ids = sorted(set(r["ordinal"] for r in groups["native"]))
        require(ids == list(range(len(ids))), "Native ordinal gap")
        for ordinal in ids:
            component = [r for r in groups["native"] if r["ordinal"] == ordinal]
            sequence(component, "component", "Native component sequence mismatch")
            require(len({r["shape_id"] for r in component}) == 1, "Native shape ID mismatch")
        nets[name] = {"identity": row, **groups}
    require(position == len(rows) - 1, "Trailing or duplicate net evidence")
    require(len({n["identity"]["native_oid"] for n in nets.values()}) == 3, "Duplicate native net OID")
    layer_join, oid_join = {}, {}
    for net in nets.values():
        for kind in ("internal", "native"):
            for r in net[kind]:
                oid, name = r["layer"][-2:]
                require(layer_join.setdefault(name, oid) == oid and oid_join.setdefault(oid, name) == name,
                        "Layer name/OID mismatch")
    return {"header": head, "nets": nets, "sha256": sha(data), "bytes": len(data)}

def material(rows):
    """Exact native-layer/rectangle multiset, preserving component multiplicity."""
    return Counter((r["layer"][-1], *r["rect"]) for r in rows)

def union(rows):
    """Integer rectangle union; separate multiset results retain representation differences."""
    by_layer = defaultdict(list)
    for r in rows:
        by_layer[r["layer"][-1]].append(rect(r["rect"]))
    result = []
    for layer, boxes in sorted(by_layer.items()):
        events = defaultdict(list)
        for x1, y1, x2, y2 in boxes:
            events[x1].append((1, (y1, y2)))
            events[x2].append((-1, (y1, y2)))
        active, previous_x, previous_ys, run_x = Counter(), None, None, None
        for x in sorted(events):
            if previous_x is not None:
                merged = []
                for (a, b), count in sorted(active.items()):
                    if count <= 0: continue
                    if merged and a <= merged[-1][1]: merged[-1][1] = max(merged[-1][1], b)
                    else: merged.append([a, b])
                ys = tuple(tuple(y) for y in merged)
                if ys != previous_ys:
                    if previous_ys:
                        result.extend((layer, run_x, a, previous_x, b) for a, b in previous_ys)
                    run_x, previous_ys = previous_x, ys
            for change, interval in events[x]:
                active[interval] += change
                require(active[interval] >= 0, "Invalid union sweep")
            previous_x = x
        if previous_ys:
            result.extend((layer, run_x, a, previous_x, b) for a, b in previous_ys)
        require(not any(active.values()), "Unclosed union sweep")
    return result

def compare(stage_bytes):
    require(type(stage_bytes) is dict and tuple(stage_bytes) == STAGES, "Four exact ordered stages required")
    stages = {s: parse_stage(stage_bytes[s], s) for s in STAGES}
    require(len({x["header"]["dbu"] for x in stages.values()}) == 1, "Cross-stage DBU mismatch")
    layer_names, layer_oids, fr_layers = {}, {}, {}
    for stage in STAGES:
        for net in stages[stage]["nets"].values():
            for kind in ("internal", "native"):
                for row in net[kind]:
                    oid, name = row["layer"][-2:]
                    require(layer_names.setdefault(name, oid) == oid and layer_oids.setdefault(oid, name) == name,
                            "Cross-stage native layer identity mismatch")
                    if kind == "internal":
                        require(fr_layers.setdefault(row["layer"][0], (oid, name)) == (oid, name),
                                "Cross-stage internal layer identity mismatch")
    result = {}
    for name in NAMES:
        n = {s: stages[s]["nets"][name] for s in STAGES}
        require(all(n[s]["identity"] == n["imported"]["identity"] for s in STAGES), "Cross-stage net identity mismatch")
        require(all(n[s]["raw"] == n["imported"]["raw"] and n[s]["native"] == n["imported"]["native"]
                    for s in ("before_dr", "after_dr")), "Unexpected native write before writer")
        require(n["after_dr"]["internal"] == n["after_writer"]["internal"], "Writer altered internal witness")
        unions = {s: {k: union(n[s][k]) for k in ("internal", "native")} for s in STAGES}
        require(unions["imported"]["internal"] == unions["imported"]["native"], "Imported native/internal material mismatch")
        output = {
            "fixed": n["imported"]["identity"]["fixed"],
            "internal_changed_during_preparation": n["imported"]["internal"] != n["before_dr"]["internal"],
            "internal_changed_during_dr": n["before_dr"]["internal"] != n["after_dr"]["internal"],
            "internal_material_changed_during_dr": unions["before_dr"]["internal"] != unions["after_dr"]["internal"],
            "emitted_raw_changed": n["imported"]["raw"] != n["after_writer"]["raw"],
            "emitted_material_changed": unions["imported"]["native"] != unions["after_writer"]["native"],
            "internal_final_matches_emitted_material": unions["after_dr"]["internal"] == unions["after_writer"]["native"],
            "internal_final_matches_emitted_multiset": material(n["after_dr"]["internal"]) == material(n["after_writer"]["native"]),
            "counts": {s: {k: len(n[s][k]) for k in ("internal", "native", "raw")} for s in STAGES},
            "canonical_material_sha256": {s: {k: sha(canonical(unions[s][k])) for k in ("internal", "native")} for s in STAGES},
        }
        output["observed_fixed_internal_change_not_emitted"] = (
            output["fixed"] and output["internal_material_changed_during_dr"]
            and not output["emitted_material_changed"] and not output["internal_final_matches_emitted_material"])
        result[name] = output
    return {"status": "COMPLETE_DIAGNOSTIC_ONLY", "physical_acceptance": False, "root_cause_established": False,
            "all_fixed_internal_conservation_claimed": False, "nets": result,
            "stages": {s: {"sha256": v["sha256"], "bytes": v["bytes"]} for s, v in stages.items()},
            "required_external_gates": ["complete immutable source/input/build admission", "all 1691 original clocks",
                 "all non-target native geometry and DEF records", "original-class complete JSON/TR DRC",
                 "original process/resource guards", "exact writer-output ODB/DEF and witness joins"]}

def methods(root=ROOT):
    p = root / METHOD
    m = json.loads(p.read_bytes(), object_pairs_hook=pairs)
    require(m["schema"] == "mainchip-two-signal-internal-witness-source-v1", "Wrong method schema")
    require(type(m["source_controls_authorized"]) is bool, "Invalid source-control authorization")
    for field in ("engine_build_authorized", "native_execution_authorized",
                  "native_routing_authorized", "physical_acceptance", "rc_sta_execution_authorized"):
        require(m[field] is False, "Disabled observer authorization required")
    require(m["source_unit_complete"] is False and m["qualified_engine"] is None, "Unqualified engine boundary")
    for path, expected in m["protected"].items():
        require(not Path(path).is_absolute() and ".." not in Path(path).parts, "Protected path escape")
        f = root
        for part in Path(path).parts:
            f = f / part
            require(not f.is_symlink(), "Protected path symlink")
        require(f.is_file() and not f.is_symlink() and sha(f.read_bytes()) == expected, "Protected source mismatch: " + path)
    return m
