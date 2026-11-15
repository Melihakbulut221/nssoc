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
 {$abc$734931$auto$blifparse.cc:397:parse_blif$749437} {sg13g2_mux2_1 sg13g2_mux2_2}
 {$abc$734931$auto$blifparse.cc:397:parse_blif$760815} {sg13g2_mux2_1 sg13g2_mux2_2}
 {$abc$734931$auto$blifparse.cc:397:parse_blif$766482} {sg13g2_a21o_1 sg13g2_a21o_2}
 {$abc$734931$auto$blifparse.cc:397:parse_blif$760931} {sg13g2_nor2_1 sg13g2_nor2_2}
 {$abc$734931$auto$blifparse.cc:397:parse_blif$760974} {sg13g2_nor2_1 sg13g2_nor2_2}
 {$abc$734931$auto$blifparse.cc:397:parse_blif$763373} {sg13g2_nand2b_1 sg13g2_nand2b_2}
}
set targets [dict keys $choices]
if {[llength $targets]!=6} {error "Wrong measured resize census"}
if {[llength [info commands replace_cell]] != 1} {error "Missing native replace_cell"}
foreach name $targets {
 set inst [$block findInst $name]
 if {$inst eq "NULL" || [[$inst getMaster] getName] ne [lindex [dict get $choices $name] 0]} {error "Reset target preflight mismatch $name"}
}
set sink_specs {
 {{$abc$734931$auto$blifparse.cc:397:parse_blif$749437} {X} {{{u_eth.u_mac.rx_fifo.fifo_inst.u_sram.g_bank[2].u_mem} {B_DIN[11]}} {{u_eth.u_mac.rx_fifo.fifo_inst.u_sram.g_bank[3].u_mem} {B_DIN[11]}} {{load_slew5678} {A}} {{wire5676} {A}}}}
 {{$abc$734931$auto$blifparse.cc:397:parse_blif$760815} {X} {{{u_eth.u_mac.tx_fifo.fifo_inst.u_sram.g_bank[2].u_mem} {B_DIN[11]}} {{u_eth.u_mac.tx_fifo.fifo_inst.u_sram.g_bank[3].u_mem} {B_DIN[11]}} {{load_slew4866} {A}} {{wire4864} {A}}}}
 {{$abc$734931$auto$blifparse.cc:397:parse_blif$766482} {X} {{{u_eth.u_mac.rx_fifo.fifo_inst.u_sram.g_bank[2].u_mem} {A_MEN}}}}
 {{$abc$734931$auto$blifparse.cc:397:parse_blif$760931} {Y} {{{u_eth.u_mac.tx_fifo.fifo_inst.u_sram.g_bank[2].u_mem} {B_MEN}}}}
 {{$abc$734931$auto$blifparse.cc:397:parse_blif$760974} {Y} {{{u_eth.u_mac.tx_fifo.fifo_inst.u_sram.g_bank[4].u_mem} {B_MEN}}}}
 {{$abc$734931$auto$blifparse.cc:397:parse_blif$763373} {Y} {{{u_eth.u_mac.rx_fifo.fifo_inst.u_sram.g_bank[6].u_mem} {A_WEN}} {{$abc$734931$auto$blifparse.cc:397:parse_blif$763374} {A}}}}
}
foreach spec $sink_specs {
 lassign $spec driver_name driver_pin expected_sinks
 set driver_inst [$block findInst $driver_name]
 set term [$driver_inst findITerm $driver_pin]
 if {$term eq "NULL" || [$term getIoType] ne "OUTPUT"} {error "Missing driver output"}
 set net [$term getNet]
 if {$net eq "NULL" || [llength [$net getBTerms]]!=0 || [llength [$net getITerms]]!=1+[llength $expected_sinks]} {error "Measured net census changed"}
 set actual {}
 foreach pin [$net getITerms] {
  if {$pin eq $term} {continue}
  if {[$pin getIoType] ne "INPUT"} {error "Unexpected output on measured net"}
  lappend actual [list [string map [list "\\" ""] [[$pin getInst] getName]] [string map [list "\\" ""] [[$pin getMTerm] getName]]]
 }
 if {[lsort $actual] ne [lsort $expected_sinks]} {error "Measured complete sink set changed"}
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
puts "NSSOC_SRAM_REMAINING_DRIVERS_UPSIZED_EXACT_SINKS"
"""
class ResetBufferECO(ElectricalPostCTS):
    id = "NSSOC.ResetBufferECO"
    name = "Size six remaining SRAM drivers"
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
