# SPDX-License-Identifier: Apache-2.0
"""Measure setup and hold for every current PCIe input and Ethernet output."""
from pathlib import Path
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
class TargetIOSTA(SingleCornerSTA):
    def get_script_path(self):
        p=Path(super().get_script_path())
        s=p.read_text()
        if not s.rstrip().endswith("write_libs"):raise RuntimeError("Unexpected native STA termination")
        q=Path(self.step_dir)/"target_io.tcl";q.write_text(s+"\n"+EXTRA);return str(q)

ECO = r"""
set block [ord::get_db_block]
set master [[ord::get_db] findMaster sg13g2_dlygate4sd3_1]
if {$master eq "NULL"} {error "Missing native delay cell"}
set before {}
set original_placement {}
foreach inst [$block getInsts] {
 set pins {}
 foreach pin [$inst getITerms] {dict set pins [[$pin getMTerm] getName] [$pin getNet]}
 dict set before [$inst getName] [list [[$inst getMaster] getName] $pins]
 dict set original_placement [$inst getName] [list [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus]]
 if {[$inst getPlacementStatus] eq "PLACED"} {$inst setPlacementStatus FIRM}
}
set port_before {}
foreach port [$block getBTerms] {dict set port_before [$port getName] [$port getNet]}
set oldnets [llength [$block getNets]]
set changed_pins {}
set changed_ports {}
set index 0
foreach {direction names} {from {pcie_training_i pcie_function_id_i[0] pcie_function_id_i[1] pcie_function_id_i[2] pcie_function_id_i[3] pcie_function_id_i[4] pcie_function_id_i[5] pcie_function_id_i[6] pcie_function_id_i[7] pcie_function_id_i[8] pcie_function_id_i[9] pcie_function_id_i[10] pcie_function_id_i[11] pcie_function_id_i[12] pcie_function_id_i[13] pcie_function_id_i[14] pcie_function_id_i[15] pcie_rx_data_i[0] pcie_rx_data_i[1] pcie_rx_data_i[2] pcie_rx_data_i[3] pcie_rx_data_i[4] pcie_rx_data_i[5] pcie_rx_data_i[6] pcie_rx_data_i[7] pcie_rx_dllp_i pcie_rx_error_i pcie_rx_eop_i pcie_rx_sop_i pcie_rx_valid_i} to {eth_txd_o[0] eth_txd_o[1] eth_txd_o[2] eth_txd_o[3] eth_txd_o[4] eth_txd_o[5] eth_txd_o[6] eth_txd_o[7] eth_tx_en_o eth_tx_er_o}} {
 foreach name $names {
  set port [$block findBTerm $name]
  if {$port eq "NULL"} {error "Missing measured port $name"}
  set net [$port getNet]
  if {$net eq "NULL" || [llength [$net getBTerms]]!=1} {error "Unexpected port net"}
  if {$direction eq "from"} {
   if {[$port getIoType] ne "INPUT"} {error "Wrong port direction"}
   set loads [$net getITerms]
   if {[llength $loads]<1} {error "No input loads"}
   foreach pin $loads {if {[$pin getIoType] ne "INPUT"} {error "Unexpected input driver"}}
   set near [[lindex $loads 0] getInst]
  } else {
   if {[$port getIoType] ne "OUTPUT"} {error "Wrong port direction"}
   set drivers {}
   foreach pin [$net getITerms] {if {[$pin getIoType] eq "OUTPUT"} {lappend drivers $pin}}
   if {[llength $drivers]!=1} {error "Unexpected output driver"}
   set near [[lindex $drivers 0] getInst]
  }
  set last $net
  foreach stage {0 1} {
   set cellname [format nssoc_boundary_delay_%d_%d $index $stage]
   set netname [format nssoc_boundary_delay_%d_%d_out $index $stage]
   if {[$block findInst $cellname] ne "NULL" || [$block findNet $netname] ne "NULL"} {error "ECO collision"}
   set inst [odb::dbInst_create $block $master $cellname]
   set next [odb::dbNet_create $block $netname]
   [$inst findITerm A] connect $last
   [$inst findITerm X] connect $next
   $inst setOrient [$near getOrient]
   $inst setLocation {*}[$near getLocation]
   $inst setPlacementStatus PLACED
   set last $next
  }
  if {$direction eq "from"} {
   foreach pin $loads {$pin disconnect; $pin connect $last; dict set changed_pins $pin $last}
  } else {
   $port disconnect
   $port connect $last
   dict set changed_ports $name $last
  }
  incr index
 }
}
if {$index!=40 || [dict size $changed_ports]!=10 || [llength [$block getInsts]]!=[expr {[dict size $before]+80}] || [llength [$block getNets]]!=$oldnets+80} {error "Wrong boundary ECO census"}
foreach inst [$block getInsts] {
 set name [$inst getName]
 if {![dict exists $before $name]} {continue}
 lassign [dict get $before $name] mastername pins
 if {[[$inst getMaster] getName] ne $mastername} {error "Original master changed"}
 foreach pin [$inst getITerms] {
  set expected [dict get $pins [[$pin getMTerm] getName]]
  if {[dict exists $changed_pins $pin]} {set expected [dict get $changed_pins $pin]}
  if {[$pin getNet] ne $expected} {error "Unexpected original incidence change"}
 }
}
foreach port [$block getBTerms] {
 set name [$port getName]
 set expected [dict get $port_before $name]
 if {[dict exists $changed_ports $name]} {set expected [dict get $changed_ports $name]}
 if {[$port getNet] ne $expected} {error "Unexpected port incidence change"}
}
puts "NSSOC_80_NATIVE_DELAY_CELLS_40_BOUNDARY_PORTS_INCIDENCE_VERIFIED"
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
class BoundaryHoldECO(ElectricalPostCTS):
    id="NSSOC.BoundaryHoldECO"
    name="Two identity delay cells per measured boundary port"
    def get_script_path(self):
        p=Path(super().get_script_path());s=p.read_text()
        a=s.index("# Buffer I/O");b=s.index("report_floating_nets -verbose",a)
        s=s[:a]+ECO+"\n"+s[b:]
        if "log_cmd repair_design" in s or "unset_propagated_clock [all_clocks]" in s:raise RuntimeError("Unexpected broad repair or ideal clock")
        if s.count("write_views")!=1:raise RuntimeError("Unexpected native write boundary")
        s=s.replace("write_views",RESTORE+"\nwrite_views")
        q=Path(self.step_dir)/"boundary_hold_eco.tcl";q.write_text(s);return str(q)

