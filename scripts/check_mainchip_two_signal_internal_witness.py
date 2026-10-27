#!/usr/bin/env python3
"""Hosted-only source controls. Synthetic witness rows are not an engine result."""
import copy
import json
from pathlib import Path
import mainchip_two_signal_internal_witness as c

def encode(rows):
    return b"".join(c.canonical(r) + b"\n" for r in rows)

def fixture():
    result = {}
    for stage in c.STAGES:
        rows = [{"kind": "stage", "schema": 1, "stage": stage, "source": c.SOURCE, "dbu": 1000,
                 "ordinary_nets": 143818, "special_nets": 2, "native_nets": 143820}]
        for i, name in enumerate(c.NAMES):
            fixed = i == 2
            rows.append({"kind": "net", "name": name, "fixed": fixed, "sigtype": "CLOCK" if fixed else "SIGNAL", "native_oid": 100+i,
                         "native_class": "FIXED" if fixed else "ROUTED",
                         "terminal_count": [9, 5, 8][i]})
            origin = 100*i
            material = [
                {"kind": "internal", "net": name, "container": "shape", "ordinal": 0, "component": 0,
                 "part": "segment", "layer": [10, 15, "Metal5"], "rect": [origin, -2, origin+10, 2],
                 "primitive": [origin, 0, origin+10, 0, 4, 0, 0, 0, 0]},
                {"kind": "internal", "net": name, "container": "patch", "ordinal": 0, "component": 0,
                 "part": "patch", "layer": [10, 15, "Metal5"], "rect": [origin+10, -2, origin+12, 2],
                 "primitive": [origin, 0, [10, -2, 12, 2]]},
            ]
            for j, (part, layer, rect) in enumerate([
                    ("lower", [10, 15, "Metal5"], [origin+9, -2, origin+13, 2]),
                    ("cut", [11, 16, "Via5"], [origin+10, -1, origin+12, 1]),
                    ("cut", [11, 16, "Via5"], [origin+10, -1, origin+12, 1]),
                    ("upper", [12, 17, "TopMetal1"], [origin+9, -2, origin+13, 2])]):
                material.append({"kind": "internal", "net": name, "container": "via", "ordinal": 0,
                                 "component": j, "part": part, "layer": layer, "rect": rect,
                                 "primitive": ["VIA_M5_TM1", origin+11, 0]})
            rows.extend(material)
            for j, (opcode, data) in enumerate([(0, 15), (1, origin), (2, 0), (1, origin+10)]):
                rows.append({"kind": "raw", "net": name, "ordinal": j, "opcode": opcode, "data": data})
            for j, row in enumerate(material):
                rows.append({"kind": "native", "net": name, "ordinal": j, "component": 0,
                             "shape_id": j+1, "layer": row["layer"][1:], "rect": row["rect"][:]})
            rows.append({"kind": "end_net", "name": name, "internal_records": len(material),
                         "native_records": len(material), "raw_pairs": 4})
        rows.append({"kind": "complete", "records_before_complete": len(rows)})
        result[stage] = encode(rows)
    return result

def mutate(data, stage, choose, action):
    rows = [json.loads(line) for line in data[stage].splitlines()]
    chosen = [r for r in rows if choose(r)]
    assert chosen, "A source-control mutation must reach an actual witness row"
    action(chosen[0])
    data[stage] = encode(rows)

