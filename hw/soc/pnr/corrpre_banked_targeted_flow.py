# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Rebuffer measured critical data branches; retain original clock/STA policy."""
from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces
from corrpre_banked_flow import BankedTimingRepair
from corrpre_postcts_flow import ElectricalPostCTS, measurements

class TargetedElectrical(ElectricalPostCTS):
    id='NSSOC.CorrpreTargetedUnbuffer'
    def get_script_path(self):
        script=Path(super().get_script_path());text=script.read_text()
        anchor='set arg_list [list]\n'
        assert text.count(anchor)==1
        helper=Path(__file__).resolve().parents[1]/'flow/corrpre_targeted_unbuffer.tcl'
        script.write_text(text.replace(anchor,'source {'+str(helper)+'}\n'+anchor))
        return str(script)

@Flow.factory.register()
class CorrpreBankedTargetedRebuffer(Interfaces):
    Steps=measurements('TargetBefore')+[TargetedElectrical,BankedTimingRepair]+measurements('TargetAfter')
if __name__=='__main__':
    from librelane.__main__ import cli
    cli()
