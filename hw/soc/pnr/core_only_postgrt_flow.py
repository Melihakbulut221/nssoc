# SPDX-License-Identifier: Apache-2.0
"""Guarded global-route electrical and setup/hold repair; not final signoff."""
from core_only_postcts_flow import CorePropagated, CORNERS
from core_only_globalroute_flow import RoutedCornerSTA
from interface_flow import Interfaces, BoundedPostGRT
from librelane.flows import Flow
from librelane.steps import OpenROAD

class CoreRouteElectrical(CorePropagated, OpenROAD.RepairDesignPostGRT):
    id = "NSSOC.CoreOnlyRouteElectrical"
    def run(self, state_in, **kwargs):
        if not self.config["GRT_DESIGN_REPAIR_RUN_GRT"]:
            raise ValueError("Post-repair routes must be regenerated")
        return super().run(state_in, **kwargs)

class CoreRouteTiming(CorePropagated, BoundedPostGRT):
    id = "NSSOC.CoreOnlyRouteTiming"
    def run(self, state_in, **kwargs):
        if not self.config["GRT_RESIZER_RUN_GRT"]:
            raise ValueError("Post-repair routes must be regenerated")
        return super().run(state_in, **kwargs)

def measurements(phase):
    return [type(phase + name, (RoutedCornerSTA,),
                 dict(id="NSSOC.CoreOnly" + phase + name, corner=corner))
            for name, corner in CORNERS]

@Flow.factory.register()
class CoreOnlyRouteElectricalTrial(Interfaces):
    Steps = [CoreRouteElectrical] + measurements("RouteElectricalAfter")

@Flow.factory.register()
class CoreOnlyRouteTimingTrial(Interfaces):
    Steps = [CoreRouteTiming] + measurements("RouteTimingAfter")

if __name__ == "__main__":
    from librelane.__main__ import cli
    cli()
