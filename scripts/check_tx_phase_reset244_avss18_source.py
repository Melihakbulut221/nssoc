#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted source controls: actual power-loop AST, authenticated report inputs; no CAD."""
import ast, copy, hashlib, json, os, sys
from collections import Counter
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "hw/soc/flow"))
import make_pcie_tx_phase_reset244_avss18_v1 as g
OUT = ROOT / "hw/soc/out/tx-phase-reset244-avss18-source-controls"
SCALAR = {"device", "net", "source_layer", "actual_pin_um", "escape_lane_um", "escape_y_um"}
MIM = {"device", "plus_net", "minus_net", "plus_native_plate_um", "minus_native_plate_um",
       "plus_contact_outside_native_mim", "plus_escape_um", "minus_escape_um"}

def digest(b):
    return hashlib.sha256(b).hexdigest()

def terminals(report):
    devices = {v["name"]: v for v in report["instances"]}
    assert len(devices) == 334 and len(report["routes"]) == 586
    result = {"DIV_AVDD": [], "AVSS": []}; count = Counter()
    for row in report["routes"]:
        d = devices[row["device"]]; rid = d["placement_row"]
        if set(row) == SCALAR:
            count["scalar"] += 1
            assert d["kind"] in ("hbt", "resistor")
            entries = [(row["net"], row["escape_lane_um"], row["escape_y_um"])]
        else:
            assert set(row) == MIM and d["kind"] == "capacitor"
            assert row["plus_contact_outside_native_mim"] is True
            count["mim"] += 1
            entries = [(row[k+"_net"], *row[k+"_escape_um"]) for k in ("plus", "minus")]
        for net, x, y in entries:
            if net in result:
                result[net].append((rid, x, y))
    assert count == dict(scalar=578, mim=8)
    assert {k: len(v) for k, v in result.items()} == dict(DIV_AVDD=61, AVSS=85)
    return result

def power_plan(main_text, report):
    tree = ast.parse(main_text); assert len(tree.body) == 1
    main = tree.body[0]; assert isinstance(main, ast.FunctionDef) and main.name == "main"
    loops = [(i, node) for i, node in enumerate(main.body) if isinstance(node, ast.For)
             and isinstance(node.target, ast.Tuple)
             and [v.id for v in node.target.elts if isinstance(v, ast.Name)] == ["net", "trunk_x"]]
    assert len(loops) == 1
    i, loop = loops[0]; census = main.body[i+1]
    assert isinstance(census, ast.If) and "power_straps" in ast.unparse(census.test)
    functions = [n for n in main.body if isinstance(n, ast.FunctionDef) and n.name == "power_via"]
    assert len(functions) == 1
    assignments = [n for n in functions[0].body if isinstance(n, ast.Assign)
                   and len(n.targets) == 1 and isinstance(n.targets[0], ast.Name)
                   and n.targets[0].id == "parameters"]
    assert len(assignments) == 1
    params = compile(ast.Expression(assignments[0].value), "<actual-power-via-parameters>", "eval")
    straps, vias = [], []
    def rectangle(layer, net, x1, y1, x2, y2, role):
        # Match the frozen power_rect argument normalization; no native shapes.
        straps.append(dict(net=net, layer=layer, role=role,
                           rect_um=[min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)]))
    def via(bottom, upper, x, y, net, role):
        parameters = eval(params, {"__builtins__": {}, "dict": dict}, {"bottom": bottom, "upper": upper})
        vias.append(dict(net=net, role=role, parameters=parameters, center_um=[x, y]))
    ns = dict(buses=copy.deepcopy(report["local_buses"]), terminals=terminals(report),
              row_starts={int(k): v for k, v in report["row_starts_um"].items()},
              GROUP_COUNT=15, power_straps=straps, power_rect=rectangle, power_via=via)
    block = ast.fix_missing_locations(ast.Module(body=[copy.deepcopy(loop), copy.deepcopy(census)], type_ignores=[]))
    exec(compile(block, "<actual-extracted-power-loop-no-native>", "exec"), ns)
    return dict(straps=straps, vias=vias)

def expected_plan(report, changed):
    straps = copy.deepcopy(report["additive_power_straps"])
    target = [v for v in straps if v["net"] == "AVSS" and v["role"] == "cross_row_trunk"]
    assert len(target) == 1 and target[0]["layer"] == "TopMetal1" and target[0]["rect_um"] == g.OLD_RECT
    if changed:
        target[0]["rect_um"] = list(g.NEW_RECT)
    vias = [{k: v for k, v in row.items() if k != "bbox_um"} for row in report["additive_power_vias"]]
    assert len(vias) == 178
    assert Counter((v["net"], v["role"]) for v in vias) == {
        ("DIV_AVDD", "actual_branch"): 61, ("AVSS", "actual_branch"): 85,
        ("DIV_AVDD", "trunk_join"): 15, ("AVSS", "trunk_join"): 15,
        ("DIV_AVDD", "public_port"): 1, ("AVSS", "public_port"): 1}
    return dict(straps=straps, vias=vias)

