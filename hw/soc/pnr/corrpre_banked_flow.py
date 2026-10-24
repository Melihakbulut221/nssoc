# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Measure and repair a source-bound banked candidate without timing waivers."""
from librelane.flows import Flow
from interface_flow import Interfaces, BoundedPostCTS
from corrpre_postcts_flow import GuardedPropagated, ElectricalPostCTS, measurements


class BankedTimingRepair(GuardedPropagated, BoundedPostCTS):
    """Retain setup100/hold1000 search limits and assert actual clock budgets."""


@Flow.factory.register()
class CorrpreBankedPostCTS(Interfaces):
    Steps = (measurements("BankedBefore") + [ElectricalPostCTS, BankedTimingRepair]
             + measurements("BankedAfter"))


if __name__ == "__main__":
    from librelane.__main__ import cli
    cli()
