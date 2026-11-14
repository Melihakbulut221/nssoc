from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces
from corrpre_postcts_flow import SingleCornerSTA,CORNERS,ElectricalPostCTS
EXTRA = r"""
set index 0
foreach name {eth_txd_o[0] eth_txd_o[1] eth_txd_o[2] eth_txd_o[3] eth_txd_o[4] eth_txd_o[5] eth_txd_o[6] eth_txd_o[7] eth_tx_en_o eth_tx_er_o} {
 set port [get_ports [list $name]]
 if {[llength $port] != 1} {error "Missing exact Ethernet output $name"}
 foreach type {max min} {
  puts "%OL_CREATE_REPORT io-$index-$type.rpt"
  report_checks -to $port -corner $corner_name -path_delay $type -group_path_count 10000 -fields {slew cap input net fanout} -format full_clock_expanded -digits 9
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
set index 0
foreach portname {eth_txd_o[0] eth_txd_o[1] eth_txd_o[2] eth_txd_o[3] eth_txd_o[4] eth_txd_o[5] eth_txd_o[6] eth_txd_o[7] eth_tx_en_o eth_tx_er_o} {
 set port [$block findBTerm $portname]
 if {$port eq "NULL" || [$port getIoType] ne "OUTPUT"} {error "Missing output $portname"}
 set net [$port getNet]
 if {[llength [$net getITerms]] != 1 || [llength [$net getBTerms]] != 1} {error "Unexpected output fanout $portname"}
 set driver [lindex [$net getITerms] 0]
 if {[[$driver getMTerm] getIoType] ne "OUTPUT"} {error "Expected single output driver"}
 set location [[$driver getInst] getLocation]
 set orientation [[$driver getInst] getOrient]
 set stem nssoc_eth_hold_${index}
 foreach name [list ${stem}_0 ${stem}_1] {
  if {[$block findInst $name] ne "NULL" || [$block findNet ${name}_in] ne "NULL"} {error "ECO name collision"}
 }
 set first [odb::dbNet_create $block ${stem}_0_in]
 set middle [odb::dbNet_create $block ${stem}_1_in]
 $driver disconnect
 $driver connect $first
 dict set changed $driver $first
 foreach suffix {0 1} {
  set inst [odb::dbInst_create $block $master ${stem}_${suffix}]
  if {$suffix==0} {set in $first;set out $middle} else {set in $middle;set out $net}
  [$inst findITerm A] connect $in
  [$inst findITerm X] connect $out
  $inst setOrient $orientation
  $inst setLocation {*}$location
  $inst setPlacementStatus PLACED
 }
 if {[$port getNet] ne $net} {error "Original port net changed"}
 incr index
}
if {$index!=10 || [llength [$block getInsts]]!=$old_count+20 || [llength [$block getNets]]!=$old_nets+20} {error "Wrong ECO census"}
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
puts "NSSOC_TWENTY_NATIVE_DELAY_CELLS_TEN_ETH_OUTPUTS_ONLY"
"""
class TrainingHoldECO(ElectricalPostCTS):
 id='NSSOC.TrainingHoldECO'
 name='Two native delay cells on each Ethernet data or control output'
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
