from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces
from corrpre_postcts_flow import SingleCornerSTA,CORNERS,ElectricalPostCTS
EXTRA = r"""
set index 0
foreach {direction names} {from {pcie_rx_dllp_i pcie_rx_error_i pcie_rx_eop_i pcie_rx_sop_i pcie_rx_data_i[0] pcie_rx_data_i[1] pcie_rx_data_i[2] pcie_rx_data_i[3] pcie_rx_data_i[4] pcie_rx_data_i[5] pcie_rx_data_i[6] pcie_rx_data_i[7] pcie_rx_valid_i pcie_function_id_i[0] pcie_function_id_i[1] pcie_function_id_i[2] pcie_function_id_i[3] pcie_function_id_i[4] pcie_function_id_i[5] pcie_function_id_i[6] pcie_function_id_i[7] pcie_function_id_i[8] pcie_function_id_i[9] pcie_function_id_i[10] pcie_function_id_i[11] pcie_function_id_i[12] pcie_function_id_i[13] pcie_function_id_i[14] pcie_function_id_i[15] pcie_training_i} to {eth_txd_o[0] eth_txd_o[1] eth_txd_o[2] eth_txd_o[3] eth_txd_o[4] eth_txd_o[5] eth_txd_o[6] eth_txd_o[7] eth_tx_en_o eth_tx_er_o}} {
 foreach name $names {
  set port [get_ports [list $name]]
  if {[llength $port]!=1} {error "Missing IO $name"}
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
foreach bank {1 2 3} {
 set name [format {u_eth.u_mac.tx_fifo.fifo_inst.u_sram.g_bank[%d].u_mem/A_MEN} $bank]
 set target [get_pins [list $name]]
 if {[llength $target]!=1} {error "Missing SRAM enable target $name"}
 foreach type {max min} {
  puts "%OL_CREATE_REPORT io-$index-$type.rpt"
  puts "NSSOC_TARGET_PIN $name"
  report_checks -to $target -corner $corner_name -path_delay $type -group_path_count 10000 -fields {slew cap input net fanout} -format full_clock_expanded -digits 9
  puts "%OL_END_REPORT"
 }
 incr index
}
"""
class InputSTA(SingleCornerSTA):
 def get_script_path(self):
  p=Path(super().get_script_path());s=p.read_text()
  if not s.rstrip().endswith('write_libs'):raise RuntimeError('Unexpected native STA termination')
  q=Path(self.step_dir)/'input_timing_native.tcl';q.write_text(s+'\n'+EXTRA);return str(q)

ECO = r"""
set block [ord::get_db_block]
set master [[ord::get_db] findMaster sg13g2_dlygate4sd3_1]
if {$master eq "NULL"} {error "Missing native delay cell"}
set before {}
foreach inst [$block getInsts] {
 set pins {}
 foreach pin [$inst getITerms] {dict set pins [[$pin getMTerm] getName] [$pin getNet]}
 dict set before [$inst getName] [list [[$inst getMaster] getName] $pins]
}
set old_count [llength [$block getInsts]]
set old_nets [llength [$block getNets]]
set changed {}
foreach bank {1 2 3} {
 set instname [format {u_eth.u_mac.tx_fifo.fifo_inst.u_sram.g_bank[%d].u_mem} $bank]
 set matches {}
 foreach candidate [$block getInsts] {
  set rawname [$candidate getName]
  set canonical [string map [list "\\" ""] $rawname]
  if {$canonical eq $instname} {lappend matches $candidate}
 }
 if {[llength $matches]!=1} {error "Expected one exact SRAM instance $instname, found [llength $matches]"}
 set memory [lindex $matches 0]
 set actual_master [[$memory getMaster] getName]
 if {$actual_master ne "RM_IHPSG13_2P_256x16_c2_bm_bist"} {error "Wrong SRAM master $actual_master for $instname"}
 puts "NSSOC_SRAM_TARGET [$memory getName] $actual_master"
 set sink [$memory findITerm A_MEN]
 if {$sink eq "NULL" || [[$sink getMTerm] getIoType] ne "INPUT"} {error "Missing SRAM enable pin"}
 set net [$sink getNet]
 if {$net eq "NULL"} {error "Unconnected SRAM enable"}
 set drivers {}
 foreach pin [$net getITerms] {if {[[$pin getMTerm] getIoType] eq "OUTPUT"} {lappend drivers $pin}}
 if {[llength $drivers]!=1 || [llength [$net getBTerms]]!=0} {error "Unexpected SRAM enable source"}
 set driver [lindex $drivers 0]
 set location [[$driver getInst] getLocation]
 set orientation [[$driver getInst] getOrient]
 set stem nssoc_sram_men_hold_${bank}
 foreach name [list ${stem}_0 ${stem}_1] {
  if {[$block findInst $name] ne "NULL" || [$block findNet ${name}_out] ne "NULL"} {error "ECO name collision"}
 }
 $sink disconnect
 set last $net
 foreach suffix {0 1} {
  set inst [odb::dbInst_create $block $master ${stem}_${suffix}]
  set next [odb::dbNet_create $block ${stem}_${suffix}_out]
  [$inst findITerm A] connect $last
  [$inst findITerm X] connect $next
  $inst setOrient $orientation
  $inst setLocation {*}$location
  $inst setPlacementStatus PLACED
  set last $next
 }
 $sink connect $last
 dict set changed $sink $last
}
if {[dict size $changed]!=3 || [llength [$block getInsts]]!=$old_count+6 || [llength [$block getNets]]!=$old_nets+6} {error "Wrong ECO census"}
foreach inst [$block getInsts] {
 set name [$inst getName]
 if {![dict exists $before $name]} {continue}
 lassign [dict get $before $name] cell pins
 if {[[$inst getMaster] getName] ne $cell} {error "Original master changed"}
 foreach pin [$inst getITerms] {
  set expected [dict get $pins [[$pin getMTerm] getName]]
  if {[dict exists $changed $pin]} {set expected [dict get $changed $pin]}
  if {[$pin getNet] ne $expected} {error "Original incidence changed"}
 }
}
puts "NSSOC_SIX_NATIVE_DELAY_CELLS_THREE_SRAM_ENABLE_PINS_ONLY"
"""
class TrainingHoldECO(ElectricalPostCTS):
 id='NSSOC.TrainingHoldECO'
 name='Two native delay cells on three SRAM enable pins'
 def get_script_path(self):
  p=Path(super().get_script_path());s=p.read_text()
  a=s.index('# Buffer I/O');b=s.index('report_floating_nets -verbose',a)
  s=s[:a]+ECO+'\n'+s[b:]
  if 'log_cmd repair_design' in s or 'unset_propagated_clock [all_clocks]' in s:raise RuntimeError('Unexpected broad repair or ideal clock')
  q=Path(self.step_dir)/'training_hold_eco.tcl';q.write_text(s);return str(q)

@Flow.factory.register()
class InputTiming(Interfaces):
 Steps=[TrainingHoldECO]+[type('Input'+n,(InputSTA,),dict(id='NSSOC.Input'+n,corner=c))for n,c in CORNERS]
if __name__=='__main__':
 from librelane.__main__ import cli
 cli()
