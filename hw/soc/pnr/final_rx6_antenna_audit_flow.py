# SPDX-License-Identifier: Apache-2.0
"""Fresh read-only antenna audit, no routing or limit changes."""
import hashlib,json
from pathlib import Path
from interface_flow import Interfaces
from librelane.flows import Flow
from librelane.steps import OpenROAD
from librelane.state import DesignFormat
class FinalAntenna(OpenROAD.CheckAntennas):
    id='NSSOC.FinalAntenna'
    def run(self,state_in,**kwargs):
        assert not state_in.metrics
        paths={f.name:str(state_in[f]) for f in (DesignFormat.ODB,DesignFormat.SDC)}
        def hashes():return {k:hashlib.sha256(Path(v).read_bytes()).hexdigest() for k,v in paths.items()}
        before=hashes()
        assert before['SDC']=='5c65218b6106315c71d45c19eb61af09781607f0f438f2c7f99c4427884d24a4'
        views,metrics=super().run(state_in,**kwargs)
        assert not views
        assert before==hashes()
        assert 'antenna__violating__nets' in metrics and 'antenna__violating__pins' in metrics
        (Path(self.step_dir)/'fresh-check-proof.json').write_text(json.dumps({'input_hashes':before,'input_files_unchanged':True,'stale_metrics_removed':True,'native_metrics':metrics,'manufacturing_approval':False},indent=2))
        return views,metrics
@Flow.factory.register()
class FinalAntennaAudit(Interfaces):
    Steps=[FinalAntenna]
if __name__=='__main__':
    from librelane.__main__ import cli
    cli()
