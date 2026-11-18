# SPDX-License-Identifier: Apache-2.0
"""Core-only native detailed routing. Completion is not signoff."""
from core_only_postcts_flow import CorePropagated
from interface_flow import Interfaces, CleanOrphanGuides
from librelane.flows import Flow
from librelane.steps import OpenROAD, Odb

class CoreDetailedRouting(CorePropagated, CleanOrphanGuides):
    id = "NSSOC.CoreOnlyDetailedRouting"

@Flow.factory.register()
class CoreOnlyDetailedRoute(Interfaces):
    Steps = [CoreDetailedRouting, OpenROAD.CheckAntennas, Odb.ReportDisconnectedPins]

if __name__ == "__main__":
    from librelane.__main__ import cli
    cli()
