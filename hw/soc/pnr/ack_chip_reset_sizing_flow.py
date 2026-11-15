from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces
from corrpre_postcts_flow import ElectricalPostCTS,CORNERS
from ack_chip_branches_flow import BranchSTA
ECO = r"""
set block [ord::get_db_block]
source [file join $::env(GITHUB_WORKSPACE) ack-chip-branches probe-pins.tcl]
set fh [open [file join $::env(GITHUB_WORKSPACE) ack-chip-branches native-driver-probe.tsv] w]
puts $fh "kind\tpin\tnet\tsignal_type\titerms\tbterms\toutput_drivers\tinput_ports"
foreach kind {slew unannotated} {
 if {$kind eq "slew"} {set names $slew_pins} else {set names $unannotated_pins}
 foreach pin_name $names {
  set slash [string last / $pin_name]
  if {$slash<1} {error "Bad pin $pin_name"}
  set instance_name [string range $pin_name 0 [expr {$slash-1}]]
  set terminal_name [string range $pin_name [expr {$slash+1}] end]
  set inst [$block findInst $instance_name]
  if {$inst eq "NULL"} {error "Missing instance $instance_name"}
  set pin [$inst findITerm $terminal_name]
  if {$pin eq "NULL"} {error "Missing pin $pin_name"}
  set net [$pin getNet]
  if {$net eq "NULL"} {error "Unconnected pin $pin_name"}
  set drivers {};set inputs {}
  foreach term [$net getITerms] {
   if {[$term getIoType] in {OUTPUT INOUT}} {
    set di [$term getInst]
    lappend drivers [list [$di getName] [[$term getMTerm] getName] [[$di getMaster] getName]]
   }
  }
  foreach port [$net getBTerms] {if {[$port getIoType] in {INPUT INOUT}} {lappend inputs [$port getName]}}
  puts $fh [join [list $kind $pin_name [$net getName] [$net getSigType] [llength [$net getITerms]] [llength [$net getBTerms]] $drivers $inputs] "\t"]
 }
}
close $fh
puts "NSSOC_READ_ONLY_NATIVE_DRIVER_PROBE_COMPLETE"
"""
class ResetBufferECO(ElectricalPostCTS):
    id = "NSSOC.ResetBufferECO"
    name = "Read native driver incidence without modifying cells"
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
 Steps=[ResetBufferECO]
if __name__=="__main__":
 from librelane.__main__ import cli
 cli()
