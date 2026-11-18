# SPDX-License-Identifier: Apache-2.0
"""Read native CTS8 connectivity before a targeted clock ECO; no DB edits."""
from pathlib import Path
from core_only_postcts_flow import CoreCornerSTA
from interface_flow import Interfaces
from librelane.flows import Flow

PROBE = r"""
set block [ord::get_db_block]
proc core_probe_net {label net} {
    if {$net eq "NULL" || $net eq ""} {error "Missing probe net $label"}
    puts "CORE_PROBE_NET $label [$net getName] [$net getSigType] bterms=[llength [$net getBTerms]]"
    foreach pin [$net getITerms] {
        set inst [$pin getInst]
        set master [$inst getMaster]
        puts "CORE_PROBE_PIN $label [$inst getName]/[[$pin getMTerm] getName] [$pin getIoType] [$master getName] xy=[$inst getLocation]"
    }
}
set root [$block findInst clkbuf_0_clk_bus]
if {$root eq "NULL" || $root eq ""} {error "Missing exact bus clock root"}
set clock_net ""
foreach pin [$root getITerms] {
    set name [[$pin getMTerm] getName]
    puts "CORE_PROBE_ROOT_PIN $name [$pin getSigType] [$pin getIoType]"
    if {$name eq "X"} {set clock_net [$pin getNet]}
}
core_probe_net bus_clock $clock_net
set loads 0
foreach pin [$clock_net getITerms] {
    if {[$pin getIoType] eq "INPUT"} {incr loads}
}
if {$loads != 16} {error "Unexpected bus-clock load count $loads, expected16"}
set bank [$block findInst u_ram.g_ram_2048x64_ecc.u_b2]
if {$bank eq "NULL" || $bank eq ""} {error "Missing SRAM b2"}
set men_net ""
foreach pin [$bank getITerms] {
    if {[[$pin getMTerm] getName] eq "A_MEN"} {set men_net [$pin getNet]}
}
core_probe_net sram_men $men_net
foreach command {::odb::dbInst_create ::odb::dbNet_create ::odb::dbITerm_connect ::odb::dbITerm_disconnect ::make_instance ::make_net ::connect_pin ::disconnect_pin} {
    puts "CORE_PROBE_API $command [info commands $command]"
}
puts "CORE_PROBE_COMPLETE_NO_DATABASE_EDITS"
"""

class CoreClockProbe(CoreCornerSTA):
    id = "NSSOC.CoreOnlyClockProbeSlow"
    corner = "nom_slow_1p08V_125C"
    def get_script_path(self):
        original = Path(super().get_script_path())
        text = original.read_text()
        anchor = "read_current_odb\n"
        if text.count(anchor) != 1:
            raise RuntimeError("Unsupported native read script")
        path = Path(self.step_dir) / "clock_probe.tcl"
        path.write_text(text.replace(anchor, anchor + PROBE))
        return str(path)

@Flow.factory.register()
class CoreOnlyClockProbe(Interfaces):
    Steps = [CoreClockProbe]

if __name__ == "__main__":
    from librelane.__main__ import cli
    cli()
