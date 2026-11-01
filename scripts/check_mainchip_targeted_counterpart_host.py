"""Actual inherited host gates plus targeted clear/transport refusal controls."""
import ast
import base64
import copy
import hashlib
import inspect
import json
import os
import tempfile
import types
import unittest
import zlib
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import cloud_mainchip_targeted_counterpart_routing as host
import mainchip_targeted_counterpart_routing as core

ROOT = host.ROOT

def fixture():
    config, plan, scope = host.inputs_scope()
    labels = ["bulk-postdrt-version", "bulk-postdrt-ldd"] + [
        "bulk-postdrt-route-continuation-" + x if x in host.original.plan.PREPARATION else "bulk-postdrt-" + x
        for x in host.original.plan.PHASES]
    commands = [dict(label=x, returncode=0) for x in labels]
    argv = ["/work/engine/openroad", "-no_init", "-exit", "-python",
            "/work/tail-source/scripts/mainchip_targeted_counterpart_routing_native.py"]
    record = dict(label="bulk-postdrt-stale-wire-clear", argv=argv, returncode=0, pid=123,
                  supervision_failure=None, minimum_available_kib=2097152,
                  maximum_group_rss_kib=10485760, elapsed_seconds=1.0, requested_timeout_seconds=1200,
                  process_group_cleanup=dict(signals=[], remaining_live=[], remaining_nonrunning=[]),
                  last_memory_sentinel_sample=dict(available_kib=3000000, group_rss_kib=1024),
                  memory_read_error=None, memory_terminal_resolution=None,
                  stdout_bytes=0, stderr_bytes=0, stdout_sha256=hashlib.sha256(b"").hexdigest(),
                  stderr_sha256=hashlib.sha256(b"").hexdigest())
    row = dict(label="bulk-postdrt-stale-wire-clear", argv=argv, returncode=0,
               requested_timeout_seconds=1200, supervision_record=record,
               command_evidence=host.command_evidence.validate(record, 1200),
               command_record_pin=host.original.p.pin(host.original.p.encode(record)))
    commands.insert(labels.index("bulk-postdrt-route"), row)
    result = dict(status="COMPLETE_SAVED_DIODE_ROUTING_QUALIFICATION", bounded_cycle_qualified=True,
                  current_repair_antennas_calls=0, current_reconstruction_calls=0, current_route_calls=1,
                  direct_diode_pg_contact_passed=True, candidate=dict(bytes=1, sha256="a" * 64), **core.FLAGS)
    terminal = dict(phase="stale-wire-clear", complete=True, error=None, terminal_errors=[], **core.FLAGS)
    inner = dict(status="COMPLETE_SAVED_DIODE_ROUTING_ENGINE", terminal_errors=[], native_complete=True,
                 route_cycle=dict(complete=True, terminal_errors=[],
                                  phases={x: "complete" for x in host.original.plan.PHASES}),
                 saved_diode_routing_result=result, commands=commands, stale_wire_clear=terminal, **core.FLAGS)
    delta = dict(complete=True, original_antenna_plan_preserved=True, all_nonmutable_exact=True,
                 cleared_nets=scope["routing_nets"], original_antenna_nets=608,
                 additional_counterpart_nets=220, **core.FLAGS)
    mutation = dict(scope=scope, input=config["seed_pins"]["fixed_odb"],
                    fixed_snapshot=config["seed_pins"]["fixed_snapshot"], complete=True,
                    all_guides_unchanged=True, removed=scope["routing_nets"], delta=delta, **core.FLAGS)
    return config, plan, scope, inner, mutation

def accept(config, plan, scope, inner, mutation):
    return host.accept_result(inner, mutation, config, plan, scope, host.original.plan.accept_native_result)

