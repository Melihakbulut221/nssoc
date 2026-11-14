# SPDX-License-Identifier: Apache-2.0
"""Restore only the authenticated guide-stage state; no GRT regeneration."""
import pathlib,json,hashlib
P=pathlib.Path;root=P('hw/soc/out/impl-probe').resolve()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert not (root/'jumper-source').exists()
(root/'route').rename(root/'jumper-source')
step=root/'jumper-source/1-nssoc-legalizedglobalrouting'
proof=json.loads((step/'jumper-connectivity-proof.json').read_text())
screen=json.loads((step/'jumper-screen-proof.json').read_text())
assert proof['invariants_passed'] and proof['all_instance_geometry_and_status_unchanged']
assert proof['instances']==159934 and proof['top_ports']==354 and proof['changed_guide_net_count']==473
assert screen['total_reported_jumpers']==699
s=json.loads((step/'state_out.json').read_text())
state={k:v.replace('/impl-probe/route/','/impl-probe/jumper-source/') for k,v in s.items() if k in ('odb','def','nl','pnl','sdc') and v is not None}
state['odb']=str(step/'after-jumpers.odb');state['metrics']={}
assert sha(P(state['sdc']))=='1fab1c6a3d4777bca6c00e4008ea6546ef403b100a3bc480683172a0ba682511'
for k,v in state.items():
    if k!='metrics':assert P(v).is_file(),(k,v)
c=json.loads((root/'prepared/config-routed.json').read_text())
assert c['DRT_OPT_ITERS']==16 and c['DRT_ANTENNA_REPAIR_ITERS']==0
assert c['DIODE_CELL']=='sg13g2_antennanp/A'
guide=step/'after-jumpers.guide';assert guide.is_file()
(root/'route-initial.json').write_text(json.dumps(state,indent=2))
P('out').mkdir(exist_ok=True)
binding=dict(source_run=43612029407,source_native_artifact=14120788686,archive_sha256='69172352eb82e92a998843405c2db5ade521c96654e85fd9ff1fe1785e93b510',odb_sha256=sha(P(state['odb'])),guide=str(guide),guide_sha256=sha(guide),state_views={k:dict(path=v,sha256=sha(P(v))) for k,v in state.items() if k!='metrics'},configuration_changes={},global_routing_repeated=False,manufacturing_approval=False)
(root/'jumper-input-proof.json').write_text(json.dumps(binding,indent=2));P('out/jumper-input-proof.json').write_text(json.dumps(binding,indent=2))
