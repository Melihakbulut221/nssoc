from pathlib import Path
import json
from librelane.flows import Flow
from interface_flow import Interfaces
from corrpre_postcts_flow import ElectricalPostCTS,CORNERS
from ack_chip_branches_flow import BranchSTA
ECO = '\nset block [ord::get_db_block]\nset before {}\nset original_placement {}\nforeach inst [$block getInsts] {\n set pins {}\n foreach pin [$inst getITerms] {dict set pins [[$pin getMTerm] getName] [$pin getNet]}\n dict set before [$inst getName] [list [[$inst getMaster] getName] $pins]\n dict set original_placement [$inst getName] [list [$inst getLocation] [$inst getOrient] [$inst getPlacementStatus]]\n if {[$inst getPlacementStatus] eq "PLACED"} {$inst setPlacementStatus FIRM}\n}\nset oldnets [llength [$block getNets]]\nset original_ports {}\nforeach port [$block getBTerms] {dict set original_ports [$port getName] [$port getNet]}\nset changes {}\nset index 0\nforeach {name expected_master delay_master delay_count expected_port} {TARGET_PAIRS} {\n set slash [string last / $name]\n set ti [$block findInst [string range $name 0 [expr {$slash-1}]]]\n if {$ti eq "NULL" || [[$ti getMaster] getName] ne $expected_master} {error "Measured target master mismatch"}\n set sink [$ti findITerm [string range $name [expr {$slash+1}] end]]\n if {$sink eq "NULL" || [$sink getIoType] ne "INPUT"} {error "Target input mismatch"}\n set net [$sink getNet]\n if {$net eq "NULL"} {error "Disconnected target"}\n set drivers {}\n foreach pin [$net getITerms] {if {[$pin getIoType] eq "OUTPUT"} {lappend drivers $pin}}\n set ports [$net getBTerms]\n if {[llength $ports]} {\n  if {[llength $ports]!=1 || [llength $drivers]!=0} {error "Ambiguous boundary driver"}\n  set port [lindex $ports 0]\n  if {[$port getIoType] ne "INPUT" || [$port getName] ne $expected_port} {error "Measured input port identity mismatch"}\n } elseif {[llength $drivers]!=1} {error "Nonunique original driver"}\n set master [[ord::get_db] findMaster $delay_master]\n if {$master eq "NULL" || $delay_count<1 || $delay_count>2} {error "Invalid measured native delay chain"}\n set current $net\n for {set stage 0} {$stage<$delay_count} {incr stage} {\n  set stem [format "nssoc_ack_hold_%03d_%d" $index $stage]\n  set netname [format "%s_out" $stem]\n  if {[$block findInst $stem] ne "NULL" || [$block findNet $netname] ne "NULL"} {error "ECO collision"}\n  set inst [odb::dbInst_create $block $master $stem]\n  set next [odb::dbNet_create $block $netname]\n  [$inst findITerm A] connect $current\n  [$inst findITerm X] connect $next\n  set current $next\n  $inst setOrient [$ti getOrient]\n  $inst setLocation {*}[$ti getLocation]\n  $inst setPlacementStatus PLACED\n }\n $sink disconnect\n $sink connect $current\n dict set changes $sink $current\n puts "NSSOC_POST174_IDENTITY $index $name $expected_master $delay_master $delay_count"\n incr index\n}\nif {$index!=254 || [llength [$block getInsts]]!=[dict size $before]+267 || [llength [$block getNets]]!=$oldnets+267 || [dict size $changes]!=254} {error "Wrong repair census"}\nforeach inst [$block getInsts] {\n set name [$inst getName]\n if {![dict exists $before $name]} {continue}\n lassign [dict get $before $name] master pins\n if {[[$inst getMaster] getName] ne $master} {error "Original master changed"}\n foreach pin [$inst getITerms] {\n  set expected [dict get $pins [[$pin getMTerm] getName]]\n  if {[dict exists $changes $pin]} {set expected [dict get $changes $pin]}\n  if {[$pin getNet] ne $expected} {error "Unexpected incidence change"}\n }\n}\nputs "NSSOC_ACK_267_CELLS_IDENTITY_VERIFIED"\n\nif {[llength [$block getBTerms]]!=[dict size $original_ports]} {error "Port census changed"}\nforeach port [$block getBTerms] {if {[$port getNet] ne [dict get $original_ports [$port getName]]} {error "External port connectivity changed"}}\n'
RESTORE='\nforeach inst [$block getInsts] {\n set name [$inst getName]\n if {![dict exists $original_placement $name]} {continue}\n lassign [dict get $original_placement $name] location orientation status\n if {[$inst getLocation] ne $location || [$inst getOrient] ne $orientation} {error "Original placement moved"}\n $inst setPlacementStatus $status\n}\nputs "NSSOC_ORIGINAL_PLACEMENT_UNCHANGED_AND_STATUSES_RESTORED"\n'
class AckHoldECO(ElectricalPostCTS):
 id='NSSOC.AckHoldECO'
 name='Insert267 noninverting delays on254 measured hold branches'
 def get_script_path(self):
  s=Path(super().get_script_path()).read_text()
  rows=json.loads((Path(__file__).resolve().parents[3]/'ack-chip-branches/hold-selected.json').read_text())
  assert len(rows)==254 and sum(r['delay_count']for r in rows)==267
  pairs=[]
  for r in rows:
   assert r['worst_setup_slack_ns']>=r['delay_count'] and r['delay_master']=='sg13g2_dlygate4sd3_1'
   name=r['sink'].replace(chr(92)*2,chr(92))
   assert not any(c in name+r['master']for c in '{}\n\r')
   pairs.extend(['{'+name+'}','{'+r['master']+'}','{'+r['delay_master']+'}',str(r['delay_count']),'{'+r['expected_port']+'}'])
  start=s.index('# Buffer I/O');end=s.index('report_floating_nets -verbose',start)
  s=s[:start]+ECO.replace('TARGET_PAIRS',' '.join(pairs))+'\n'+s[end:]
  assert 'log_cmd repair_design' not in s and 'unset_propagated_clock [all_clocks]'not in s
  assert s.count('write_views')==1
  s=s.replace('write_views',RESTORE+'\nwrite_views')
  p=Path(self.step_dir)/'ack_hold_eco.tcl';p.write_text(s);return str(p)
@Flow.factory.register()
class AckChipHoldRepair(Interfaces):
 Steps=[AckHoldECO]+[type('Hold'+n,(BranchSTA,),dict(id='NSSOC.Hold'+n,corner=c))for n,c in CORNERS]
if __name__=='__main__':
 from librelane.__main__ import cli
 cli()
