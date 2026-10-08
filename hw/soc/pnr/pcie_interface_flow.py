# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Packet SoC flow with an explicit pre-CTS clock policy.

LibreLane only supplies OPENLANE_SDC_IDEAL_CLOCKS in its pre/post-PnR STA
steps. The first mid-PnR STA runs before CTS; propagating the unbuffered
clock net there is inappropriate. Later mid-PnR stages retain propagated
clocks. Timing budgets, report coverage and acceptance checkers are unchanged.
"""
from interface_flow import Interfaces
from librelane.flows import Flow
from librelane.steps import OpenROAD


class PacketPreCTSSTA(OpenROAD.STAMidPNR):
    def prepare_env(self, env, state):
        env = super().prepare_env(env, state)
        env["OPENLANE_SDC_IDEAL_CLOCKS"] = "1"
        return env


@Flow.factory.register()
class PacketInterfaces(Interfaces):
    Steps = [PacketPreCTSSTA if step.id == "OpenROAD.STAMidPNR" else step
             for step in Interfaces.Steps]


if __name__ == "__main__":
    from librelane.__main__ import cli
    cli()