def controls(root=c.ROOT):
    m = c.methods(root)
    original = (root / c.PRIMARY).read_bytes()
    generated = c.derive(original)
    assert c.sha(generated) == m["derived_router_sha256"]
    header = (root / c.HEADER).read_text()
    assert "std::getenv" in header and 'O_EXCL | O_NOFOLLOW' in header
    assert "dbShape::getViaBoxes" in header and "via->getTransform().apply(r)" in header
    assert all(word not in header for word in ("setFixed(", "setWireType(", "removeShape(", "addShape(", "setModified("))
    assert generated.count(b"mainchip_witness::observe(") == 4
    tested = []
    baseline = fixture()
    got = c.compare(baseline)
    assert not got["physical_acceptance"] and not got["root_cause_established"]
    assert all(not n["internal_changed_during_dr"] and n["internal_final_matches_emitted_multiset"]
               for n in got["nets"].values())
    tested.append("complete_synthetic_four_stage_identity")

    # A real parser path representing the specific candidate mechanism, not a claim
    # that this geometry occurred in the historical or future native run.
    changed = copy.deepcopy(baseline)
    for stage in ("after_dr", "after_writer"):
        def move(r):
            r["rect"][1] += 10; r["rect"][3] += 10
            r["primitive"][1] += 10; r["primitive"][3] += 10
        mutate(changed, stage, lambda r: r.get("kind") == "internal"
               and r.get("net") == c.NAMES[2] and r.get("container") == "shape", move)
    result = c.compare(changed)
    assert result["nets"][c.NAMES[2]]["observed_fixed_internal_change_not_emitted"]
    assert not result["physical_acceptance"] and not result["root_cause_established"]
    tested.append("fixed_internal_material_change_with_unchanged_emitted_material")

    written = copy.deepcopy(baseline)
    for stage in ("after_dr", "after_writer"):
        mutate(written, stage, lambda r: r.get("kind") == "internal"
               and r.get("net") == c.NAMES[0] and r.get("container") == "shape", move)
    mutate(written, "after_writer", lambda r: r.get("kind") == "native"
           and r.get("net") == c.NAMES[0] and r.get("ordinal") == 0,
           lambda r: r.update(rect=[0, 8, 10, 12]))
    mutate(written, "after_writer", lambda r: r.get("kind") == "raw"
           and r.get("net") == c.NAMES[0] and r.get("ordinal") == 2,
           lambda r: r.update(data=10))
    result = c.compare(written)
    assert result["nets"][c.NAMES[0]]["internal_material_changed_during_dr"]
    assert result["nets"][c.NAMES[0]]["emitted_material_changed"]
    assert result["nets"][c.NAMES[0]]["emitted_raw_changed"]
    assert result["nets"][c.NAMES[0]]["internal_final_matches_emitted_material"]
    assert not result["physical_acceptance"]
    tested.append("target_internal_change_is_emitted_without_acceptance")

    # Same material with differing rectangle representation must not be called a
    # material change. The separate multiset comparison retains the distinction.
    sample = [{"layer": [15, "Metal5"], "rect": [0, 0, 10, 2]}]
    split = [{"layer": [15, "Metal5"], "rect": [0, 0, 5, 2]},
             {"layer": [15, "Metal5"], "rect": [5, 0, 10, 2]}]
    assert c.union(sample) == c.union(split) and c.material(sample) != c.material(split)
    assert c.union(sample + sample) == c.union(sample) and c.material(sample + sample) != c.material(sample)
    assert c.union(sample) != c.union([{"layer": [15, "Metal5"], "rect": [0, 0, 10, 3]}])
    tested.append("integer_union_with_separate_multiplicity")

    refused = []
    def refusal(label, operation, reason):
        try:
            operation()
        except ValueError as exc:
            assert str(exc) == reason, (label, str(exc), reason)
            refused.append(label)
        else:
            raise AssertionError("Accepted invalid witness: " + label)
    def change(label, choose, action, reason, stage="after_dr"):
        data = copy.deepcopy(baseline)
        mutate(data, stage, choose, action)
        refusal(label, lambda: c.compare(data), reason)
    def iskind(kind):
        return lambda r: r.get("kind") == kind
    change("source", iskind("stage"), lambda r: r.update(source="0"*40), "Witness stage/source mismatch")
    change("stage", iskind("stage"), lambda r: r.update(stage="imported"), "Witness stage/source mismatch")
    change("dbu", iskind("stage"), lambda r: r.update(dbu=2000), "Cross-stage DBU mismatch")
    change("census", iskind("stage"), lambda r: r.update(ordinary_nets=143817), "Witness census mismatch")
    change("complete_count", iskind("complete"), lambda r: r.update(records_before_complete=1), "Incomplete witness stage")
    change("unknown_field", iskind("net"), lambda r: r.update(accepted=True), "Unexpected witness row fields")
    change("name", iskind("net"), lambda r: r.update(name="net999"), "Witness net order/identity mismatch")
    change("fixed", iskind("net"), lambda r: r.update(fixed=True), "Witness fixed state mismatch")
    change("clock_is_not_SIGNAL", lambda r: r.get("kind") == "net" and r.get("name") == c.NAMES[2],
           lambda r: r.update(sigtype="SIGNAL"), "Witness signal type mismatch")
    change("boolean_oid", iskind("net"), lambda r: r.update(native_oid=True), "Invalid native net OID")
    change("net_oid_change", iskind("net"), lambda r: r.update(native_oid=900), "Cross-stage net identity mismatch")
    change("terminal", iskind("net"), lambda r: r.update(terminal_count=8), "Target terminal count mismatch")
    change("owner", iskind("internal"), lambda r: r.update(net="unowned"), "Witness material ownership mismatch")
    change("boolean_coordinate", iskind("internal"), lambda r: r["rect"].__setitem__(0, True), "Invalid rectangle integer")
    change("bbox", iskind("internal"), lambda r: r["rect"].__setitem__(2, 11), "Segment bbox/primitive mismatch")
    change("raw_gap", iskind("raw"), lambda r: r.update(ordinal=5), "Raw opcode sequence mismatch")
    change("opcode", iskind("raw"), lambda r: r.update(opcode=256), "Invalid opcode")
    change("raw_native_write_before_writer", iskind("raw"), lambda r: r.update(data=999), "Unexpected native write before writer")
    change("internal_component_gap", iskind("internal"), lambda r: r.update(component=1), "Invalid segment primitive")
    change("layer_oid", iskind("native"), lambda r: r["layer"].__setitem__(0, 777), "Layer name/OID mismatch")
    change("native_component_gap", iskind("native"), lambda r: r.update(component=1), "Native component sequence mismatch")
    change("counts", iskind("end_net"), lambda r: r.update(native_records=1), "Net completion count mismatch")
    change("via_part", lambda r: r.get("kind") == "internal" and r.get("part") == "lower",
           lambda r: r.update(part="cut"), "Incomplete via components")
    for mode in ("no_completion", "truncated"):
        data = copy.deepcopy(baseline)
        data["after_dr"] = (data["after_dr"].rsplit(b"\n", 2)[0] + b"\n"
                            if mode == "no_completion" else data["after_dr"][:-1])
        refusal(mode, lambda: c.compare(data),
                "Unexpected witness row fields" if mode == "no_completion" else "Truncated witness line")
    data = dict(reversed(list(baseline.items())))
    refusal("stage_order", lambda: c.compare(data), "Four exact ordered stages required")
    data = copy.deepcopy(baseline)
    data["after_dr"] = data["after_dr"].replace(b'"schema":1', b'"schema":1,"schema":1', 1)
    refusal("duplicate_key", lambda: c.compare(data), "Duplicate JSON key")
    refusal("unbound_original_source", lambda: c.derive(original + b"\n"), "Original router source hash mismatch")
    data = copy.deepcopy(changed)
    data["after_writer"] = baseline["after_writer"]
    refusal("writer_internal_mutation", lambda: c.compare(data), "Writer altered internal witness")

    return {"status": "PASS", "scope": "source derivation and explicitly synthetic witness/parser controls",
            "positive_count": len(tested), "refusal_count": len(refused), "positive_cases": tested,
            "refusal_cases": refused, "engine_compiled": False, "native_executed": False,
            "actual_internal_fixed_mutation_observed": False, "physical_acceptance": False}

if __name__ == "__main__":
    print(json.dumps(controls(), sort_keys=True, indent=2))
