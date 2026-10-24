# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Resume saved routed native50-buffer ECO and independently extract actual nominal RC/STA."""
from interface_flow import Interfaces
from corrpre_banked_clock200_grt_flow import BankedGlobalRouting
from replay_onehot_detailed_route_flow import GuardedDetailedRouting
from replay_onehot_routed_extraction_flow import AuditedRCX,AuditedRoutedSTA
from librelane.flows import Flow
from librelane.steps import OpenROAD,Odb
@Flow.factory.register()
class OnehotLoadResume(Interfaces):
    Steps=[GuardedDetailedRouting,OpenROAD.CheckAntennas,Odb.ReportDisconnectedPins,AuditedRCX,AuditedRoutedSTA]
if __name__=='__main__':
    from librelane.__main__ import cli
    cli()
