# SPDX-License-Identifier: Apache-2.0
"""Nine-buffer sizing and one identity load stage; no timing exceptions."""
from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces
from corrpre_postcts_flow import ElectricalPostCTS, measurements

ECO = r"""

set block [ord::get_db_block]
set before {}
foreach inst [$block getInsts] {
 set pins {}
 foreach pin [$inst getITerms] {dict set pins [[$pin getMTerm] getName] [$pin getNet]}
 dict set before [$inst getName] [list [[$inst getMaster] getName] $pins]
}
set replacements {
 {fanout9423 sg13g2_buf_1 sg13g2_buf_4}
 {fanout9422 sg13g2_buf_1 sg13g2_buf_4}
 {fanout9421 sg13g2_buf_1 sg13g2_buf_4}
 {fanout9411 sg13g2_buf_1 sg13g2_buf_4}
 {fanout9409 sg13g2_buf_1 sg13g2_buf_4}
 {fanout8720 sg13g2_buf_2 sg13g2_buf_8}
 {fanout7591 sg13g2_buf_1 sg13g2_buf_4}
 {fanout3418 sg13g2_buf_1 sg13g2_buf_4}
 {fanout2618 sg13g2_buf_1 sg13g2_buf_4}
}
set targets {}
foreach row $replacements {
 lassign $row name old new
 set inst [$block findInst $name]
 if {$inst eq "NULL" || [[$inst getMaster] getName] ne $old} {error "Unexpected measured driver $name"}
 replace_cell $name $new
 if {[[$inst getMaster] getName] ne $new} {error "Replacement failed"}
 dict set targets $name $new
}
set sinkinst [$block findInst wire4382]
if {$sinkinst eq "NULL" || [[$sinkinst getMaster] getName] ne "sg13g2_buf_8"} {error "Unexpected measured load"}
set sink [$sinkinst findITerm A]
set originalnet [$sink getNet]
if {[llength [$originalnet getITerms]]!=2 || [llength [$originalnet getBTerms]]!=0} {error "Measured load topology differs"}
set driverinst [$block findInst {$abc$735036$auto$blifparse.cc:397:parse_blif$739624}]
if {$driverinst eq "NULL" || [[$driverinst getMaster] getName] ne "sg13g2_nand4_1"} {error "Missing measured weak NAND"}
set driver [$driverinst findITerm Y]
if {[$driver getNet] ne $originalnet} {error "Unexpected NAND load connection"}
set stem nssoc_nand_load_stage
set netname nssoc_nand_load_stage_out
if {[$block findInst $stem] ne "NULL" || [$block findNet $netname] ne "NULL"} {error "ECO collision"}
set master [[ord::get_db] findMaster sg13g2_buf_2]
if {$master eq "NULL"} {error "Missing native buffer"}
set inst [odb::dbInst_create $block $master $stem]
set next [odb::dbNet_create $block $netname]
[$inst findITerm A] connect $originalnet
[$inst findITerm X] connect $next
$sink disconnect
$sink connect $next
$inst setOrient [$driverinst getOrient]
$inst setLocation {*}[$driverinst getLocation]
$inst setPlacementStatus PLACED
if {[llength [$block getInsts]] != [expr {[dict size $before]+1}]} {error "Instance census changed"}
foreach inst [$block getInsts] {
 set name [$inst getName]
 if {$name eq $stem} {continue}
 lassign [dict get $before $name] master pins
 if {[dict exists $targets $name]} {set master [dict get $targets $name]}
 if {[[$inst getMaster] getName] ne $master} {error "Unexpected master change"}
 foreach pin [$inst getITerms] {
  set expected [dict get $pins [[$pin getMTerm] getName]]
  if {$pin eq $sink} {set expected $next}
  if {[$pin getNet] ne $expected} {error "Unexpected incidence change"}
 }
}
puts "NSSOC_NINE_SIZES_ONE_IDENTITY_STAGE_INCIDENCE_VERIFIED"
"""
class LoadedDriverECO(ElectricalPostCTS):
    id = "NSSOC.LoadedDriverECO"
    name = "Size measured drivers and split NAND load"
    def get_script_path(self):
        p = Path(super().get_script_path())
        s = p.read_text()
        a = s.index("# Buffer I/O")
        b = s.index("report_floating_nets -verbose", a)
        s = s[:a] + ECO + "\n" + s[b:]
        if "log_cmd repair_design" in s or "unset_propagated_clock [all_clocks]" in s:
            raise RuntimeError("Unexpected broad repair or ideal clock")
        q = Path(self.step_dir) / "loaded_driver_eco.tcl"
        q.write_text(s)
        return str(q)
@Flow.factory.register()
class LoadedDriverTrial(Interfaces):
    Steps = [LoadedDriverECO] + measurements("LoadedDriverAfter")
if __name__ == "__main__":
    from librelane.__main__ import cli
    cli()
