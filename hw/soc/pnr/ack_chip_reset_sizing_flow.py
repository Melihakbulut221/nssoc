from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces
from corrpre_postcts_flow import ElectricalPostCTS,CORNERS
from ack_chip_branches_flow import BranchSTA
ECO = r"""
set block [ord::get_db_block]
set before {}
foreach inst [$block getInsts] {
 set pins {}
 foreach pin [$inst getITerms] {dict set pins [[$pin getMTerm] getName] [$pin getNet]}
 dict set before [$inst getName] [list [[$inst getMaster] getName] $pins]
}
set choices {
 {$abc$734931$auto$blifparse.cc:397:parse_blif$763417} {sg13g2_nor2_1 sg13g2_nor2_2}
 {$abc$734931$auto$blifparse.cc:397:parse_blif$760981} {sg13g2_nor2_1 sg13g2_nor2_2}
 {$abc$734931$auto$blifparse.cc:397:parse_blif$763372} {sg13g2_a21o_1 sg13g2_a21o_2}
 {$abc$734931$auto$blifparse.cc:397:parse_blif$766536} {sg13g2_nor2_1 sg13g2_nor2_2}
 {$abc$734931$auto$blifparse.cc:397:parse_blif$763419} {sg13g2_nor2b_1 sg13g2_nor2b_2}
}
set targets [dict keys $choices]
if {[llength $targets]!=5} {error "Wrong measured resize census"}
if {[llength [info commands replace_cell]] != 1} {error "Missing native replace_cell"}
foreach name $targets {
 set inst [$block findInst $name]
 if {$inst eq "NULL" || [[$inst getMaster] getName] ne [lindex [dict get $choices $name] 0]} {error "Reset target preflight mismatch $name"}
}
set sink_specs {
 {{$abc$734931$auto$blifparse.cc:397:parse_blif$763417} {Y} {u_ram.g_ram_2048x64_ecc.u_b0} {A_MEN}}
 {{$abc$734931$auto$blifparse.cc:397:parse_blif$760981} {Y} {u_eth.u_mac.tx_fifo.fifo_inst.u_sram.g_bank[5].u_mem} {B_MEN}}
 {{$abc$734931$auto$blifparse.cc:397:parse_blif$763372} {X} {u_eth.u_mac.rx_fifo.fifo_inst.u_sram.g_bank[6].u_mem} {A_MEN}}
 {{$abc$734931$auto$blifparse.cc:397:parse_blif$766536} {Y} {u_eth.u_mac.rx_fifo.fifo_inst.u_sram.g_bank[2].u_mem} {B_MEN}}
 {{$abc$734931$auto$blifparse.cc:397:parse_blif$763419} {Y} {u_ram.g_ram_2048x64_ecc.u_b1} {A_MEN}}
}
foreach spec $sink_specs {
 lassign $spec driver_name driver_pin expected_instance expected_pin
 set driver_inst [$block findInst $driver_name]
 set driver_term [$driver_inst findITerm $driver_pin]
 if {$driver_term eq "NULL"} {error "Missing measured output"}
 set net [$driver_term getNet]
 if {$net eq "NULL" || [llength [$net getITerms]]!=2 || [llength [$net getBTerms]]!=0} {error "Control net census changed"}
 set found 0
 foreach term [$net getITerms] {
  if {$term eq $driver_term} {continue}
  set name [string map [list "\\" ""] [[$term getInst] getName]]
  set pin [string map [list "\\" ""] [[$term getMTerm] getName]]
  if {$name ne $expected_instance || $pin ne $expected_pin || [$term getIoType] ne "INPUT"} {error "Wrong SRAM control sink"}
  incr found
 }
 if {$found!=1} {error "SRAM sink not unique"}
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
detailed_placement
check_placement -verbose
puts "NSSOC_SRAM_CONTROL_DRIVERS_UPSIZED_SAME_INCIDENCE"
"""
class ResetBufferECO(ElectricalPostCTS):
    id = "NSSOC.ResetBufferECO"
    name = "Size five measured SRAM control drivers"
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