def validate_plan(main_text, report, changed):
    actual = power_plan(main_text, report)
    assert actual == expected_plan(report, changed), "Actual extracted power-loop plan differs"
    return actual

def widened_overlap_guard(main_text, original_main, report):
    witnesses = []
    for side, bound in (("left_um", 106.0), ("right_um", 118.0)):
        bad = copy.deepcopy(report)
        bus = next(v for v in bad["local_buses"] if v["net"] == "AVSS" and v["row"] == 1)
        bus[side] = bound
        power_plan(original_main, bad)  # Old 6 um fits this deliberately narrowed bus.
        try:
            power_plan(main_text, bad)
        except ValueError as e:
            assert str(e) == "Power trunk must overlap existing actual bus extent"
        else:
            raise AssertionError("Widened rectangle was admitted by a stale narrow overlap guard")
        witnesses.append(dict(side=side, boundary_um=bound, old6_fits=True, new18_rejected=True))
    return witnesses

def mutate_report(report, name):
    bad = copy.deepcopy(report)
    target = next(v for v in bad["additive_power_straps"] if v["net"] == "AVSS" and v["role"] == "cross_row_trunk")
    if name == "target_width": target["rect_um"][2] = 120.0
    elif name == "target_center": target["rect_um"][0] += 1; target["rect_um"][2] += 1
    elif name == "target_y": target["rect_um"][3] += 6
    elif name == "target_layer": target["layer"] = "TopMetal2"
    elif name == "target_net": target["net"] = "SUB"
    elif name == "AVDD_width": bad["additive_power_straps"][0]["rect_um"][2] += 6
    elif name == "row_bus": bad["additive_power_straps"][1]["rect_um"][3] += 1
    elif name == "via_center": bad["additive_power_vias"][0]["center_um"][0] += 1
    elif name == "via_array": bad["additive_power_vias"][0]["parameters"]["vt1_columns"] += 1
    elif name == "bounds": bad["bbox_um"][3] += 1
    elif name == "origin": bad["origin_translation_um"][1] += 1
    elif name == "public_port": bad["ports"]["AVSS"]["rect_um"][0] += .1
    elif name == "compact_Nx": next(v for v in bad["instances"] if v["kind"] == "hbt")["nx"] += 1
    elif name == "finite_tap": next(v for v in bad["instances"] if v["kind"] == "substrate_tap")["nets"][0] = "AVSS"
    elif name == "MIM_route": next(v for v in bad["routes"] if "minus_net" in v)["minus_escape_um"][0] += 1
    elif name == "schematic": bad["candidate_source_sha256"] = "0"*64
    else: raise AssertionError(name)
    assert bad != report
    return bad

