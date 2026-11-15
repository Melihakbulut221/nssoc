# SPDX-License-Identifier: Apache-2.0
"""Three measured load stages on exact bulk candidate; no timing exceptions."""
from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces
from corrpre_postcts_flow import ElectricalPostCTS, measurements

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
set changed {}
set targets {
 {{$auto$ff.cc:337:slice$164048} Q sg13g2_dfrbpq_1 7 sg13g2_buf_4 nssoc_link2_load_stage}
 {{$abc$735036$auto$blifparse.cc:397:parse_blif$739610} X sg13g2_xor2_1 8 sg13g2_buf_2 nssoc_xor_load_stage}
 {{$abc$735036$auto$blifparse.cc:397:parse_blif$739624} Y sg13g2_nand4_1 1 sg13g2_buf_2 nssoc_nand_load_stage}
}
foreach row $targets {
 lassign $row name pinname cell count buffer stem
 set driverinst [$block findInst $name]
 if {$driverinst eq "NULL" || [[$driverinst getMaster] getName] ne $cell} {error "Measured driver differs"}
 set driver [$driverinst findITerm $pinname]
 if {$driver eq "NULL" || [$driver getIoType] ne "OUTPUT"} {error "Missing measured output"}
 set net [$driver getNet]
 if {$net eq "NULL" || [llength [$net getBTerms]]!=0} {error "Unexpected measured net"}
 set loads {}
 foreach pin [$net getITerms] {
  if {$pin eq $driver} {continue}
  if {[$pin getIoType] ne "INPUT"} {error "Unexpected second driver"}
  lappend loads $pin
 }
 if {[llength $loads]!=$count} {error "Measured fanout differs"}
 set netname [format %s_out $stem]
 if {[$block findInst $stem] ne "NULL" || [$block findNet $netname] ne "NULL"} {error "ECO collision"}
 set master [[ord::get_db] findMaster $buffer]
 if {$master eq "NULL"} {error "Missing native buffer"}
 set inst [odb::dbInst_create $block $master $stem]
 set next [odb::dbNet_create $block $netname]
 [$inst findITerm A] connect $net
 [$inst findITerm X] connect $next
 $inst setOrient [$driverinst getOrient]
 $inst setLocation {*}[$driverinst getLocation]
 $inst setPlacementStatus PLACED
 foreach pin $loads {
  if {[dict exists $changed $pin]} {error "Overlapping ECO sink"}
  $pin disconnect
  $pin connect $next
  dict set changed $pin $next
 }
}
if {[dict size $changed]!=16 || [llength [$block getInsts]]!=[expr {[dict size $before]+3}] || [llength [$block getNets]]!=$oldnets+3} {error "Wrong ECO census"}
foreach inst [$block getInsts] {
 set name [$inst getName]
 if {![dict exists $before $name]} {continue}
 lassign [dict get $before $name] master pins
 if {[[$inst getMaster] getName] ne $master} {error "Original master changed"}
 foreach pin [$inst getITerms] {
  set expected [dict get $pins [[$pin getMTerm] getName]]
  if {[dict exists $changed $pin]} {set expected [dict get $changed $pin]}
  if {[$pin getNet] ne $expected} {error "Unexpected original incidence change"}
 }
}
puts "NSSOC_THREE_IDENTITY_LOAD_STAGES_16_SINKS_VERIFIED"
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
class CriticalLoadECO(ElectricalPostCTS):
    id = "NSSOC.CriticalLoadECO"
    name = "Stage three measured critical loads"
    def get_script_path(self):
        p = Path(super().get_script_path())
        s = p.read_text()
        a = s.index("# Buffer I/O")
        b = s.index("report_floating_nets -verbose", a)
        s = s[:a] + ECO + "\n" + s[b:]
        if "log_cmd repair_design" in s or "unset_propagated_clock [all_clocks]" in s:
            raise RuntimeError("Unexpected broad repair or ideal clock")
        if s.count("write_views")!=1:raise RuntimeError("Unexpected native write boundary")
        s=s.replace("write_views",RESTORE+"\nwrite_views")
        q = Path(self.step_dir) / "critical_load_eco.tcl"
        q.write_text(s)
        return str(q)
@Flow.factory.register()
class CriticalLoadTrial(Interfaces):
    Steps = [CriticalLoadECO] + measurements("CriticalLoadAfter")
if __name__ == "__main__":
    from librelane.__main__ import cli
    cli()
