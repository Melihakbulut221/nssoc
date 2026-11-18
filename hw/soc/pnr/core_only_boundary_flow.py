"""Provisional boundary export; no physical modification or timing acceptance."""
from interface_flow import Interfaces
from librelane.flows import Flow
from librelane.steps import OpenROAD
@Flow.factory.register()
class CoreOnlyBoundaryProbe(Interfaces):
    Steps=[OpenROAD.WriteViews]
if __name__=='__main__':
    from librelane.__main__ import cli
    cli()
