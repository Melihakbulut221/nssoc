# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Classic interface flow with bounded setup optimization, unchanged checkers.

The installed OpenROAD defaults to unlimited setup iterations. On this design
it repeatedly rolls back the same sizing moves after iteration 340. Cap the
search, not its acceptance criteria: all timing corners and Classic checkers
are retained. The generated Tcl is saved in each step's evidence directory.
"""
from pathlib import Path

from librelane.flows import Flow
from librelane.flows.classic import Classic
from librelane.steps import OpenROAD


class BoundedSetup:
    def get_script_path(self):
        original = Path(super().get_script_path())
        source = original.read_text()
        anchor = "lappend setup_args -setup\n"
        if source.count(anchor) != 1:
            raise RuntimeError(f"Unsupported LibreLane resizer script: {original}")
        source = source.replace(anchor, anchor + "lappend setup_args -max_iterations 600\n")
        output = Path(self.step_dir) / "bounded_setup.tcl"
        output.write_text(source)
        return str(output)


class BoundedPostCTS(BoundedSetup, OpenROAD.ResizerTimingPostCTS):
    pass


class BoundedPostGRT(BoundedSetup, OpenROAD.ResizerTimingPostGRT):
    pass


SUBSTITUTIONS = {
    OpenROAD.ResizerTimingPostCTS: BoundedPostCTS,
    OpenROAD.ResizerTimingPostGRT: BoundedPostGRT,
}


@Flow.factory.register()
class Interfaces(Classic):
    Steps = [SUBSTITUTIONS.get(step, step) for step in Classic.Steps]


if __name__ == "__main__":
    # CLI choices are captured at import time, after this flow is registered.
    from librelane.__main__ import cli

    cli()
