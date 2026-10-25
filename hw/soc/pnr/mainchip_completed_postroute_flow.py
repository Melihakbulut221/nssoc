# SPDX-License-Identifier: Apache-2.0
"""Analyze a completed route; there are no routing or repair stages."""
from interface_flow import Interfaces
from librelane.flows import Flow
from librelane.steps import OpenROAD,Odb
from replay_onehot_routed_extraction_flow import AuditedRCX,AuditedRoutedSTA
@Flow.factory.register()
class MainchipCompletedPostroute(Interfaces):
    Steps=[OpenROAD.CheckAntennas,Odb.ReportDisconnectedPins,AuditedRCX,AuditedRoutedSTA]
if __name__=='__main__':
    from librelane.__main__ import cli
    cli()
