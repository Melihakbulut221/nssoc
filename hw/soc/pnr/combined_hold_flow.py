# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import json,re
from librelane.flows import Flow
from interface_flow import Interfaces
from corrpre_postcts_flow import SingleCornerSTA,CORNERS
from combined_boundary_hold import BoundaryHoldECO,EXTRA
from combined_selective_hold import SelectiveHoldECO
from combined_remaining_hold import RemainingHoldECO
BRANCH_EXTRA=r"""

set index 0
foreach name {BRANCH_NAMES} {
 set target [get_pins [list $name]]
 if {[llength $target]!=1} {error "Missing measured branch $name"}
 foreach type {max min} {
  puts "%OL_CREATE_REPORT branch-$index-$type.rpt"
  puts "NSSOC_TARGET_BRANCH_PIN $name"
  report_checks -through $target -corner $corner_name -path_delay $type -group_path_count 10000 -fields {slew cap input net fanout} -format full_clock_expanded -digits 9
  puts "%OL_END_REPORT"
 }
 incr index
}
if {$index!=123} {error "Wrong branch census"}
puts "NSSOC_123_BRANCHES_MEASURED"
"""
class CombinedSTA(SingleCornerSTA):
 def get_script_path(self):
  p=Path(super().get_script_path());s=p.read_text()
  assert s.rstrip().endswith("write_libs")
  rows=json.loads((Path(__file__).resolve().parents[3]/"combined-hold-trial/targets.json").read_text());assert len(rows)==123
  names=[]
  for row in rows:
   name=row["sink"];assert not any(c in name for c in "{}\n\r");names.append("{"+name+"}")
  q=Path(self.step_dir)/"combined_target.tcl";q.write_text(s+"\n"+EXTRA+"\n"+BRANCH_EXTRA.replace("BRANCH_NAMES"," ".join(names)));return str(q)
def measure(phase):return [type("Combined"+phase+n,(CombinedSTA,),dict(id="NSSOC.Combined"+phase+n,corner=c))for n,c in CORNERS]
class GuardedBoundary(BoundaryHoldECO):
 id="NSSOC.CombinedBoundaryHold"
 def run(self,state_in,**kwargs):
  reports=list(Path(self.step_dir).parent.glob("*/branch-*-max.rpt"))+list(Path(self.step_dir).parent.glob("*/io-*-max.rpt"))
  assert len(reports)==489
  for path in reports:
   values=re.findall(r"([-+]?[0-9]+\.[0-9]+)\s+slack\s+\((?:MET|VIOLATED)\)",path.read_text())
   assert values and min(map(float,values))>=1.0,("Insufficient actual combined setup headroom",str(path),values)
  return super().run(state_in,**kwargs)
@Flow.factory.register()
class CombinedHoldTrial(Interfaces):
 Steps=measure("Before")+[GuardedBoundary,SelectiveHoldECO,RemainingHoldECO]+measure("After")
if __name__=="__main__":
 from librelane.__main__ import cli
 cli()
