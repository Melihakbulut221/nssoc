#!/usr/bin/env python3
"""Mutation checks for the explicit core-only test inventory."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from check_core_only_cocotb_inventory import ROOT, MANIFEST, validate

class InventoryTests(unittest.TestCase):
    def setUp(self):
        self.manifest = json.loads(MANIFEST.read_text())
    def test_current_inventory(self):
        self.assertTrue(validate(ROOT, self.manifest))
    def test_reject_retained_exclusion(self):
        m = copy.deepcopy(self.manifest)
        p = "hw/soc/tb/cocotb/Makefile.soc_interfaces"
        m["retained"].remove(p); m["excluded"].append(p); m["excluded"].sort()
        with self.assertRaisesRegex(ValueError, "classification"):
            validate(ROOT, m)
    def test_missing_duplicate_and_overlap(self):
        for mode in ("missing", "duplicate", "overlap"):
            m = copy.deepcopy(self.manifest)
            if mode == "missing": m["retained"].pop()
            elif mode == "duplicate": m["retained"].append(m["retained"][-1])
            else: m["excluded"] = sorted(m["excluded"] + [m["retained"][0]])
            with self.subTest(mode=mode), self.assertRaises(ValueError):
                validate(ROOT, m)
    def test_new_test_requires_review_even_network_test(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for p in self.manifest["retained"] + self.manifest["excluded"]:
                target = root / p; target.parent.mkdir(parents=True, exist_ok=True); target.touch()
            validate(root, self.manifest)
            for name in ("test_new_retained.py", "test_soc_pcie_new.py"):
                p = root / "hw/soc/tb/cocotb" / name; p.touch()
                with self.subTest(name=name), self.assertRaisesRegex(ValueError, "delta"):
                    validate(root, self.manifest)
                p.unlink()

if __name__ == "__main__":
    unittest.main(verbosity=2)
