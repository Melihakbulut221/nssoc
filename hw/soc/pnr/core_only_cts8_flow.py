# SPDX-License-Identifier: Apache-2.0
"""CTS candidate with at most eight sinks per leaf/macro cluster.

This changes topology, not the SDC fanout limit or acceptance policy.
Fresh three-corner STA is required after CTS and each repair phase.
"""
from core_only_postcts_flow import (
    CorePropagated, measurements, CoreOnlyElectricalTrial, CoreOnlyTimingTrial)
from interface_flow import Interfaces
from librelane.flows import Flow
from librelane.steps import OpenROAD

class CoreCluster8CTS(CorePropagated, OpenROAD.CTS):
    id = "NSSOC.CoreOnlyCluster8CTS"
    def run(self, state_in, **kwargs):
        for key in ("CTS_SINK_CLUSTERING_SIZE", "CTS_MACRO_CLUSTERING_SIZE"):
            if self.config[key] != 8:
                raise ValueError("Expected eight-sink CTS cluster: " + key)
        if not self.config["CTS_SINK_CLUSTERING_ENABLE"]:
            raise ValueError("CTS sink clustering must be enabled")
        return super().run(state_in, **kwargs)

@Flow.factory.register()
class CoreOnlyCluster8CTS(Interfaces):
    Steps = [CoreCluster8CTS] + measurements("CTSAfter")

if __name__ == "__main__":
    from librelane.__main__ import cli
    cli()
