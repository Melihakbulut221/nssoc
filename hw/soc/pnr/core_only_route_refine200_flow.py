# SPDX-License-Identifier: Apache-2.0
"""Continue routed repair; only the search bound changes, never acceptance."""
from core_only_postgrt_flow import CoreRouteTiming, measurements, CoreOnlyRouteElectricalTrial
from interface_flow import Interfaces
from librelane.flows import Flow

class CoreRouteTiming200(CoreRouteTiming):
    id = "NSSOC.CoreOnlyRouteTiming200"
    max_setup_iterations = 200

@Flow.factory.register()
class CoreOnlyRouteTiming200Trial(Interfaces):
    Steps = [CoreRouteTiming200] + measurements("RouteTimingAfter")

if __name__ == "__main__":
    from librelane.__main__ import cli
    cli()
