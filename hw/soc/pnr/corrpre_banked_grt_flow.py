# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""One durable global-routing stage; unchanged clocks and no signoff claim."""
from interface_flow import Interfaces
from corrpre_postcts_flow import GuardedPropagated
from librelane.flows import Flow
from librelane.steps import OpenROAD

class BankedGlobalRouting(GuardedPropagated, OpenROAD.GlobalRouting):
    pass

@Flow.factory.register()
class CorrpreBankedGlobalRouting(Interfaces):
    Steps = [BankedGlobalRouting]

if __name__ == '__main__':
    from librelane.__main__ import cli
    cli()
