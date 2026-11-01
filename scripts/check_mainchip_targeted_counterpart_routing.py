"""Hosted controls using the actual authenticated plan and classification."""
import ast
import copy
import hashlib
import json
import os
import types
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
import mainchip_targeted_counterpart_routing as target

ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "targeted-routing-inputs"

def load(name):
    return json.loads((INPUT / name).read_bytes())

def clone(fn, **updates):
    return types.FunctionType(fn.__code__, dict(fn.__globals__, **updates),
                              fn.__name__, fn.__defaults__, fn.__closure__)

def definition(path, name, namespace):
    source = (ROOT / path).read_text()
    nodes = [n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == name]
    assert len(nodes) == 1
    exec(compile(ast.Module(body=nodes, type_ignores=[]), path, "exec"), namespace)
    return namespace[name]

def setup_data():
    plan = load("insertion_plan.json")
    scope = target.build_scope(plan, load("counterparts.json"), load("summary.json"))
    return plan, scope

def fixture():
    plan, scope = setup_data()
    def row(kind="ROUTED", signal="SIGNAL"):
        return dict(identity=dict(sigtype=signal, terminals=[["original", "Y"]]),
                    encoded=dict(wire_present=True, metadata=kind, paths=[kind]),
                    wire=dict(pin=dict(bytes=8, sha256="original"), opcode_count=2))
    nets = {name: row("ROUTED") for name in scope["antenna_nets"]}
    nets.update({name: row("FIXED") for name in scope["counterpart_nets"]})
    nets.update({name: row("FIXED", "CLOCK") for name in scope["protected_nets"]})
    nets["TEST_UNOWNED"] = row("FIXED")
    nets["TEST_POWER"] = row("FIXED", "POWER")
    before = dict(nets=nets, instances={"inst": {"master": "cell", "location": [1, 2]}},
                  masters={"cell": {"pins": ["Y"]}}, immutable={"PG": [3, 4]}, block={"dbu": 1000},
                  protected=scope["protected_nets"], diode_template={"master": "diode"},
                  clock_record_pins={"all": "unchanged"}, def_pin="before")
    after = copy.deepcopy(before)
    after["def_pin"] = "after"
    empty = dict(bytes=4, sha256="empty")
    for name in scope["routing_nets"]:
        after["nets"][name]["encoded"].update(metadata="ROUTED", wire_present=False, paths=[])
        after["nets"][name]["wire"] = dict(pin=empty, opcode_count=0)
    return plan, scope, before, after, empty

def routed_fixture():
    plan, scope, before, _, _ = fixture()
    for name in scope["counterpart_nets"]:
        before["nets"][name]["encoded"].update(metadata="ROUTED", paths=["ROUTED"])
    after = copy.deepcopy(before)
    after["def_pin"] = "routed"
    for name in scope["routing_nets"]:
        after["nets"][name]["wire"]["pin"]["sha256"] = "different:" + name
    return plan, scope, before, after

def original_same_base():
    namespace = dict(require=target.require, exact=target.exact)
    return definition("scripts/mainchip_bulk_postdrt_antenna.py", "same_base", namespace)