def main():
    g.host(); method = g.methods()
    assert method["source_controls_authorized"] is True
    assert method["native_generation_authorized"] is method["simulation_authorized"] is method["extraction_authorized"] is False
    full = g.baseline(); flat, original, changed, derivation = g.derivations()
    for text in (flat, original, changed): ast.parse(text)
    assert len(derivation["edits"]) == 3
    assert dict(original_main_sha256=derivation["original_main_sha256"], candidate_main_sha256=derivation["candidate_main_sha256"], flatten_sha256=derivation["flatten_sha256"], edit_count=3) == method["source_derivation"]
    # The old source and every unchanged native function remain frozen; do not
    # manufacture a positive claim about GDS from these source-plan fixtures.
    faults, positives = [], {}
    def reject(name, fn):
        try: fn()
        except (AssertionError, ValueError, KeyError, TypeError) as e:
            faults.append(dict(name=name, rejected=True, exception=type(e).__name__, message=str(e)))
        else: raise AssertionError("Accepted source/report corruption: " + name)
    for polarity in ("p", "n"):
        before = full["variants"][polarity]["generation"]
        g.q.configure(polarity)
        source_rows = g.q.source_rows(ROOT, polarity)
        assert source_rows == before["explicit_source_device_map"]
        assert len(source_rows) == 244
        plan, starts, nets = g.q.placement_plan(source_rows)
        compact = [v for v in before["instances"] if v["kind"] != "substrate_tap"]
        assert all(tuple(v["placement_um"]) == tuple(plan[v["name"]][1:]) for v in compact)
        assert {str(k): v for k, v in starts.items()} == before["row_starts_um"]
        assert {str(k): v for k, v in nets.items()} == before["explicit_row_net_map"]
        old_plan = validate_plan(original, before, False)
        new_plan = validate_plan(changed, before, True)
        candidate = copy.deepcopy(before); candidate["additive_power_straps"] = new_plan["straps"]
        comparison = g.validate_generation(before, candidate, polarity)
        overlap = widened_overlap_guard(changed, original, before)
        report_names = ("target_width", "target_center", "target_y", "target_layer", "target_net", "AVDD_width",
                        "row_bus", "via_center", "via_array", "bounds", "origin", "public_port", "compact_Nx",
                        "finite_tap", "MIM_route", "schematic")
        for name in report_names:
            reject(polarity+"_report_"+name, lambda name=name: g.validate_generation(before, mutate_report(candidate, name), polarity))
        source_edits = (
            ("both_trunks", '9.0 if net == "AVSS" else 3.0', '9.0 if net == "AVSS" else 9.0'),
            ("no_widening", '9.0 if net == "AVSS" else 3.0', '3.0 if net == "AVSS" else 3.0'),
            ("wrong_net", '9.0 if net == "AVSS" else 3.0', '9.0 if net == "DIV_AVDD" else 3.0'),
            ("trunk_y", 'selected[-1]["y_um"] + 3,', 'selected[-1]["y_um"] + 9,'),
            ("bus_width", 'power_rect("TopMetal2", net, left, y - 3, right, y + 3, "row_bus")',
                          'power_rect("TopMetal2", net, left, y - 9, right, y + 9, "row_bus")'),
            ("via_array", '            vt1_columns=2,', '            vt1_columns=3,'),
            ("via_center", 'power_via("TopMetal1", "TopMetal2", trunk_x, y, net, "trunk_join")',
                           'power_via("TopMetal1", "TopMetal2", trunk_x+1, y, net, "trunk_join")'),
        )
        for name, old, new in source_edits:
            mutated = g.q.exact_replace(changed, [(old, new)])
            reject(polarity+"_actual_source_"+name, lambda mutated=mutated: validate_plan(mutated, before, True))
        stale = g.q.exact_replace(changed, [(g.TRUNK_EDITS[2][1], g.TRUNK_EDITS[2][0])])
        reject(polarity+"_actual_source_stale_overlap", lambda: widened_overlap_guard(stale, original, before))
        for name in ("missing_bus", "missing_terminal"):
            bad = copy.deepcopy(before)
            if name == "missing_bus":
                bad["local_buses"].remove(next(v for v in bad["local_buses"] if v["net"] == "AVSS" and v["row"] == 14))
            else:
                bad["routes"].remove(next(v for v in bad["routes"] if "net" in v and v["net"] == "AVSS"))
            reject(polarity+"_actual_input_"+name, lambda bad=bad: validate_plan(changed, bad, True))
        positives[polarity] = dict(report_comparison=comparison, synthetic_report_projection_only=True,
                                  actual_original_plan=old_plan, candidate_source_plan=new_plan, overlap=overlap,
                                  source_map_sha256=digest(json.dumps(source_rows, sort_keys=True).encode()),
                                  native_material_proof=False)
    reject("ambiguous_source_derivation", lambda: g.q.exact_replace("same same", [("same", "new")]))
    reject("missing_source_derivation", lambda: g.q.exact_replace("different", [("same", "new")]))
    assert len(faults) == 54 and len({v["name"] for v in faults}) == 54
    g.methods()
    report = dict(status="PASS_TWO_POLARITY_AVSS18_SOURCE_PLANS_54_FAULTS_NO_NATIVE_PROOF",
                  source_head=os.environ["GITHUB_SHA"], source_method=method, derivation=derivation,
                  baseline_sha256=g.BASELINE_SHA, polarity=positives, faults=faults,
                  native_execution=False, native_geometry_proved=False, native_DRC_LVS_RC_passed=False,
                  electrical_accepted=False, original_electrical_rejection_preserved=True,
                  all31_clock_tree_accepted=False, PLL_connected=False, full_PHY_accepted=False)
    OUT.mkdir(parents=True, exist_ok=False)
    raw = (json.dumps(report, indent=2, allow_nan=False) + "\n").encode()
    (OUT / "result.json").write_bytes(raw)
    print(json.dumps(report, indent=2, allow_nan=False))

if __name__ == "__main__":
    main()
