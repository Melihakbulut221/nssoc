import subprocess,os
assert os.environ.get('GITHUB_ACTIONS')=='true'
import hashlib,json,pathlib,tarfile,zipfile
P=pathlib.Path
import time
def api(path):return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+path]))
source_run=43774645625
source_head='f20f16a05dbf5eab3f8263c4c566857b3d7db4a5'
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
for dest,name in [('source.zip','queue-count-rechecked-native-'),('mapping.zip','queue-count-rechecked-mapping-')]:
 rows=[x for x in artifacts if x['name']==name+str(source_run)]
 assert len(rows)==1
 meta=rows[0];assert not meta['expired'] and meta['workflow_run']['head_sha']==source_head
 assert meta['workflow_run']['id']==source_run and meta['digest'].startswith('sha256:') and len(meta['digest'])==71
 with P(dest).open('xb')as stream:subprocess.run(['gh','api','repos/Melihakbulut221/nssoc/actions/artifacts/'+str(meta['id'])+'/zip'],stdout=stream,check=True)
 assert 'sha256:'+hashlib.sha256(P(dest).read_bytes()).hexdigest()==meta['digest']
with zipfile.ZipFile('mapping.zip') as z:report=json.loads(z.read('mapping.json'))
assert report['source_head']=='f20f16a05dbf5eab3f8263c4c566857b3d7db4a5' and report['registered_bit_count']==26
assert report['rx_cursor_local_reset_enabled'] and report['rx_local_lane_next_enabled']
assert report['configuration']['SOC_PCIE_RX_LOCAL_LANE_NEXT']=='1'
assert report['inputs']['hw/soc/rtl/pcie/soc_pcie_rx_credit.v']=='ea123da56f450bdde9183b43083ca6c8df3086494feff54be7bf9a201ecbc391'
assert report['crc_select_enabled'] and len(report['cached_eop_register'])==1
assert report['ack_stale_prefix_enabled'] and report['configuration']['SOC_PCIE_ACK_STALE_PREFIX']=='1'
assert report['inputs']['hw/soc/rtl/pcie/soc_pcie_replay_tx.v']=='f5634cd4692abde4aa576aa11e392c4ef5c2787a35962aeec0ac444340ec4c7a'
assert report['rx_dllp_last_compare_enabled'] and report['configuration']['SOC_PCIE_RX_DLLP_LAST_COMPARE']=='1'
assert sum(report['macros'].values())==20 and report['macros']['RM_IHPSG13_2P_256x16_c2_bm_bist']==16
assert report['accepted'] is False and report['mapped_boot_passed'] is False
assert len(report['outputs'])>=63
assert report['status']=='MAPPED_ACK_PREFIX_RX_CURSOR_CRC_SELECT_EOP_CHIP_REQUIRES_GATE_BOOT_AND_PHYSICAL_IMPLEMENTATION'
assert report['outputs']['synthesis/soc_top.netlist.v']=='20abf0b03df52c83d6ce5771f24615807c951a2ccbf809b74c9ae72aeb6e79e8'
assert report['outputs']['synthesis/soc_top.mapped.json']=='5edb96033cc42e68a36f9be71ba7efd3b68f8c03fb4996f3dd9f170a4a9a66c7'
assert report['cells']==116107 and len(report['credit_crc_registers'])==3
for flag in ('SOC_PCIE_CREDIT_DATA_SIGN_REG','SOC_PCIE_CRC_UPPER_COMPARE_REG','SOC_PCIE_CREDIT_PICK','SOC_PCIE_SEQ_RX_REG'):assert report['configuration'][flag]=='1'
q=report['credit_crc_qualification'];assert q['credit_formal']['passed'] and q['credit_mutation']['detected'] and all(c['passed']for c in q['crc_composition']['cases'])
for file,key in [('hw/soc/rtl/pcie/soc_pcie_credit_tx.v','credit_source_sha256'),('hw/soc/rtl/pcie/soc_pcie_lcrc_rx.v','crc_source_sha256')]:assert hashlib.sha256(P(file).read_bytes()).hexdigest()==q[key]
expected_artifacts={14185698025:'sha256:da38dd0e22d69901c1a884d02fb335a41fab81bdc74a7a9649763515dec1e065',14186340040:'sha256:879b57f74835f8308bb94e68bd52c415168bdab4c44876fe1d214416598189a5'}
assert all(any(a['id']==i and a['digest']==h for a in artifacts)for i,h in expected_artifacts.items())
assert report['configuration']['SOC_PCIE_RX_COUNT_FLAGS']=='1'
assert len(report['queue_count_registers'])==3
n=report['native_producer']
assert n['run']==43772035360 and n['source_head']=='a233897f18e3eae27b130cdf3cf4d444802f3f01'
assert n['original_run_conclusion']=='failure' and n['resynthesized'] is False
assert n['native_archive_sha256']=='b9e64f1c5f4934483d7dda8495b9462ce952b6e0acc4769e6ac789d25b48028b'
assert n['before_hashes']['synthesis/soc_top.netlist.v']==report['outputs']['synthesis/soc_top.netlist.v']
q=report['queue_count_qualification']
assert q['cycles']==2400000 and q['mutation']['detected'] and all(c['passed'] for c in q['formal']['cases']) and all(c['passed'] for c in q['lemmas'])
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
P('out').mkdir(exist_ok=True);P('out/source-binding.json').write_text(json.dumps({'source_run':43774645625,'source_head':report['source_head'],'authenticated_files':len(seen),'netlist_sha256':report['outputs']['synthesis/soc_top.netlist.v'],'mapped_json_sha256':report['outputs']['synthesis/soc_top.mapped.json'],'artifact_bindings':[{k:v for k,v in x.items() if k in ('id','name','digest','workflow_run')} for x in artifacts if x['name'] in ['queue-count-rechecked-native-'+str(source_run),'queue-count-rechecked-mapping-'+str(source_run)]],'native_producer':report['native_producer'],'accepted':False},indent=2))
