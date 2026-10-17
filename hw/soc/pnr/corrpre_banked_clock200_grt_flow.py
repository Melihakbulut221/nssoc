# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Unchanged guarded global router plus native congestion-region diagnostics."""
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
