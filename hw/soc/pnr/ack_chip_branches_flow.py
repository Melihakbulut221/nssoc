from pathlib import Path
import json
from librelane.flows import Flow
from interface_flow import Interfaces
from corrpre_postcts_flow import SingleCornerSTA,CORNERS
class BranchSTA(SingleCornerSTA):
 def get_script_path(self):
  p=Path(super().get_script_path());s=p.read_text();assert s.rstrip().endswith("write_libs")
  rows=json.loads((Path(__file__).resolve().parents[3]/"ack-chip-branches/targets.json").read_text())
  extra=['set pin_by_name {}','foreach pin [get_pins -hierarchical *] {set name [get_full_name $pin]; if {[dict exists $pin_by_name $name]} {error "Duplicate pin name"}; dict set pin_by_name $name $pin}', 'set port_by_name {}','foreach port [get_ports *] {dict set port_by_name [get_full_name $port] $port}']
  for i,row in enumerate(rows):
   name=row["name"];assert not any(c in name for c in "{}\n\r")
   table="pin_by_name"if row["kind"]=="pin"else"port_by_name"
   aliases=list(dict.fromkeys([name,name.replace(chr(92)*2,chr(92))]))
   choices=' '.join('{'+n+'}'for n in aliases)
   extra+=['set matches {}','foreach alias {'+choices+'} {if {[dict exists $'+table+' $alias]} {dict set matches [dict get $'+table+' $alias] 1}}','if {[dict size $matches]!=1} {error {Unresolved or ambiguous exact target '+name+'}}','set target [dict keys $matches]']
   for mode in ["max","min"]:
    extra+=['puts "%OL_CREATE_REPORT branch-'+str(i)+'-'+mode+'.rpt"','puts {NSSOC_TARGET '+name+'}','report_checks -through $target -corner $corner_name -path_delay '+mode+' -group_path_count 1 -fields {slew cap input net fanout} -format full_clock_expanded -digits 9','puts "%OL_END_REPORT"']
  extra += ['puts "%OL_CREATE_REPORT head-last-hold-connectivity.rpt"', 'set block [ord::get_db_block]', 'set inst [$block findInst hold32105]', 'if {$inst eq "NULL" || [[$inst getMaster] getName] ne "sg13g2_dlygate4sd3_1"} {error "Wrong shared hold instance"}', 'foreach port {A X} {set pin [$inst findITerm $port]; set net [$pin getNet]; puts [list HOLD_PORT $port NET [$net getName]]; foreach p [$net getITerms] {puts [list [[$p getInst] getName] [[$p getMTerm] getName] [$p getIoType] [[$p getInst] getMaster]]}}', 'puts "%OL_END_REPORT"']
  q=Path(self.step_dir)/"branch_sta.tcl";q.write_text(s+"\n"+"\n".join(extra)+"\n");return str(q)
@Flow.factory.register()
class AckChipBranches(Interfaces):
 Steps=[type("Branch"+n,(BranchSTA,),dict(id="NSSOC.AckBranch"+n,corner=c))for n,c in CORNERS]
if __name__=="__main__":
 from librelane.__main__ import cli
 cli()