class Controls(unittest.TestCase):
    def test_source_and_actual_input_pins(self):
        config = json.loads((ROOT / "scripts/mainchip-targeted-counterpart-routing-inputs.json").read_bytes())
        self.assertIs(type(config["native_execution_authorized"]), bool)
        for name, pin in config["source_files"].items():
            raw = (ROOT / name).read_bytes()
            self.assertEqual((len(raw), hashlib.sha256(raw).hexdigest()), (pin["bytes"], pin["sha256"]))
        for name, pin in config["inputs"].items():
            raw = (INPUT / name).read_bytes()
            self.assertEqual((len(raw), hashlib.sha256(raw).hexdigest()), (pin["bytes"], pin["sha256"]))
        for name in ("scripts/mainchip_targeted_counterpart_routing_native.py",
                     "scripts/mainchip_targeted_counterpart_routing_inner.py"):
            compile((ROOT / name).read_bytes(), name, "exec")
    def test_actual_complete_scope(self):
        plan = load("insertion_plan.json")
        original = copy.deepcopy(plan)
        scope = target.build_scope(plan, load("counterparts.json"), load("summary.json"))
        self.assertEqual(plan, original)
        self.assertEqual([len(scope[k]) for k in ("antenna_nets", "counterpart_nets", "routing_nets", "protected_nets")],
                         [608, 220, 828, 1691])
        self.assertEqual(len(plan["attachments"]), 1351)
    def test_original_plan_cannot_be_relabelled_or_fabricated(self):
        plan, scope = setup_data()
        for change in ("mutable", "attachment", "protected", "unrelated"):
            bad = copy.deepcopy(plan)
            if change == "mutable": bad["mutable_nets"].append(scope["counterpart_nets"][0])
            if change == "attachment": bad["attachments"]["fabricated"] = scope["counterpart_nets"][0]
            if change == "protected": bad["protected_nets"].pop()
            if change == "unrelated": bad["unrelated"] = "changed"
            with self.subTest(change=change), self.assertRaises(AssertionError):
                target.validate_scope(scope, bad)
    def test_counterpart_evidence_is_not_blanket_authority(self):
        plan = load("insertion_plan.json")
        for change in ("duplicate", "fixed-original", "missing-witness", "clock", "owned", "authorized"):
            rows = load("counterparts.json")
            if change == "duplicate": rows[1]["net"] = rows[0]["net"]
            if change == "fixed-original": rows[0]["original_class"] = "FIXED"
            if change == "missing-witness": rows[0]["witnesses"].pop()
            if change == "clock": rows[0]["net"] = plan["protected_nets"][0]
            if change == "owned": rows[0]["net"] = plan["mutable_nets"][0]
            if change == "authorized": rows[0]["route_mutation_authorized"] = True
            with self.subTest(change=change), self.assertRaises(AssertionError):
                target.build_scope(plan, rows, load("summary.json"))
    def test_exact_clear_828_preserves_original_plan(self):
        plan, scope, before, after, empty = fixture()
        original = copy.deepcopy(plan)
        result = target.clear_delta(before, after, plan, scope, empty)
        self.assertEqual(len(result["cleared_nets"]), 828)
        self.assertEqual(plan, original)
        # Reproduce the real failed native boundary with the actual adapter's
        # saved-record reader; do not relax the unchanged strict delta function.
        reader = definition("scripts/mainchip_targeted_counterpart_routing_native.py",
                            "read_snapshot", {"json": json})
        before["masters"] = {"cell": {"pins": {"Y": {"boxes": [[["Metal2", 1, 2, 3, 4]]]}}}}
        after["masters"] = {"cell": {"pins": {"Y": {"boxes": [[("Metal2", 1, 2, 3, 4)]]}}}}
        with self.assertRaisesRegex(AssertionError, "unchanged snapshot masters"):
            target.clear_delta(before, after, plan, scope, empty)
        def record(value):
            return SimpleNamespace(read_bytes=lambda: json.dumps(value, allow_nan=False).encode())
        saved_before, saved_after = reader(record(before)), reader(record(after))
        self.assertTrue(target.clear_delta(saved_before, saved_after, plan, scope, empty)["complete"])
        for change in ("coordinate", "missing-pin", "unowned-wire"):
            changed = copy.deepcopy(after)
            if change == "coordinate":
                changed["masters"]["cell"]["pins"]["Y"]["boxes"][0][0] = ("Metal2", 9, 2, 3, 4)
            elif change == "missing-pin":
                del changed["masters"]["cell"]["pins"]["Y"]
            else:
                changed["nets"]["TEST_UNOWNED"]["wire"]["opcode_count"] = 0
            with self.subTest(change=change), self.assertRaises(AssertionError):
                target.clear_delta(saved_before, reader(record(changed)), plan, scope, empty)
    def test_clear_rejects_clock_pg_unowned_and_all_snapshot_drift(self):
        plan, scope, before, after, empty = fixture()
        for name in ("TEST_UNOWNED", "TEST_POWER", scope["protected_nets"][0]):
            bad = copy.deepcopy(after)
            bad["nets"][name]["wire"]["opcode_count"] = 0
            with self.subTest(name=name), self.assertRaises(AssertionError):
                target.clear_delta(before, bad, plan, scope, empty)
        for key in ("instances", "masters", "immutable", "block", "protected", "diode_template", "clock_record_pins"):
            bad = copy.deepcopy(after)
            bad[key] = {"changed": True}
            with self.subTest(key=key), self.assertRaises(AssertionError):
                target.clear_delta(before, bad, plan, scope, empty)
    def test_clear_requires_exact_initial_and_final_classes(self):
        plan, scope, before, after, empty = fixture()
        for name in (scope["antenna_nets"][0], scope["counterpart_nets"][0]):
            for change in ("initial-class", "initial-power", "missing-wire", "new-fixed", "new-identity"):
                b, a = copy.deepcopy(before), copy.deepcopy(after)
                if change == "initial-class": b["nets"][name]["encoded"]["metadata"] = "COVER"
                if change == "initial-power": b["nets"][name]["identity"]["sigtype"] = "POWER"
                if change == "missing-wire": b["nets"][name]["encoded"]["wire_present"] = False
                if change == "new-fixed": a["nets"][name]["encoded"]["metadata"] = "FIXED"
                if change == "new-identity": a["nets"][name]["identity"]["terminals"].append(["new", "A"])
                with self.subTest(name=name, change=change), self.assertRaises(AssertionError):
                    target.clear_delta(b, a, plan, scope, empty)
    def test_complete_route_delta_with_original_same_base(self):
        plan, scope, before, after = routed_fixture()
        original = copy.deepcopy(plan)
        result = target.route_delta(before, after, plan, scope, original_same_base())
        self.assertEqual(len(result["changed_nets"]), 828)
        self.assertEqual(len(result["changed_counterparts"]), 220)
        self.assertEqual(plan, original)
    def test_original_608_diodes_still_require_route_changes(self):
        plan, scope, before, after = routed_fixture()
        name = scope["antenna_nets"][0]
        after["nets"][name] = copy.deepcopy(before["nets"][name])
        with self.assertRaisesRegex(AssertionError, "each diode owner"):
            target.route_delta(before, after, plan, scope, original_same_base())
    def test_counterpart_can_restore_identical_valid_wire(self):
        plan, scope, before, after = routed_fixture()
        for name in scope["counterpart_nets"]:
            after["nets"][name] = copy.deepcopy(before["nets"][name])
        result = target.route_delta(before, after, plan, scope, original_same_base())
        self.assertEqual(len(result["changed_nets"]), 608)
        self.assertEqual(result["changed_counterparts"], [])
    def test_routed_snapshot_refuses_every_unowned_change_and_partial_route(self):
        plan, scope, before, after = routed_fixture()
        for change in ("clock", "power", "other", "instance", "master", "immutable", "block",
                       "identity", "metadata", "empty-wire", "empty-opcodes", "missing-net"):
            bad = copy.deepcopy(after)
            net = scope["counterpart_nets"][0]
            if change in ("clock", "power", "other"):
                name = {"clock": scope["protected_nets"][0], "power": "TEST_POWER", "other": "TEST_UNOWNED"}[change]
                bad["nets"][name]["wire"]["opcode_count"] = 99
            elif change in ("instance", "master", "immutable", "block"):
                key = {"instance": "instances", "master": "masters"}.get(change, change)
                bad[key]["new"] = "changed"
            elif change == "identity": bad["nets"][net]["identity"]["terminals"] = []
            elif change == "metadata": bad["nets"][net]["encoded"]["metadata"] = "FIXED"
            elif change == "empty-wire": bad["nets"][net]["encoded"]["wire_present"] = False
            elif change == "empty-opcodes": bad["nets"][net]["wire"]["opcode_count"] = 0
            elif change == "missing-net": del bad["nets"][net]
            with self.subTest(change=change), self.assertRaises(AssertionError):
                target.route_delta(before, bad, plan, scope, original_same_base())
    def test_full_def_validator_receives_routing_scope_and_keeps_protected(self):
        plan, scope = setup_data()
        calls = []
        def original(before, after, owners):
            calls.append((before, after, owners))
            return "unchanged original checker result"
        owners = dict(mutable=plan["mutable_nets"], selected=plan["protected_nets"])
        self.assertEqual(target.scoped_def_delta(b"before", b"after", owners, plan, scope, original),
                         "unchanged original checker result")
        self.assertEqual(calls, [(b"before", b"after",
                                 dict(mutable=scope["routing_nets"], selected=scope["protected_nets"]))])
        with self.assertRaises(AssertionError):
            target.scoped_def_delta(b"", b"", dict(mutable=[], selected=[]), plan, scope, original)
    def test_original_connectivity_validator_covers_all_828_and_1351_diodes(self):
        plan, scope = setup_data()
        selection = target.observation_scope(plan, scope)
        self.assertEqual(selection["attachments"], plan["attachments"])
        namespace = dict(require=target.require, exact=target.exact, FLAGS=target.FLAGS)
        validator = definition("scripts/mainchip_bulk_postdrt_antenna.py", "validate_connectivity", namespace)
        rows = {}
        for net in scope["routing_nets"]:
            ids = [["iterm", inst, "A"] for inst, owner in plan["attachments"].items() if owner == net]
            ids.append(["iterm", "original_driver", "Y"])
            rows[net] = {mode: dict(mode=mode, all_pins_share_one_wire_component=True,
                                   all_wire_material_one_component=True,
                                   pins=[dict(scoped_identity=i) for i in ids])
                         for mode in ("positive_area", "closed_boundary")}
        self.assertEqual(validator(rows, selection)["changed_nets"], 828)
        for net in (scope["antenna_nets"][0], scope["counterpart_nets"][0]):
            for mode in ("positive_area", "closed_boundary"):
                bad = copy.deepcopy(rows)
                bad[net][mode]["all_pins_share_one_wire_component"] = False
                with self.subTest(net=net, mode=mode), self.assertRaises(AssertionError):
                    validator(bad, selection)
        bad = copy.deepcopy(rows)
        inst, net = next(iter(plan["attachments"].items()))
        bad[net]["positive_area"]["pins"] = [x for x in bad[net]["positive_area"]["pins"]
                                           if x["scoped_identity"] != ["iterm", inst, "A"]]
        with self.assertRaises(AssertionError):
            validator(bad, selection)
    def test_native_phase_binding_does_not_mutate_original_namespaces(self):
        plan, scope = setup_data()
        calls = []
        def record(*args):
            calls.append(args)
            return args
        ns = dict(p=SimpleNamespace(same_base=record),
                  router=SimpleNamespace(routing_delta=record), n=SimpleNamespace(original_gate=record),
                  connectivity=record, preserve_owned_routes=record)
        exec("def phase():\n return p,router,n,connectivity,preserve_owned_routes\n", ns)
        original_native = SimpleNamespace(phase=ns["phase"], router=ns["router"],
                                         connectivity=record, preserve_owned_routes=record)
        fake_p = SimpleNamespace(exact=target.exact, same_base=record)
        fake_n = ns["n"]
        namespace = dict(p=fake_p, n=fake_n, native=original_native, SimpleNamespace=SimpleNamespace,
                         scope_core=target, inherited=SimpleNamespace(clone=clone, gate_adapter=lambda f:f))
        bind = definition("scripts/mainchip_targeted_counterpart_routing_native.py", "bind_phase", namespace)
        bound = bind(plan, scope)
        result = bound()
        self.assertIsNot(result[0], fake_p)
        self.assertIsNot(result[1], original_native.router)
        self.assertIs(original_native.phase.__globals__["p"], ns["p"])
        self.assertIs(original_native.router.routing_delta, record)
        for fn in result[3:]:
            if fn is result[3]: fn("db", plan, "out")
            else: fn("db", plan, "out", "restored")
            self.assertEqual(calls[-1][1]["mutable_nets"], scope["routing_nets"])
            self.assertEqual(calls[-1][1]["attachments"], plan["attachments"])
        self.assertEqual(plan, load("insertion_plan.json"))
    def test_inner_refuses_unactivated_source_before_any_native_call(self):
        class DisabledRoot:
            def __truediv__(self, name):
                assert name == "scripts/mainchip-targeted-counterpart-routing-inputs.json"
                return SimpleNamespace(read_bytes=lambda: b'{"native_execution_authorized":false}')
        namespace = dict(p=SimpleNamespace(ROOT=DisabledRoot(), require=target.require), json=json,
                         inherited=SimpleNamespace(source_gate=lambda: self.fail("native source reached")),
                         original=SimpleNamespace(main=lambda: self.fail("native work reached")))
        main = definition("scripts/mainchip_targeted_counterpart_routing_inner.py", "main", namespace)
        with self.assertRaisesRegex(AssertionError, "not activated"):
            main()

if __name__ == "__main__":
    assert os.environ.get("GITHUB_ACTIONS") == "true", "cloud-only controls"
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Controls)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    out = ROOT / "targeted-routing-controls"
    out.mkdir(exist_ok=False)
    plan, scope = setup_data()
    (out / "scope.json").write_text(json.dumps(scope, sort_keys=True, indent=2) + "\n")
    report = dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                  skips=len(result.skipped), native_executed=False, source=os.environ["GITHUB_SHA"],
                  run=int(os.environ["GITHUB_RUN_ID"]), **target.FLAGS)
    (out / "result.json").write_text(json.dumps(report, sort_keys=True, indent=2) + "\n")
    import base64, zlib
    for path in sorted(out.glob("*.json")):
        raw = path.read_bytes()
        print("TARGET_ROUTE_INDEX " + json.dumps(dict(name=path.name, bytes=len(raw),
                                                       sha256=hashlib.sha256(raw).hexdigest())))
        value = base64.b64encode(zlib.compress(raw, 9)).decode()
        for i in range(0, len(value), 10000):
            print("TARGET_ROUTE_CHUNK " + path.name + " " + value[i:i + 10000])
    raise SystemExit(0 if result.wasSuccessful() else 1)
