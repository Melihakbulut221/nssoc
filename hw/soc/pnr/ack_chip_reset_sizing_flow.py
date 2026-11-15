from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces
from corrpre_postcts_flow import ElectricalPostCTS,CORNERS
from ack_chip_branches_flow import BranchSTA
ECO = r"""
set block [ord::get_db_block]
source [file join $::env(GITHUB_WORKSPACE) ack-chip-branches buffer-specs.tcl]
set expected_count [llength $buffer_specs]
if {$expected_count<1 || $expected_count>31} {error "Unexpected target census"}
set before {};set nets_before {};set ports_before {}
foreach net [$block getNets] {dict set nets_before [$net getName] $net}
foreach inst [$block getInsts] {
 set pins {}
 foreach pin [$inst getITerms] {dict set pins [[$pin getMTerm] getName] [$pin getNet]}
 dict set before [$inst getName] [list [[$inst getMaster] getName] $pins]
}
foreach port [$block getBTerms] {dict set ports_before [$port getName] [$port getNet]}
set originals {};set changed_pins {};set original_nets {}
foreach spec $buffer_specs {
 lassign $spec driver_name expected_instance expected_terminal
 set driver [$block findInst $driver_name]
 if {$driver eq "NULL" || [[$driver getMaster] getName] ne "sg13g2_o21ai_1"} {error "Wrong measured driver"}
 set source_pin [$driver findITerm Y]
 set original_net [$source_pin getNet]
 if {$original_net eq "NULL" || [llength [$original_net getITerms]]!=2 || [llength [$original_net getBTerms]]!=0} {error "Original two-terminal net changed"}
 if {[dict exists $original_nets $original_net]} {error "Duplicate target net"}
 dict set original_nets $original_net 1
 set sink "NULL"
 foreach term [$original_net getITerms] {if {$term ne $source_pin} {set sink $term}}
 if {$sink eq "NULL" || [$sink getIoType] ne "INPUT"} {error "Missing SRAM input"}
 if {[string map [list "\\" ""] [[$sink getInst] getName]] ne $expected_instance || [string map [list "\\" ""] [[$sink getMTerm] getName]] ne $expected_terminal} {error "Wrong SRAM target"}
 lappend originals [list $source_pin $sink $original_net]
 dict set changed_pins $source_pin 1;dict set changed_pins $sink 1
}
if {[dict size $changed_pins]!=2*$expected_count} {error "Targets overlap"}
if {[llength [info commands insert_buffer]]!=1 || [llength [info commands rsz::insert_buffer_after_driver_cmd]]!=1} {error "Insertion API missing"}
set chains {};set added_instances {};set added_nets {};set index 0
foreach record $originals {
 lassign $record source_pin sink original_net
 set inst_before {};set net_before {}
 foreach inst [$block getInsts] {dict set inst_before [$inst getName] 1}
 foreach net [$block getNets] {dict set net_before [$net getName] 1}
 insert_buffer -buffer_cell sg13g2_buf_4 -net [$original_net getName] -buffer_name nssoc_sram_oai_buf_$index -net_name nssoc_sram_oai_net_$index
 set new_instances {};set new_nets {}
 foreach inst [$block getInsts] {if {![dict exists $inst_before [$inst getName]]} {lappend new_instances $inst}}
 foreach net [$block getNets] {if {![dict exists $net_before [$net getName]]} {lappend new_nets $net}}
 if {[llength $new_instances]!=1 || [llength $new_nets]!=1} {error "Insertion delta not one cell and net"}
 set added [lindex $new_instances 0];set created [lindex $new_nets 0]
 if {[[$added getMaster] getName] ne "sg13g2_buf_4"} {error "Wrong buffer master"}
 dict set added_instances [$added getName] $added;dict set added_nets [$created getName] $created
 lappend chains [list $source_pin $sink $original_net $added $created]
 puts "NSSOC_BUFFER_ACTUAL_NAMES [list [$added getName] [$created getName]]"
 incr index
}
if {[llength [$block getInsts]]!=[dict size $before]+$expected_count || [llength [$block getNets]]!=[dict size $nets_before]+$expected_count} {error "Global insertion census mismatch"}
foreach chain $chains {
 lassign $chain source_pin sink original_net added created
 set ai [$added findITerm A];set xo [$added findITerm X]
 if {$ai eq "NULL" || $xo eq "NULL" || [$ai getIoType] ne "INPUT" || [$xo getIoType] ne "OUTPUT"} {error "Wrong buffer interface"}
 set upstream [$source_pin getNet];set downstream [$sink getNet]
 if {$upstream eq "NULL" || $downstream eq "NULL" || $upstream eq $downstream || [$ai getNet] ne $upstream || [$xo getNet] ne $downstream} {error "Broken or bypassed chain"}
 if {!($original_net in [list $upstream $downstream]) || !($created in [list $upstream $downstream])} {error "Unexpected chain nets"}
 foreach net [list $upstream $downstream] {if {[llength [$net getITerms]]!=2 || [llength [$net getBTerms]]!=0} {error "Extra chain branches"}}
 foreach term [$added getITerms] {
  if {$term eq $ai || $term eq $xo} {continue}
  set pinname [[$term getMTerm] getName];set net [$term getNet]
  if {$pinname ni {VDD VSS}} {error "Unexpected buffer pin"}
  if {$net ne "NULL" && (![dict exists $nets_before [$net getName]] || [$net getSigType] ni {POWER GROUND})} {error "Incorrect supply"}
 }
}
foreach net [$block getNets] {
 set name [$net getName]
 if {[dict exists $added_nets $name]} {continue}
 if {![dict exists $nets_before $name] || [dict get $nets_before $name] ne $net} {error "Unrelated net identity changed"}
}
foreach inst [$block getInsts] {
 set name [$inst getName]
 if {[dict exists $added_instances $name]} {continue}
 if {![dict exists $before $name]} {error "Unexpected instance"}
 lassign [dict get $before $name] master pins
 if {[[$inst getMaster] getName] ne $master || [llength [$inst getITerms]]!=[dict size $pins]} {error "Existing cell changed"}
 foreach term [$inst getITerms] {
  if {[dict exists $changed_pins $term]} {continue}
  set pinname [[$term getMTerm] getName]
  if {![dict exists $pins $pinname] || [$term getNet] ne [dict get $pins $pinname]} {error "Unrelated pin incidence changed"}
 }
}
foreach port [$block getBTerms] {if {[$port getNet] ne [dict get $ports_before [$port getName]]} {error "Port incidence changed"}}
detailed_placement
check_placement -verbose
puts "NSSOC_SRAM_OAI_BATCH_EXACT_NONINVERTING_CHAINS_VERIFIED $expected_count"
"""
class ResetBufferECO(ElectricalPostCTS):
    id = "NSSOC.ResetBufferECO"
    name = "Insert guarded SRAM OAI buffer batch"
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
