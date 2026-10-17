#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Synthetic orchestration controls, never native design verification."""
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch
import cloud_corrpre_banked_handoff as handoff


def main():
    assert os.environ.get("GITHUB_ACTIONS") == "true"
    title = "fixture only"
    run = dict(id=9, head_sha="a" * 40, status="in_progress", conclusion=None,
               display_title=title, html_url="https://example.invalid/fixture",
               path=handoff.BOOT_WORKFLOW, head_branch=handoff.BRANCH, run_attempt=1)
    checks = []
    with tempfile.TemporaryDirectory() as temp, patch.dict(os.environ, GITHUB_OUTPUT=str(Path(temp) / "output")):
        # An observed running or completed successor is reused, never dispatched twice.
        for status, conclusion in [("in_progress", None), ("completed", "success")]:
            source = dict(run, status=status, conclusion=conclusion)
            with patch.object(handoff, "existing", return_value=source), patch.object(handoff, "api") as api:
                assert handoff.launch("fixture.yml", title, {}, {}, lambda: None)["id"] == 9
                api.assert_not_called()
            checks.append("reuse_" + status)
        with patch.object(handoff, "existing", return_value=dict(run, status="completed", conclusion="failure")), patch.object(handoff, "api") as api:
            try:
                handoff.launch("fixture.yml", title, {}, {}, lambda: None)
            except AssertionError:
                pass
            else:
                raise AssertionError("Failed successor was adopted")
            api.assert_not_called()
        checks.append("failed_successor_no_restart")
        with patch.object(handoff, "api", return_value={"workflow_runs": [run, dict(run, id=10)]}):
            try:
                handoff.existing("fixture.yml", title)
            except AssertionError:
                pass
            else:
                raise AssertionError("Ambiguous successors accepted")
        checks.append("duplicate_history_rejected")
        with patch.object(handoff, "existing", return_value=None), patch.object(handoff, "api", side_effect=RuntimeError("uncertain transport")) as api:
            try:
                handoff.launch("fixture.yml", title, {}, {}, lambda: None)
            except RuntimeError:
                pass
            else:
                raise AssertionError("Uncertain dispatch was hidden")
            assert api.call_count == 1
        checks.append("uncertain_dispatch_no_retry")
        with patch.object(handoff, "existing", side_effect=[None, run]), patch.object(handoff, "api") as api:
            assert handoff.launch("fixture.yml", title, {}, {}, lambda: None)["id"] == 9
            assert api.call_count == 1
        checks.append("single_dispatch_then_observed_run")
        for bad in [dict(run, id=handoff.BOOT_RUN, head_sha="0" * 40),
                    dict(run, id=handoff.BOOT_RUN, head_sha=handoff.BOOT_HEAD,
                         status="completed", conclusion="failure")]:
            with patch.object(handoff, "api", return_value=bad), patch.object(handoff.time, "sleep") as sleep:
                try:
                    handoff.wait_success(handoff.BOOT_RUN, handoff.BOOT_WORKFLOW, 0, {}, lambda: None)
                except AssertionError:
                    pass
                else:
                    raise AssertionError("Wrong or failed boot accepted")
                sleep.assert_not_called()
        checks.extend(["wrong_source_head_rejected", "failed_boot_no_successor"])
    print(json.dumps(dict(status="PASS_SYNTHETIC_HANDOFF_CONTROLS_ONLY", checks=checks,
                          native_acceptance=False)))


if __name__ == "__main__":
    main()
