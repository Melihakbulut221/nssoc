# SPDX-License-Identifier: Apache-2.0
"""Exact five-buffer setup experiment; no timing exceptions."""
from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces
from corrpre_postcts_flow import ElectricalPostCTS, measurements

ECO = r"""
set block [ord::get_db_block]
set before {}
foreach inst [$block getInsts] {
 set pins {}
 foreach pin [$inst getITerms] {dict set pins [[$pin getMTerm] getName] [$pin getNet]}
 dict set before [$inst getName] [list [[$inst getMaster] getName] $pins]
}
set targets {fanout9423 fanout9422 fanout9421 fanout9411 fanout9409}
if {[llength [info commands replace_cell]] != 1} {error "Missing native replace_cell"}
foreach name $targets {
 set inst [$block findInst $name]
 if {$inst eq "NULL" || [[$inst getMaster] getName] ne "sg13g2_buf_1"} {error "Unexpected measured driver $name"}
 replace_cell $name sg13g2_buf_4
 if {[[$inst getMaster] getName] ne "sg13g2_buf_4"} {error "Replacement failed"}
}
if {[llength [$block getInsts]] != [dict size $before]} {error "Instance census changed"}
foreach inst [$block getInsts] {
 set name [$inst getName]
 lassign [dict get $before $name] master pins
 if {$name in $targets} {set master sg13g2_buf_4}
 if {[[$inst getMaster] getName] ne $master} {error "Unexpected master change"}
 foreach pin [$inst getITerms] {
  if {[$pin getNet] ne [dict get $pins [[$pin getMTerm] getName]]} {error "Incidence changed"}
 }
}
puts "NSSOC_FIVE_MEASURED_BUFFERS_UPSIZED_SAME_INCIDENCE"
"""
class FiveBufferECO(ElectricalPostCTS):
    id = "NSSOC.FiveBufferECO"
    name = "Size five measured reset-tree buffers"
    def get_script_path(self):
        p = Path(super().get_script_path())
        s = p.read_text()
        a = s.index("# Buffer I/O")
        b = s.index("report_floating_nets -verbose", a)
        s = s[:a] + ECO + "\n" + s[b:]
        if "log_cmd repair_design" in s or "unset_propagated_clock [all_clocks]" in s:
            raise RuntimeError("Unexpected broad repair or ideal clock")
        q = Path(self.step_dir) / "five_buffer_eco.tcl"
        q.write_text(s)
        return str(q)
@Flow.factory.register()
class FiveBufferTrial(Interfaces):
    Steps = [FiveBufferECO] + measurements("FiveBufferAfter")
if __name__ == "__main__":
    from librelane.__main__ import cli
    cli()
