import subprocess,os
assert os.environ.get('GITHUB_ACTIONS')=='true'
import hashlib,json,pathlib,tarfile,zipfile
P=pathlib.Path
import time
def api(path):return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+path]))
source_run=43781012464
source_head='badd72fcfe8ed59b6b9fea3c97b610f918b1d2ac'
deadline=time.monotonic()+9000
while True:
 r=api('actions/runs/'+str(source_run))
 assert r['head_sha']==source_head and r['run_attempt']==1
 if r['status']=='completed':
  assert r['conclusion']=='success',r['conclusion']
  break
 assert time.monotonic()<deadline,'Exact synthesis still pending; no acceptance'
 print('Waiting for exact qualified synthesis',source_run,flush=True);time.sleep(30)
artifacts=api('actions/runs/'+str(source_run)+'/artifacts')['artifacts']
for dest,name in [('source.zip','eop-credit-crc-mainchip-source-native-'),('mapping.zip','eop-credit-crc-mainchip-mapping-')]:
 rows=[x for x in artifacts if x['name']==name+str(source_run)]
 assert len(rows)==1
 meta=rows[0];assert not meta['expired'] and meta['workflow_run']['head_sha']==source_head
 assert meta['workflow_run']['id']==source_run and meta['digest'].startswith('sha256:') and len(meta['digest'])==71
 with P(dest).open('xb')as stream:subprocess.run(['gh','api','repos/Melihakbulut221/nssoc/actions/artifacts/'+str(meta['id'])+'/zip'],stdout=stream,check=True)
 assert 'sha256:'+hashlib.sha256(P(dest).read_bytes()).hexdigest()==meta['digest']
with zipfile.ZipFile('mapping.zip') as z:report=json.loads(z.read('mapping.json'))
assert report['source_head']=='badd72fcfe8ed59b6b9fea3c97b610f918b1d2ac' and report['registered_bit_count']==26
assert report['rx_cursor_local_reset_enabled'] and report['rx_local_lane_next_enabled']
assert report['configuration']['SOC_PCIE_RX_LOCAL_LANE_NEXT']=='1'
assert report['inputs']['hw/soc/rtl/pcie/soc_pcie_rx_credit.v']=='a83699c6311ba0ac6414060f68699ee29510bf5ed99fee64f92168546bf16223'
assert report['crc_select_enabled'] and len(report['cached_eop_register'])==1
assert report['ack_stale_prefix_enabled'] and report['configuration']['SOC_PCIE_ACK_STALE_PREFIX']=='1'
assert report['inputs']['hw/soc/rtl/pcie/soc_pcie_replay_tx.v']=='f5634cd4692abde4aa576aa11e392c4ef5c2787a35962aeec0ac444340ec4c7a'
assert report['rx_dllp_last_compare_enabled'] and report['configuration']['SOC_PCIE_RX_DLLP_LAST_COMPARE']=='1'
assert sum(report['macros'].values())==20 and report['macros']['RM_IHPSG13_2P_256x16_c2_bm_bist']==16
assert report['accepted'] is False and report['mapped_boot_passed'] is False
assert len(report['outputs'])>=63
assert report['status']=='MAPPED_ACK_PREFIX_RX_CURSOR_CRC_SELECT_EOP_CHIP_REQUIRES_GATE_BOOT_AND_PHYSICAL_IMPLEMENTATION'
assert report['outputs']['synthesis/soc_top.netlist.v']=='5c4691226686cbdf8e6a34546421a2d14dd735b8eaeb17141a8122b6032bb3b3'
assert report['outputs']['synthesis/soc_top.mapped.json']=='50b076e3cfa25cd0314baa0c3530f6761d047ed9dfd77355ff2a1248dabc0d04'
assert report['cells']==115358 and len(report['credit_crc_registers'])==3
assert report['configuration']['SOC_PCIE_RX_EOP_FLAGS']=='1' and report['configuration'].get('SOC_PCIE_RX_COUNT_FLAGS','0')=='0'
assert len(report['rx_eop_registers'])==2 and {c['name']for c in report['rx_eop_registers']}=={'$auto$ff.cc:337:slice$365945','$auto$ff.cc:337:slice$365946'}
assert len({c['q'][0]for c in report['rx_eop_registers']})==2
eop=report['eop_qualification'];assert eop['source_sha256']==report['inputs']['hw/soc/rtl/pcie/soc_pcie_rx_credit.v'] and eop['cycles']==2400000 and len(eop['traffic_cases'])==8 and eop['physical_accepted'] is False
assert all(c['passed']for c in eop['formal']['cases']) and len(eop['formal']['cases'])==2 and len(eop['lemmas'])==6 and all(c['passed']for c in eop['lemmas'])
for flag in ('SOC_PCIE_CREDIT_DATA_SIGN_REG','SOC_PCIE_CRC_UPPER_COMPARE_REG','SOC_PCIE_CREDIT_PICK','SOC_PCIE_SEQ_RX_REG'):assert report['configuration'][flag]=='1'
q=report['credit_crc_qualification'];assert q['credit_formal']['passed'] and q['credit_mutation']['detected'] and all(c['passed']for c in q['crc_composition']['cases'])
for file,key in [('hw/soc/rtl/pcie/soc_pcie_credit_tx.v','credit_source_sha256'),('hw/soc/rtl/pcie/soc_pcie_lcrc_rx.v','crc_source_sha256')]:assert hashlib.sha256(P(file).read_bytes()).hexdigest()==q[key]
expected_artifacts={14189117157:'sha256:4f1812f814cc6b688250e947697f0898ff8255b74029ce31cfbfe10a426fd2fd',14188972587:'sha256:a985e4b2448370e4da2d5c11606e5785038163fa1fb0a5c0e13d4e0e2fa2fc11'}
assert all(any(a['id']==i and a['digest']==h for a in artifacts)for i,h in expected_artifacts.items())
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
P('out').mkdir(exist_ok=True);P('out/source-binding.json').write_text(json.dumps({'source_run':43781012464,'source_head':report['source_head'],'authenticated_files':len(seen),'netlist_sha256':report['outputs']['synthesis/soc_top.netlist.v'],'mapped_json_sha256':report['outputs']['synthesis/soc_top.mapped.json'],'artifact_bindings':[{k:v for k,v in x.items() if k in ('id','name','digest','workflow_run')} for x in artifacts if x['name'] in ['eop-credit-crc-mainchip-source-native-'+str(source_run),'eop-credit-crc-mainchip-mapping-'+str(source_run)]],'accepted':False},indent=2))
