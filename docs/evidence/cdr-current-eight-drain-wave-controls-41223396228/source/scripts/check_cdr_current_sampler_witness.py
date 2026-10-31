#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Hosted synthetic tests of query-vs-native-row distinction and exact replay."""
import copy
import os
import unittest
import numpy as np
from cdr_current_sampler_witness import analyze, UI, START, STOP, STEP


def fixture():
    n = round(STOP / STEP)
    t = np.linspace(0., STOP, n + 1, dtype=np.float64)
    columns, aliases = {}, {}
    for tag in "abcd":
        for side, value in (("p", .25), ("n", 0.)):
            logical = "xpd." + tag + "q" + side
            aliases[logical] = logical
            columns["v("+logical+")"] = np.full(t.shape, value, dtype=np.float64)
    for tag in "xy":
        columns["v("+tag+"p)"] = np.full(t.shape, .25, dtype=np.float64)
        columns["v("+tag+"n)"] = np.zeros(t.shape, dtype=np.float64)
    good = dict(samples=765, minimum_signed_margin_v=.25, wrong_sign_samples=0,
                below_100mv_samples=0, maximum_clock_to_valid_s=0.,
                clock_to_valid_by_bit_s=[0.] * 255, passed=True)
    report = dict(case="nominal_early", returncode=0, diagnostics=[], sources_unchanged=True,
        raw_capture=dict(complete_unmodified_rows=True, header_rows=len(t), raw_sha256="1"*64),
        status="PASS_WHOLE_MIM_PD500_LOADED_SCREEN_NOT_CLOSED_LOOP_OR_PHY_SIGNOFF",
        binding=dict(aliases=aliases), expected_samples={x:[1]*255 for x in "abcd"},
        expected_comparisons={x:[1]*255 for x in "xy"},
        sampler_checks={x:copy.deepcopy(good) for x in "abcd"},
        comparisons={x:copy.deepcopy(good) for x in "xy"})
    return t, columns, report


class WitnessTests(unittest.TestCase):
    def test_constant_known_signal_preserves_all_queries(self):
        t, d, r = fixture()
        result = analyze(t, d, r, ["v(xp)"])
        self.assertEqual(result["query_count"], 4590)
        self.assertEqual(result["window_count"], 1530)
        self.assertTrue(all(q["query_signed_margin_v"] == .25 for q in result["queries"]))
        self.assertTrue(all(not w["bad_native_rows"] for w in result["windows"]))
        self.assertFalse(result["electrical_accepted"])
        self.assertEqual(r["status"], result["original_verdict"])
        self.assertTrue(all(f["values"] == [.25] for f in result["native_frames"]))

    def test_interpolated_failure_is_not_a_native_zero(self):
        t, d, r = fixture()
        edge = START + 1.5 * UI
        query = edge + .3 * UI
        k = int(np.argmin(abs(t-query)))
        self.assertLess(abs(t[k]-query), 1e-18)
        # Replace the query row with two symmetric native rows. Neither is zero.
        left, right = query-STEP/4, query+STEP/4
        t = np.concatenate((t[:k], np.array([left, right]), t[k+1:]))
        for name in d:
            d[name] = np.insert(d[name], k, d[name][k])
        d["v(xpd.aqp)"][k:k+2] = [-.125, .125]
        self.assertEqual(query-left, right-query)
        r["raw_capture"]["header_rows"] = len(t)
        delay = float(left-edge+STEP)
        check = r["sampler_checks"]["a"]
        check.update(minimum_signed_margin_v=0., wrong_sign_samples=1,
                     below_100mv_samples=1, maximum_clock_to_valid_s=delay, passed=False)
        check["clock_to_valid_by_bit_s"][0] = delay
        r["status"] = "REJECTED_WHOLE_MIM_PD500_LOADED"
        result = analyze(t, d, r, ["v(xpd.aqp)"])
        q = result["queries"][0]
        self.assertTrue(q["query_is_interpolated"])
        self.assertEqual(q["query_signed_margin_v"], 0.)
        self.assertEqual((q["left_native_row"], q["right_native_row"]), (k, k+1))
        self.assertEqual((q["left_differential_v"], q["right_differential_v"]), (-.125, .125))
        w = result["windows"][0]
        self.assertEqual(w["bad_native_rows"], [k])
        self.assertEqual(w["clock_to_valid_s"], delay)
        self.assertTrue(w["violated"])
        frames = {x["native_row"]: x for x in result["native_frames"]}
        self.assertEqual(frames[k]["values"], [-.125])
        self.assertEqual(frames[k+1]["values"], [.125])
        self.assertFalse(result["original_verdict_changed"])

    def test_saved_failure_cannot_be_silently_recomputed_as_pass(self):
        t, d, r = fixture()
        r["sampler_checks"]["c"]["passed"] = False
        with self.assertRaisesRegex(AssertionError, "original scalar mismatch: sampler_c"):
            analyze(t, d, r)

    def test_changed_delay_vector_is_rejected(self):
        t, d, r = fixture()
        r["comparisons"]["y"]["clock_to_valid_by_bit_s"][17] = STEP
        with self.assertRaisesRegex(AssertionError, "original scalar mismatch: comparator_y"):
            analyze(t, d, r)

    def test_bad_capture_or_missing_vector_is_rejected(self):
        t, d, r = fixture()
        for kind in ("time", "nonfinite", "missing", "rows", "expected"):
            a, b, c = t.copy(), {k:v.copy() for k,v in d.items()}, copy.deepcopy(r)
            if kind == "time": a[10] = a[9]
            if kind == "nonfinite": b["v(yp)"][10] = np.nan
            if kind == "missing": del b["v(yn)"]
            if kind == "rows": c["raw_capture"]["header_rows"] -= 1
            if kind == "expected": c["expected_samples"]["a"][0] = True
            with self.subTest(kind=kind), self.assertRaises(AssertionError):
                analyze(a, b, c)

    def test_simulator_errors_and_partial_capture_are_not_observations(self):
        t, d, r = fixture()
        for key, value in (("returncode", 1), ("diagnostics", ["solver error"]),
                           ("sources_unchanged", False)):
            copy_r = copy.deepcopy(r); copy_r[key] = value
            with self.subTest(key=key), self.assertRaises(AssertionError):
                analyze(t, d, copy_r)
        r["raw_capture"]["complete_unmodified_rows"] = False
        with self.assertRaises(AssertionError):
            analyze(t, d, r)


if __name__ == "__main__":
    assert os.environ.get("GITHUB_ACTIONS") == "true", "Run numeric tests on GitHub only"
    unittest.main()
