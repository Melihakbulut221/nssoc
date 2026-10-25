# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Rebuffer measured critical data branches; retain original clock/STA policy."""
import hashlib,json
from pathlib import Path
from librelane.flows import Flow
from interface_flow import Interfaces
from corrpre_banked_flow import BankedTimingRepair
from corrpre_postcts_flow import ElectricalPostCTS, measurements

class TargetedElectrical(ElectricalPostCTS):
    id='NSSOC.CorrpreTargetedUnbuffer'
    def run(self,state_in,**kwargs):
        root=Path(__file__).resolve().parents[3]
        source=root/'hw/soc/out/cloud-replay-onehot-postcts/result.json'
        assert hashlib.sha256(source.read_bytes()).hexdigest()=='bedead30ddb1f70e1ecd8154684e8f1be84eee4ca93e79839e88efbfe3230c3a'
        prior=json.loads(source.read_text())
        for short,corner in [('slow','nom_slow_1p08V_125C'),('typical','nom_typ_1p20V_25C'),('fast','nom_fast_1p32V_m40C')]:
            paths=list(Path(self.step_dir).parent.glob('*-nssoc-corrpretargetbefore'+short+'/state_out.json'))
            assert len(paths)==1
            metrics=json.loads(paths[0].read_text())['metrics']
            for key,value in prior['measurements']['after'][corner]['metrics'].items():
                assert metrics[key]==value,('Baseline differs before mutation',key,metrics[key],value)
        return super().run(state_in,**kwargs)
    def get_script_path(self):
        script=Path(super().get_script_path());text=script.read_text()
        anchor='set arg_list [list]\n'
        assert text.count(anchor)==1
        helper=Path(__file__).resolve().parents[1]/'flow/replay_onehot_targeted_unbuffer.tcl'
        script.write_text(text.replace(anchor,'source {'+str(helper)+'}\n'+anchor))
        return str(script)

@Flow.factory.register()
class CorrpreBankedTargetedRebuffer(Interfaces):
    Steps=measurements('TargetBefore')+[TargetedElectrical,BankedTimingRepair]+measurements('TargetAfter')
if __name__=='__main__':
    from librelane.__main__ import cli
    cli()
