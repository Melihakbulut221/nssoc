# SPDX-License-Identifier: Apache-2.0
"""Authenticated core-only global routing; route estimates are not signoff."""
from pathlib import Path
from core_only_postcts_flow import CorePropagated, CoreCornerSTA, CORNERS
from interface_flow import Interfaces
from librelane.flows import Flow
from librelane.steps import OpenROAD

class CoreGlobalRoute(CorePropagated, OpenROAD.GlobalRouting):
    id = "NSSOC.CoreOnlyGlobalRoute"

class RoutedCornerSTA(CoreCornerSTA):
    def get_script_path(self):
        path = Path(super().get_script_path())
        text = path.read_text()
        anchor = "    # Internal API- brittle"
        if text.count(anchor) != 1:
            raise RuntimeError("Unsupported native route STA script")
        guard = 'if {![grt::have_routes]} {error "Missing global routes; placement fallback forbidden"}\nputs "CORE_ONLY_GLOBAL_ROUTES_VERIFIED"\n'
        path.write_text(text.replace(anchor, guard + anchor))
        return str(path)

@Flow.factory.register()
class CoreOnlyGlobalRoute(Interfaces):
    Steps = [CoreGlobalRoute] + [
        type("Routed" + name, (RoutedCornerSTA,),
             dict(id="NSSOC.CoreOnlyRouted" + name, corner=corner))
        for name, corner in CORNERS]

if __name__ == "__main__":
    from librelane.__main__ import cli
    cli()
