# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native regional capacity reduction on two measured congestion columns; all guards retained."""
from pathlib import Path
from interface_flow import Interfaces
from corrpre_postcts_flow import GuardedPropagated
from librelane.flows import Flow
from librelane.steps import OpenROAD

class BankedGlobalRouting(GuardedPropagated, OpenROAD.GlobalRouting):
    def get_script_path(self):
        path=Path(super().get_script_path())
        text=path.read_text()
        anchor='read_current_odb\n'
        assert text.count(anchor)==1
        report=str(Path(self.step_dir)/'congestion.rpt')
        assert not any(c in report for c in '{}\\\n')
        diagnostic="""
rename global_route nssoc_native_global_route
proc global_route {args} {
    set_global_routing_region_adjustment {2325.6 1692.0 2368.8 2174.4} -layer Metal5 -adjustment 0.5
    puts "NSSOC_REGION_RESERVE_APPLIED Metal5 2325.6 1692.0 2368.8 2174.4 0.5"
    set_global_routing_region_adjustment {3081.6 1692.0 3124.8 2174.4} -layer Metal5 -adjustment 0.5
    puts "NSSOC_REGION_RESERVE_APPLIED Metal5 3081.6 1692.0 3124.8 2174.4 0.5"
    puts "NSSOC_CONGESTION_REPORT_EVERY_25_ITERATIONS"
    return [uplevel 1 [list nssoc_native_global_route {*}$args -congestion_report_file {REPORT_PATH} -congestion_report_iter_step 25]]
}
""".replace('REPORT_PATH',report)
        path.write_text(text.replace(anchor,diagnostic+'\n'+anchor))
        return str(path)

@Flow.factory.register()
class CorrpreBankedGlobalRouting(Interfaces):
    Steps=[BankedGlobalRouting]

if __name__=='__main__':
    from librelane.__main__ import cli
    cli()
