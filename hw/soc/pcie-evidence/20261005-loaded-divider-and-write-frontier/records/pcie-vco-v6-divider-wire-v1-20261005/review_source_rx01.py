# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent saved-byte/source review; executes no producer or simulator."""
import ast
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path

R = Path.cwd()
B = Path(__file__).resolve().parent


def pin(path):
    p = Path(path)
    return dict(bytes=p.stat().st_size, sha256=hashlib.sha256(p.read_bytes()).hexdigest())


def load(path):
    return json.loads(Path(path).read_text())


def definitions(path):
    text = Path(path).read_text()
    return {
        node.name: ast.get_source_segment(text, node)
        for node in ast.parse(text).body
        if isinstance(node, (ast.FunctionDef, ast.ClassDef))
    }


freeze = load(B / "source-freeze.json")
for path, wanted in freeze["pins"].items():
    assert pin(path) == wanted, path
assert len(freeze["pins"]) == 161
for path, wanted in freeze["new_sources"].items():
    assert pin(R / path) == wanted
bridge = load(B / "characterizer-source-bridge.json")
parent_path, parent_pin = next(iter(bridge["parent"].items()))
new_path, new_pin = next(iter(bridge["new"].items()))
assert pin(parent_path) == parent_pin and pin(new_path) == new_pin
old_defs, new_defs = definitions(parent_path), definitions(new_path)
for name, record in bridge["functions"].items():
    assert old_defs[name] == record["old"].rstrip()
    assert new_defs[name] == record["new"].rstrip()
    value = record["old"]
    for before, after in record["operations"]:
        assert value.count(before) == 1
        value = value.replace(before, after)
    assert value == record["new"]
    for before, after in reversed(record["operations"]):
        assert value.count(after) == 1
        value = value.replace(after, before)
    assert value == record["old"]

fixture = R / "sw/tests/fixtures/pcie_clock_div4_v7_hybrid_v1"
builder_source = ast.parse((R / "scripts/build_pcie_clock_div4_v7_hybrid_v1.py").read_text())
pins = next(ast.literal_eval(n.value) for n in builder_source.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "PINS" for t in n.targets))
compressed = {}
for key, name in dict(anchors="anchors.json", devices="device-location-geometry.json", geometry="wire-component-geometry.json", native="extracted.cir", wires="wires.spice").items():
    data = gzip.decompress((fixture / "inputs" / (name + ".gz")).read_bytes())
    got = dict(bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
    assert got["sha256"] == pins[key]
    compressed[key] = got
for name in ("hybrid-open.spice", "composition.json"):
    assert (fixture / name).read_bytes() == (B / "composed01" / name).read_bytes()
composition = load(fixture / "composition.json")
assert len(composition["records"]) == 91
assert sum(len(r["terminals"]) for r in composition["records"]) == 283
assert sum(t["node"] == "BODY_SUBSTRATE" for r in composition["records"] for t in r["terminals"]) == 85
assert composition["finite_contacts"] == 18 and composition["wire_components"] == 37

recipes = {}
for path in sorted(B.glob("recipe-*.json")):
    row = load(path)
    devices, config = row["devices"], row["config"]
    census = Counter(d["model"] for d in devices)
    assert len(devices) == len({d["path"] for d in devices}) == 455
    assert census["npn13g2"] == 64 and census["ptap1"] + census["ntap1"] == 31
    assert len([d for d in devices if d["path"].startswith("xchain.xdiv.")]) == 91
    assert sum(n == "div_body_substrate" for d in devices if d["path"].startswith("xchain.xdiv.") for n in d["nets"]) == 85
    assert row["vector_count"] == 956
    assert config["step_s"] == 5e-12 and config["stop_s"] == 34e-9
    assert config["window_s"] == [4e-9, 34e-9]
    assert config["wire_resistors"] == 1201 and config["wire_capacitors"] == 1383
    assert config["fixture"][-2:] == ["VDIVBODY div_body_substrate 0 0", "VDIVWREF div_wire_cref 0 0"]
    assert "CLOAD_CLKP clkp 0 50f" in config["fixture"] and "CLOAD_CLKN clkn 0 50f" in config["fixture"]
    recipes[path.name] = dict(pin=pin(path), census=dict(census), vectors=row["vector_count"])
gold = load(B / "recipe-0.6-nominal.json")
disconnect = load(B / "recipe-0.6-disconnect_divider_clock.json")
wrong = load(B / "recipe-0.6-wrong_feedback_modulus.json")
assert gold["devices"] == disconnect["devices"]
assert [a["path"] for a, b in zip(gold["devices"], wrong["devices"]) if a != b] == ["xchain.xfb.xcount.xd2n.xpc", "xchain.xfb.xcount.xd2n.xnc"]

owned = {}
for path in sorted((B / "pytest02").rglob("owned-processes.json")):
    row = load(path)
    assert row["elapsed_watchdog_seconds"] is None
    assert all(p["status"] in ("REAPED_NO_LIVE_MEMBERS", "FAILURE_REAPED") for p in row["processes"])
    if any(p["status"] == "FAILURE_REAPED" for p in row["processes"]):
        assert row["status"] == "CANCELLED"
        assert all(not g["immediate_after_kill"] and not g["identity_reused"] for g in row["cleanup"]["groups"])
    owned[str(path.relative_to(B))] = dict(pin=pin(path), status=row["status"], processes=len(row["processes"]))
assert len(owned) == 4
assert "25 passed" in (B / "source-controls02.log").read_text()
record = dict(
    status="SOURCE_AND_SAVED_CONTROLS_PASS_LAUNCHER01_CANCELLATION_FIX_REQUIRED",
    freeze=pin(B / "source-freeze.json"), method=pin(__file__),
    verified_input_count=len(freeze["pins"]), source_pins=freeze["new_sources"],
    bridge=pin(B / "characterizer-source-bridge.json"), full_function_forward_inverse=list(bridge["functions"]),
    decompressed_fixture_pins=compressed, saved_recipes=recipes, saved_lifecycle_controls=owned,
    tests=dict(passed=25, log=pin(B / "source-controls02.log"), rerun=False),
    findings=[dict(scope="launch_probe01.py only", issue="An outer empty ProcessOwner cancellation flag set between its initial check and inner owner installation does not reach run_native until the full run returns. Use immediate raising handlers outside the actual native owner; retain terminal checks and prove the handoff with real signals before launch.")],
    manual_review="Read complete new characterizer, SPICE topology, test harness and launcher. Strict 73 old schematic-to-91 native correspondence; 62 VCO plus91 divider plus302 CMOS devices. Both RC networks and31 contacts remain, distinct ideal body/wire boundaries are explicit. No ideal oscillator substitution. Private globals clone unchanged collection/measurement/limits. Actual 64 OFF and clean OP checks retained; full455 electrical-screen census required.",
    limitations="Source and existing saved controls only; no SPICE, generation or pytest execution. Metal-only prototype model, explicit ideal body boundaries, schematic CMOS feedback, no qualified PEX, PVT, PLL lock, jitter, BER or full PHY signoff. Teardown control's last inner HEALTHY receipt precedes signal; post-context guard/expected test failure enforce rejection.",
)
(B / "source-review-rx01-findings.json").write_text(json.dumps(record, indent=2) + "\n")
print(json.dumps(dict(status=record["status"], receipt=pin(B / "source-review-rx01-findings.json"))))
