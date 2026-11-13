# SPDX-License-Identifier: Apache-2.0
"""Four-driver candidate with explicit global and detailed antenna repair.
Same clock budgets, source layout and signal-driver changes as electrical4.
Fresh routing/extraction required; not manufacturing acceptance.
"""
from interface_flow import Interfaces
from cut10j_electrical4_reroute_flow import TargetedResize
from corrpre_banked_clock200_grt_flow import BankedGlobalRouting
from replay_onehot_detailed_route_flow import GuardedDetailedRouting
from replay_onehot_routed_extraction_flow import AuditedRCX, AuditedRoutedSTA
from librelane.flows import Flow
from librelane.steps import OpenROAD, Odb
@Flow.factory.register()
class Cut10jElectrical4Antenna(Interfaces):
    Steps = [TargetedResize, BankedGlobalRouting, OpenROAD.RepairAntennas,
             GuardedDetailedRouting, OpenROAD.CheckAntennas,
             Odb.ReportDisconnectedPins, AuditedRCX, AuditedRoutedSTA]
if __name__ == '__main__':
    from librelane.__main__ import cli
    cli()
