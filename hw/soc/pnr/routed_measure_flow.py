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

RoutedHoldRepair (section 12) continues from a routed database instead:
PostRouteHold (hw/soc/pnr/post_route_hold.tcl: extraction of the routed
wires, setup-protected hold repair in every corner, legalization of the new
buffers with the original instances held, incremental global route),
RemoveNonOrthogonalWires (hw/soc/pnr/remove_nonorthogonal_wires.py: the
changed nets and any net with a diagonal wire segment lose their wires),
then detailed routing again, which routes those nets. The result is
extracted and timed by the same ReplayOnehotRoutedExtraction.
"""
from decimal import Decimal
from pathlib import Path

from interface_flow import Interfaces, CleanOrphanGuides
from librelane.config import Variable
from librelane.flows import Flow
from librelane.steps import OpenROAD, Odb
from librelane.steps.odb import OdbpyStep


@Flow.factory.register()
class RoutedMeasureRoute(Interfaces):
    Steps = [
        OpenROAD.DetailedPlacement,
        OpenROAD.GlobalRouting,
        CleanOrphanGuides,
        Odb.RemoveRoutingObstructions,
    ]


RCX_VARIABLES = [v for v in OpenROAD.RCX.config_vars
                 if v.name in ("RCX_RULESETS", "RCX_MERGE_VIA_WIRE_RES")]


class PostRouteHold(OpenROAD.ResizerStep):
    """Setup-protected hold repair on extracted parasitics of a routed design."""

    id = "NSSOC.PostRouteHold"
    name = "Post-route hold repair"

    config_vars = OpenROAD.ResizerStep.config_vars + RCX_VARIABLES + [
        Variable(
            "NSSOC_POST_ROUTE_HOLD_MARGIN",
            Decimal,
            "Hold slack the post-route repair aims for (repair target, not an acceptance threshold).",
            default=Decimal("0.01"),
            units="ns",
        ),
        Variable(
            "NSSOC_POST_ROUTE_HOLD_MAX_BUFFER_PCT",
            Decimal,
            "Maximum hold buffers the post-route repair may insert, as a percentage of the instances.",
            default=Decimal("10"),
            units="%",
        ),
    ]

    def get_script_path(self):
        return str(Path(__file__).resolve().parent / "post_route_hold.tcl")

    def prepare_env(self, env, state):
        env = super().prepare_env(env, state)
        rules = self.config["RCX_RULESETS"] or {}
        if len(rules) != 1:
            raise RuntimeError(f"Expected one nominal RCX ruleset, got {sorted(rules)}")
        env["NSSOC_RCX_RULESET"] = str(next(iter(rules.values())))
        return env

    def run(self, state_in, **kwargs):
        # Every STA corner, not only the resizer corners: hold is repaired
        # where the routed STA measures it.
        kwargs, env = self.extract_env(kwargs)
        return OpenROAD.OpenROADStep.run(
            self, state_in, corners=self.config["STA_CORNERS"], env=env, **kwargs
        )


class RemoveNonOrthogonalWires(OdbpyStep):
    """Remove the wires of the changed nets and of any net with a diagonal segment."""

    id = "NSSOC.RemoveNonOrthogonalWires"
    name = "Remove wires detailed routing cannot take back"
    config_vars = []

    def get_script_path(self):
        return str(Path(__file__).resolve().parent / "remove_nonorthogonal_wires.py")

    def get_command(self):
        nets = Path(self.step_dir).parent / "post-route-hold-nets.txt"
        return super().get_command() + ["--nets-file", str(nets)]


@Flow.factory.register()
class RoutedHoldRepair(Interfaces):
    Steps = [
        PostRouteHold,
        RemoveNonOrthogonalWires,
        CleanOrphanGuides,
    ]


if __name__ == "__main__":
    from librelane.__main__ import cli

    cli()
