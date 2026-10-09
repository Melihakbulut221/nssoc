# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Packet SoC flow with an explicit clock policy for every physical stage.

LibreLane only supplies OPENLANE_SDC_IDEAL_CLOCKS in its pre/post-PnR STA
steps. Placement and electrical repair also run before CTS and must not
propagate an unbuffered clock tree. CTS starts ideal, then its native script
explicitly propagates the newly built tree. Later stages retain propagated
clocks. Timing budgets, report coverage and acceptance checkers are unchanged.
"""
from interface_flow import Interfaces
from librelane.flows import Flow
from librelane.steps import OpenROAD
from librelane.steps.openroad import OpenROADStep


class PacketIdealClockEnvironment:
    def prepare_env(self, env, state):
        env = super().prepare_env(env, state)
        env["OPENLANE_SDC_IDEAL_CLOCKS"] = "1"
        return env


def packet_steps(steps):
    cts = [i for i, step in enumerate(steps) if step.id == OpenROAD.CTS.id]
    if len(cts) != 1:
        raise ValueError("Expected exactly one native CTS boundary")
    return [
        type("PacketIdeal" + step.__name__, (PacketIdealClockEnvironment, step), {})
        if i <= cts[0] and issubclass(step, OpenROADStep) else step
        for i, step in enumerate(steps)
    ]


@Flow.factory.register()
class PacketInterfaces(Interfaces):
    Steps = packet_steps(Interfaces.Steps)


if __name__ == "__main__":
    from librelane.__main__ import cli
    cli()
