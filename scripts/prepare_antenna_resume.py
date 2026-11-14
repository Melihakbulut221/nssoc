# SPDX-License-Identifier: Apache-2.0
"""Prepare exact recovered route state in the cloud, dropping stale metrics."""
import hashlib,json,pathlib
P=pathlib.Path;root=P('hw/soc/out/impl-probe').resolve()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
odb=root/'rcx/4-openroad-detailedrouting/drt-run-1/soc_top.odb';sdc=root/'rcx/1-nssoc-cut10jrx6holdthree/soc_top.sdc'
assert sha(odb)=='329e6ef42702320243b595ab56554d5fc3fd3c63e93ff452faad0a206df36c82'
assert sha(sdc)=='5c65218b6106315c71d45c19eb61af09781607f0f438f2c7f99c4427884d24a4'
state=json.loads((root/'rcx/4-openroad-detailedrouting/state_in.json').read_text())
# Keep only authoritative inputs needed for resumed physical operation.
state={k:state[k] for k in ('nl','pnl') if k in state}
state.update(odb=str(odb),sdc=str(sdc),metrics={})
for key,value in state.items():
 if key!='metrics':assert P(value).is_file(),key
(root/'route-initial.json').write_text(json.dumps(state,indent=2))
cpath=root/'prepared/config-routed.json';config=json.loads(cpath.read_text())
assert config['DRT_OPT_ITERS']==16 and config['DRT_ANTENNA_REPAIR_ITERS']==3
assert config['DIODE_CELL']=='sg13g2_antennanp/A'
P('out').mkdir(exist_ok=True)
P('out/recovery-input-proof.json').write_text(json.dumps({'parent_run':43541234973,'native_artifact':14103417683,'odb_sha256':sha(odb),'sdc_sha256':sha(sdc),'config_sha256':sha(cpath),'config_changed':False,'stale_metrics_removed':True,'scope':'Resume checkpoint test only; fresh route/antenna and STA required'},indent=2))
