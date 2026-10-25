# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Native DRT and antenna/pin reports from exact onehot global-route guides."""
from interface_flow import Interfaces, CleanOrphanGuides
from corrpre_postcts_flow import GuardedPropagated
from librelane.flows import Flow
from librelane.steps import OpenROAD, Odb

class GuardedDetailedRouting(GuardedPropagated, CleanOrphanGuides):
    pass

@Flow.factory.register()
class ReplayOnehotDetailedRoute(Interfaces):
    Steps = [GuardedDetailedRouting, OpenROAD.CheckAntennas, Odb.ReportDisconnectedPins]

if __name__ == '__main__':
    from librelane.__main__ import cli
    cli()
