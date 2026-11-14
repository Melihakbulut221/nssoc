# SPDX-License-Identifier: Apache-2.0
"""Recover completed CRC route and alter repair method, never timing constraints."""
import hashlib,json,pathlib
P=pathlib.Path;root=P('hw/soc/out/impl-probe').resolve()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
odb=root/'recovered-route/3-openroad-detailedrouting/drt-run-0/soc_top.odb'
sdc=root/'recovered-route/1-openroad-detailedplacement/soc_top.sdc'
assert sha(odb)=='9adefc224ed62b8e661cdf4c2ae009f4e9910e5e2c5b848156464eb0fdfca40c'
assert sha(sdc)=='1fab1c6a3d4777bca6c00e4008ea6546ef403b100a3bc480683172a0ba682511'
s=json.loads((root/'recovered-route/3-openroad-detailedrouting/state_in.json').read_text())
state={k:s[k].replace('/impl-probe/route/','/impl-probe/recovered-route/') for k in ('nl','pnl')}
state.update(odb=str(odb),sdc=str(sdc),metrics={})
for k,v in state.items():
 if k!='metrics':assert P(v).is_file(),(k,v)
(root/'route-initial.json').write_text(json.dumps(state,indent=2))
p=root/'prepared/config-routed.json';c=json.loads(p.read_text());before=dict(c)
assert c['DRT_OPT_ITERS']==16 and c['DRT_ANTENNA_REPAIR_ITERS']==5
assert c['DIODE_CELL']=='sg13g2_antennanp/A'
c['DRT_ANTENNA_REPAIR_JUMPER_ONLY']=False
c['DRT_ANTENNA_REPAIR_DIODE_ONLY']=True
changed={k:{'before':before.get(k),'after':v} for k,v in c.items() if before.get(k)!=v}
assert set(changed)<= {'DRT_ANTENNA_REPAIR_JUMPER_ONLY','DRT_ANTENNA_REPAIR_DIODE_ONLY'}
p.write_text(json.dumps(c,indent=2));P('out').mkdir(exist_ok=True)
P('out/recovery-input-proof.json').write_text(json.dumps({'parent_run':43561900502,'native_artifact':14107653261,'odb_sha256':sha(odb),'sdc_sha256':sha(sdc),'configuration_changes':changed,'stale_metrics_removed':True,'initial_route_skipped':True,'diagnostic_only_no_final_antenna_acceptance':True,'manufacturing_approval':False},indent=2))
