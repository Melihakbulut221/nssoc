from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces
from corrpre_postcts_flow import ElectricalPostCTS,CORNERS
from ack_chip_branches_flow import BranchSTA
ECO = r"""
set block [ord::get_db_block]
set before {}
foreach inst [$block getInsts] {
 set pins {}
 foreach pin [$inst getITerms] {dict set pins [[$pin getMTerm] getName] [$pin getNet]}
 dict set before [$inst getName] [list [[$inst getMaster] getName] $pins]
}
set choices {
 {input49} {sg13g2_buf_1 sg13g2_buf_2}
}
set targets [dict keys $choices]
if {[llength $targets]!=1} {error "Wrong measured resize census"}
if {[llength [info commands replace_cell]] != 1} {error "Missing native replace_cell"}
foreach name $targets {
 set inst [$block findInst $name]
 if {$inst eq "NULL" || [[$inst getMaster] getName] ne [lindex [dict get $choices $name] 0]} {error "Reset target preflight mismatch $name"}
}
set driver [$block findInst {$abc$734931$auto$blifparse.cc:397:parse_blif$767656}]
set dy [$driver findITerm Y]
set wb [$block findInst wire7238]
if {$dy eq "NULL" || $wb eq "NULL" || [[$wb getMaster] getName] ne "sg13g2_buf_8"} {error "Reset output or buffer missing"}
set wa [$wb findITerm A]
set rn [$dy getNet]
if {$rn eq "NULL" || $wa eq "NULL" || [$wa getNet] ne $rn || [$rn getName] ne "u_pcie_cdc.reset_ni" || [llength [$rn getITerms]]!=2 || [llength [$rn getBTerms]]!=0} {error "Reset driver chain changed"}
set release [$block findInst {$auto$ff.cc:337:slice$310738}]
if {$release eq "NULL" || [[$release getMaster] getName] ne "sg13g2_dfrbpq_1"} {error "Reset release instance changed"}
foreach {pin expected} {Q {u_pcie_cdc.destination_release[0]} D net20216 RESET_B net23863 CLK clknet_leaf_111_clk_i_regs} {
 set term [$release findITerm $pin]
 if {$term eq "NULL" || [$term getNet] eq "NULL" || [[ $term getNet] getName] ne $expected} {error "Reset release connectivity changed"}
}
set inp [$block findInst input49]
set ip [$inp findITerm X]
set delay [$block findInst hold23828]
if {$ip eq "NULL" || $delay eq "NULL" || [[$delay getMaster] getName] ne "sg13g2_dlygate4sd3_1"} {error "Input recovery chain missing"}
set sink [$delay findITerm A]
set inet [$ip getNet]
if {$inet eq "NULL" || $sink eq "NULL" || [$sink getNet] ne $inet || [$inet getName] ne "net49" || [llength [$inet getITerms]]!=2 || [llength [$inet getBTerms]]!=0} {error "Input recovery chain mismatch"}
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
detailed_placement
check_placement -verbose
puts "NSSOC_RESET_RECOVERY_INPUT_UPSIZED_SAME_INCIDENCE"
"""
class ResetBufferECO(ElectricalPostCTS):
    id = "NSSOC.ResetBufferECO"
    name = "Size measured reset recovery input buffer"
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
 Steps=[ResetBufferECO]+[type("Sized"+n,(BranchSTA,),dict(id="NSSOC.Sized"+n,corner=c))for n,c in CORNERS]
if __name__=="__main__":
 from librelane.__main__ import cli
 cli()
