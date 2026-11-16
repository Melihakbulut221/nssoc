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
if {[llength $added]!=5 || [dict size $changed]!=3 || [llength [$block getInsts]]!=[dict size $before]+5} {error "ECO census"}
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
puts "NSSOC_ENDPOINT_DELAY_STRUCTURAL_PASS ports=3 cells=5"

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
} {
 set endpoint [get_pins "$instance/D"]
 if {[llength $endpoint]!=1} {error "Missing exact mapped data pin $instance"}
 foreach mode {max min} {
  puts "%OL_CREATE_REPORT targeted_${label}_${mode}.rpt"
  report_checks -to $endpoint -path_delay $mode -format full_clock_expanded -digits 6 -group_path_count 10 -endpoint_path_count 2
  puts "%OL_END_REPORT"
 }
}
"""
class TargetedSTA(BranchSTA):
    def get_script_path(self):
        original=Path(super().get_script_path())
        text=original.read_text()
        import re
        if re.search(r'^\s*exit(?:\s|$)',text,re.M):raise RuntimeError('Native STA exits before targeted report insertion')
        output=Path(self.step_dir)/'targeted_native.tcl'
        output.write_text(text+'\n'+TARGETED)
        return str(output)
@Flow.factory.register()
class AckChipResetSized(Interfaces):
 Steps=[ResetBufferECO]+[type("Sized"+n,(TargetedSTA,),dict(id="NSSOC.Sized"+n,corner=c))for n,c in CORNERS]
if __name__=="__main__":
 from librelane.__main__ import cli
 cli()
