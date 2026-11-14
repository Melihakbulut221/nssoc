# SPDX-License-Identifier: Apache-2.0
"""Actual full-chip native comparer identity/open/device-size controls, cloud only."""
import pathlib,json,hashlib,tarfile,zipfile,io,sys,time,collections
import klayout.db as db
def value(obj,key):
 v=getattr(obj,key);return v() if callable(v) else v
P=pathlib.Path;case=sys.argv[1];assert case in ['identity','signal_open','sram_mos_width','inspect']
out=P('out');out.mkdir();derived=out/'derived';derived.mkdir()
def sha(p):
 with P(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
assert sha('native.zip')=='fd250afa9a2c55ef266149c583d76256dd8dcdd9d5f043cfd892a7043e15979b'
with zipfile.ZipFile('native.zip') as z:
 assert z.namelist()==['full-chip-lvs-native.tgz']
 with tarfile.open(fileobj=io.BytesIO(z.read(z.namelist()[0])),mode='r:gz') as t:
  matches=[m for m in t.getmembers() if m.name=='native/full-chip.lvsdb'];assert len(matches)==1 and matches[0].isfile()
  with t.extractfile(matches[0]) as src,(out/'full-chip.lvsdb').open('wb') as dst:
   import shutil
   shutil.copyfileobj(src,dst)
report=out/'full-chip.lvsdb';digest=sha(report);assert digest=='3ddd851b8f0d80050bc97aabb6576836eb1d20ef41d0184c239f7840b479ca22'
lvs=db.LayoutVsSchematic();lvs.read(str(report));layout=lvs.netlist();reference=lvs.reference
# Bind only original circuit name pairs, never original net/pin matches.
pairs=[(p.first().name,p.second().name,str(p.status())) for p in lvs.xref().each_circuit_pair()]
assert len(pairs)==108 and all(s=='Match' for a,b,s in pairs)
top=reference.circuit_by_name('SOC_TOP');assert top is not None
if case=='inspect':
 info={'status':'STORED_NETLIST_STRUCTURE_INVENTORY','accepted':False}
 for side,nl in [('layout',layout),('reference',reference)]:
  tops=[c for c in nl.each_circuit() if c.name.lower()=='soc_top'];assert len(tops)==1;c=tops[0]
  subs=list(c.each_subcircuit());devs=list(c.each_device());classes=list(nl.each_device_class())
  info[side]={'top_subcircuits':len(subs),'top_devices':len(devs),'top_pins':[value(p,'name') for p in c.each_pin()],'subcircuits_first':[{'name':x.name,'type':x.circuit_ref().name,'pins':[value(p,'name') for p in x.circuit_ref().each_pin()]} for x in subs[:3]],'devices_first':[{'name':d.name,'class':d.device_class().name} for d in devs[:3]],'classes':[{'name':dc.name,'python_type':str(type(dc)),'parameters':[{'name':value(p,'name'),'id':value(p,'id')} for p in dc.parameter_definitions()]} for dc in classes]}
 (derived/'inventory.json').write_text(json.dumps(info,indent=2));sys.exit(0)

mutation=None
if case=='signal_open':
 for sub in top.each_subcircuit():
  if sub.circuit_ref().name.upper().startswith('SG13G2_'):
   candidates=[p for p in sub.circuit_ref().each_pin() if value(p,'name')=='A']
   if not candidates:continue
   pin=candidates[0];old=sub.net_for_pin(pin.id())
   if old is None or old.name.upper() in ['VPWR','VGND']:continue
   fresh=top.create_net('FAULT_CONTROL_OPEN_INPUT')
   sub.connect_pin(pin.id(),fresh)
   mutation={'kind':'single_top_cell_input_disconnected','instance':sub.name,'cell':sub.circuit_ref().name,'pin':value(pin,'name'),'old_net':old.name,'new_net':fresh.name}
   break
 assert mutation is not None
elif case=='sram_mos_width':
 c=reference.circuit_by_name('NSDP_RM_IHPSG13_256X16_C2_2P_BITKIT_16X2_SRAM');assert c is not None
 for dev in c.each_device():
  if 'nmos' not in dev.device_class().name.lower():continue
  old=dev.parameter('W');assert old>0
  dev.set_parameter('W',old*1.5)
  mutation={'kind':'one_DP_SRAM_MOS_width','circuit':c.name,'device':dev.name,'model':dev.device_class().name,'old_width':old,'new_width':dev.parameter('W')};break
 assert mutation is not None
comparer=db.NetlistComparer();comparer.max_branch_complexity=2048
for a,b,status in pairs:comparer.same_circuits(layout.circuit_by_name(a),reference.circuit_by_name(b))
start=time.monotonic();matched=lvs.compare(comparer);ports=lvs.flag_missing_ports(top) if matched else False
rows=[{'layout':p.first().name if p.first() is not None else None,'reference':p.second().name if p.second() is not None else None,'status':str(p.status())} for p in lvs.xref().each_circuit_pair()]
actual=bool(matched and ports);expected=case=='identity'
result={'case':case,'native_comparison_completed':True,'compare_returned':matched,'missing_ports_check_passed':ports,'accepted':actual,'expected_acceptance':expected,'control_passed':actual==expected,'mutation':mutation,'circuit_status_counts':dict(collections.Counter(x['status'] for x in rows)),'nonmatching':[x for x in rows if x['status']!='Match'],'elapsed_seconds':time.monotonic()-start,'original_database_sha256':digest,'original_database_unchanged':sha(report)==digest,'scope':'Full stored transistor graphs, original circuit-name correspondence only. No original net/pin matching reused, no blackboxes or device removal. Controlled reference mutation in memory; original extracted database unchanged. Not new layout or manufacturing acceptance.'}
(derived/'result.json').write_text(json.dumps(result,indent=2));print(json.dumps(result));assert result['control_passed'] and result['original_database_unchanged']
