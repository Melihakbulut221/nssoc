from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces
from corrpre_postcts_flow import ElectricalPostCTS,CORNERS
from ack_chip_branches_flow import BranchSTA
ECO = '\nset block [ord::get_db_block]\nset before {}\nforeach inst [$block getInsts] {\n set pins {}\n foreach pin [$inst getITerms] {dict set pins [[$pin getMTerm] getName] [$pin getNet]}\n dict set before [$inst getName] [list [[$inst getMaster] getName] $pins]\n}\nset endpoint [$block findInst {$abc$735174$auto$blifparse.cc:397:parse_blif$761075}]\nif {$endpoint eq "NULL" || [[$endpoint getMaster] getName] ne "sg13g2_and4_2"} {error "Wrong actual status AND4"}\nset changed {}\nset plans {}\nforeach terminal {A B C D} {\n set sink [$endpoint findITerm $terminal]\n if {$sink eq "NULL" || [$sink getIoType] ne "INPUT"} {error "Wrong status logic input"}\n set oldnet [$sink getNet]\n set current $oldnet\n set seen {}\n set chain {}\n while {1} {\n  if {$current eq "NULL" || $current in $seen || [llength $seen]>32} {error "Invalid cyclic or excessive buffer chain"}\n  lappend seen $current\n  if {[llength [$current getBTerms]]} {error "Unexpected external source in status buffer ancestry"}\n  set drivers {}\n  foreach pin [$current getITerms] {if {[$pin getIoType] eq "OUTPUT"} {lappend drivers $pin}}\n  if {[llength $drivers]!=1} {error "Nonunique status ancestry driver"}\n  set driver [lindex $drivers 0]\n  set inst [$driver getInst]\n  set master [[$inst getMaster] getName]\n  if {$master ni {sg13g2_buf_1 sg13g2_buf_2 sg13g2_buf_4 sg13g2_buf_8 sg13g2_buf_16}} {break}\n  if {$driver ne [$inst findITerm X]} {error "Wrong identity buffer output"}\n  set input [$inst findITerm A]\n  if {$input eq "NULL" || [$input getIoType] ne "INPUT"} {error "Wrong identity buffer input"}\n  lappend chain [list [$inst getName] $master [$current getName]]\n  set current [$input getNet]\n }\n if {[llength $chain]} {\n  dict set changed $sink $current\n  dict set plans $terminal [list [$oldnet getName] [$current getName] $chain]\n }\n}\nif {[dict size $changed]<1 || [dict size $changed]>4} {error "Unexpected status input bypass census"}\nputs "%OL_CREATE_REPORT status-bypass-plan.rpt"\ndict for {terminal plan} $plans {puts "NSSOC_STATUS_INPUT $terminal $plan"}\nputs "%OL_END_REPORT"\ndict for {sink root} $changed {$sink disconnect; $sink connect $root}\nif {[llength [$block getInsts]]!=[dict size $before]} {error "Cell census changed"}\nforeach inst [$block getInsts] {\n lassign [dict get $before [$inst getName]] master pins\n if {[[$inst getMaster] getName] ne $master} {error "Original master changed"}\n foreach pin [$inst getITerms] {\n  set expected [dict get $pins [[$pin getMTerm] getName]]\n  if {[dict exists $changed $pin]} {set expected [dict get $changed $pin]}\n  if {[$pin getNet] ne $expected} {error "Unexpected incidence mutation"}\n }\n}\nputs "NSSOC_STATUS_INPUTS_PROVEN_IDENTITY_BUFFER_ANCESTRY_BYPASSED [dict size $changed]"\n'
class StatusBranchECO(ElectricalPostCTS):
    id = "NSSOC.StatusBranchECO"
    name = "Shorten all measured PCIe status AND4 input branches"
    def get_script_path(self):
        p = Path(super().get_script_path())
        s = p.read_text()
        a = s.index("# Buffer I/O")
        b = s.index("report_floating_nets -verbose", a)
        s = s[:a] + ECO + "\n" + s[b:]
        if "log_cmd repair_design" in s or "unset_propagated_clock [all_clocks]" in s:
            raise RuntimeError("Unexpected broad repair or ideal clock")
        q = Path(self.step_dir) / "status_branch_eco.tcl"
        q.write_text(s)
        return str(q)
@Flow.factory.register()
class AckChipStatusBranch(Interfaces):
 Steps=[StatusBranchECO]+[type("Sized"+n,(BranchSTA,),dict(id="NSSOC.Sized"+n,corner=c))for n,c in CORNERS]
if __name__=="__main__":
 from librelane.__main__ import cli
 cli()
