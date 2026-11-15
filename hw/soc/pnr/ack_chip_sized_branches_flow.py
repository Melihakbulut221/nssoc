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
 fanout3516 {sg13g2_buf_4 sg13g2_buf_8}
 fanout3514 {sg13g2_buf_4 sg13g2_buf_8}
 fanout3513 {sg13g2_buf_4 sg13g2_buf_8}
 fanout2832 {sg13g2_buf_1 sg13g2_buf_4}
 {$abc$735174$auto$blifparse.cc:397:parse_blif$760989} {sg13g2_buf_1 sg13g2_buf_4}
 {$abc$735174$auto$blifparse.cc:397:parse_blif$760990} {sg13g2_buf_1 sg13g2_buf_4}
 fanout2411 {sg13g2_buf_1 sg13g2_buf_4}
}
set targets [dict keys $choices]
if {[llength $targets]!=7} {error "Wrong measured resize census"}
if {[llength [info commands replace_cell]] != 1} {error "Missing native replace_cell"}
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
puts "NSSOC_SEVEN_ACTUAL_ACK_CHIP_BUFFERS_UPSIZED_SAME_INCIDENCE"
"""
class SevenBufferECO(ElectricalPostCTS):
    id = "NSSOC.SevenBufferECO"
    name = "Size seven measured RX control-tree buffers"
    def get_script_path(self):
        p = Path(super().get_script_path())
        s = p.read_text()
        a = s.index("# Buffer I/O")
        b = s.index("report_floating_nets -verbose", a)
        s = s[:a] + ECO + "\n" + s[b:]
        if "log_cmd repair_design" in s or "unset_propagated_clock [all_clocks]" in s:
            raise RuntimeError("Unexpected broad repair or ideal clock")
        q = Path(self.step_dir) / "seven_buffer_eco.tcl"
        q.write_text(s)
        return str(q)
@Flow.factory.register()
class AckChipSizedBranches(Interfaces):
 Steps=[SevenBufferECO]+[type("Sized"+n,(BranchSTA,),dict(id="NSSOC.Sized"+n,corner=c))for n,c in CORNERS]
if __name__=="__main__":
 from librelane.__main__ import cli
 cli()
