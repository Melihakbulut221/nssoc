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
        paths={name:str(state_in[f]) for name,f in (('odb',DesignFormat.ODB),('sdc',DesignFormat.SDC))}
        def hashes():return {k:hashlib.sha256(Path(v).read_bytes()).hexdigest() for k,v in paths.items()}
        before=hashes()
        # Exact final views are bound by the SHA-verified routed archive.
        # The router rewrites SDC; do not compare it to the pre-route SDC.
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
