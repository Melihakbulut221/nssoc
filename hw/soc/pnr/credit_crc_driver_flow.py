from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces, BoundedPostCTS
from corrpre_postcts_flow import ElectricalPostCTS,CORNERS
from corrpre_postcts_flow import SingleCornerSTA as BranchSTA
ECO = r"""
set block [ord::get_db_block]
set before {}
foreach inst [$block getInsts] {
 set pins {}
 foreach pin [$inst getITerms] {dict set pins [[$pin getMTerm] getName] [$pin getNet]}
 dict set before [$inst getName] [list [[$inst getMaster] getName] $pins]
}
set choices {
 {fanout9730} {sg13g2_buf_1 sg13g2_buf_4}
 {fanout9729} {sg13g2_buf_1 sg13g2_buf_4}
 {$abc$735341$auto$blifparse.cc:397:parse_blif$770552} {sg13g2_buf_1 sg13g2_buf_4}
}
set targets [dict keys $choices]
if {[llength $targets]!=3} {error "Wrong measured resize census"}
if {[llength [info commands replace_cell]] != 1} {error "Missing native replace_cell"}
foreach name $targets {
 set inst [$block findInst $name]
 if {$inst eq "NULL" || [[$inst getMaster] getName] ne [lindex [dict get $choices $name] 0]} {error "Reset target preflight mismatch $name"}
}
set ports_before {}
foreach port [$block getBTerms] {dict set ports_before [$port getName] [$port getNet]}
foreach name $targets {
 lassign [dict get $choices $name] old_master new_master
 set inst [$block findInst $name]
 if {$inst eq "NULL" || [[$inst getMaster] getName] ne $old_master} {error "Unexpected measured driver $name"}
 replace_cell $name $new_master
 if {[[$inst getMaster] getName] ne $new_master} {error "Replacement failed"}
}
if {[llength [$block getInsts]] != [dict size $before]} {error "Instance census changed"}
foreach inst [$block getInsts] {
 set name [$inst getName]
 lassign [dict get $before $name] master pins
 if {$name in $targets} {set master [lindex [dict get $choices $name] 1]}
 if {[[$inst getMaster] getName] ne $master} {error "Unexpected master change"}
 foreach pin [$inst getITerms] {
  if {[$pin getNet] ne [dict get $pins [[$pin getMTerm] getName]]} {error "Incidence changed"}
 }
}
foreach port [$block getBTerms] {if {[$port getNet] ne [dict get $ports_before [$port getName]]} {error "Port incidence changed"}}
# Taper the measured high-capacitance buf8 input with native buf2.
set origin [$block findInst wire3244]
if {$origin eq "NULL" || [[$origin getMaster] getName] ne "sg13g2_buf_8"} {error "Taper sink mismatch"}
set sink [$origin findITerm A];set net [$sink getNet];set drivers {}
if {$net eq "NULL" || [llength [$net getBTerms]]!=0 || [llength [$net getITerms]]!=2} {error "Taper source is not isolated"}
foreach pin [$net getITerms] {if {[$pin getIoType] eq "OUTPUT"} {lappend drivers "[[$pin getInst] getName]/[[$pin getMTerm] getName]"}}
if {[llength $drivers]!=1 || [lindex $drivers 0] ne {$abc$735341$auto$blifparse.cc:397:parse_blif$770517/Y}} {error "Taper driver mismatch"}
set supply {}
foreach pin [$origin getITerms] {
 if {[[$pin getMTerm] getSigType] in {POWER GROUND}} {
  if {[$pin getNet] eq "NULL"} {error "Taper supply missing"}
  dict set supply [[$pin getMTerm] getName] [$pin getNet]
 }
}
if {[dict size $supply]!=2} {error "Taper supply census"}
set master [[ord::get_db] findMaster sg13g2_buf_2]
if {$master eq "NULL" || [$block findInst nssoc_linkup_taper] ne "NULL" || [$block findNet nssoc_linkup_taper_out] ne "NULL"} {error "Taper master or collision"}
set cell [odb::dbInst_create $block $master nssoc_linkup_taper];set next [odb::dbNet_create $block nssoc_linkup_taper_out]
lassign [$origin getLocation] x y;$cell setLocation $x $y;$cell setOrient [$origin getOrient];$cell setPlacementStatus PLACED
foreach pin [$cell getITerms] {
 set pn [[$pin getMTerm] getName]
 if {[[$pin getMTerm] getSigType] in {POWER GROUND}} {$pin connect [dict get $supply $pn]} elseif {$pn ni {A X}} {error "Taper terminal"}
}
[$cell findITerm A] connect $net;[$cell findITerm X] connect $next;$sink connect $next
if {[llength [$block getInsts]]!=[dict size $before]+1 || [llength [$net getITerms]]!=2 || [llength [$next getITerms]]!=2} {error "Taper census"}
foreach inst [$block getInsts] {
 set name [$inst getName];if {$name eq "nssoc_linkup_taper"} {continue}
 lassign [dict get $before $name] master pins
 foreach pin [$inst getITerms] {
  set pn [[$pin getMTerm] getName];set expected [dict get $pins $pn]
  if {$name eq "wire3244" && $pn eq "A"} {set expected $next}
  if {[$pin getNet] ne $expected} {error "Taper unrelated incidence changed"}
 }
}
foreach port [$block getBTerms] {if {[$port getNet] ne [dict get $ports_before [$port getName]]} {error "Taper port changed"}}
puts "NSSOC_LINKUP_TAPER_STRUCTURAL_PASS"

detailed_placement
check_placement -verbose
puts "NSSOC_SHARED_PCIE_DRIVERS_SAME_INCIDENCE"
"""
class ResetBufferECO(ElectricalPostCTS):
    id = "NSSOC.ResetBufferECO"
    name = "Size measured new EOP link-up critical drivers"
    def get_script_path(self):
        p = Path(super().get_script_path())
        s = p.read_text()
        a = s.index("# Buffer I/O")
        b = s.index("report_floating_nets -verbose", a)
        s = s[:a] + ECO + "\n" + s[b:]
        if "log_cmd repair_design" in s or "unset_propagated_clock [all_clocks]" in s:
            raise RuntimeError("Unexpected broad repair or ideal clock")
        q = Path(self.step_dir) / "reset_buffer_eco.tcl"
        q.write_text(s)
        return str(q)
@Flow.factory.register()
class AckChipResetSized(Interfaces):
 Steps=[ResetBufferECO, BoundedPostCTS]+[type("Sized"+n,(BranchSTA,),dict(id="NSSOC.Sized"+n,corner=c))for n,c in CORNERS]
if __name__=="__main__":
 from librelane.__main__ import cli
 cli()
