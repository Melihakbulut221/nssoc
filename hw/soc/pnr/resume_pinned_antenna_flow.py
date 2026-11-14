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
        assert self.config['DRT_ANTENNA_REPAIR_JUMPER_ONLY'] is False
        assert self.config['DRT_ANTENNA_REPAIR_DIODE_ONLY'] is True
        return super().run(state_in,**kwargs)
    def get_script_path(self):
        original=Path(super().get_script_path())
        assert sha(original)=='d389d9e6d75bbb82552321f689d92a2e0392684142c11ffabe59c757ece59461', 'Runtime DRT script differs from reviewed source'
        text=original.read_text()
        assert text.count('set i 0')==1
        text=text.split('set i 0',1)[0]+'puts "NSSOC_OPENROAD_VERSION [ord::openroad_version]"\nset before_count [check_antennas]\nif {$before_count != 565} {error "Unexpected initial antenna count"}\nset block [ord::get_db_block]\nset status_file [open "$::env(STEP_DIR)/before-status.tsv" w]\nforeach inst [$block getInsts] {puts $status_file "[$inst getName]\\t[$inst getPlacementStatus]"}\nclose $status_file\nset rc [catch {repair_antennas sg13g2_antennanp -ratio_margin 10 -diode_only} message options]\nputs "NSSOC_DIODE_DIAGNOSTIC_RC $rc"\nputs "NSSOC_DIODE_DIAGNOSTIC_MESSAGE $message"\nwrite_db "$::env(STEP_DIR)/diode-diagnostic.odb"\nset status_file [open "$::env(STEP_DIR)/after-status.tsv" w]\nforeach inst [$block getInsts] {puts $status_file "[$inst getName]\\t[$inst getPlacementStatus]"}\nclose $status_file\nif {$rc} {return -options $options $message}\nerror "DIAGNOSTIC_ONLY_DIODE_INSERTION_COMPLETED_NO_ROUTING_OR_ACCEPTANCE"\n'
        target=Path(self.step_dir)/'resume_drt.tcl';target.write_text(text)
        (Path(self.step_dir)/'resume-script-proof.json').write_text(json.dumps({'original_sha256':sha(original),'adapted_sha256':sha(target),'diagnostic_only_no_detailed_route':True,'expected_initial_antenna_nets':565,'manufacturing_approval':False},indent=2))
        return str(target)
@Flow.factory.register()
class ResumePinnedAntenna(Interfaces):
    Steps=[ResumeAntennaDRT]
if __name__=='__main__':
    from librelane.__main__ import cli
    cli()
