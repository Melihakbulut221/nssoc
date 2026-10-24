# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Exercise the actual timing-flow CLI up to its native launch boundary.

Run with the pinned LibreLane AppImage's Python, --config and --pdk-root. Native
Click parsing and flow configuration are real. Only Flow.start and Classic.run
are intercepted, so this test never loads a chip database or starts OpenROAD.
"""

import argparse
from contextlib import redirect_stderr, redirect_stdout
import io
from pathlib import Path
import runpy
import sys
import tempfile
from unittest.mock import patch

from librelane.flows import Flow
from librelane.flows.classic import Classic
from librelane.state import State
from librelane.steps import OpenROAD


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--pdk-root", type=Path, required=True)
    parser.add_argument("--pdk", default="ihp-sg13g2")
    parser.add_argument("--initial-state", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    entrypoint = root / "hw/soc/pnr/timing_experiment_flow.py"
    target = OpenROAD.ResizerTimingPostGRT.id
    calls = []
    original_save = State.save_snapshot

    def no_native_steps(self, initial_state, **kwargs):
        assert kwargs["frm"] == kwargs["to"] == target
        calls.append(("run", kwargs))
        return initial_state, []

    def launch_boundary(self, **kwargs):
        assert type(self).__name__ == "TimingExperiments"
        assert kwargs["frm"] == kwargs["to"] == target
        assert Path(kwargs["_force_run_dir"]).is_dir()
        candidates = [step for step in self.Steps if step.id == target]
        assert len(candidates) == 1
        assert candidates[0].__name__ == "ExperimentTimingRepair"
        calls.append(("start", kwargs))
        state = kwargs.get("with_initial_state") or State()
        with patch.object(Classic, "run", no_native_steps):
            self.run(state, frm=kwargs["frm"], to=kwargs["to"])
        assert State.save_snapshot is original_save
        return state

    def invoke(directory):
        argv = [str(entrypoint), "--flow", "TimingExperiments", "--manual-pdk",
                "--pdk-root", str(args.pdk_root.resolve()), "--pdk", args.pdk,
                "--force-run-dir", str(directory), "--from", target, "--to", target]
        if args.initial_state:
            argv.extend(["--with-initial-state", str(args.initial_state.resolve())])
        argv.append(str(args.config.resolve()))
        output = io.StringIO()
        status = 0
        with patch.object(sys, "argv", argv), patch.object(Flow, "start", launch_boundary):
            with redirect_stdout(output), redirect_stderr(output):
                try:
                    runpy.run_path(str(entrypoint), run_name="__main__")
                except SystemExit as error:
                    status = error.code or 0
        return status, output.getvalue()

    with tempfile.TemporaryDirectory(prefix="timing-cli-native-") as scratch:
        directory = Path(scratch) / "isolated-stage"
        status, output = invoke(directory)
        assert status == 2, (status, output)
        assert "Invalid value for '--force-run-dir'" in output, output
        assert "does not exist" in output, output
        assert not calls and not directory.exists()
        print("MISSING_STAGE_DIRECTORY_REJECTED_BEFORE_FLOW_START")

        directory.mkdir(exist_ok=False)
        status, output = invoke(directory)
        assert status == 0, (status, output)
        assert [kind for kind, _ in calls] == ["start", "run"]
        assert Path(calls[0][1]["_force_run_dir"]) == directory
        print("EXISTING_STAGE_DIRECTORY_REACHES_NATIVE_FLOW_BOUNDARY")
        print("ACTUAL_CLI_FROM_TO_CASE_AND_MANIFEST_RESTORATION_VALIDATED")
    print("NATIVE_TIMING_FLOW_CLI_TEST_PASSED_NO_DATABASE_LOADED")


if __name__ == "__main__":
    main()
