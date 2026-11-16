import subprocess,os
assert os.environ.get('GITHUB_ACTIONS')=='true'
import hashlib,json,pathlib,tarfile,zipfile
P=pathlib.Path
import time
def api(path):return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+path]))
source_run=43863638598
source_head='9cc44d12883c192f9ab54b14908bed15d4ed3c3e'
r=api('actions/runs/'+str(source_run))
assert r['head_sha']==source_head and r['run_attempt']==1
assert r['status']=='completed' and r['conclusion']=='success', 'New FC CRC synthesis must finish successfully before boot'
artifacts=api('actions/runs/'+str(source_run)+'/artifacts')['artifacts']
for dest,name in [('source.zip','fc-crc-mainchip-source-native-'),('mapping.zip','fc-crc-mainchip-mapping-')]:
 rows=[x for x in artifacts if x['name']==name+str(source_run)]
 assert len(rows)==1
 meta=rows[0];assert not meta['expired'] and meta['workflow_run']['head_sha']==source_head
 assert meta['workflow_run']['id']==source_run and meta['digest'].startswith('sha256:') and len(meta['digest'])==71
 with P(dest).open('xb')as stream:subprocess.run(['gh','api','repos/Melihakbulut221/nssoc/actions/artifacts/'+str(meta['id'])+'/zip'],stdout=stream,check=True)
 assert 'sha256:'+hashlib.sha256(P(dest).read_bytes()).hexdigest()==meta['digest']
with zipfile.ZipFile('mapping.zip') as z:report=json.loads(z.read('mapping.json'))
assert report['source_head']=='9cc44d12883c192f9ab54b14908bed15d4ed3c3e' and report['registered_bit_count']==26
assert report['rx_cursor_local_reset_enabled'] and report['rx_local_lane_next_enabled']
assert report['configuration']['SOC_PCIE_RX_LOCAL_LANE_NEXT']=='1'
assert report['inputs']['hw/soc/rtl/pcie/soc_pcie_rx_credit.v']=='a83699c6311ba0ac6414060f68699ee29510bf5ed99fee64f92168546bf16223'
assert report['crc_select_enabled'] and len(report['cached_eop_register'])==1
assert report['ack_stale_prefix_enabled'] and report['configuration']['SOC_PCIE_ACK_STALE_PREFIX']=='1'
assert report['inputs']['hw/soc/rtl/pcie/soc_pcie_replay_tx.v']=='0833d4a4126272253fd0cd35e7eca118c163c435a803ef32930f61f16948f554'
assert report['rx_dllp_last_compare_enabled'] and report['configuration']['SOC_PCIE_RX_DLLP_LAST_COMPARE']=='1'
assert sum(report['macros'].values())==20 and report['macros']['RM_IHPSG13_2P_256x16_c2_bm_bist']==16
assert report['accepted'] is False and report['mapped_boot_passed'] is False
assert len(report['outputs'])>=63
assert report['status']=='MAPPED_FC_CRC_SNAPSHOT_MAINCHIP_REQUIRES_NEW_BOOT_AND_PHYSICAL_VALIDATION'
assert len(report['credit_crc_registers'])==4
assert report['inputs']['hw/soc/rtl/pcie/soc_pcie_credit_tx.v']=='35b0b71994d793797c86f074f4d0d774789d64cf986049c5aec254b29121c530'
assert report['configuration']['SOC_PCIE_RX_EOP_FLAGS']=='1' and report['configuration'].get('SOC_PCIE_RX_COUNT_FLAGS','0')=='0'
assert len(report['rx_eop_registers'])==2
assert report['ack_delta_group_prefix_enabled']
assert report['ack_delta_qualification']['current_source_sha256']==report['inputs']['hw/soc/rtl/pcie/soc_pcie_replay_tx.v']
assert report['source_binding']['all_files_unchanged']
assert report['inputs']['hw/soc/rtl/pcie/soc_pcie_fc_tx.v']=='1360051e88dc8c95fb7f3e896d47621b871887aa811d6dd2990c2959e4240f23'
subprocess.run(['python3','scripts/require_fc_crc_snapshot_qualification.py'],check=True)
fc=json.loads(P('out/fc-crc-snapshot-qualification.json').read_text())
assert fc['passed'] and fc['candidate_sha256']==report['inputs']['hw/soc/rtl/pcie/soc_pcie_fc_tx.v']
for f,h in report['source_binding']['before'].items():
 assert hashlib.sha256(P(f).read_bytes()).hexdigest()==h,(f,'producer source mismatch')
