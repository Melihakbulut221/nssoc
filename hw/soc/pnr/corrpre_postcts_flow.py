# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fresh per-corner CTS measurements around electrical repair; no signoff claim."""
from pathlib import Path
from interface_flow import Interfaces
from librelane.flows import Flow
from librelane.steps import OpenROAD

CLOCK_CHECK = r"""
set_propagated_clock [all_clocks]
foreach {name period} {clk_i 20 pcie_clk_i 4 eth_rx_clk_i 8 eth_tx_clk_i 8} {
    set clock [get_clocks $name]
    if {[llength $clock] != 1 || abs([get_property $clock period]-$period)>1e-9} {
        error "Original physical clock budget changed: $name"
    }
}
foreach clock [all_clocks] {
    if {![get_property $clock is_propagated]} {error "PostCTS ideal clock"}
}
puts "%OL_CREATE_REPORT high-fanout.rpt"
foreach net [[ord::get_db_block] getNets] {
    if {[$net getSigType] in {POWER GROUND}} {continue}
    set pins [$net getITerms]
    if {[llength $pins] < 128} {continue}
    set drivers {}
    foreach pin $pins {
        if {[$pin getIoType] == "OUTPUT"} {
            lappend drivers "[[$pin getInst] getName]/[[$pin getMTerm] getName]"
        }
    }
    puts [list [$net getName] [$net getSigType] [llength $pins] $drivers]
}
puts "%OL_END_REPORT"
"""

class GuardedPropagated:
    def prepare_env(self, env, state):
        env = super().prepare_env(env, state)
        env['OPENLANE_SDC_IDEAL_CLOCKS'] = '0'
        return env

    def get_script_path(self):
        original = Path(super().get_script_path())
        text = original.read_text()
        anchor = 'read_current_odb\n'
        if text.count(anchor) != 1:
            raise RuntimeError('Unsupported native script: ' + str(original))
        guard = Path(__file__).resolve().parents[1] / 'flow/check_timing_derate.tcl'
        text = text.replace(anchor, guard.read_text() + '\n' + anchor + CLOCK_CHECK)
        if isinstance(self, ElectricalPostCTS):
            ideal = 'unset_propagated_clock [all_clocks]'
            if text.count(ideal) != 1:
                raise RuntimeError('Unsupported native repair clock policy')
            text = text.replace(ideal, 'set_propagated_clock [all_clocks]')
        output = Path(self.step_dir) / 'propagated_native.tcl'
        output.write_text(text)
        return str(output)

class SingleCornerSTA(GuardedPropagated, OpenROAD.STAMidPNR):
    def run(self, state_in, **kwargs):
        # Native corner.tcl explicitly reports only its first loaded corner.
        # Give each measurement a separate native process and report directory.
        return super().run(state_in, corners=[self.corner], **kwargs)

class ElectricalPostCTS(GuardedPropagated, OpenROAD.RepairDesignPostGPL):
    id = 'NSSOC.CorrpreElectricalPostCTS'
    name = 'CORRPRE postCTS electrical repair'

CORNERS = [('Slow', 'nom_slow_1p08V_125C'),
           ('Typical', 'nom_typ_1p20V_25C'),
           ('Fast', 'nom_fast_1p32V_m40C')]
def measurements(phase):
    return [type(phase+name, (SingleCornerSTA,),
                 dict(id='NSSOC.Corrpre'+phase+name, corner=corner))
            for name, corner in CORNERS]

@Flow.factory.register()
class CorrpreElectricalTrial(Interfaces):
    Steps = measurements('Before') + [ElectricalPostCTS] + measurements('After')

if __name__ == '__main__':
    from librelane.__main__ import cli
    cli()
