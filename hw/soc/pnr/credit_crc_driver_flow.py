from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces
from corrpre_postcts_flow import ElectricalPostCTS,CORNERS
from corrpre_postcts_flow import SingleCornerSTA as BranchSTA
ECO = r"""
set block [ord::get_db_block]
set before {}
foreach inst [$block getInsts] {
 set pins {}
 foreach pin [$inst getITerms] {dict set pins [[$pin getMTerm] getName] [$pin getNet]}
 dict set before [$inst getName] [list [[$inst getMaster] getName] $pins]
}
set choices {
 {$abc$735191$auto$blifparse.cc:397:parse_blif$740611} {sg13g2_buf_1 sg13g2_buf_4}
 {fanout8587} {sg13g2_buf_1 sg13g2_buf_4}
 {$abc$735191$auto$blifparse.cc:397:parse_blif$760683} {sg13g2_nor4_1 sg13g2_nor4_2}
}
set targets [dict keys $choices]
if {[llength $targets]!=3} {error "Wrong measured resize census"}
if {[llength [info commands replace_cell]] != 1} {error "Missing native replace_cell"}
foreach name $targets {
 set inst [$block findInst $name]
 if {$inst eq "NULL" || [[$inst getMaster] getName] ne [lindex [dict get $choices $name] 0]} {error "Reset target preflight mismatch $name"}
}
set ports_before {}
foreach port [$block getBTerms] {dict set ports_before [$port getName] [$port getNet]}
foreach name $targets {
 lassign [dict get $choices $name] old_master new_master
 set inst [$block findInst $name]
 if {$inst eq "NULL" || [[$inst getMaster] getName] ne $old_master} {error "Unexpected measured driver $name"}
 replace_cell $name $new_master
 if {[[$inst getMaster] getName] ne $new_master} {error "Replacement failed"}
}
if {[llength [$block getInsts]] != [dict size $before]} {error "Instance census changed"}
foreach inst [$block getInsts] {
 set name [$inst getName]
 lassign [dict get $before $name] master pins
 if {$name in $targets} {set master [lindex [dict get $choices $name] 1]}
 if {[[$inst getMaster] getName] ne $master} {error "Unexpected master change"}
 foreach pin [$inst getITerms] {
  if {[$pin getNet] ne [dict get $pins [[$pin getMTerm] getName]]} {error "Incidence changed"}
 }
}
foreach port [$block getBTerms] {if {[$port getNet] ne [dict get $ports_before [$port getName]]} {error "Port incidence changed"}}

set master [[ord::get_db] findMaster sg13g2_dlygate4sd3_1]
if {$master eq "NULL"} {error "Delay master missing"}
set changed {};set added {}
foreach {label pname count endpoint} {
 training pcie_training_i 3 {$auto$ff.cc:337:slice$183526}
 rx_error pcie_rx_error_i 1 {$auto$ff.cc:337:slice$172492}
 rx_data7 {pcie_rx_data_i[7]} 1 {$auto$ff.cc:337:slice$172502}
 rx_valid {pcie_rx_valid_i} 1 {$auto$ff.cc:337:slice$172503}
 rx_sop {pcie_rx_sop_i} 1 {$auto$ff.cc:337:slice$172494}
 rx_eop {pcie_rx_eop_i} 1 {$auto$ff.cc:337:slice$172493}
 rx_dllp {pcie_rx_dllp_i} 1 {$auto$ff.cc:337:slice$172491}
 rx_data0 {pcie_rx_data_i[0]} 1 {$auto$ff.cc:337:slice$172495}
 rx_data1 {pcie_rx_data_i[1]} 1 {$auto$ff.cc:337:slice$172496}
 rx_data2 {pcie_rx_data_i[2]} 1 {$auto$ff.cc:337:slice$172497}
 rx_data3 {pcie_rx_data_i[3]} 1 {$auto$ff.cc:337:slice$172498}
 rx_data4 {pcie_rx_data_i[4]} 1 {$auto$ff.cc:337:slice$172499}
 rx_data5 {pcie_rx_data_i[5]} 1 {$auto$ff.cc:337:slice$172500}
 rx_data6 {pcie_rx_data_i[6]} 1 {$auto$ff.cc:337:slice$172501}
 function_id3 {pcie_function_id_i[3]} 1 {$auto$ff.cc:337:slice$365940}
 function_id7 {pcie_function_id_i[7]} 1 {$auto$ff.cc:337:slice$365944}
 function_id8 {pcie_function_id_i[8]} 1 {$auto$ff.cc:337:slice$365945}
 function_id13 {pcie_function_id_i[13]} 1 {$auto$ff.cc:337:slice$365950}
} {
 set port [$block findBTerm $pname]
 if {$port eq "NULL" || [$port getIoType] ne "INPUT"} {error "Input missing $pname"}
 # Insert only at the measured endpoint D branch; input buffers are preserved.
 set origin [$block findInst $endpoint]
 if {$origin eq "NULL"} {error "Measured endpoint missing"}
 set sink [$origin findITerm D]
 if {$sink eq "NULL" || [$sink getIoType] ne "INPUT"} {error "Measured endpoint D missing"}
 set net [$sink getNet]
 if {$net eq "NULL" || [$net getSigType] ne "SIGNAL"} {error "Endpoint net not signal"}
 set driver_count 0
 foreach pin [$net getITerms] {if {[$pin getIoType] eq "OUTPUT"} {incr driver_count}}
 foreach bp [$net getBTerms] {if {[$bp getIoType] eq "INPUT"} {incr driver_count}}
 if {$driver_count!=1} {error "Endpoint net must have exactly one driver"}
 set original_iterm_count [llength [$net getITerms]]
 puts "NSSOC_ENDPOINT_DELAY $label endpoint=$endpoint net=[$net getName] sinks=$original_iterm_count stages=$count"
 set supply {}
 foreach pin [$origin getITerms] {
  if {[[$pin getMTerm] getSigType] in {POWER GROUND}} {
   if {[$pin getNet] eq "NULL"} {error "Supply disconnected"}
   dict set supply [[$pin getMTerm] getName] [$pin getNet]
  }
 }
 if {[dict size $supply]!=2} {error "Supply census"}
 set previous $net
 for {set i 0} {$i<$count} {incr i} {
  set name nssoc_input_hold_${label}_${i}
  if {[$block findInst $name] ne "NULL" || [$block findNet ${name}_out] ne "NULL"} {error "ECO collision"}
  set cell [odb::dbInst_create $block $master $name];set next [odb::dbNet_create $block ${name}_out]
  lassign [$origin getLocation] x y
  $cell setLocation $x $y;$cell setOrient [$origin getOrient];$cell setPlacementStatus PLACED
  foreach pin [$cell getITerms] {
   set pn [[$pin getMTerm] getName]
   if {[[$pin getMTerm] getSigType] in {POWER GROUND}} {$pin connect [dict get $supply $pn]} elseif {$pn ni {A X}} {error "Unknown delay pin"}
  }
  [$cell findITerm A] connect $previous;[$cell findITerm X] connect $next
  set previous $next;lappend added $name
 }
 $sink connect $previous;dict set changed "$endpoint/D" $previous
 if {[llength [$net getITerms]]!=$original_iterm_count || [llength [$previous getITerms]]!=2} {error "Chain mismatch"}
}
if {[llength $added]!=20 || [dict size $changed]!=18 || [llength [$block getInsts]]!=[dict size $before]+20} {error "ECO census"}
foreach inst [$block getInsts] {
 set name [$inst getName]
 if {$name in $added} {continue}
 lassign [dict get $before $name] old pins
 foreach pin [$inst getITerms] {
  set pn [[$pin getMTerm] getName];set key "$name/$pn";set expected [dict get $pins $pn]
  if {[dict exists $changed $key]} {set expected [dict get $changed $key]}
  if {[$pin getNet] ne $expected} {error "Unrelated incidence changed"}
 }
}
foreach port [$block getBTerms] {if {[$port getNet] ne [dict get $ports_before [$port getName]]} {error "Port net changed"}}
puts "NSSOC_ENDPOINT_DELAY_STRUCTURAL_PASS ports=18 cells=20"

set before_eth_count [llength [$block getInsts]]
# Two positive delay cells on each of nine measured Ethernet output ports.
set delay_master [[ord::get_db] findMaster sg13g2_dlygate4sd3_1]
if {$delay_master eq "NULL"} {error "Missing characterized delay master"}
set snapshot {};set ports_snapshot {}
foreach inst [$block getInsts] {
 foreach pin [$inst getITerms] {dict set snapshot "[$inst getName]/[[$pin getMTerm] getName]" [$pin getNet]}
}
foreach port [$block getBTerms] {dict set ports_snapshot [$port getName] [$port getNet]}
set changed {};set additions {}
foreach bit {0 1 2 3 4 5 6 7 enable} {
 if {$bit eq "enable"} {set port_name eth_tx_en_o} else {set port_name [format {eth_txd_o[%d]} $bit]}
 set port [$block findBTerm $port_name]
 if {$port eq "NULL" || [$port getIoType] ne "OUTPUT"} {error "Expected Ethernet output missing"}
 set net [$port getNet]
 if {[$net getSigType] ne "SIGNAL" || [llength [$net getBTerms]]!=1 || [llength [$net getITerms]]!=1} {error "Output net is not isolated one-driver port"}
 set driver [lindex [$net getITerms] 0]
 if {[$driver getIoType] ne "OUTPUT"} {error "Output driver mismatch"}
 set origin [$driver getInst];set supply {}
 foreach pin [$origin getITerms] {
  if {[[$pin getMTerm] getSigType] in {POWER GROUND}} {
   if {[$pin getNet] eq "NULL"} {error "Driver supply unconnected"}
   dict set supply [[$pin getMTerm] getName] [$pin getNet]
  }
 }
 if {[dict size $supply]!=2} {error "Expected connected source cell power and ground"}
 set n0_name nssoc_eth_hold_${bit}_source;set n1_name nssoc_eth_hold_${bit}_mid
 foreach name [list $n0_name $n1_name] {if {[$block findNet $name] ne "NULL"} {error "ECO net already exists"}}
 set n0 [odb::dbNet_create $block $n0_name];set n1 [odb::dbNet_create $block $n1_name]
 set insts {}
 foreach stage {0 1} {
  set name nssoc_eth_hold_${bit}_${stage}
  if {[$block findInst $name] ne "NULL"} {error "ECO instance already exists"}
  set cell [odb::dbInst_create $block $delay_master $name]
  lassign [$origin getLocation] x y
  $cell setLocation $x $y
  $cell setOrient [$origin getOrient]
  $cell setPlacementStatus PLACED
  foreach pin [$cell getITerms] {
   set pname [[$pin getMTerm] getName]
   if {[[$pin getMTerm] getSigType] in {POWER GROUND}} {
    if {![dict exists $supply $pname]} {error "Delay cell supply signature mismatch"}
    $pin connect [dict get $supply $pname]
   } elseif {$pname ni {A X}} {error "Unexpected delay signal terminal"}
  }
  lappend insts $cell;lappend additions $name
 }
 $driver connect $n0
 dict set changed "[$origin getName]/[[$driver getMTerm] getName]" $n0
 lassign $insts c0 c1
 [$c0 findITerm A] connect $n0;[$c0 findITerm X] connect $n1
 [$c1 findITerm A] connect $n1;[$c1 findITerm X] connect $net
 if {[llength [$n0 getITerms]]!=2 || [llength [$n1 getITerms]]!=2 || [llength [$net getITerms]]!=1} {error "Delay chain incidence mismatch"}
}
if {[llength $additions]!=18 || [dict size $changed]!=9} {error "Unexpected delay ECO census"}
foreach inst [$block getInsts] {
 if {[$inst getName] in $additions} {continue}
 foreach pin [$inst getITerms] {
  set key "[$inst getName]/[[$pin getMTerm] getName]"
  set expected [dict get $snapshot $key]
  if {[dict exists $changed $key]} {set expected [dict get $changed $key]}
  if {[$pin getNet] ne $expected} {error "Unrelated signal or clock incidence changed"}
 }
}
foreach port [$block getBTerms] {if {[$port getNet] ne [dict get $ports_snapshot [$port getName]]} {error "Port net changed"}}
puts "NSSOC_ETH_OUTPUT_DELAY_STRUCTURAL_PASS ports=9 cells=18"


if {[llength [$block getInsts]]!=$before_eth_count+18} {error "Combined ECO cell census mismatch"}

# Only endpoints with measured >1ns worst setup headroom in all three corners.
set internal_before {};set internal_ports {};set internal_new {};set internal_changed {}
foreach inst [$block getInsts] {
 foreach pin [$inst getITerms] {dict set internal_before "[$inst getName]/[[$pin getMTerm] getName]" [$pin getNet]}
}
foreach port [$block getBTerms] {dict set internal_ports [$port getName] [$port getNet]}
set internal_count [llength [$block getInsts]]
foreach {label instance terminal} {
 {internal_238} {u_eth.u_mac.rx_fifo.fifo_inst.u_sram.g_bank[7].u_mem} {A_ADDR[3]}
 {internal_239} {u_eth.u_mac.rx_fifo.fifo_inst.u_sram.g_bank[7].u_mem} {A_ADDR[5]}
 {internal_240} {u_eth.u_mac.tx_fifo.fifo_inst.u_sram.g_bank[2].u_mem} {A_MEN}
 {internal_241} {u_eth.u_mac.tx_fifo.fifo_inst.u_sram.g_bank[3].u_mem} {A_MEN}
 {internal_242} {u_eth.u_mac.tx_fifo.fifo_inst.u_sram.g_bank[4].u_mem} {A_MEN}
} {
 set origin [$block findInst $instance]
 if {$origin eq "NULL"} {error "Internal endpoint missing"}
 set sink [$origin findITerm $terminal]
 if {$sink eq "NULL" || [$sink getIoType] ne "INPUT"} {error "Internal endpoint is not input"}
 set net [$sink getNet]
 if {$net eq "NULL" || [$net getSigType] ne "SIGNAL"} {error "Internal endpoint is not signal"}
 set drivers 0
 foreach pin [$net getITerms] {if {[$pin getIoType] eq "OUTPUT"} {incr drivers}}
 foreach pin [$net getBTerms] {if {[$pin getIoType] eq "INPUT"} {incr drivers}}
 if {$drivers!=1} {error "Internal net driver census"}
 set count [llength [$net getITerms]]
 set supply {}
 foreach pin [$origin getITerms] {
  set kind [[$pin getMTerm] getSigType]
  if {$kind in {POWER GROUND}} {
   set rail [$pin getNet]
   if {$rail eq "NULL"} {error "Internal endpoint supply disconnected"}
   if {[dict exists $supply $kind] && [dict get $supply $kind] ne $rail} {error "Ambiguous supply domain"}
   dict set supply $kind $rail
  }
 }
 if {[dict size $supply]!=2} {error "Internal endpoint supply census"}
 set name nssoc_safe_hold_$label
 if {[$block findInst $name] ne "NULL" || [$block findNet ${name}_out] ne "NULL"} {error "Internal ECO collision"}
 set cell [odb::dbInst_create $block $delay_master $name];set next [odb::dbNet_create $block ${name}_out]
 lassign [$origin getLocation] x y
 $cell setLocation $x $y;$cell setPlacementStatus PLACED
 foreach pin [$cell getITerms] {
  set kind [[$pin getMTerm] getSigType];set pn [[$pin getMTerm] getName]
  if {$kind in {POWER GROUND}} {$pin connect [dict get $supply $kind]} elseif {$pn ni {A X}} {error "Unknown internal delay terminal"}
 }
 [$cell findITerm A] connect $net;[$cell findITerm X] connect $next;$sink connect $next
 dict set internal_changed "$instance/$terminal" $next;lappend internal_new $name
 if {[llength [$net getITerms]]!=$count || [llength [$next getITerms]]!=2} {error "Internal delay chain incidence"}
}
if {[llength $internal_new]!=5 || [dict size $internal_changed]!=5 || [llength [$block getInsts]]!=$internal_count+5} {error "Internal ECO census"}
foreach inst [$block getInsts] {
 if {[$inst getName] in $internal_new} {continue}
 foreach pin [$inst getITerms] {
  set key "[$inst getName]/[[$pin getMTerm] getName]";set expected [dict get $internal_before $key]
  if {[dict exists $internal_changed $key]} {set expected [dict get $internal_changed $key]}
  if {[$pin getNet] ne $expected} {error "Unrelated internal incidence changed"}
 }
}
foreach port [$block getBTerms] {if {[$port getNet] ne [dict get $internal_ports [$port getName]]} {error "Internal ECO changed port"}}
puts "NSSOC_SAFE_INTERNAL_HOLD_STRUCTURAL_PASS cells=5 endpoints=5"

detailed_placement
check_placement -verbose
puts "NSSOC_SHARED_PCIE_DRIVERS_SAME_INCIDENCE"
"""
class ResetBufferECO(ElectricalPostCTS):
    id = "NSSOC.ResetBufferECO"
    name = "Size measured credit CRC staging to commit drivers"
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
TARGETED = r"""
foreach {label instance} {
 training {$auto$ff.cc:337:slice$183526}
 rx_error {$auto$ff.cc:337:slice$172492}
 rx_data7 {$auto$ff.cc:337:slice$172502}
 rx_valid {$auto$ff.cc:337:slice$172503}
 rx_sop {$auto$ff.cc:337:slice$172494}
 rx_eop {$auto$ff.cc:337:slice$172493}
 rx_dllp {$auto$ff.cc:337:slice$172491}
 rx_data0 {$auto$ff.cc:337:slice$172495}
 rx_data1 {$auto$ff.cc:337:slice$172496}
 rx_data2 {$auto$ff.cc:337:slice$172497}
 rx_data3 {$auto$ff.cc:337:slice$172498}
 rx_data4 {$auto$ff.cc:337:slice$172499}
 rx_data5 {$auto$ff.cc:337:slice$172500}
 rx_data6 {$auto$ff.cc:337:slice$172501}
 function_id3 {$auto$ff.cc:337:slice$365940}
 function_id7 {$auto$ff.cc:337:slice$365944}
 function_id8 {$auto$ff.cc:337:slice$365945}
 function_id13 {$auto$ff.cc:337:slice$365950}
} {
 set endpoint [get_pins "$instance/D"]
 if {[llength $endpoint]!=1} {error "Missing exact mapped data pin $instance"}
 foreach mode {max min} {
  puts "%OL_CREATE_REPORT targeted_${label}_${mode}.rpt"
  report_checks -to $endpoint -path_delay $mode -format full_clock_expanded -digits 6 -group_path_count 10 -endpoint_path_count 2
  puts "%OL_END_REPORT"
 }
}
foreach bit {0 1 2 3 4 5 6 7} {
 set port [get_ports [format {eth_txd_o[%d]} $bit]]
 if {[llength $port]!=1} {error "Ethernet report endpoint missing"}
 foreach mode {max min} {
  puts "%OL_CREATE_REPORT targeted_eth${bit}_${mode}.rpt"
  report_checks -to $port -path_delay $mode -format full_clock_expanded -digits 6 -group_path_count 10 -endpoint_path_count 2
  puts "%OL_END_REPORT"
 }
}

set port [get_ports eth_tx_en_o]
if {[llength $port]!=1} {error "Ethernet enable endpoint missing"}
foreach mode {max min} {
 puts "%OL_CREATE_REPORT targeted_eth_enable_${mode}.rpt"
 report_checks -to $port -path_delay $mode -format full_clock_expanded -digits 6 -group_path_count 10 -endpoint_path_count 2
 puts "%OL_END_REPORT"
}

"""
class TargetedSTA(BranchSTA):
    def get_script_path(self):
        original=Path(super().get_script_path())
        text=original.read_text()
        import re
        if re.search(r'^\s*exit(?:\s|$)',text,re.M):raise RuntimeError('Native STA exits before targeted report insertion')
        output=Path(self.step_dir)/'targeted_native.tcl'
        output.write_text(text+'\n'+TARGETED+'\n'+(Path(__file__).resolve().parents[3]/'credit-crc-driver-trial/internal-targets.tcl').read_text())
        return str(output)
@Flow.factory.register()
class AckChipResetSized(Interfaces):
 Steps=[ResetBufferECO]+[type("Sized"+n,(TargetedSTA,),dict(id="NSSOC.Sized"+n,corner=c))for n,c in CORNERS]
if __name__=="__main__":
 from librelane.__main__ import cli
 cli()
