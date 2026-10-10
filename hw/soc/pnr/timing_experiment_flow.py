# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Run one isolated, measured timing experiment from an existing checkpoint.

This flow deliberately requires an explicit one-step range. Its outputs remain
global-route timing estimates; no routing, RC extraction, signoff or logical
equivalence is implied by successful execution.
"""

from pathlib import Path

from librelane.flows import Flow
from librelane.flows.classic import Classic
from librelane.state import State
from librelane.steps import OpenROAD


class ExperimentTimingRepair(OpenROAD.ResizerTimingPostGRT):
    def get_script_path(self):
        return str(Path(__file__).with_name("timing_experiment_step.tcl"))


@Flow.factory.register()
class TimingExperiments(Classic):
    Steps = [
        ExperimentTimingRepair if step == OpenROAD.ResizerTimingPostGRT else step
        for step in Classic.Steps
    ]

    def run(self, initial_state, **kwargs):
        target = OpenROAD.ResizerTimingPostGRT.id
        if kwargs.get("frm") != target or kwargs.get("to") != target:
            raise ValueError(f"Specify --from {target} --to {target}")

        # Per-step views are authoritative. Avoid another large copy in final/.
        # This runs in a dedicated process; always restore the native method.
        original = State.save_snapshot

        def save_manifest(state, path):
            destination = Path(path)
            destination.mkdir(parents=True, exist_ok=True)
            (destination / "state.json").write_text(state.dumps())

        State.save_snapshot = save_manifest
        try:
            return super().run(initial_state, **kwargs)
        finally:
            State.save_snapshot = original


if __name__ == "__main__":
    from librelane.__main__ import cli

    cli()
