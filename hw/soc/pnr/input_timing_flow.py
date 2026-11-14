from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces
from corrpre_postcts_flow import SingleCornerSTA,CORNERS
EXTRA = r"""
set training [get_ports pcie_training_i]
if {[llength $training] != 1} {error "Missing exact training input"}
foreach type {max min} {
 puts "%OL_CREATE_REPORT training-$type.rpt"
 report_checks -from $training -corner $corner_name -path_delay $type -group_path_count 10000 -fields {slew cap input net fanout} -format full_clock_expanded -digits 9
 puts "%OL_END_REPORT"
}
"""
class InputSTA(SingleCornerSTA):
 def get_script_path(self):
  p=Path(super().get_script_path());s=p.read_text()
  if not s.rstrip().endswith('write_libs'):raise RuntimeError('Unexpected native STA termination')
  q=Path(self.step_dir)/'input_timing_native.tcl';q.write_text(s+'\n'+EXTRA);return str(q)
@Flow.factory.register()
class InputTiming(Interfaces):
 Steps=[type('Input'+n,(InputSTA,),dict(id='NSSOC.Input'+n,corner=c))for n,c in CORNERS]
if __name__=='__main__':
 from librelane.__main__ import cli
 cli()
