# SPDX-License-Identifier: Apache-2.0
"""Five-driver candidate plus three isolated RX bank6 address delay cells.
Same original cut10j source layout and four electrical repairs, plus measured CRC A21OI driver. Clock budgets unchanged.
Fresh routing/extraction required; not manufacturing acceptance.
"""
from interface_flow import Interfaces
from pathlib import Path
from cut10j_electrical4_reroute_flow import TargetedResize as FourDriverResize
class TargetedResize(FourDriverResize):
    id = "NSSOC.Cut10jRx6HoldThree"
    def get_script_path(self):
        return str(Path(__file__).with_name("cut10j_rx6_hold3.tcl"))
from corrpre_banked_clock200_grt_flow import BankedGlobalRouting
from replay_onehot_detailed_route_flow import GuardedDetailedRouting
from replay_onehot_routed_extraction_flow import AuditedRCX, AuditedRoutedSTA
from librelane.flows import Flow
from librelane.steps import OpenROAD, Odb
@Flow.factory.register()
class Cut10jRx6Hold3Antenna(Interfaces):
    Steps = [TargetedResize, BankedGlobalRouting, OpenROAD.RepairAntennas,
             GuardedDetailedRouting, OpenROAD.CheckAntennas,
             Odb.ReportDisconnectedPins, AuditedRCX, AuditedRoutedSTA]
if __name__ == '__main__':
    from librelane.__main__ import cli
    cli()