peer=report['peer_ready_qualification']
assert peer['current']['candidate_sha256']==report['inputs']['hw/soc/rtl/pcie/soc_pcie_credit_tx.v']
assert report['full_phy_accepted'] is False and report['final_timing_complete'] is False
assert len({c['q'][0]for c in report['rx_eop_registers']})==2
eop=report['eop_qualification'];assert eop['source_sha256']==report['inputs']['hw/soc/rtl/pcie/soc_pcie_rx_credit.v'] and eop['cycles']==2400000 and len(eop['traffic_cases'])==8 and eop['physical_accepted'] is False
assert all(c['passed']for c in eop['formal']['cases']) and len(eop['formal']['cases'])==2 and len(eop['lemmas'])==6 and all(c['passed']for c in eop['lemmas'])
for flag in ('SOC_PCIE_CREDIT_DATA_SIGN_REG','SOC_PCIE_CRC_UPPER_COMPARE_REG','SOC_PCIE_CREDIT_PICK','SOC_PCIE_SEQ_RX_REG'):assert report['configuration'][flag]=='1'
q=report['credit_crc_qualification'];assert q['credit_formal']['passed'] and q['credit_mutation']['detected'] and all(c['passed']for c in q['crc_composition']['cases'])
for file,key in [('hw/soc/rtl/pcie/soc_pcie_credit_tx.v','credit_source_sha256'),('hw/soc/rtl/pcie/soc_pcie_lcrc_rx.v','crc_source_sha256')]:assert hashlib.sha256(P(file).read_bytes()).hexdigest()==q[key]
with zipfile.ZipFile('source.zip') as z:
 assert z.namelist()==['build.tgz'];z.extract('build.tgz')
root=P('hw/soc/out/corrpre-pcie-mbist-native-boot');seen=set()
with tarfile.open('build.tgz') as tar:
 for m in tar:
  path=P(m.name);assert not path.is_absolute() and '..' not in path.parts
  assert path==root or root in path.parents
  if m.isdir():continue
  assert m.isfile();rel=str(path.relative_to(root));assert rel in report['outputs'] and rel not in seen;seen.add(rel)
  data=tar.extractfile(m).read();assert hashlib.sha256(data).hexdigest()==report['outputs'][rel]
  assert not path.exists();path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data)
assert seen==set(report['outputs'])
for f,h in report['inputs'].items():assert hashlib.sha256(P(f).read_bytes()).hexdigest()==h
P('out').mkdir(exist_ok=True);P('out/source-binding.json').write_text(json.dumps({'source_run':43863638598,'source_head':report['source_head'],'authenticated_files':len(seen),'netlist_sha256':report['outputs']['synthesis/soc_top.netlist.v'],'mapped_json_sha256':report['outputs']['synthesis/soc_top.mapped.json'],'artifact_bindings':[{k:v for k,v in x.items() if k in ('id','name','digest','workflow_run')} for x in artifacts if x['name'] in ['fc-crc-mainchip-source-native-'+str(source_run),'fc-crc-mainchip-mapping-'+str(source_run)]],'accepted':False},indent=2))

# Bind reported register evidence to this exact restored map, not old cell IDs.
module=json.loads((root/'synthesis/soc_top.mapped.json').read_text())['modules']['soc_top']
for cell in report['rx_eop_registers']:
 actual=module['cells'][cell['name']]
 assert actual['type']==cell['type'] and actual['connections']['Q']==cell['q']
 assert actual['connections']['CLK']==module['ports']['pcie_clk_i']['bits']

# Check every reported credit/CRC register against the freshly restored map.
for name, evidence in report['credit_crc_registers'].items():
 actual=module['cells'][evidence['cell']]
 assert actual['type']==evidence['type']
 assert actual['connections']['Q']==[evidence['bit']]
 assert module['netnames'][name]['bits']==[evidence['bit']]
 assert actual['connections']['CLK']==module['ports']['pcie_clk_i']['bits']
assert len({v['bit'] for v in report['credit_crc_registers'].values()})==4
assert any(n.endswith('.peer_ready') for n in report['credit_crc_registers'])
assert len(module['cells'])==report['cells']
actual_macros={}
for c in module['cells'].values():
 if c['type'].startswith('RM_IHPSG13'):actual_macros[c['type']]=actual_macros.get(c['type'],0)+1
assert actual_macros==report['macros']
