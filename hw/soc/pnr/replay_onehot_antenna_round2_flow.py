# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Continue exact saved routing at antenna round2; save before and after insertion."""
from pathlib import Path
from replay_onehot_detailed_route_flow import GuardedDetailedRouting
from interface_flow import Interfaces
from librelane.flows import Flow
from librelane.steps import OpenROAD,Odb

def resume_script(text):
    edits=[
        ('set i 0\n','set i 2\n'),
        ('lappend drt_args {*}$drc_report_iter_step_arg\ndrt_run $i {*}$drt_args\n\nincr i\n',
         'lappend drt_args {*}$drc_report_iter_step_arg\nset prior_antennas [log_cmd check_antennas]\nif {$prior_antennas != 172} {error "Saved route antenna count changed: $prior_antennas"}\nputs "NSSOC_RESUMED_EXACT_ROUND1_WITH_172_ANTENNA_NETS"\nwrite_db "$::env(STEP_DIR)/before_round2.odb"\n'),
        ('while {$i <= $::env(DRT_ANTENNA_REPAIR_ITERS) && [log_cmd check_antennas]} {',
         'while {$i == 2 && $i <= $::env(DRT_ANTENNA_REPAIR_ITERS) && [log_cmd check_antennas]} {'),
        ('set diodes_inserted [log_cmd repair_antennas {*}$arg_list]',
         'set diodes_inserted [log_cmd repair_antennas {*}$arg_list]\n        write_db "$::env(STEP_DIR)/after_round2_insertion.odb"\n        puts "NSSOC_ROUND2_INSERTED_DIODES $diodes_inserted"')]
    for before,after in edits:
        assert text.count(before)==1,('Unsupported native continuation anchor',before)
        text=text.replace(before,after)
    return text

class ResumeAntennaRound2(GuardedDetailedRouting):
    def get_script_path(self):
        native=Path(super().get_script_path());original=native.read_text()
        text=resume_script(original)
        assert 'set_propagated_clock [all_clocks]'in text and 'DERATE_GUARD'in text
        assert text.count('drt_run $i {*}$drt_args')==1
        out=Path(self.step_dir)/'resume_antenna_round2.tcl';out.write_text(text);return str(out)

@Flow.factory.register()
class ReplayOnehotAntennaRound2(Interfaces):
    Steps=[ResumeAntennaRound2,OpenROAD.CheckAntennas,Odb.ReportDisconnectedPins]
if __name__=='__main__':
    from librelane.__main__ import cli
    cli()
