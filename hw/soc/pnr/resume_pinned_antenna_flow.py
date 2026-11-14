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
        assert sha(state_in[DesignFormat.ODB])=='9adefc224ed62b8e661cdf4c2ae009f4e9910e5e2c5b848156464eb0fdfca40c'
        assert sha(state_in[DesignFormat.SDC])=='1fab1c6a3d4777bca6c00e4008ea6546ef403b100a3bc480683172a0ba682511'
        assert not any(k.startswith(('route__','antenna__')) for k in state_in.metrics)
        assert self.config['DRT_ANTENNA_REPAIR_JUMPER_ONLY'] is True
        assert self.config['DRT_ANTENNA_REPAIR_DIODE_ONLY'] is False
        return super().run(state_in,**kwargs)
    def get_script_path(self):
        original=Path(super().get_script_path())
        assert sha(original)=='d389d9e6d75bbb82552321f689d92a2e0392684142c11ffabe59c757ece59461', 'Runtime DRT script differs from reviewed source'
        text=original.read_text()
        anchor='drt_run $i {*}$drt_args\n\nincr i'
        assert text.count(anchor)==1
        replacement='set resumed_antenna_count [log_cmd check_antennas]\nif {$resumed_antenna_count != 565} {error "Recovered checkpoint antenna count differs from expected 565"}\nputs "NSSOC_RESUMED_PINNED_DRT_ANTENNA_565"\n\nincr i'
        text=text.replace(anchor,replacement)
        target=Path(self.step_dir)/'resume_drt.tcl';target.write_text(text)
        (Path(self.step_dir)/'resume-script-proof.json').write_text(json.dumps({'original_sha256':sha(original),'adapted_sha256':sha(target),'omitted_initial_route_only':True,'expected_initial_antenna_nets':565,'manufacturing_approval':False},indent=2))
        return str(target)
@Flow.factory.register()
class ResumePinnedAntenna(Interfaces):
    Steps=[ResumeAntennaDRT,OpenROAD.CheckAntennas,Odb.RemoveRoutingObstructions]
if __name__=='__main__':
    from librelane.__main__ import cli
    cli()
