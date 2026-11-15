from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces
from corrpre_postcts_flow import SingleCornerSTA,CORNERS
EXTRA = r"""
set index 0
foreach name {{$abc$734844$auto$blifparse.cc:397:parse_blif$778838/B2}} {
 set target [get_pins [list $name]]
 if {[llength $target]!=1} {error "Missing exact feedback branch $name"}
 foreach type {max min} {
  puts "%OL_CREATE_REPORT io-$index-$type.rpt"
  puts "NSSOC_TARGET_BRANCH_PIN $name"
  report_checks -through $target -corner $corner_name -path_delay $type -group_path_count 10000 -fields {slew cap input net fanout} -format full_clock_expanded -digits 9
  puts "%OL_END_REPORT"
 }
 incr index
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
