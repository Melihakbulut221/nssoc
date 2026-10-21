# SPDX-License-Identifier: Apache-2.0
"""Fresh global guides for a proved repaired candidate; no detailed routing."""
import hashlib,json,sys
from pathlib import Path
from onehot_fanout_fresh_route_flow import FreshFanoutDetailedRouting,FRESH_GUIDES,OnehotFreshFanoutRoute
from librelane.flows import Flow
ORIGINAL_SHA='dcfb68741ea369b67c9dcd551c8d7b4aca4e7387ec999568cefa3a68c13f684e'
class RepairFreshGlobal(FreshFanoutDetailedRouting):
    id='NSSOC.RepairFreshGlobal'
    name='Fresh repaired-candidate global routing'
    def get_script_path(self):
        original=Path(super().get_script_path());text=original.read_text()
        assert hashlib.sha256(text.encode()).hexdigest()==ORIGINAL_SHA
        anchor='set i 0\n'
        assert text.count(anchor)==1 and text.count(FRESH_GUIDES)==1
        prefix,tail=text.split(anchor,1)
        assert prefix.endswith(FRESH_GUIDES+'\n') and 'drt_run $i {*}$drt_args' in tail
        # Keep the complete native input/clock/NDR preparation and original
        # global router. Detailed route is a separate resumable process.
        generated=prefix+'write_views\nputs NSSOC_REPAIRED_FRESH_GLOBAL_ONLY_COMPLETE\n'
        target=Path(self.step_dir)/'repair_global_native.tcl';target.write_text(generated)
        proof=dict(parent_sha256=ORIGINAL_SHA,generated_sha256=hashlib.sha256(generated.encode()).hexdigest(),
            retained_prefix_sha256=hashlib.sha256(prefix.encode()).hexdigest(),
            fresh_guides_sha256=hashlib.sha256(FRESH_GUIDES.encode()).hexdigest(),
            native_global_unchanged=True,native_detailed_route_started=False,final_timing_complete=False)
        (Path(self.step_dir)/'global-script-proof.json').write_text(json.dumps(proof,indent=2)+'\n')
        return str(target)
@Flow.factory.register()
class MainchipRepairFreshGlobal(OnehotFreshFanoutRoute):
    # Retain original downstream config variables. CLI must stop at the global
    # stage; the controller verifies no downstream stage was executed.
    Steps=[RepairFreshGlobal,*OnehotFreshFanoutRoute.Steps[1:]]
if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='--audit-config':
        package=Path(sys.argv[2]);out=Path(sys.argv[3])
        old=json.loads((package/'resolved-flow-config.json').read_text())
        f=MainchipRepairFreshGlobal(str(package/'trial-config.json'),pdk_root=old['PDK_ROOT'],pdk='ihp-sg13g2',scl='sg13g2_stdcell')
        current=json.loads(f.config.dumps());ignored={'meta','DESIGN_DIR'}
        changes={k:dict(original=old.get(k),actual=v)for k,v in current.items()if k not in ignored and (k not in old or old[k]!=v)}
        out.write_text(json.dumps(dict(differences=changes,resolved=current),indent=2)+'\n')
        assert not changes,changes
        assert current['CLOCK_PORT']==['clk_i','pcie_clk_i','eth_rx_clk_i','eth_tx_clk_i']
        assert current['CLOCK_PERIOD']==20 and current['TIME_DERATING_CONSTRAINT']==5
    else:
        from librelane.__main__ import cli
        cli()
