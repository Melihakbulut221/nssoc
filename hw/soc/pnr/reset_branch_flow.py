# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import re
from librelane.flows import Flow
from interface_flow import Interfaces
from corrpre_postcts_flow import ElectricalPostCTS, SingleCornerSTA, CORNERS
TARGET = r"""
set target [get_ports pcie_initialized_o]
if {[llength $target]!=1} {error "Missing exact output port"}
foreach type {max min} {
 puts "%OL_CREATE_REPORT one-$type.rpt"
 report_checks -to $target -corner $corner_name -path_delay $type -group_path_count 10000 -fields {slew cap input net fanout} -format full_clock_expanded -digits 9
 puts "%OL_END_REPORT"
}
"""
ECO = r"""

set block [ord::get_db_block]
set before {}
set original_placement {}
foreach inst [$block getInsts] {
 set pins {}
 foreach pin [$inst getITerms] {dict set pins [[$pin getMTerm] getName] [$pin getNet]}
 dict set before [$inst getName] [list [[$inst getMaster] getName] $pins]
 dict set original_placement [$inst getName] [list [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus]]
 if {[$inst getPlacementStatus] eq "PLACED"} {$inst setPlacementStatus FIRM}
}
set oldnets [llength [$block getNets]]
proc unique_driver {net} {
 if {$net eq "NULL" || [llength [$net getBTerms]]!=0} {error "Unexpected boundary net"}
 set drivers {}
 foreach pin [$net getITerms] {if {[$pin getIoType] eq "OUTPUT"} {lappend drivers $pin}}
 if {[llength $drivers]!=1} {error "Nonunique driver"}
 return [lindex $drivers 0]
}
set plans {
 {retry_reset {$auto$ff.cc:337:slice$343481} Q sg13g2_dfrbpq_2 {$abc$735036$auto$blifparse.cc:397:parse_blif$739577} B sg13g2_and2_1 5}
 {quarantine_inv {$auto$ff.cc:337:slice$343483} Q sg13g2_dfrbpq_2 {$abc$735036$auto$blifparse.cc:397:parse_blif$736012} A sg13g2_inv_2 2}
 {quarantine_gate {$auto$ff.cc:337:slice$343483} Q sg13g2_dfrbpq_2 {$abc$735036$auto$blifparse.cc:397:parse_blif$736127} A sg13g2_nand4_1 5}
}
set changes {}
foreach plan $plans {
 lassign $plan label source_name source_port source_master sink_name sink_port sink_master depth
 set si [$block findInst $source_name];set ti [$block findInst $sink_name]
 if {$si eq "NULL" || $ti eq "NULL"} {error "Missing exact branch endpoint"}
 if {[[$si getMaster] getName] ne $source_master || [[$ti getMaster] getName] ne $sink_master} {error "Endpoint master differs"}
 set sourcepin [$si findITerm $source_port];set sink [$ti findITerm $sink_port]
 if {$sourcepin eq "NULL" || $sink eq "NULL" || [$sourcepin getIoType] ne "OUTPUT" || [$sink getIoType] ne "INPUT"} {error "Endpoint pin direction differs"}
 set walk [unique_driver [$sink getNet]]
 set count 0
 set visited {}
 while {$walk ne $sourcepin} {
  set wi [$walk getInst]
  if {![regexp {^sg13g2_buf_(1|2|4|8|16)$} [[$wi getMaster] getName]] || [[$walk getMTerm] getName] ne "X"} {error "Path contains nonidentity cell"}
  if {[dict exists $visited [$wi getName]]} {error "Identity path cycle"}
  dict set visited [$wi getName] 1
  set walk [unique_driver [[$wi findITerm A] getNet]]
  incr count
  if {$count>10} {error "Unexpected buffer chain length"}
 }
 if {$count!=$depth} {error "Measured chain depth differs"}
 if {[unique_driver [$sourcepin getNet]] ne $sourcepin} {error "Source driver differs"}
 set stem [format "nssoc_reset_branch_%s" $label]
 set netname [format "%s_out" $stem]
 if {[$block findInst $stem] ne "NULL" || [$block findNet $netname] ne "NULL"} {error "ECO collision"}
 set master [[ord::get_db] findMaster sg13g2_buf_4]
 if {$master eq "NULL"} {error "Missing native identity buffer"}
 set inst [odb::dbInst_create $block $master $stem]
 set next [odb::dbNet_create $block $netname]
 [$inst findITerm A] connect [$sourcepin getNet]
 [$inst findITerm X] connect $next
 $sink disconnect
 $sink connect $next
 dict set changes $sink $next
 $inst setOrient [$si getOrient]
 $inst setLocation {*}[$si getLocation]
 $inst setPlacementStatus PLACED
 puts "NSSOC_IDENTITY_BRANCH $label $depth $source_name $sink_name"
}
if {[llength [$block getInsts]]!=[dict size $before]+3 || [llength [$block getNets]]!=$oldnets+3 || [dict size $changes]!=3} {error "Wrong ECO census"}
foreach inst [$block getInsts] {
 set name [$inst getName]
 if {![dict exists $before $name]} {continue}
 lassign [dict get $before $name] master pins
 if {[[$inst getMaster] getName] ne $master} {error "Original master changed"}
 foreach pin [$inst getITerms] {
  set expected [dict get $pins [[$pin getMTerm] getName]]
  if {[dict exists $changes $pin]} {set expected [dict get $changes $pin]}
  if {[$pin getNet] ne $expected} {error "Unexpected original incidence change"}
 }
}
puts "NSSOC_THREE_RESET_BRANCHES_IDENTITY_VERIFIED"
"""
RESTORE = r"""
foreach inst [$block getInsts] {
 set name [$inst getName]
 if {![dict exists $original_placement $name]} {continue}
 lassign [dict get $original_placement $name] location orientation status
 if {[$inst getLocation] ne $location || [$inst getOrient] ne $orientation} {error "Original placement moved"}
 $inst setPlacementStatus $status
}
puts "NSSOC_ORIGINAL_PLACEMENT_UNCHANGED_AND_STATUSES_RESTORED"
"""
class TargetSTA(SingleCornerSTA):
    def get_script_path(self):
        p=Path(super().get_script_path());s=p.read_text()
        if not s.rstrip().endswith("write_libs"):raise RuntimeError("Unexpected native STA termination")
        q=Path(self.step_dir)/"one_target.tcl";q.write_text(s+"\n"+TARGET);return str(q)
def measure(phase):
    return [type("One"+phase+n,(TargetSTA,),dict(id="NSSOC.CorrpreResetBranch"+phase+n,corner=c)) for n,c in CORNERS]
class ResetBranchECO(ElectricalPostCTS):
    id="NSSOC.ResetBranchECO"
    name="Dedicated branches on dominant reset setup paths"
    def get_script_path(self):
        p=Path(super().get_script_path());s=p.read_text()
        a=s.index("# Buffer I/O");b=s.index("report_floating_nets -verbose",a)
        s=s[:a]+ECO+"\n"+s[b:]
        if "log_cmd repair_design" in s or "unset_propagated_clock [all_clocks]" in s:raise RuntimeError("Unexpected broad repair or ideal clocks")
        assert s.count("write_views")==1
        s=s.replace("write_views",RESTORE+"\nwrite_views")
        q=Path(self.step_dir)/"one_branch_eco.tcl";q.write_text(s);return str(q)
@Flow.factory.register()
class ResetBranchTrial(Interfaces):
    Steps=measure("Before")+[ResetBranchECO]+measure("After")
if __name__=="__main__":
    from librelane.__main__ import cli
    cli()
