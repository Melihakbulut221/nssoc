from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces
from corrpre_postcts_flow import ElectricalPostCTS,CORNERS
from ack_chip_branches_flow import BranchSTA
ECO = '\nset block [ord::get_db_block]\nset before {}\nforeach inst [$block getInsts] {\n set pins {}\n foreach pin [$inst getITerms] {dict set pins [[$pin getMTerm] getName] [$pin getNet]}\n dict set before [$inst getName] [list [[$inst getMaster] getName] $pins]\n}\nset driver [$block findInst {$abc$735174$auto$blifparse.cc:397:parse_blif$749641}]\nset endpoint [$block findInst {$abc$735174$auto$blifparse.cc:397:parse_blif$761075}]\nif {$driver eq "NULL" || $endpoint eq "NULL"} {error "Missing measured port branch"}\nif {[[$driver getMaster] getName] ne "sg13g2_and2_2" || [[$endpoint getMaster] getName] ne "sg13g2_and4_2"} {error "Wrong actual port logic masters"}\nset root [[$driver findITerm X] getNet]\nset net $root\nforeach name {fanout7544 {$abc$735174$auto$blifparse.cc:397:parse_blif$761074} fanout6459} {\n set inst [$block findInst $name]\n if {$inst eq "NULL" || [[$inst getMaster] getName] ne "sg13g2_buf_4"} {error "Chain contains nonidentity cell"}\n if {[[$inst findITerm A] getNet] ne $net} {error "Measured buffer-chain incidence mismatch"}\n set net [[$inst findITerm X] getNet]\n}\nset sink [$endpoint findITerm D]\nif {$sink eq "NULL" || [$sink getIoType] ne "INPUT" || [$sink getNet] ne $net} {error "Wrong measured final sink"}\nif {$root eq "NULL" || $root eq $net || [llength [$root getBTerms]]!=0 || [llength [$net getBTerms]]!=0} {error "Invalid internal branch"}\nset drivers {}\nforeach pin [$root getITerms] {if {[$pin getIoType] eq "OUTPUT"} {lappend drivers $pin}}\nif {[llength $drivers]!=1 || [lindex $drivers 0] ne [$driver findITerm X]} {error "Ambiguous root driver"}\n$sink disconnect\n$sink connect $root\nif {[llength [$block getInsts]]!=[dict size $before]} {error "Cell census changed"}\nforeach inst [$block getInsts] {\n lassign [dict get $before [$inst getName]] master pins\n if {[[$inst getMaster] getName] ne $master} {error "Original master changed"}\n foreach pin [$inst getITerms] {\n  set expected [dict get $pins [[$pin getMTerm] getName]]\n  if {$pin eq $sink} {set expected $root}\n  if {[$pin getNet] ne $expected} {error "Unexpected incidence mutation"}\n }\n}\nputs "NSSOC_ONE_SINK_THREE_PROVEN_IDENTITY_BUFFERS_BYPASSED"\n'
class StatusBranchECO(ElectricalPostCTS):
    id = "NSSOC.StatusBranchECO"
    name = "Shorten one measured PCIe status branch"
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
