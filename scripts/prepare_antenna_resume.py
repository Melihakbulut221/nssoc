# SPDX-License-Identifier: Apache-2.0
"""Recover completed CRC route and alter repair method, never timing constraints."""
import hashlib,json,pathlib,zipfile,tarfile,io,re
P=pathlib.Path;root=P('hw/soc/out/impl-probe').resolve()
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
odb=root/'recovered-route/3-openroad-detailedrouting/drt-run-0/soc_top.odb'
sdc=root/'recovered-route/1-openroad-detailedplacement/soc_top.sdc'
assert sha(odb)=='9adefc224ed62b8e661cdf4c2ae009f4e9910e5e2c5b848156464eb0fdfca40c'
assert sha(sdc)=='1fab1c6a3d4777bca6c00e4008ea6546ef403b100a3bc480683172a0ba682511'
s=json.loads((root/'recovered-route/3-openroad-detailedrouting/state_in.json').read_text())
state={k:s[k].replace('/impl-probe/route/','/impl-probe/recovered-route/') for k in ('nl','pnl')}
blob=P('legalized.zip').read_bytes();assert hashlib.sha256(blob).hexdigest()=='d67191c33b2015eb39b097946904044e564990b12fddcd0c6d88f643d9ada340'
z=zipfile.ZipFile(io.BytesIO(blob));assert z.namelist()==['retry-buf4-native.tgz']
with tarfile.open(fileobj=io.BytesIO(z.read('retry-buf4-native.tgz')),mode='r:gz') as t:
 data=t.extractfile('native/buf4-legalized-unrouted.odb').read()
assert hashlib.sha256(data).hexdigest()=='972d9676e2f3af51fda24b2411048b60383e9dfffdb92cd8550a9caf9c53e0b9'
odb=root/'retry-buf4-legalized.odb';odb.write_bytes(data)
# Original logical connectivity is preserved by the native whole-chip audit.
# Only the selected positive-buffer master changes; retain independent reference
# pin order and text byte-for-byte, with an exact reversible replacement.
reference_changes={}
for view in ('nl','pnl'):
 original_path=P(state[view]);before_text=original_path.read_text()
 pattern=r'(?m)^(\s*)sg13g2_buf_1(\s+\\?place31551\s*\()'
 changed_text,count=re.subn(pattern,r'\1sg13g2_buf_4\2',before_text)
 assert count==1,('Expected original driver exactly once',view,count)
 inverse=r'(?m)^(\s*)sg13g2_buf_4(\s+\\?place31551\s*\()'
 restored,n=re.subn(inverse,r'\1sg13g2_buf_1\2',changed_text)
 assert n==1 and restored==before_text
 target=root/('retry-buf4-'+view+'.v');target.write_text(changed_text)
 reference_changes[view]={'original_path':str(original_path),'original_sha256':sha(original_path),'new_path':str(target),'new_sha256':sha(target),'exact_reversible_master_replacement':True}
 state[view]=str(target)
state.update(odb=str(odb),sdc=str(sdc),metrics={})
for k,v in state.items():
 if k!='metrics':assert P(v).is_file(),(k,v)
(root/'route-initial.json').write_text(json.dumps(state,indent=2))
p=root/'prepared/config-routed.json';c=json.loads(p.read_text());before=dict(c)
assert c['DRT_OPT_ITERS']==16 and c['DRT_ANTENNA_REPAIR_ITERS']==5
assert c['DIODE_CELL']=='sg13g2_antennanp/A'
c['DRT_ANTENNA_REPAIR_ITERS']=0
c['DRT_ANTENNA_REPAIR_JUMPER_ONLY']=False
c['DRT_ANTENNA_REPAIR_DIODE_ONLY']=False
changed={k:{'before':before.get(k),'after':v} for k,v in c.items() if before.get(k)!=v}
assert set(changed)<= {'DRT_ANTENNA_REPAIR_ITERS','DRT_ANTENNA_REPAIR_JUMPER_ONLY','DRT_ANTENNA_REPAIR_DIODE_ONLY'}
p.write_text(json.dumps(c,indent=2));P('out').mkdir(exist_ok=True)
P('out/recovery-input-proof.json').write_text(json.dumps({'parent_run':43561900502,'native_artifact':14107653261,'odb_sha256':sha(odb),'sdc_sha256':sha(sdc),'configuration_changes':changed,'stale_metrics_removed':True,'initial_route_skipped':False,'placement_parent_run':43609939062,'native_placement_artifact':14120090635,'reference_changes':reference_changes,'scope':'Reroute one measured overloaded buffer upsize on existing diode-legalized placement. Exactly one master replacement in independent nl/pnl; no pin or RTL changes. All original timing/antenna gates remain mandatory.','fresh_final_antenna_step':True,'manufacturing_approval':False},indent=2))