class Controls(unittest.TestCase):
    def test_complete_source_projection_and_disabled_authority(self):
        manifest = host.source_gate()
        self.assertIs(type(manifest["native_execution_authorized"]), bool)
        disabled = dict(manifest, native_execution_authorized=False)
        with self.assertRaisesRegex(AssertionError, "disabled"):
            host.authorize(disabled)
        # Explicit source-policy refusal occurs before any inherited native work.
        with mock.patch.object(host, "source_gate", return_value=disabled), \
             mock.patch.object(host, "control_evidence", side_effect=AssertionError("too late")):
            with self.assertRaisesRegex(AssertionError, "disabled"):
                host.perform({}, {}, Path("unused"))
    def test_exact_clear_projection_preserves_original_full_acceptance(self):
        config, plan, scope, inner, mutation = fixture()
        original = copy.deepcopy(inner)
        result = accept(config, plan, scope, inner, mutation)
        self.assertEqual(result["actual_clear_calls"], 1)
        self.assertEqual(result["actual_complete_command_count"], len(inner["commands"]))
        self.assertTrue(result["saved_diode_routing_complete"])
        self.assertEqual(inner, original)
    def test_clear_command_missing_duplicate_reordered_argv_and_budget_rejected(self):
        config, plan, scope, inner, mutation = fixture()
        i = next(i for i, r in enumerate(inner["commands"]) if r["label"] == "bulk-postdrt-stale-wire-clear")
        for change in ("missing", "duplicate", "reorder", "argv", "budget", "status", "record"):
            bad = copy.deepcopy(inner)
            if change == "missing": bad["commands"].pop(i)
            if change == "duplicate": bad["commands"].insert(i, copy.deepcopy(bad["commands"][i]))
            if change == "reorder": bad["commands"][i], bad["commands"][i + 1] = bad["commands"][i + 1], bad["commands"][i]
            if change == "argv": bad["commands"][i]["argv"] = ["other"]
            if change == "budget": bad["commands"][i]["requested_timeout_seconds"] = 14400
            if change == "status": bad["commands"][i]["returncode"] = 7
            if change == "record": bad["commands"][i]["supervision_record"]["returncode"] = 7
            with self.subTest(change=change), self.assertRaises((AssertionError, ValueError)):
                accept(config, plan, scope, bad, mutation)
    def test_original_command_or_physical_failure_is_not_hidden(self):
        config, plan, scope, inner, mutation = fixture()
        for change in ("old-command", "phase", "terminal", "antenna-drc", "PG", "two-routes", "extra-command"):
            bad = copy.deepcopy(inner)
            if change == "old-command": bad["commands"][0]["returncode"] = 7
            if change == "phase": bad["route_cycle"]["phases"]["restored-audit"] = "failed"
            if change == "terminal": bad["terminal_errors"] = [{"error": "retained"}]
            if change == "antenna-drc": bad["saved_diode_routing_result"]["bounded_cycle_qualified"] = False
            if change == "PG": bad["saved_diode_routing_result"]["direct_diode_pg_contact_passed"] = False
            if change == "two-routes": bad["saved_diode_routing_result"]["current_route_calls"] = 2
            if change == "extra-command": bad["commands"].append(dict(label="extra", returncode=0))
            with self.subTest(change=change), self.assertRaises(AssertionError):
                accept(config, plan, scope, bad, mutation)
    def test_native_seed_scope_and_complete_readback_are_required(self):
        config, plan, scope, inner, mutation = fixture()
        for change in ("seed", "snapshot", "scope", "removed", "delta", "guides", "complete", "accepted", "terminal"):
            bad = copy.deepcopy(mutation)
            clone = copy.deepcopy(inner)
            if change == "seed": bad["input"]["sha256"] = "b" * 64
            if change == "snapshot": bad["fixed_snapshot"]["sha256"] = "b" * 64
            if change == "scope": bad["scope"]["routing_nets"].pop()
            if change == "removed": bad["removed"].pop()
            if change == "delta": bad["delta"]["all_nonmutable_exact"] = False
            if change == "guides": bad["all_guides_unchanged"] = False
            if change == "complete": bad["complete"] = False
            if change == "accepted": bad["physical_acceptance"] = True
            if change == "terminal": clone["stale_wire_clear"]["terminal_errors"] = ["retained"]
            with self.subTest(change=change), self.assertRaises(AssertionError):
                accept(config, plan, scope, clone, bad)
    def test_actual_command_bytes_and_both_streams_are_authenticated(self):
        _, _, _, inner, _ = fixture()
        i = next(i for i, r in enumerate(inner["commands"]) if r["label"] == "bulk-postdrt-stale-wire-clear")
        record = inner["commands"][i]["supervision_record"]
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            trace = out / "bulk-postdrt-supervision"
            trace.mkdir()
            stem = trace / "bulk-postdrt-stale-wire-clear"
            Path(str(stem) + ".command.json").write_bytes(host.original.p.encode(record))
            Path(str(stem) + ".stdout").write_bytes(b"")
            Path(str(stem) + ".stderr").write_bytes(b"")
            host.authenticate_clear_streams(inner, out)
            for suffix in (".stdout", ".stderr", ".command.json"):
                path = Path(str(stem) + suffix)
                original = path.read_bytes()
                path.write_bytes(original + b"x")
                with self.subTest(suffix=suffix), self.assertRaises(AssertionError):
                    host.authenticate_clear_streams(inner, out)
                path.write_bytes(original)
    def test_original_host_ast_and_publication_are_preserved(self):
        # Test the exact adapter used in perform, without executing its body.
        adapter = host.inherited.clone(host.inherited.host_perform, INNER=host.INNER)
        bound = adapter(host.original.perform, source_gate=host.source_gate, MANIFEST=host.MANIFEST)
        def constants(code):
            for value in code.co_consts:
                if isinstance(value, types.CodeType):
                    yield from constants(value)
                else:
                    yield value
        old = list(constants(host.original.perform.__code__))
        new = list(constants(bound.__code__))
        self.assertEqual(new, [host.INNER if v == host.inherited.OLD_INNER else v for v in old])
        # CPython interns repeated constants within a code object. Count source
        # occurrences in the AST, while retaining full compiled-constant equality.
        tree = ast.parse(inspect.getsource(host.original.perform))
        occurrences = [n for n in ast.walk(tree) if isinstance(n, ast.Constant)
                       and n.value == host.inherited.OLD_INNER]
        self.assertEqual(len(occurrences), 3)
        for name in ("publish_capsule", "preserve_outputs", "retained_workspace", "reservation",
                     "acquire_current", "acquire_failed", "acquire_reconstruction"):
            self.assertIs(bound.__globals__[name], host.original.perform.__globals__[name])
    def test_real_host_environment_is_required(self):
        original = lambda *args: ["docker", "create", "--network", "none", "image"]
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
            argv = host.inherited.hosted_argv(original, None, None, 1, 1)
        self.assertEqual(argv, ["docker", "create", "--env", "GITHUB_ACTIONS=true", "--network", "none", "image"])
        with mock.patch.dict(os.environ, {"GITHUB_ACTIONS": "false"}):
            with self.assertRaises(AssertionError):
                host.inherited.hosted_argv(original, None, None, 1, 1)
    def test_seed_hasher_is_streaming_and_exact(self):
        path = ROOT / "scripts/mainchip_targeted_counterpart_routing_native.py"
        nodes = [n for n in ast.parse(path.read_text()).body if isinstance(n, ast.FunctionDef) and n.name == "seed_pin"]
        self.assertEqual(len(nodes), 1)
        namespace = dict(hashlib=hashlib)
        exec(compile(ast.Module(body=nodes, type_ignores=[]), str(path), "exec"), namespace)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "synthetic"
            raw = bytes(range(256)) * 8193
            path.write_bytes(raw)
            self.assertEqual(namespace["seed_pin"](path), dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()))
    def test_all_new_controls_bound_to_same_actual_source_and_run(self):
        ctx = dict(source=os.environ["GITHUB_SHA"], run_id=int(os.environ["GITHUB_RUN_ID"]))
        fake_host = dict(source=ctx["source"], run=ctx["run_id"], tests=10, failures=0, errors=0, skips=0, native_executed=False)
        # Scope controls have actually run earlier in this same job. Only this
        # currently running suite's future report is synthetic in this unit.
        real = Path.read_bytes
        target = ROOT / "targeted-host-controls/result.json"
        def read(path):
            return json.dumps(fake_host).encode() if path == target else real(path)
        with mock.patch.object(Path, "read_bytes", read):
            self.assertEqual(host.control_evidence(ctx)["scope"]["tests"], 15)
            with self.assertRaises(AssertionError):
                host.control_evidence(dict(ctx, source="0" * 40))
            with self.assertRaises(AssertionError):
                host.control_evidence(dict(ctx, run_id=ctx["run_id"] + 1))

if __name__ == "__main__":
    assert os.environ.get("GITHUB_ACTIONS") == "true"
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
    out = ROOT / "targeted-host-controls"
    out.mkdir(exist_ok=False)
    report = dict(source=os.environ["GITHUB_SHA"], run=int(os.environ["GITHUB_RUN_ID"]), tests=result.testsRun,
                  failures=len(result.failures), errors=len(result.errors), skips=len(result.skipped),
                  native_executed=False)
    raw = (json.dumps(report, sort_keys=True, indent=2) + "\n").encode()
    (out / "result.json").write_bytes(raw)
    print("TARGET_HOST_INDEX " + json.dumps(dict(name="result.json", bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())))
    print("TARGET_HOST_CHUNK result.json " + base64.b64encode(zlib.compress(raw, 9)).decode())
    raise SystemExit(0 if result.wasSuccessful() else 1)
