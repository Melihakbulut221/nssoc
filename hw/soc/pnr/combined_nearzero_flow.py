from pathlib import Path
import json
from librelane.flows import Flow
from interface_flow import Interfaces
from corrpre_postcts_flow import SingleCornerSTA,CORNERS
from combined_boundary_hold import EXTRA
TAIL=r"""
set index 0
foreach name {PIN_NAMES} {
 set target [get_pins [list $name]]
 if {[llength $target]!=1} {error "Missing actual target pin $name"}
 foreach type {max min} {
  puts "%OL_CREATE_REPORT branch-$index-$type.rpt"
  puts "NSSOC_TARGET_BRANCH_PIN $name"
  report_checks -through $target -corner $corner_name -path_delay $type -group_path_count 1 -fields {slew cap input net fanout} -format full_clock_expanded -digits 9
  puts "%OL_END_REPORT"
 }
 incr index
}
if {$index!=PIN_COUNT} {error "Wrong target census"}
"""
class MarginSTA(SingleCornerSTA):
 def get_script_path(self):
  p=Path(super().get_script_path());s=p.read_text();assert s.rstrip().endswith("write_libs")
  rows=json.loads((Path(__file__).resolve().parents[3]/"combined-nearzero-trial/targets.json").read_text());assert len(rows)>0
  names=[]
  for r in rows:
   name=r['sink'];assert not any(c in name for c in "{}\n\r");names.append("{"+name+"}")
  q=Path(self.step_dir)/"margin_target.tcl";q.write_text(s+"\n"+EXTRA+"\n"+TAIL.replace("PIN_NAMES"," ".join(names)).replace("PIN_COUNT",str(len(rows))));return str(q)
@Flow.factory.register()
class CombinedNearzeroTrial(Interfaces):
 Steps=[type("Margin"+n,(MarginSTA,),dict(id="NSSOC.CombinedAfter"+n,corner=c))for n,c in CORNERS]
if __name__=="__main__":
 from librelane.__main__ import cli
 cli()
