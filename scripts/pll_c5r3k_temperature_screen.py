#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Temperature-only screening of the unchanged extracted c5r3k PLL."""
import hashlib
import json
import re
import sys
from pathlib import Path

def sha(text):
    return hashlib.sha256(text.encode()).hexdigest()

def apply_temperature(text, temperature):
    if temperature not in (-40, 125):
        raise ValueError("Only the declared temperature-screen corners are allowed")
    if re.search(r"(?im)^\s*(?:set\s+(?:temp|tnom)\b|altermod\b|\.option[s]?\b[^\n]*\btemp\s*=)", text):
        raise ValueError("Unexpected competing temperature/model override")
    cards = list(re.finditer(r"(?im)^[ \t]*\.temp\b[^\r\n]*", text))
    if len(cards) > 1:
        raise ValueError("Multiple temperature cards")
    replacement = ".temp " + str(temperature)
    if cards:
        hit = cards[0]
        values = hit.group().split()
        if len(values) != 2 or float(values[1]) != 27:
            raise ValueError("Baseline must use the native nominal 27 C temperature")
        start, end, old = hit.start(), hit.end(), hit.group()
    else:
        controls = list(re.finditer(r"(?im)^[ \t]*\.control[ \t]*$", text))
        if len(controls) != 1:
            raise ValueError("Expected one native control block")
        start = end = controls[0].start()
        old = ""
        replacement += "\n"
    changed = text[:start] + replacement + text[end:]
    restored = changed[:start] + old + changed[start + len(replacement):]
    if restored != text:
        raise ValueError("Temperature-only reversibility failed")
    return changed, {"temperature_c": temperature, "old_card": old or None,
        "new_card": replacement.strip(), "original_sha256": sha(text),
        "screen_sha256": sha(changed), "temperature_only_reversible": True,
        "process_corner_changed": False, "supply_changed": False,
        "scope": "Temperature-only acquisition screen; not full PVT or device safety"}

def validate_temperature(log, expected):
    values = [float(x) for x in re.findall(r"\bTEMP\s*=\s*([-+0-9.eE]+)", log)]
    if not values or any(abs(x - expected) > 1e-6 for x in values):
        raise ValueError("Missing or inconsistent simulator temperature readback")
    return values

def selftest():
    import unittest
    class Tests(unittest.TestCase):
        def test_temperature_only(self):
            for t in (-40, 125):
                for card in ("", ".temp 27\n", ".TEMP 2.7e1\n"):
                    original = "title\n" + card + ".tran 3.125e-13 1e-06\n.control\nrun\n.endc\n.end\n"
                    changed, report = apply_temperature(original, t)
                    self.assertIn(".temp " + str(t), changed)
                    self.assertIn(".tran 3.125e-13 1e-06", changed)
                    self.assertTrue(report["temperature_only_reversible"])
        def test_rejections(self):
            for text in (".temp 27\n.temp 27\n.control\n", ".temp 125\n.control\n",
                         ".control\nset temp=27\n", ".options temp=27\n.control\n",
                         ".control\n.control\n", ".temp 27 125\n.control\n"):
                with self.subTest(text=text), self.assertRaises(ValueError):
                    apply_temperature(text, 125)
            with self.assertRaises(ValueError):
                apply_temperature(".control\n", 28)
        def test_readback(self):
            for t in (-40,125):
                self.assertEqual(validate_temperature("Doing analysis at TEMP = %s and TNOM = 27"%t,t),[t])
            for log in ("", "TEMP = 27", "TEMP = 125\nTEMP = 27"):
                with self.subTest(log=log), self.assertRaises(ValueError):
                    validate_temperature(log,125)
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Tests))
    return 0 if result.wasSuccessful() else 1

def main():
    mode = sys.argv[1]
    if mode == "selftest":
        return selftest()
    path, temp, output = Path(sys.argv[2]), int(sys.argv[3]), Path(sys.argv[4])
    if mode == "prepare":
        changed, record = apply_temperature(path.read_text(), temp)
        path.write_text(changed)
    elif mode == "verify":
        record = {"requested_temperature_c": temp,
                  "native_temperature_readbacks_c": validate_temperature(path.read_text(), temp),
                  "temperature_verified": True}
    else:
        raise ValueError("Unknown mode")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
