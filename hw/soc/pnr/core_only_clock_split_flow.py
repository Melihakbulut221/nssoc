# SPDX-License-Identifier: Apache-2.0
"""Guarded CTS8 bus-root split, legalization, repair and routing trials."""
from pathlib import Path
from core_only_postcts_flow import (
    CorePropagated, measurements, CoreOnlyElectricalTrial, CoreOnlyTimingTrial)
from core_only_globalroute_flow import CoreGlobalRoute, RoutedCornerSTA
from interface_flow import Interfaces
from librelane.flows import Flow
from librelane.steps import OpenROAD

class CoreClockSplit(CorePropagated, OpenROAD.DetailedPlacement):
    id = "NSSOC.CoreOnlyClockSplit"
    def get_script_path(self):
        original = Path(super().get_script_path())
        source = original.read_text()
        anchor = "read_current_odb\n"
        if source.count(anchor) != 1:
            raise RuntimeError("Unsupported native placement script")
        helper = Path(__file__).resolve().parents[1] / "flow/core_only_clock_split.tcl"
        source = source.replace(anchor, anchor + helper.read_text() + "\n")
        source += "\nverify_core_clock_split\n"
        output = Path(self.step_dir) / "core_clock_split.tcl"
        output.write_text(source)
        return str(output)

@Flow.factory.register()
class CoreOnlyClockSplitTrial(Interfaces):
    Steps = [CoreClockSplit] + measurements("SplitAfter")

@Flow.factory.register()
class CoreOnlyClockSplitRoute(Interfaces):
    Steps = [CoreGlobalRoute] + [
        type("SplitRouted" + name, (RoutedCornerSTA,),
             dict(id="NSSOC.CoreOnlySplitRouted" + name, corner=corner))
        for name, corner in [("Slow", "nom_slow_1p08V_125C"),
                             ("Typical", "nom_typ_1p20V_25C"),
                             ("Fast", "nom_fast_1p32V_m40C")]]

if __name__ == "__main__":
    from librelane.__main__ import cli
    cli()
