# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import re
from librelane.flows import Flow
from interface_flow import Interfaces
from corrpre_postcts_flow import ElectricalPostCTS, SingleCornerSTA, CORNERS
TARGET = r"""
set target [get_pins {{$auto$ff.cc:337:slice$326833/D}}]
if {[llength $target]!=1} {error "Missing exact target register D"}
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
set targetinst [$block findInst {$auto$ff.cc:337:slice$326833}]
if {$targetinst eq "NULL" || [[$targetinst getMaster] getName] ne "sg13g2_dfrbpq_1"} {error "Target register differs"}
set sink [$targetinst findITerm D]
set net [$sink getNet]
set sourceinst [$block findInst nssoc_link2_load_stage]
if {$sourceinst eq "NULL" || [[$sourceinst getMaster] getName] ne "sg13g2_buf_4"} {error "Missing measured source"}
set sourcepin [$sourceinst findITerm X]
if {[$sourcepin getNet] ne $net || [llength [$net getBTerms]]!=0} {error "Measured branch incidence differs"}
set drivers {}
foreach pin [$net getITerms] {if {[$pin getIoType] eq "OUTPUT"} {lappend drivers $pin}}
if {[llength $drivers]!=1 || [lindex $drivers 0] ne $sourcepin} {error "Unexpected drivers"}
set stem nssoc_link2_short_hold
set netname nssoc_link2_short_hold_out
if {[$block findInst $stem] ne "NULL" || [$block findNet $netname] ne "NULL"} {error "ECO collision"}
set master [[ord::get_db] findMaster sg13g2_dlygate4sd3_1]
if {$master eq "NULL"} {error "Missing native delay"}
set inst [odb::dbInst_create $block $master $stem]
set next [odb::dbNet_create $block $netname]
[$inst findITerm A] connect $net
[$inst findITerm X] connect $next
$sink disconnect
$sink connect $next
$inst setOrient [$targetinst getOrient]
$inst setLocation {*}[$targetinst getLocation]
$inst setPlacementStatus PLACED
if {[llength [$block getInsts]]!=[dict size $before]+1 || [llength [$block getNets]]!=$oldnets+1} {error "Wrong ECO census"}
foreach inst [$block getInsts] {
 set name [$inst getName]
 if {![dict exists $before $name]} {continue}
 lassign [dict get $before $name] master pins
 if {[[$inst getMaster] getName] ne $master} {error "Original master changed"}
 foreach pin [$inst getITerms] {
  set expected [dict get $pins [[$pin getMTerm] getName]]
  if {$pin eq $sink} {set expected $next}
  if {[$pin getNet] ne $expected} {error "Unexpected original incidence change"}
 }
}
puts "NSSOC_ONE_LINK2_HOLD_BRANCH_IDENTITY_DELAY_VERIFIED"
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
    return [type("One"+phase+n,(TargetSTA,),dict(id="NSSOC.CorrpreOneBranch"+phase+n,corner=c)) for n,c in CORNERS]
class OneBranchHoldECO(ElectricalPostCTS):
    id="NSSOC.OneBranchHoldECO"
    name="Repair one new measured short branch"
    def run(self,state_in,**kwargs):
        paths=list(Path(self.step_dir).parent.glob("*/one-max.rpt"))
        assert len(paths)==3
        for path in paths:
            values=re.findall(r"([-+]?[0-9]+\.[0-9]+)\s+slack\s+\((?:MET|VIOLATED)\)",path.read_text())
            assert values and min(map(float,values))>=1.0, "Insufficient measured setup headroom"
        return super().run(state_in,**kwargs)
    def get_script_path(self):
        p=Path(super().get_script_path());s=p.read_text()
        a=s.index("# Buffer I/O");b=s.index("report_floating_nets -verbose",a)
        s=s[:a]+ECO+"\n"+s[b:]
        if "log_cmd repair_design" in s or "unset_propagated_clock [all_clocks]" in s:raise RuntimeError("Unexpected broad repair or ideal clocks")
        assert s.count("write_views")==1
        s=s.replace("write_views",RESTORE+"\nwrite_views")
        q=Path(self.step_dir)/"one_branch_eco.tcl";q.write_text(s);return str(q)
@Flow.factory.register()
class OneBranchTrial(Interfaces):
    Steps=measure("Before")+[OneBranchHoldECO]+measure("After")
if __name__=="__main__":
    from librelane.__main__ import cli
    cli()
