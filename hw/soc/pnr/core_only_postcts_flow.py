# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Core-only propagated-clock repair trials; placement RC is not signoff."""
from pathlib import Path
from interface_flow import Interfaces, BoundedPostCTS
from librelane.flows import Flow
from librelane.steps import OpenROAD

CLOCK_CHECK = r"""
if {![info exists ::env(TIME_DERATING_CONSTRAINT)] ||
    ![string is double -strict $::env(TIME_DERATING_CONSTRAINT)] ||
    $::env(TIME_DERATING_CONSTRAINT) != 5.0} {
    error "Core-only requires five percent timing derate"
}
if {[llength [all_clocks]] != 1} {
    error "Core-only requires exactly one clock"
}
set clock [get_clocks clk_i]
if {[llength $clock] != 1 || abs([get_property $clock period] - 20.0) > 1e-9} {
    error "Core-only requires clk_i at 20 ns"
}
set_propagated_clock [all_clocks]
foreach clock [all_clocks] {
    if {![get_property $clock is_propagated]} {error "PostCTS ideal clock"}
}
"""

def protect_script(source, derate_guard):
    anchor = "read_current_odb\n"
    if source.count(anchor) != 1:
        raise RuntimeError("Unsupported native database load")
    # These trials always start from a completed CTS database.
    source = source.replace("unset_propagated_clock [all_clocks]",
                            "set_propagated_clock [all_clocks]")
    return source.replace(anchor, derate_guard + "\n" + anchor + CLOCK_CHECK)

class CorePropagated:
    def prepare_env(self, env, state):
        env = super().prepare_env(env, state)
        env["OPENLANE_SDC_IDEAL_CLOCKS"] = "0"
        return env

    def get_script_path(self):
        original = Path(super().get_script_path())
        guard = Path(__file__).resolve().parents[1] / "flow/check_timing_derate.tcl"
        output = Path(self.step_dir) / "core_only_propagated_native.tcl"
        output.write_text(protect_script(original.read_text(), guard.read_text()))
        return str(output)

class CoreCornerSTA(CorePropagated, OpenROAD.STAMidPNR):
    def run(self, state_in, **kwargs):
        return super().run(state_in, corners=[self.corner], **kwargs)

class CoreElectrical(CorePropagated, OpenROAD.RepairDesignPostGPL):
    id = "NSSOC.CoreOnlyElectrical"
    name = "Core-only postCTS electrical repair"

class CoreTiming(CorePropagated, BoundedPostCTS):
    id = "NSSOC.CoreOnlyTiming"
    name = "Core-only bounded postCTS setup and hold repair"

CORNERS = [("Slow", "nom_slow_1p08V_125C"),
           ("Typical", "nom_typ_1p20V_25C"),
           ("Fast", "nom_fast_1p32V_m40C")]

def measurements(phase):
    return [type(phase + name, (CoreCornerSTA,),
                 dict(id="NSSOC.CoreOnly" + phase + name, corner=corner))
            for name, corner in CORNERS]

@Flow.factory.register()
class CoreOnlyElectricalTrial(Interfaces):
    Steps = measurements("Before") + [CoreElectrical] + measurements("ElectricalAfter")

@Flow.factory.register()
class CoreOnlyTimingTrial(Interfaces):
    Steps = measurements("Before") + [CoreTiming] + measurements("TimingAfter")

if __name__ == "__main__":
    from librelane.__main__ import cli
    cli()
