#!/usr/bin/env python3
"""Executable guard qualification, not a chip timing or CAD acceptance test."""
import ast
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
FLOW = ROOT / "hw/soc/pnr/core_only_postcts_flow.py"
tree = ast.parse(FLOW.read_text())
selected = [node for node in tree.body if
            isinstance(node, ast.FunctionDef) and node.name == "protect_script" or
            isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "CLOCK_CHECK" for t in node.targets)]
namespace = {}
exec(compile(ast.Module(body=selected, type_ignores=[]), str(FLOW), "exec"), namespace)
protect = namespace["protect_script"]
guard = (ROOT / "hw/soc/flow/check_timing_derate.tcl").read_text()

class Guards(unittest.TestCase):
    def run_tcl(self, clocks="clk_i", period="20", derate="5.0", propagated="1"):
        fixture = """
set test_clocks {%s}
set test_period %s
set test_propagated %s
proc all_clocks {} {return $::test_clocks}
proc get_clocks {name} {
    if {[lsearch -exact $::test_clocks $name] >= 0} {return $name}
    return {}
}
proc get_property {clock property} {
    if {$property eq "period"} {return $::test_period}
    return $::test_propagated
}
proc set_propagated_clock {clocks} {}
proc read_current_odb {} {}
""" % (clocks, period, propagated)
        if derate is not None:
            fixture += "set ::env(TIME_DERATING_CONSTRAINT) {%s}\n" % derate
        else:
            fixture += "unset -nocomplain ::env(TIME_DERATING_CONSTRAINT)\n"
        script = fixture + protect("read_current_odb\nputs GUARD_PASS\n", guard)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "guard.tcl"
            path.write_text(script)
            return subprocess.run(["tclsh", str(path)], capture_output=True, text=True, timeout=10)

    def test_valid_budget(self):
        result = self.run_tcl()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("GUARD_PASS", result.stdout)
        self.assertIn("early=0.95 late=1.05", result.stdout)

    def test_reject_invalid_constraints(self):
        cases = [
            ({"clocks": "clk_i pcie_clk_i"}, "exactly one clock"),
            ({"clocks": ""}, "exactly one clock"),
            ({"clocks": "eth_rx_clk_i"}, "requires clk_i"),
            ({"period": "21"}, "20 ns"),
            ({"period": "19"}, "20 ns"),
            ({"derate": "5"}, "loses precision"),
            ({"derate": "0.0"}, "five percent"),
            ({"derate": "4.0"}, "five percent"),
            ({"derate": "nonsense"}, "Invalid TIME"),
            ({"derate": None}, "Missing TIME"),
            ({"propagated": "0"}, "PostCTS ideal clock"),
        ]
        for parameters, diagnostic in cases:
            with self.subTest(parameters=parameters):
                result = self.run_tcl(**parameters)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("GUARD_PASS", result.stdout)
                self.assertIn(diagnostic, result.stderr)

    def test_fail_closed_on_changed_native_script(self):
        for native in ("", "read_current_odb\nread_current_odb\n"):
            with self.assertRaises(RuntimeError):
                protect(native, guard)

    def test_ideal_clock_reset_removed(self):
        result = protect("read_current_odb\nunset_propagated_clock [all_clocks]\n", guard)
        self.assertNotIn("unset_propagated_clock", result)
        self.assertIn("set_propagated_clock [all_clocks]", result)
        self.assertLess(result.index("loses precision"), result.index("read_current_odb"))
        self.assertLess(result.index("read_current_odb"), result.index("exactly one clock"))

if __name__ == "__main__":
    unittest.main(verbosity=2)
