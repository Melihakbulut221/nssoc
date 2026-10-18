# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Fresh nominal OpenRCX plus propagated OpenSTA; not RCmin/max qualification."""
import hashlib,json,sys
from pathlib import Path
from interface_flow import Interfaces
from librelane.flows import Flow
from librelane.steps import OpenROAD
from librelane.state import DesignFormat
ROOT=Path(__file__).resolve().parents[3]
CORNERS={'nom_slow_1p08V_125C','nom_typ_1p20V_25C','nom_fast_1p32V_m40C'}
RULES_SHA='ffda02d57a6ecb39b02268be9511d89ef072911f17bd2dcd095f3f3cbeb5a905'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
CLOCK_GUARD=r"""
foreach {name period} {clk_i 20 pcie_clk_i 4 eth_rx_clk_i 8 eth_tx_clk_i 8} {
    set clock [get_clocks $name]
    if {[llength $clock] != 1 || abs([get_property $clock period]-$period)>1e-9} {
        error "Original routed clock budget changed: $name"
    }
}
foreach clock [all_clocks] {
    if {![get_property $clock is_propagated]} {error "Routed STA has ideal clock"}
}
puts "NSSOC_ROUTED_ORIGINAL_CLOCKS_PROPAGATED"
"""
def guarded_sta(text,derate):
    anchor='source $::env(SCRIPTS_DIR)/openroad/common/io.tcl\n'
    assert text.count(anchor)==1 and text.count('read_spefs\n')==1
    assert text.count('    read_timing_info\n')==1
    # STAPostPNR must invoke standalone OpenSTA. Its OpenROAD branch estimates
    # parasitics and is explicitly rejected before any circuit is loaded.
    text=text.replace(anchor,anchor+derate+'\nif {[namespace exists ::ord]} {error "Routed STA requires standalone OpenSTA and actual SPEF"}\n')
    return text.replace('read_spefs\n','read_spefs\n'+CLOCK_GUARD)
class AuditedRCX(OpenROAD.RCX):
    id='NSSOC.OnehotRouteRCX'
    def run(self,state_in,**kwargs):
        assert set(self.config['STA_CORNERS'])==CORNERS
        rules=self.config['RCX_RULESETS']
        assert len(rules)==1 and {sha(p)for p in rules.values()}=={RULES_SHA}
        assert self.config['STA_THREADS']==1
        before={str(p):sha(p)for p in rules.values()}
        views,metrics=super().run(state_in,**kwargs)
        files=views[DesignFormat.SPEF];assert isinstance(files,dict)and len(files)==1
        sys.path.insert(0,str(ROOT/'hw/soc/flow'))
        from audit_estimated_spef import audit
        checks={}
        for corner,path in files.items():
            check=audit(Path(path),allow_coupling=True)
            assert check['status'].startswith('PASS')
            checks[corner]=dict(path=str(path),sha256=sha(path),audit=check)
        assert all(sha(p)==h for p,h in before.items())
        (Path(self.step_dir)/'native-spef-integrity.json').write_text(json.dumps(dict(rules=before,nominal_only=True,qualified_rc_minmax=False,spefs=checks),indent=2)+'\n')
        return views,metrics
class AuditedRoutedSTA(OpenROAD.STAPostPNR):
    id='NSSOC.OnehotRoutedSTA'
    def prepare_env(self,env,state):
        assert set(self.config['STA_CORNERS'])==CORNERS
        assert self.config['STA_THREADS']==1 and state[DesignFormat.SPEF]
        env=super().prepare_env(env,state)
        assert env['OPENLANE_SDC_IDEAL_CLOCKS']=='0'
        return env
    def get_script_path(self):
        original=Path(super().get_script_path());guard=ROOT/'hw/soc/flow/check_timing_derate.tcl'
        text=guarded_sta(original.read_text(),guard.read_text())
        target=Path(self.step_dir)/'routed_corner.tcl';target.write_text(text)
        (Path(self.step_dir)/'native-sta-script-proof.json').write_text(json.dumps(dict(original=str(original),original_sha256=sha(original),guard_sha256=sha(guard),adapted_sha256=sha(target),only_added_derate_engine_and_clock_guards=True),indent=2)+'\n')
        return str(target)
@Flow.factory.register()
class ReplayOnehotRoutedExtraction(Interfaces):
    Steps=[AuditedRCX,AuditedRoutedSTA]
if __name__=='__main__':
    from librelane.__main__ import cli
    cli()
