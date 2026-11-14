# SPDX-License-Identifier: Apache-2.0
"""Consume frozen pre-DRT jumper guides, then route and measure antennas."""
import hashlib,json
from pathlib import Path
from interface_flow import Interfaces
from librelane.flows import Flow
from librelane.steps import OpenROAD,Odb
from librelane.state import DesignFormat
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
class ExactJumperDRT(OpenROAD.DetailedRouting):
    id='NSSOC.ExactJumperDRT'
    def run(self,state_in,**kwargs):
        p=Path('hw/soc/out/impl-probe/jumper-input-proof.json')
        binding=json.loads(p.read_text())
        assert sha(state_in[DesignFormat.ODB])==binding['odb_sha256']
        assert sha(binding['guide'])==binding['guide_sha256']
        assert sha(state_in[DesignFormat.SDC])=='1fab1c6a3d4777bca6c00e4008ea6546ef403b100a3bc480683172a0ba682511'
        kwargs,env=self.extract_env(kwargs)
        env['NSSOC_EXACT_JUMPER_GUIDE']=binding['guide']
        (Path(self.step_dir)/'jumper-input-proof.json').write_text(json.dumps(binding,indent=2))
        return super().run(state_in,env=env,**kwargs)
    def get_script_path(self):
        original=Path(super().get_script_path())
        assert sha(original)=='d389d9e6d75bbb82552321f689d92a2e0392684142c11ffabe59c757ece59461'
        text=original.read_text();anchor='read_current_odb\n';assert text.count(anchor)==1
        addition='''if {[ord::openroad_version] ne "dcf36133a369abc8f3c5e5738cd4d82e4903c0e0"} {error "Runtime changed"}
check_placement -verbose
if {[llength [[ord::get_db_block] getInsts]] != 159934} {error "Instance count changed"}
if {[llength [[ord::get_db_block] getBTerms]] != 354} {error "Port count changed"}
read_guides $::env(NSSOC_EXACT_JUMPER_GUIDE)
puts "NSSOC_EXACT_JUMPER_GUIDES_LOADED_NO_GRT $::env(NSSOC_EXACT_JUMPER_GUIDE)"
'''
        target=Path(self.step_dir)/'exact_jumper_drt.tcl';target.write_text(text.replace(anchor,anchor+addition))
        return str(target)
@Flow.factory.register()
class ResumePinnedAntenna(Interfaces):
    Steps=[ExactJumperDRT,OpenROAD.CheckAntennas,Odb.RemoveRoutingObstructions]
if __name__=='__main__':
    from librelane.__main__ import cli
    cli()
