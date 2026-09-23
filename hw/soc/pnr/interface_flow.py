# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Classic interface flow with bounded setup optimization, unchanged checker limits.

The installed OpenROAD defaults to unlimited setup iterations. On this design
it repeatedly rolls back the same sizing moves after iteration 340. Cap the
search, not its acceptance criteria: all timing corners and Classic checkers
are retained. The generated Tcl is saved in each step's evidence directory.
The optional top LEF's metadata warning runs only when that LEF is generated;
the routed-design antenna check remains independent and enabled.
Before detailed routing, discard stale guides on unloaded internal outputs
left by an ECO. Connected nets, cells and constraints remain untouched.
"""
from pathlib import Path

from librelane.flows import Flow
from librelane.flows.classic import Classic
from librelane.steps import OpenROAD


class BoundedSetup:
    max_setup_iterations = 600

    def get_script_path(self):
        original = Path(super().get_script_path())
        source = original.read_text()
        anchor = "lappend setup_args -setup\n"
        if source.count(anchor) != 1:
            raise RuntimeError(f"Unsupported LibreLane resizer script: {original}")
        source = source.replace(anchor, anchor + f"lappend setup_args -max_iterations {self.max_setup_iterations}\n")
        load = "read_current_odb\n"
        if source.count(load) != 1:
            raise RuntimeError(f"Unsupported LibreLane database load: {original}")
        guard = Path(__file__).resolve().parents[1] / "flow/check_timing_derate.tcl"
        if not guard.is_file():
            raise RuntimeError(f"Missing timing derate guard: {guard}")
        # Embed the same guard used by independent corner reports. In saved
        # step JSON, native 5.0 becomes integer 5 and silently disables derate.
        # Reject a bad restart before reading constraints or optimizing cells.
        source = source.replace(load, guard.read_text() + "\n" + load)
        output = Path(self.step_dir) / "bounded_setup.tcl"
        output.write_text(source)
        return str(output)


class BoundedPostCTS(BoundedSetup, OpenROAD.ResizerTimingPostCTS):
    # The request/writeback candidate exhausted the hosted 300-minute step
    # at iteration 140/600, losing the entire unfinished repair. Preserve a
    # completed stage for subsequent routing and extracted timing checks.
    max_setup_iterations = 100


class BoundedPostGRT(BoundedSetup, OpenROAD.ResizerTimingPostGRT):
    # The 20-macro hosted candidate spent nearly four hours in this search
    # and was cancelled at iteration 430/600 before detailed routing. Bound
    # this search separately so route/extraction and unchanged checkers run.
    # An unfinished timing repair remains a timing failure, not a waiver.
    max_setup_iterations = 100


class CleanOrphanGuides(OpenROAD.DetailedRouting):
    def get_script_path(self):
        original = Path(super().get_script_path())
        source = original.read_text()
        anchor = "read_current_odb\n"
        if source.count(anchor) != 1:
            raise RuntimeError(f"Unsupported LibreLane routing script: {original}")
        helper = Path(__file__).resolve().parents[1] / "flow" / "prune_orphan_guides.tcl"
        if not helper.is_file():
            raise RuntimeError(f"Missing guide cleanup script: {helper}")
        # Quote a literal Tcl path, including workspaces with spaces/$/brackets.
        quoted = '"' + ''.join('\\' + c if c in '\\"$[]' else c for c in str(helper)) + '"'
        insertion = f'source {quoted}\nputs "REMOVED_ORPHAN_GUIDES [prune_orphan_guides [ord::get_db_block]]"\n'
        output = Path(self.step_dir) / "clean_orphan_guides_drt.tcl"
        output.write_text(source.replace(anchor, anchor + insertion))
        return str(output)


SUBSTITUTIONS = {
    OpenROAD.ResizerTimingPostCTS: BoundedPostCTS,
    OpenROAD.ResizerTimingPostGRT: BoundedPostGRT,
    OpenROAD.DetailedRouting: CleanOrphanGuides,
}


@Flow.factory.register()
class Interfaces(Classic):
    Steps = [SUBSTITUTIONS.get(step, step) for step in Classic.Steps]
    # Classic 3.0.5 leaves this informational step enabled even when its
    # required LEF producer is disabled, causing a missing-input exception.
    gating_config_vars = {
        **Classic.gating_config_vars,
        "Odb.CheckDesignAntennaProperties": ["RUN_MAGIC_WRITE_LEF"],
    }


if __name__ == "__main__":
    # CLI choices are captured at import time, after this flow is registered.
    from librelane.__main__ import cli

    cli()
