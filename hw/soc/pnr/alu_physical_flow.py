# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fresh matched floorplan/placement/CTS/GRT; never load a prior ODB as state."""
from pathlib import Path

from librelane.flows import Flow
from librelane.flows.classic import Classic
from librelane.state import State
from librelane.steps import Odb, OpenROAD


class TemplateGeometry(OpenROAD.OpenROADStep):
    id = 'OpenROAD.ALUPhysicalTemplateGeometry'
    name = 'Record actual shared template pin and macro geometry'

    def get_script_path(self):
        return str(Path(__file__).with_name('alu_physical_geometry.tcl'))


class FreshRouteAudit(OpenROAD.GlobalRouting):
    id = 'OpenROAD.ALUPhysicalFreshRouteAudit'
    name = 'Audit complete fresh global-route timing and geometry'
    # GlobalRouting supplies the RC/GRT configuration variables required by
    # common/grt.tcl. Keep the complete view export of the generic OpenROAD step.
    outputs = list(OpenROAD.OpenROADStep.outputs)

    def get_script_path(self):
        return str(Path(__file__).with_name('alu_physical_audit.tcl'))


# Same pre-GRT omissions as the original fresh C10 PipelinedCorePhysical recipe:
# synthesis is already frozen/proved, and absent qualified SRAM Liberty keeps
# this standard-cell timing experiment outside full-chip timing acceptance.
OMITTED = {'Verilator.Lint', 'Checker.LintTimingConstructs', 'Checker.LintErrors',
    'Checker.LintWarnings', 'Yosys.Synthesis', 'Checker.YosysUnmappedCells',
    'Checker.YosysSynthChecks', 'Checker.NetlistAssignStatements', 'OpenROAD.STAPrePNR',
    'OpenROAD.STAMidPNR', 'OpenROAD.STAMidPNR-1', 'OpenROAD.STAMidPNR-2',
    'OpenROAD.ResizerTimingPostCTS'}
STEPS = []
for step in Classic.Steps:
    if step.id not in OMITTED:
        STEPS.append(step)
    if step == Odb.ApplyDEFTemplate:
        STEPS.append(TemplateGeometry)
    if step == OpenROAD.GlobalRouting:
        STEPS.append(FreshRouteAudit)
        break


@Flow.factory.register()
class ALUFreshPhysical(Classic):
    Steps = STEPS

    def run(self, initial_state, **kwargs):
        present = {k for k, value in initial_state.items() if value is not None}
        if present != {'nl'}:
            raise ValueError('Fresh physical flow requires nl-only state; no ODB/DEF/SDC checkpoint substitution')
        if kwargs.get('frm') is not None or kwargs.get('to') is not None:
            raise ValueError('The complete fresh placement/CTS/GRT sequence is mandatory')
        if self.config['FP_TEMPLATE_MATCH_MODE'] != 'strict' or self.config['FP_DEF_TEMPLATE'] is None:
            raise ValueError('Strict common C10 terminal template required')
        original = State.save_snapshot

        def manifest_only(state, path):
            path = Path(path); path.mkdir(parents=True, exist_ok=True)
            (path/'state.json').write_text(state.dumps())

        State.save_snapshot = manifest_only
        try:
            return super().run(initial_state, **kwargs)
        finally:
            State.save_snapshot = original


if __name__ == '__main__':
    from librelane.__main__ import cli
    cli()
