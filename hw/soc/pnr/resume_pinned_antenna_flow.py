# SPDX-License-Identifier: Apache-2.0
"""Resume antenna repair from a pinned, completed intermediate DRT database."""
import hashlib,json
from pathlib import Path
from interface_flow import Interfaces
from librelane.flows import Flow
from librelane.steps import OpenROAD,Odb
from librelane.state import DesignFormat

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
class ResumeAntennaDRT(OpenROAD.DetailedRouting):
    id='NSSOC.ResumeAntennaDRT'
    def run(self,state_in,**kwargs):
        assert sha(state_in[DesignFormat.ODB])=='329e6ef42702320243b595ab56554d5fc3fd3c63e93ff452faad0a206df36c82'
        assert sha(state_in[DesignFormat.SDC])=='5c65218b6106315c71d45c19eb61af09781607f0f438f2c7f99c4427884d24a4'
        assert not any(k.startswith(('route__','antenna__')) for k in state_in.metrics)
        return super().run(state_in,**kwargs)
    def get_script_path(self):
        original=Path(super().get_script_path())
        assert sha(original)=='d389d9e6d75bbb82552321f689d92a2e0392684142c11ffabe59c757ece59461', 'Runtime DRT script differs from reviewed source'
        text=original.read_text()
        anchor='drt_run $i {*}$drt_args\n\nincr i'
        assert text.count(anchor)==1
        replacement='set resumed_antenna_count [log_cmd check_antennas]\nif {$resumed_antenna_count != 39} {error "Recovered checkpoint antenna count differs from expected 39"}\nputs "NSSOC_RESUMED_PINNED_DRT_ANTENNA_39"\n\nincr i'
        text=text.replace(anchor,replacement)
        target=Path(self.step_dir)/'resume_drt.tcl';target.write_text(text)
        (Path(self.step_dir)/'resume-script-proof.json').write_text(json.dumps({'original_sha256':sha(original),'adapted_sha256':sha(target),'omitted_initial_route_only':True,'expected_initial_antenna_nets':39,'manufacturing_approval':False},indent=2))
        return str(target)
@Flow.factory.register()
class ResumePinnedAntenna(Interfaces):
    Steps=[ResumeAntennaDRT,Odb.RemoveRoutingObstructions]
if __name__=='__main__':
    from librelane.__main__ import cli
    cli()
