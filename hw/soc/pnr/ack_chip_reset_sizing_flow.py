from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces
from corrpre_postcts_flow import ElectricalPostCTS,CORNERS
from ack_chip_branches_flow import BranchSTA
ECO = r"""
set block [ord::get_db_block]
set before {};set nets_before {};set ports_before {}
foreach net [$block getNets] {dict set nets_before [$net getName] $net}
foreach inst [$block getInsts] {
 set pins {}
 foreach pin [$inst getITerms] {dict set pins [[$pin getMTerm] getName] [$pin getNet]}
 dict set before [$inst getName] [list [[$inst getMaster] getName] $pins]
}
foreach port [$block getBTerms] {dict set ports_before [$port getName] [$port getNet]}
set driver_name {$abc$734931$auto$blifparse.cc:397:parse_blif$747988}
set driver [$block findInst $driver_name]
if {$driver eq "NULL" || [[$driver getMaster] getName] ne "sg13g2_o21ai_1"} {error "Wrong measured driver"}
set source_pin [$driver findITerm Y]
set original_net [$source_pin getNet]
if {$original_net eq "NULL" || [llength [$original_net getITerms]]!=2 || [llength [$original_net getBTerms]]!=0} {error "Original two-terminal net changed"}
set sink "NULL"
foreach term [$original_net getITerms] {if {$term ne $source_pin} {set sink $term}}
if {$sink eq "NULL" || [$sink getIoType] ne "INPUT"} {error "Missing SRAM input"}
set sink_inst [$sink getInst]
set sink_name [$sink_inst getName]
if {[string map [list "\\" ""] $sink_name] ne {u_eth.u_mac.rx_fifo.fifo_inst.u_sram.g_bank[6].u_mem}} {error "Wrong SRAM instance"}
set sink_term [[$sink getMTerm] getName]
if {[string map [list "\\" ""] $sink_term] ne {A_DIN[9]}} {error "Wrong SRAM terminal"}
set buffer_name nssoc_sram_din9_buf
set new_net_name nssoc_sram_din9_buf_net
if {[$block findInst $buffer_name] ne "NULL" || [$block findNet $new_net_name] ne "NULL"} {error "ECO names already exist"}
if {[llength [info commands insert_buffer]]!=1 || [llength [info commands rsz::insert_buffer_after_driver_cmd]]!=1} {error "Pinned insertion API missing"}
insert_buffer -buffer_cell sg13g2_buf_4 -net [$original_net getName] -buffer_name $buffer_name -net_name $new_net_name
# Native insertion uniquifies requested base names. Identify the exact delta.
set added_instances {};set added_nets {}
foreach candidate [$block getInsts] {
 if {![dict exists $before [$candidate getName]]} {lappend added_instances $candidate}
}
foreach candidate [$block getNets] {
 if {![dict exists $nets_before [$candidate getName]]} {lappend added_nets $candidate}
}
if {[llength $added_instances]!=1 || [llength $added_nets]!=1} {error "Insertion did not add exactly one cell and net"}
set added [lindex $added_instances 0]
set buffer_name [$added getName]
set created [lindex $added_nets 0]
set new_net_name [$created getName]
if {[[$added getMaster] getName] ne "sg13g2_buf_4"} {error "New cell is not the requested noninverting buffer"}
puts "NSSOC_BUFFER_ACTUAL_NAMES [list $buffer_name $new_net_name]"
set ai [$added findITerm A];set xo [$added findITerm X]
if {$ai eq "NULL" || $xo eq "NULL" || [$ai getIoType] ne "INPUT" || [$xo getIoType] ne "OUTPUT"} {error "Wrong buffer interface"}
set upstream [$source_pin getNet];set downstream [$sink getNet]
if {$upstream eq "NULL" || $downstream eq "NULL" || $upstream eq $downstream} {error "Buffer bypass or disconnected chain"}
if {[$ai getNet] ne $upstream || [$xo getNet] ne $downstream} {error "Wrong chain polarity or wiring"}
set created [$block findNet $new_net_name]
if {$created eq "NULL" || !($original_net in [list $upstream $downstream]) || !($created in [list $upstream $downstream])} {error "Unexpected chain nets"}
foreach net [list $upstream $downstream] {
 if {[llength [$net getITerms]]!=2 || [llength [$net getBTerms]]!=0} {error "Unexpected chain branches"}
}
if {[llength [$block getInsts]]!=[expr {[dict size $before]+1}] || [llength [$block getNets]]!=[expr {[dict size $nets_before]+1}]} {error "Unexpected cell/net census"}
foreach net [$block getNets] {
 if {[$net getName] eq $new_net_name} {continue}
 if {![dict exists $nets_before [$net getName]] || [dict get $nets_before [$net getName]] ne $net} {error "Other net identity changed"}
}
foreach inst [$block getInsts] {
 set name [$inst getName]
 if {$name eq $buffer_name} {continue}
 if {![dict exists $before $name]} {error "Unexpected instance"}
 lassign [dict get $before $name] master pins
 if {[[$inst getMaster] getName] ne $master || [llength [$inst getITerms]]!=[dict size $pins]} {error "Existing cell changed"}
 foreach term [$inst getITerms] {
  if {$term eq $source_pin || $term eq $sink} {continue}
  set pinname [[$term getMTerm] getName]
  if {![dict exists $pins $pinname] || [$term getNet] ne [dict get $pins $pinname]} {error "Unrelated incidence changed"}
 }
}
foreach term [$added getITerms] {
 if {$term eq $ai || $term eq $xo} {continue}
 set pinname [[$term getMTerm] getName];set net [$term getNet]
 if {$pinname ni {VDD VSS}} {error "Unexpected buffer pin"}
 if {$net ne "NULL"} {
  if {![dict exists $nets_before [$net getName]] || [$net getSigType] ni {POWER GROUND}} {error "Incorrect buffer supply connection"}
 }
}
foreach port [$block getBTerms] {if {[$port getNet] ne [dict get $ports_before [$port getName]]} {error "Port incidence changed"}}
detailed_placement
check_placement -verbose
puts "NSSOC_SRAM_DIN_BUFFER_EXACT_NONINVERTING_CHAIN_VERIFIED"
"""
class ResetBufferECO(ElectricalPostCTS):
    id = "NSSOC.ResetBufferECO"
    name = "Insert one guarded SRAM data buffer"
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
