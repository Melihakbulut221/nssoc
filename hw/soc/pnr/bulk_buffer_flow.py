# SPDX-License-Identifier: Apache-2.0
"""Measured 102-buffer setup experiment; no timing exceptions."""
from pathlib import Path
import json
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
set old_nets [llength [$block getNets]]
set replacements {REPLACEMENT_ROWS}
set targets {}
foreach row $replacements {
 lassign $row name old new
 set inst [$block findInst $name]
 if {$inst eq "NULL" || [[$inst getMaster] getName] ne $old} {error "Measured driver mismatch: $name"}
 replace_cell $name $new
 if {[[$inst getMaster] getName] ne $new} {error "Replacement failed"}
 dict set targets $name $new
}
if {[dict size $targets]!=102 || [llength [$block getInsts]]!=[dict size $before] || [llength [$block getNets]]!=$old_nets} {error "Unexpected ECO census"}
foreach inst [$block getInsts] {
 set name [$inst getName]
 lassign [dict get $before $name] master pins
 if {[dict exists $targets $name]} {set master [dict get $targets $name]}
 if {[[$inst getMaster] getName] ne $master} {error "Unexpected master change"}
 foreach pin [$inst getITerms] {
  if {[$pin getNet] ne [dict get $pins [[$pin getMTerm] getName]]} {error "Incidence changed"}
 }
}
puts "NSSOC_102_MEASURED_BUFFER_SIZES_SAME_INCIDENCE"
"""
class BulkBufferECO(ElectricalPostCTS):
    id = "NSSOC.BulkBufferECO"
    name = "Size 102 measured overloaded setup buffers"
    def get_script_path(self):
        p = Path(super().get_script_path())
        s = p.read_text()
        a = s.index("# Buffer I/O")
        b = s.index("report_floating_nets -verbose", a)
        rows=json.loads((Path(__file__).resolve().parents[3]/"bulk-buffer-trial/targets.json").read_text())
        assert len(rows)==102
        replacements=[]
        for row in rows:
            name=row["name"]
            if any(c in name for c in "{}\n\r"):raise RuntimeError("Invalid instance name")
            old=row["cell"];new="sg13g2_buf_"+{"sg13g2_buf_1":"4","sg13g2_buf_2":"8","sg13g2_buf_4":"16"}[old]
            replacements.append("{"+name+" "+old+" "+new+"}")
        s = s[:a] + ECO.replace("REPLACEMENT_ROWS","\n".join(replacements)) + "\n" + s[b:]
        if "log_cmd repair_design" in s or "unset_propagated_clock [all_clocks]" in s:
            raise RuntimeError("Unexpected broad repair or ideal clock")
        q = Path(self.step_dir) / "bulk_buffer_eco.tcl"
        q.write_text(s)
        return str(q)
@Flow.factory.register()
class BulkBufferTrial(Interfaces):
    Steps = [BulkBufferECO] + measurements("BulkBufferAfter")
if __name__ == "__main__":
    from librelane.__main__ import cli
    cli()
