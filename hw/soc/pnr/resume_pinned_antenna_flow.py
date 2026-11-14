# SPDX-License-Identifier: Apache-2.0
"""Reroute verified diode-legalized state with original constraints and strict final gates."""
import hashlib,json
from pathlib import Path
from interface_flow import Interfaces
from librelane.flows import Flow
from librelane.steps import OpenROAD,Odb
from librelane.state import DesignFormat
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
RESET_ROUTES='if {[ord::openroad_version] ne "dcf36133a369abc8f3c5e5738cd4d82e4903c0e0"} {error "Runtime changed"}\ncheck_placement -verbose\nset removed 0\nforeach net [[ord::get_db_block] getNets] {\n if {[$net isSpecial] || [$net getSigType] in {POWER GROUND}} {continue}\n set wire [$net getWire]\n if {$wire ne "NULL"} {odb::dbWire_destroy $wire; incr removed}\n}\nif {$removed == 0} {error "No signal routes cleared"}\nputs "NSSOC_SIGNAL_ROUTES_REBUILT $removed"\n'
class LegalizedGlobalRouting(OpenROAD.GlobalRouting):
    id='NSSOC.LegalizedGlobalRouting'
    def run(self,state_in,**kwargs):
        assert sha(state_in[DesignFormat.ODB])=='972d9676e2f3af51fda24b2411048b60383e9dfffdb92cd8550a9caf9c53e0b9'
        assert sha(state_in[DesignFormat.SDC])=='1fab1c6a3d4777bca6c00e4008ea6546ef403b100a3bc480683172a0ba682511'
        import re
        for fmt in (DesignFormat.NETLIST,DesignFormat.POWERED_NETLIST):
            text=Path(state_in[fmt]).read_text()
            assert len(re.findall(r'(?m)^\s*sg13g2_buf_4\s+\\?place31551\s*\(',text))==1
            assert not re.search(r'(?m)^\s*sg13g2_buf_1\s+\\?place31551\s*\(',text)
        return super().run(state_in,**kwargs)
    def get_script_path(self):
        original=Path(super().get_script_path());assert sha(original)=='9cceedd2c477f85b25362d5e3833fe0e9c0d85f14248060fc38e3fdec0c6187c'
        text=original.read_text();anchor='read_current_odb\n';assert text.count(anchor)==1
        addition=RESET_ROUTES
        text=text.replace(anchor,anchor+addition)
        target=Path(self.step_dir)/'legalized_grt.tcl';target.write_text(text)
        (Path(self.step_dir)/'legalized-route-proof.json').write_text(json.dumps({'original_script_sha256':sha(original),'adapted_sha256':sha(target),'placement_source_run':43609939062,'scope':'Rebuild signal routes after one verified buffer upsize and selected legal transform. Supply and special wires retained. No timing/antenna limits relaxed.','manufacturing_approval':False},indent=2))
        return str(target)
@Flow.factory.register()
class ResumePinnedAntenna(Interfaces):
    Steps=[LegalizedGlobalRouting,OpenROAD.DetailedRouting,OpenROAD.CheckAntennas,Odb.RemoveRoutingObstructions]
if __name__=='__main__':
    from librelane.__main__ import cli
    cli()
