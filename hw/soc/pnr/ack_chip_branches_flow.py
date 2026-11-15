from pathlib import Path
import json
from librelane.flows import Flow
from interface_flow import Interfaces
from corrpre_postcts_flow import SingleCornerSTA,CORNERS
class BranchSTA(SingleCornerSTA):
 def get_script_path(self):
  p=Path(super().get_script_path());s=p.read_text();assert s.rstrip().endswith("write_libs")
  rows=json.loads((Path(__file__).resolve().parents[3]/"ack-chip-branches/targets.json").read_text())
  extra=[]
  for i,row in enumerate(rows):
   name=row["name"];assert not any(c in name for c in "{}\n\r")
   getter="get_pins"if row["kind"]=="pin"else"get_ports"
   extra+=['set target ['+getter+' [list {'+name+'}]]','if {[llength $target]!=1} {error "Target not uniquely resolved"}']
   for mode in ["max","min"]:
    extra+=['puts "%OL_CREATE_REPORT branch-'+str(i)+'-'+mode+'.rpt"','puts {NSSOC_TARGET '+name+'}','report_checks -through $target -corner $corner_name -path_delay '+mode+' -group_path_count 1 -fields {slew cap input net fanout} -format full_clock_expanded -digits 9','puts "%OL_END_REPORT"']
  q=Path(self.step_dir)/"branch_sta.tcl";q.write_text(s+"\n"+"\n".join(extra)+"\n");return str(q)
@Flow.factory.register()
class AckChipBranches(Interfaces):
 Steps=[type("Branch"+n,(BranchSTA,),dict(id="NSSOC.AckBranch"+n,corner=c))for n,c in CORNERS]
if __name__=="__main__":
 from librelane.__main__ import cli
 cli()
