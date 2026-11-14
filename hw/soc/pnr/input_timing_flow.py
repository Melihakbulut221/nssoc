from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces
from corrpre_postcts_flow import SingleCornerSTA,CORNERS,ElectricalPostCTS
EXTRA = r"""
set training [get_ports pcie_training_i]
if {[llength $training] != 1} {error "Missing exact training input"}
foreach type {max min} {
 puts "%OL_CREATE_REPORT training-$type.rpt"
 report_checks -from $training -corner $corner_name -path_delay $type -group_path_count 10000 -fields {slew cap input net fanout} -format full_clock_expanded -digits 9
 puts "%OL_END_REPORT"
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
set port [$block findBTerm pcie_training_i]
if {$port eq "NULL"} {error "Missing training port"}
set net [$port getNet]
set sink [[$block findInst hold23727] findITerm A]
if {$sink eq "NULL" || [$sink getNet] ne $net || [llength [$net getITerms]] != 1 || [llength [$net getBTerms]] != 1} {error "Source training connection changed"}
set before {}
foreach inst [$block getInsts] {
 set pins {}
 foreach pin [$inst getITerms] {dict set pins [[$pin getMTerm] getName] [$pin getNet]}
 dict set before [$inst getName] [list [[$inst getMaster] getName] $pins]
}
set old_count [llength [$block getInsts]]
set old_nets [llength [$block getNets]]
set location [[$sink getInst] getLocation]
set orientation [[$sink getInst] getOrient]
$sink disconnect
set last $net
foreach index {0 1} {
 set name nssoc_training_hold_$index
 if {[$block findInst $name] ne "NULL" || [$block findNet ${name}_out] ne "NULL"} {error "ECO name collision"}
 set inst [odb::dbInst_create $block $master $name]
 set next [odb::dbNet_create $block ${name}_out]
 [$inst findITerm A] connect $last
 [$inst findITerm X] connect $next
 $inst setOrient $orientation
 $inst setLocation {*}$location
 $inst setPlacementStatus PLACED
 set last $next
}
$sink connect $last
if {[llength [$block getInsts]] != $old_count+2 || [llength [$block getNets]] != $old_nets+2} {error "Unexpected ECO census"}
foreach inst [$block getInsts] {
 set name [$inst getName]
 if {![dict exists $before $name]} {continue}
 lassign [dict get $before $name] cell pins
 if {[[$inst getMaster] getName] ne $cell} {error "Original master changed"}
 foreach pin [$inst getITerms] {
  set terminal [[$pin getMTerm] getName]
  set expected [dict get $pins $terminal]
  if {$pin eq $sink} {set expected $last}
  if {[$pin getNet] ne $expected} {error "Original incidence changed: $name/$terminal"}
 }
}
puts "NSSOC_TWO_NATIVE_DELAY_CELLS_ONLY_ORIGINAL_INCIDENCE_PRESERVED"
"""
class TrainingHoldECO(ElectricalPostCTS):
 id='NSSOC.TrainingHoldECO'
 name='Two native training input hold delay cells'
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
