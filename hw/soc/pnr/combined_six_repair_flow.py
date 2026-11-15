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
  rows=json.loads((Path(__file__).resolve().parents[3]/"combined-six-repair/targets.json").read_text());assert len(rows)>0
  names=[]
  for r in rows:
   name=r['sink'];assert not any(c in name for c in "{}\n\r");names.append("{"+name+"}")
  q=Path(self.step_dir)/"margin_target.tcl";q.write_text(s+"\n"+EXTRA+"\n"+TAIL.replace("PIN_NAMES"," ".join(names)).replace("PIN_COUNT",str(len(rows))));return str(q)

from corrpre_postcts_flow import ElectricalPostCTS
from combined_remaining_hold import RESTORE
ECO = '\nset block [ord::get_db_block]\nset before {}\nset original_placement {}\nforeach inst [$block getInsts] {\n set pins {}\n foreach pin [$inst getITerms] {dict set pins [[$pin getMTerm] getName] [$pin getNet]}\n dict set before [$inst getName] [list [[$inst getMaster] getName] $pins]\n dict set original_placement [$inst getName] [list [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus]]\n if {[$inst getPlacementStatus] eq "PLACED"} {$inst setPlacementStatus FIRM}\n}\nset oldnets [llength [$block getNets]]\nset changes {}\nset index 0\nforeach {name expected_master delay_master} {TARGET_PAIRS} {\n set slash [string last / $name]\n set ti [$block findInst [string range $name 0 [expr {$slash-1}]]]\n if {$ti eq "NULL" || [[$ti getMaster] getName] ne $expected_master} {error "Measured target master mismatch"}\n set sink [$ti findITerm [string range $name [expr {$slash+1}] end]]\n if {$sink eq "NULL" || [$sink getIoType] ne "INPUT"} {error "Target input mismatch"}\n set net [$sink getNet]\n if {$net eq "NULL" || [llength [$net getBTerms]]!=0} {error "Boundary or disconnected target"}\n set drivers {}\n foreach pin [$net getITerms] {if {[$pin getIoType] eq "OUTPUT"} {lappend drivers $pin}}\n if {[llength $drivers]!=1} {error "Nonunique original driver"}\n set stem [format "nssoc_sixmargin_%03d" $index]\n set netname [format "%s_out" $stem]\n if {[$block findInst $stem] ne "NULL" || [$block findNet $netname] ne "NULL"} {error "ECO collision"}\n set master [[ord::get_db] findMaster $delay_master]\n if {$master eq "NULL"} {error "Missing qualified native identity"}\n set inst [odb::dbInst_create $block $master $stem]\n set next [odb::dbNet_create $block $netname]\n [$inst findITerm A] connect $net\n [$inst findITerm X] connect $next\n $sink disconnect\n $sink connect $next\n dict set changes $sink $next\n $inst setOrient [$ti getOrient]\n $inst setLocation {*}[$ti getLocation]\n $inst setPlacementStatus PLACED\n puts "NSSOC_NEARZERO_IDENTITY $index $name $expected_master"\n incr index\n}\nif {$index!=6 || [llength [$block getInsts]]!=[dict size $before]+6 || [llength [$block getNets]]!=$oldnets+6 || [dict size $changes]!=6} {error "Wrong repair census"}\nforeach inst [$block getInsts] {\n set name [$inst getName]\n if {![dict exists $before $name]} {continue}\n lassign [dict get $before $name] master pins\n if {[[$inst getMaster] getName] ne $master} {error "Original master changed"}\n foreach pin [$inst getITerms] {\n  set expected [dict get $pins [[$pin getMTerm] getName]]\n  if {[dict exists $changes $pin]} {set expected [dict get $changes $pin]}\n  if {[$pin getNet] ne $expected} {error "Unexpected incidence change"}\n }\n}\nputs "NSSOC_NEARZERO_6_IDENTITY_VERIFIED"\n'
class NearzeroECO(ElectricalPostCTS):
 id="NSSOC.NearzeroECO"
 name="Measure six native branch buffer insertions"
 def get_script_path(self):
  p=Path(super().get_script_path());s=p.read_text()
  rows=json.loads((Path(__file__).resolve().parents[3]/"combined-six-repair/targets.json").read_text())
  assert len(rows)==6 and all(r["worst_setup_slack_ns"]>=r["experiment_headroom_guard_ns"] for r in rows)
  pairs=[]
  for r in rows:
   assert not any(c in r["sink"]+r["master"] for c in "{}\n\r")
   pairs.extend(["{"+r["sink"]+"}","{"+r["master"]+"}","{"+r["delay_master"]+"}"])
  a=s.index("# Buffer I/O");b=s.index("report_floating_nets -verbose",a)
  s=s[:a]+ECO.replace("TARGET_PAIRS"," ".join(pairs))+"\n"+s[b:]
  assert "log_cmd repair_design" not in s and "unset_propagated_clock [all_clocks]" not in s
  assert s.count("write_views")==1
  s=s.replace("write_views",RESTORE+"\nwrite_views")
  q=Path(self.step_dir)/"nearzero_eco.tcl";q.write_text(s);return str(q)

@Flow.factory.register()
class CombinedSixRepair(Interfaces):
 Steps=[NearzeroECO]+[type("Margin"+n,(MarginSTA,),dict(id="NSSOC.CombinedAfter"+n,corner=c))for n,c in CORNERS]
if __name__=="__main__":
 from librelane.__main__ import cli
 cli()
