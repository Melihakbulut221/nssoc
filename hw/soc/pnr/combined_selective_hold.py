# SPDX-License-Identifier: Apache-2.0
"""Measure setup and hold for every current PCIe input and Ethernet output."""
from pathlib import Path
import json
from librelane.flows import Flow
from interface_flow import Interfaces
from corrpre_postcts_flow import SingleCornerSTA, CORNERS, ElectricalPostCTS
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
if {$index!=123} {error "Wrong branch census"}
puts "NSSOC_123_BRANCHES_MEASURED"
"""
class TargetIOSTA(SingleCornerSTA):
    def get_script_path(self):
        p=Path(super().get_script_path())
        s=p.read_text()
        if not s.rstrip().endswith("write_libs"):raise RuntimeError("Unexpected native STA termination")
        rows=json.loads((Path(__file__).resolve().parents[3]/"selective-hold-trial/targets.json").read_text())
        assert len(rows)==123
        names=[]
        for row in rows:
            name=row["sink"]
            if any(c in name for c in "{}\n\r"):raise RuntimeError("Invalid target pin")
            names.append("{"+name+"}")
        q=Path(self.step_dir)/"branch_headroom.tcl"
        q.write_text(s+"\n"+EXTRA+"\n"+BRANCH_EXTRA.replace("BRANCH_NAMES"," ".join(names)))
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
set master [[ord::get_db] findMaster sg13g2_dlygate4sd3_1]
if {$master eq "NULL"} {error "Missing native delay"}
set changed {}
set index 0
foreach row {SELECTED_ROWS} {
 lassign $row source_name source_pin source_cell sink_name sink_pin sink_cell
 set sourceinst [$block findInst $source_name]
 set sinkinst [$block findInst $sink_name]
 if {$sourceinst eq "NULL" || $sinkinst eq "NULL"} {error "Missing measured branch"}
 if {[[$sourceinst getMaster] getName] ne $source_cell || [[$sinkinst getMaster] getName] ne $sink_cell} {error "Measured branch master differs"}
 set driver [$sourceinst findITerm $source_pin]
 set sink [$sinkinst findITerm $sink_pin]
 if {$driver eq "NULL" || $sink eq "NULL" || [$driver getIoType] ne "OUTPUT" || [$sink getIoType] ne "INPUT"} {error "Measured pin role differs"}
 set net [$sink getNet]
 if {$net eq "NULL" || [$driver getNet] ne $net || [llength [$net getBTerms]]!=0} {error "Measured incidence differs"}
 set drivers {}
 foreach pin [$net getITerms] {if {[$pin getIoType] eq "OUTPUT"} {lappend drivers $pin}}
 if {[llength $drivers]!=1 || [lindex $drivers 0] ne $driver} {error "Unexpected drivers"}
 if {[dict exists $changed $sink]} {error "Duplicate sink"}
 set cellname [format nssoc_selected_hold_%d $index]
 set netname [format nssoc_selected_hold_%d_out $index]
 if {[$block findInst $cellname] ne "NULL" || [$block findNet $netname] ne "NULL"} {error "ECO collision"}
 set inst [odb::dbInst_create $block $master $cellname]
 set next [odb::dbNet_create $block $netname]
 [$inst findITerm A] connect $net
 [$inst findITerm X] connect $next
 $sink disconnect
 $sink connect $next
 $inst setOrient [$sinkinst getOrient]
 $inst setLocation {*}[$sinkinst getLocation]
 $inst setPlacementStatus PLACED
 dict set changed $sink $next
 incr index
}
if {$index!=120 || [dict size $changed]!=120 || [llength [$block getInsts]]!=[dict size $before]+120 || [llength [$block getNets]]!=$oldnets+120} {error "Wrong selective ECO census"}
foreach inst [$block getInsts] {
 set name [$inst getName]
 if {![dict exists $before $name]} {continue}
 lassign [dict get $before $name] oldmaster pins
 if {[[$inst getMaster] getName] ne $oldmaster} {error "Original master changed"}
 foreach pin [$inst getITerms] {
  set expected [dict get $pins [[$pin getMTerm] getName]]
  if {[dict exists $changed $pin]} {set expected [dict get $changed $pin]}
  if {[$pin getNet] ne $expected} {error "Unexpected original incidence change"}
 }
}
puts "NSSOC_120_MEASURED_BRANCH_IDENTITY_DELAYS_VERIFIED"
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
class SelectiveHoldECO(ElectricalPostCTS):
    id="NSSOC.SelectiveHoldECO"
    name="Repair120 branches with measured setup margin"
    def get_script_path(self):
        rows=json.loads((Path(__file__).resolve().parents[3]/"combined-hold-trial/selected.json").read_text())
        assert len(rows)==120
        tcl_rows=[]
        for row in rows:
            source,sp=row["source"].rsplit("/",1);sink,tp=row["sink"].rsplit("/",1)
            fields=[source,sp,row["source_cell"],sink,tp,row["sink_cell"]]
            assert all(not any(c in x for c in "{}\n\r") for x in fields)
            tcl_rows.append("{"+" ".join("{"+x+"}" for x in fields)+"}")
        p=Path(super().get_script_path());s=p.read_text()
        a=s.index("# Buffer I/O");b=s.index("report_floating_nets -verbose",a)
        s=s[:a]+ECO.replace("SELECTED_ROWS","\n".join(tcl_rows))+"\n"+s[b:]
        assert "log_cmd repair_design" not in s and "unset_propagated_clock [all_clocks]" not in s
        assert s.count("write_views")==1
        s=s.replace("write_views",RESTORE+"\nwrite_views")
        q=Path(self.step_dir)/"selective_hold.tcl";q.write_text(s);return str(q)

