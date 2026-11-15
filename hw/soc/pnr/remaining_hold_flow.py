# SPDX-License-Identifier: Apache-2.0
"""Measure setup and hold for every current PCIe input and Ethernet output."""
from pathlib import Path
import json
from corrpre_postcts_flow import ElectricalPostCTS
from librelane.flows import Flow
from interface_flow import Interfaces
from corrpre_postcts_flow import SingleCornerSTA, CORNERS
EXTRA = r"""
set index 0
foreach {direction names} {from {pcie_training_i pcie_function_id_i[0] pcie_function_id_i[1] pcie_function_id_i[2] pcie_function_id_i[3] pcie_function_id_i[4] pcie_function_id_i[5] pcie_function_id_i[6] pcie_function_id_i[7] pcie_function_id_i[8] pcie_function_id_i[9] pcie_function_id_i[10] pcie_function_id_i[11] pcie_function_id_i[12] pcie_function_id_i[13] pcie_function_id_i[14] pcie_function_id_i[15] pcie_rx_data_i[0] pcie_rx_data_i[1] pcie_rx_data_i[2] pcie_rx_data_i[3] pcie_rx_data_i[4] pcie_rx_data_i[5] pcie_rx_data_i[6] pcie_rx_data_i[7] pcie_rx_dllp_i pcie_rx_error_i pcie_rx_eop_i pcie_rx_sop_i pcie_rx_valid_i} to {eth_txd_o[0] eth_txd_o[1] eth_txd_o[2] eth_txd_o[3] eth_txd_o[4] eth_txd_o[5] eth_txd_o[6] eth_txd_o[7] eth_tx_en_o eth_tx_er_o}} {
 foreach name $names {
  set port [get_ports [list $name]]
  if {[llength $port]!=1} {error "Missing boundary port $name"}
  foreach type {max min} {
   puts "%OL_CREATE_REPORT io-$index-$type.rpt"
   puts "NSSOC_TARGET_PORT $name"
   if {$direction eq "from"} {
    report_checks -from $port -corner $corner_name -path_delay $type -group_path_count 10000 -fields {slew cap input net fanout} -format full_clock_expanded -digits 9
   } else {
    report_checks -to $port -corner $corner_name -path_delay $type -group_path_count 10000 -fields {slew cap input net fanout} -format full_clock_expanded -digits 9
   }
   puts "%OL_END_REPORT"
  }
  incr index
 }
}
if {$index!=40} {error "Boundary census changed"}
puts "NSSOC_IO_PATHS_MEASURED"
"""
BRANCH_EXTRA = r"""

set index 0
foreach name {BRANCH_NAMES} {
 set target [get_pins [list $name]]
 if {[llength $target]!=1} {error "Missing measured branch $name"}
 foreach type {max min} {
  puts "%OL_CREATE_REPORT branch-$index-$type.rpt"
  puts "NSSOC_TARGET_BRANCH_PIN $name"
  report_checks -through $target -corner $corner_name -path_delay $type -group_path_count 10000 -fields {slew cap input net fanout} -format full_clock_expanded -digits 9
  puts "%OL_END_REPORT"
 }
 incr index
}
if {$index!=TARGET_COUNT} {error "Wrong branch census"}
puts "NSSOC_REMAINING_BRANCH_INPUTS_MEASURED"
"""
class TargetIOSTA(SingleCornerSTA):
    def get_script_path(self):
        p=Path(super().get_script_path())
        s=p.read_text()
        if not s.rstrip().endswith("write_libs"):raise RuntimeError("Unexpected native STA termination")
        rows=json.loads((Path(__file__).resolve().parents[3]/"remaining-hold-trial/targets.json").read_text())
        assert 3<=len(rows)<=15
        names=[]
        for row in rows:
            name=row["sink"]
            if any(c in name for c in "{}\n\r"):raise RuntimeError("Invalid target pin")
            names.append("{"+name+"}")
        q=Path(self.step_dir)/"branch_headroom.tcl"
        q.write_text(s+"\n"+EXTRA+"\n"+BRANCH_EXTRA.replace("BRANCH_NAMES"," ".join(names)).replace("TARGET_COUNT",str(len(rows))))
        return str(q)
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
proc unique_driver {net} {
 if {$net eq "NULL" || [llength [$net getBTerms]]!=0} {error "Unexpected boundary net"}
 set drivers {}
 foreach pin [$net getITerms] {if {[$pin getIoType] eq "OUTPUT"} {lappend drivers $pin}}
 if {[llength $drivers]!=1} {error "Nonunique driver"}
 return [lindex $drivers 0]
}
set plans {
 {feedback_credit {$abc$735036$auto$blifparse.cc:397:parse_blif$738189} Y sg13g2_inv_1 {$abc$735036$auto$blifparse.cc:397:parse_blif$771053} A1 sg13g2_o21ai_1 0}
 {feedback_index {$abc$735036$auto$blifparse.cc:397:parse_blif$770028} Y sg13g2_nand2b_1 {$abc$735036$auto$blifparse.cc:397:parse_blif$770030} A2 sg13g2_o21ai_1 0}
 {index_branch {$abc$735036$auto$blifparse.cc:397:parse_blif$749466} X sg13g2_buf_1 {$abc$735036$auto$blifparse.cc:397:parse_blif$770358} A sg13g2_nand3_1 0}
}
set changes {}
foreach plan $plans {
 lassign $plan label source_name source_port source_master sink_name sink_port sink_master depth
 set si [$block findInst $source_name];set ti [$block findInst $sink_name]
 if {$si eq "NULL" || $ti eq "NULL"} {error "Missing exact branch endpoint"}
 if {[[$si getMaster] getName] ne $source_master || [[$ti getMaster] getName] ne $sink_master} {error "Endpoint master differs"}
 set sourcepin [$si findITerm $source_port];set sink [$ti findITerm $sink_port]
 if {$sourcepin eq "NULL" || $sink eq "NULL" || [$sourcepin getIoType] ne "OUTPUT" || [$sink getIoType] ne "INPUT"} {error "Endpoint pin direction differs"}
 set walk [unique_driver [$sink getNet]]
 set count 0
 set visited {}
 while {$walk ne $sourcepin} {
  set wi [$walk getInst]
  if {![regexp {^sg13g2_buf_(1|2|4|8|16)$} [[$wi getMaster] getName]] || [[$walk getMTerm] getName] ne "X"} {error "Path contains nonidentity cell"}
  if {[dict exists $visited [$wi getName]]} {error "Identity path cycle"}
  dict set visited [$wi getName] 1
  set walk [unique_driver [[$wi findITerm A] getNet]]
  incr count
  if {$count>10} {error "Unexpected buffer chain length"}
 }
 if {$count!=$depth} {error "Measured chain depth differs"}
 if {[unique_driver [$sourcepin getNet]] ne $sourcepin} {error "Source driver differs"}
 set stem [format "nssoc_remaining_hold_%s" $label]
 set netname [format "%s_out" $stem]
 if {[$block findInst $stem] ne "NULL" || [$block findNet $netname] ne "NULL"} {error "ECO collision"}
 set master [[ord::get_db] findMaster sg13g2_dlygate4sd3_1]
 if {$master eq "NULL"} {error "Missing native identity buffer"}
 set inst [odb::dbInst_create $block $master $stem]
 set next [odb::dbNet_create $block $netname]
 [$inst findITerm A] connect [$sourcepin getNet]
 [$inst findITerm X] connect $next
 $sink disconnect
 $sink connect $next
 dict set changes $sink $next
 $inst setOrient [$ti getOrient]
 $inst setLocation {*}[$ti getLocation]
 $inst setPlacementStatus PLACED
 puts "NSSOC_IDENTITY_BRANCH $label $depth $source_name $sink_name"
}
if {[llength [$block getInsts]]!=[dict size $before]+3 || [llength [$block getNets]]!=$oldnets+3 || [dict size $changes]!=3} {error "Wrong ECO census"}
foreach inst [$block getInsts] {
 set name [$inst getName]
 if {![dict exists $before $name]} {continue}
 lassign [dict get $before $name] master pins
 if {[[$inst getMaster] getName] ne $master} {error "Original master changed"}
 foreach pin [$inst getITerms] {
  set expected [dict get $pins [[$pin getMTerm] getName]]
  if {[dict exists $changes $pin]} {set expected [dict get $changes $pin]}
  if {[$pin getNet] ne $expected} {error "Unexpected original incidence change"}
 }
}
puts "NSSOC_THREE_REMAINING_HOLD_BRANCHES_IDENTITY_VERIFIED"
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

class RemainingHoldECO(ElectricalPostCTS):
    id="NSSOC.RemainingHoldECO"
    name="Repair three measured remaining hold branches"
    def get_script_path(self):
        p=Path(super().get_script_path());s=p.read_text()
        a=s.index("# Buffer I/O");b=s.index("report_floating_nets -verbose",a)
        s=s[:a]+ECO+"\n"+s[b:]
        if "log_cmd repair_design" in s or "unset_propagated_clock [all_clocks]" in s:raise RuntimeError("Unexpected broad repair or ideal clocks")
        assert s.count("write_views")==1
        s=s.replace("write_views",RESTORE+"\nwrite_views")
        q=Path(self.step_dir)/"one_branch_eco.tcl";q.write_text(s);return str(q)

@Flow.factory.register()
class RemainingHoldTrial(Interfaces):
    Steps=[RemainingHoldECO]+[type("TargetIO"+n,(TargetIOSTA,),dict(id="NSSOC.CorrpreTargetIOAfter"+n,corner=c)) for n,c in CORNERS]
if __name__=="__main__":
    from librelane.__main__ import cli
    cli()
