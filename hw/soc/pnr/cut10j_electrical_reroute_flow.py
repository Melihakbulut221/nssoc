# SPDX-License-Identifier: Apache-2.0
"""Two measured Ethernet drivers: resize, legalize, reroute, extract and measure.
Experimental candidate only. No RTL/clock/corner/derate changes.
"""
from pathlib import Path
from interface_flow import Interfaces
from corrpre_banked_clock200_grt_flow import BankedGlobalRouting
from replay_onehot_detailed_route_flow import GuardedDetailedRouting
from replay_onehot_routed_extraction_flow import AuditedRCX, AuditedRoutedSTA
from librelane.flows import Flow
from librelane.steps import OpenROAD, Odb
class TargetedResize(OpenROAD.RepairDesignPostGPL):
    id = "NSSOC.Cut10jTwoBufferResize"
    def prepare_env(self, env, state):
        env = super().prepare_env(env, state)
        env["OPENLANE_SDC_IDEAL_CLOCKS"] = "0"
        env["NSSOC_DERATE_GUARD"] = str(Path(__file__).resolve().parents[1] / "flow/check_timing_derate.tcl")
        return env
    def get_script_path(self):
        return str(Path(__file__).with_name("cut10j_two_buffer_resize.tcl"))
@Flow.factory.register()
class Cut10jElectricalReroute(Interfaces):
    Steps = [TargetedResize, BankedGlobalRouting, GuardedDetailedRouting,
             OpenROAD.CheckAntennas, Odb.ReportDisconnectedPins,
             AuditedRCX, AuditedRoutedSTA]
if __name__ == "__main__":
    from librelane.__main__ import cli
    cli()
