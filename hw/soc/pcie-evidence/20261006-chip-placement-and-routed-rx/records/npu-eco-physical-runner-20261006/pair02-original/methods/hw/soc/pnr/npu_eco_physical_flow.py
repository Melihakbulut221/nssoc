# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Same fresh C10 flow with complete LEFs for the independent template reader."""
from librelane.flows import Flow
from librelane.steps import Odb

from alu_physical_flow import ALUFreshPhysical
from npu_eco_template_lefs import append_template_macro_lefs


class ApplyMacroDEFTemplate(Odb.ApplyDEFTemplate):
    id = 'Odb.NPUPhysicalDEFTemplate'
    name = 'Apply the unchanged full DEF template with SRAM LEFs'

    def get_command(self):
        command = super().get_command()
        macros = {name: entry.lef for name, entry in self.config['MACROS'].items()}
        return append_template_macro_lefs(command, macros)


if sum(step == Odb.ApplyDEFTemplate for step in ALUFreshPhysical.Steps) != 1:
    raise ValueError('Frozen original physical flow must have one template step')


@Flow.factory.register()
class NPUECOFreshPhysical(ALUFreshPhysical):
    Steps = [ApplyMacroDEFTemplate if step == Odb.ApplyDEFTemplate else step
             for step in ALUFreshPhysical.Steps]


if __name__ == '__main__':
    from librelane.__main__ import cli
    cli()
