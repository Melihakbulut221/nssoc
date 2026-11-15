from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces
from corrpre_postcts_flow import ElectricalPostCTS,CORNERS
from ack_chip_branches_flow import BranchSTA
ECO = r"""
set block [ord::get_db_block]
# STA display names omit OpenDB escape characters. Require a unique mapping.
proc canonical_name {name} {return [string map [list "\\" ""] $name]}
set instance_map {}
foreach inst [$block getInsts] {
 set key [canonical_name [$inst getName]]
 if {[dict exists $instance_map $key]} {error "Ambiguous canonical instance $key"}
 dict set instance_map $key $inst
}
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
  set key [canonical_name $instance_name]
  if {![dict exists $instance_map $key]} {error "Missing instance $instance_name"}
  set inst [dict get $instance_map $key]
  set pin "NULL"
  foreach candidate [$inst getITerms] {
   if {[canonical_name [[$candidate getMTerm] getName]] eq [canonical_name $terminal_name]} {
    if {$pin ne "NULL"} {error "Ambiguous canonical pin $pin_name"}
    set pin $candidate
   }
  }
  if {$pin eq "NULL"} {error "Missing pin $pin_name"}
  set net [$pin getNet]
  if {$net eq "NULL"} {
   if {$kind ne "unannotated" || [$pin getIoType] ni {OUTPUT INOUT}} {error "Unexpected unconnected target $pin_name"}
   puts $fh [join [list $kind $pin_name "" UNCONNECTED 0 0 [list [list [$inst getName] [[$pin getMTerm] getName] [[$inst getMaster] getName]]] {}] "\t"]
   continue
  }
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
set cap [open [file join $::env(GITHUB_WORKSPACE) ack-chip-branches native-buffer-capabilities.txt] w]
puts $cap "READ_ONLY_RUNTIME_CAPABILITIES"
foreach command {insert_buffer rsz::insert_buffer_before_load_cmd rsz::insert_buffer_before_loads_cmd rsz::insert_buffer_after_driver_cmd} {
 puts $cap [list command $command available [llength [info commands $command]]]
 if {[llength [info procs $command]]==1} {puts $cap [list body $command [info body $command]]}
}
set db [ord::get_db]
foreach lib [$db getLibs] {
 foreach master [$lib getMasters] {
  set name [$master getName]
  if {[regexp {^sg13g2_(inv|buf|nor2|nor2b|a21o|o21ai|mux2|nand2b)_[0-9]+$} $name]} {
   set terms {}
   foreach term [$master getMTerms] {lappend terms [list [$term getName] [$term getIoType]]}
   puts $cap [list master $name width [$master getWidth] height [$master getHeight] terms $terms]
  }
 }
}
close $cap
set rf [open [file join $::env(GITHUB_WORKSPACE) ack-chip-branches native-reset-release.tsv] w]
puts $rf "instance\tmaster\tQ_net\tD_net\tRESET_B_net\tCLK_net"
set target_found 0
foreach inst [$block getInsts] {
 set name [$inst getName]
 set qp [$inst findITerm Q]
 if {$qp eq "NULL" || [$qp getNet] eq "NULL"} {continue}
 set qn [[$qp getNet] getName]
 if {$name ne {$auto$ff.cc:337:slice$310738} && ![regexp {u_pcie_cdc.*(release|reset)} $qn]} {continue}
 set fields [list $name [[$inst getMaster] getName] $qn]
 foreach pn {D RESET_B CLK} {
  set term [$inst findITerm $pn]
  if {$term eq "NULL"} {error "Selected reset flop lacks $pn"}
  set net [$term getNet]
  if {$net eq "NULL"} {error "Selected reset flop has disconnected $pn"}
  lappend fields [$net getName]
 }
 puts $rf [join $fields "\t"]
 if {$name eq {$auto$ff.cc:337:slice$310738}} {incr target_found}
}
if {$target_found!=1} {error "Recovery endpoint not uniquely found"}
close $rf
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
