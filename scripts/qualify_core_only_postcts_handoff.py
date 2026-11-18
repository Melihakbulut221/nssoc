#!/usr/bin/env python3
"""Regression checks for authenticated CTS handoff and fresh-corner reporting."""
import json
from pathlib import Path
import tempfile
import unittest
import cloud_core_only_postcts as runner

class Handoff(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.old_root = runner.ROOT
        self.addCleanup(setattr, runner, "ROOT", self.old_root)
        runner.ROOT = self.root / "checkout"
        runner.ROOT.mkdir()
        self.netlist = runner.ROOT / "hw/soc/out/core-only-mainchip/synthesis/soc_top.netlist.v"
        self.netlist.parent.mkdir(parents=True)
        self.netlist.write_text("module soc_top; endmodule\n")

    def test_producer_relative_and_absolute_paths(self):
        self.assertEqual(runner.current_path(str(self.netlist.relative_to(runner.ROOT))), self.netlist)
        self.assertEqual(runner.current_path(str(self.netlist)), self.netlist)

    def test_outside_checkout_and_symlink_rejected(self):
        outside = self.root / "outside.v"
        outside.write_text("outside")
        link = runner.ROOT / "escaped.v"
        link.symlink_to(outside)
        for name in ("../outside.v", str(outside), "escaped.v"):
            with self.subTest(name=name), self.assertRaises(AssertionError):
                runner.current_path(name)

    def test_missing_and_directory_rejected(self):
        for name in ("missing.v", "hw", "."):
            with self.subTest(name=name), self.assertRaises(AssertionError):
                runner.current_path(name)

class FreshMetrics(unittest.TestCase):
    corner = "nom_slow_1p08V_125C"
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.step = Path(self.temp.name)
        self.state = self.step / "state_out.json"
        self.state.write_text(json.dumps({"metrics": {
            "timing__setup__ws": 999, "timing__setup_vio__count": 0,
            "timing__setup__ws__corner:nom_fast_1p32V_m40C": -999999}}))
        self.values = {"timing__setup__ws": -0.5, "timing__hold__ws": 0.1,
                       "timing__setup_vio__count": 2, "timing__hold_vio__count": 0,
                       "design__max_slew_violation__count": 3,
                       "design__max_cap_violation__count": 4}
        self.write()

    def write(self, extra=None):
        raw = {k + "__corner:" + self.corner: v for k, v in self.values.items()}
        raw.update(extra or {})
        (self.step / "or_metrics_out.json").write_text(json.dumps(raw))

    def test_only_native_measurements_are_used(self):
        metrics, path = runner.fresh_corner_metrics(self.state, self.corner)
        self.assertEqual(metrics, self.values)
        self.assertEqual(path.name, "or_metrics_out.json")

    def test_stale_state_cannot_fill_missing_native_measurement(self):
        del self.values["timing__setup__ws"]
        self.write()
        with self.assertRaises(AssertionError):
            runner.fresh_corner_metrics(self.state, self.corner)

    def test_missing_native_file_cannot_fall_back_to_state(self):
        (self.step / "or_metrics_out.json").unlink()
        with self.assertRaises(FileNotFoundError):
            runner.fresh_corner_metrics(self.state, self.corner)

    def test_wrong_corner_is_rejected(self):
        self.write({"timing__hold__ws__corner:nom_fast_1p32V_m40C": 5})
        with self.assertRaises(AssertionError):
            runner.fresh_corner_metrics(self.state, self.corner)

    def test_invalid_native_numbers_are_rejected(self):
        for key, value in (("timing__setup__ws", float("nan")),
                           ("timing__hold__ws", float("inf")),
                           ("timing__hold_vio__count", -1),
                           ("timing__hold_vio__count", 0.5),
                           ("timing__hold_vio__count", False)):
            saved = dict(self.values)
            self.values[key] = value
            self.write()
            with self.subTest(key=key, value=value), self.assertRaises(AssertionError):
                runner.fresh_corner_metrics(self.state, self.corner)
            self.values = saved

if __name__ == "__main__":
    unittest.main(verbosity=2)
