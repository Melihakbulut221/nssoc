# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Route a repaired probe database for a post-route timing measurement.

docs/combined-timing.md: the implementation probe stops after global route
and an uncapped setup repair. This flow continues from that repaired database
with the interface flow's own steps: legalize the buffers the repair placed,
global route again with the flow's settings, detailed route (the iteration
bound comes from DRT_OPT_ITERS in the configuration) and remove the routing
obstructions. Extraction and three-corner STA follow in
ReplayOnehotRoutedExtraction (AuditedRCX, AuditedRoutedSTA). Measurement
only: DRC markers left by the bounded routing are reported, not waived.
"""
from interface_flow import Interfaces, CleanOrphanGuides
from librelane.flows import Flow
from librelane.steps import OpenROAD, Odb


@Flow.factory.register()
class RoutedMeasureRoute(Interfaces):
    Steps = [
        OpenROAD.DetailedPlacement,
        OpenROAD.GlobalRouting,
        CleanOrphanGuides,
        Odb.RemoveRoutingObstructions,
    ]


if __name__ == "__main__":
    from librelane.__main__ import cli

    cli()
