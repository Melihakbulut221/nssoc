import subprocess,os
assert os.environ.get('GITHUB_ACTIONS')=='true'
import hashlib,json,pathlib,tarfile,zipfile
P=pathlib.Path
import time
def api(path):return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+path]))
source_run=43768772862
source_head='e59e693a0a2a86d4e0edb71cf3c8ae4e07c05a88'
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
for dest,name in [('source.zip','credit-crc-mainchip-source-native-'),('mapping.zip','credit-crc-mainchip-mapping-')]:
 rows=[x for x in artifacts if x['name']==name+str(source_run)]
 assert len(rows)==1
 meta=rows[0];assert not meta['expired'] and meta['workflow_run']['head_sha']==source_head
 assert meta['workflow_run']['id']==source_run and meta['digest'].startswith('sha256:') and len(meta['digest'])==71
 with P(dest).open('xb')as stream:subprocess.run(['gh','api','repos/Melihakbulut221/nssoc/actions/artifacts/'+str(meta['id'])+'/zip'],stdout=stream,check=True)
 assert 'sha256:'+hashlib.sha256(P(dest).read_bytes()).hexdigest()==meta['digest']
with zipfile.ZipFile('mapping.zip') as z:report=json.loads(z.read('mapping.json'))
assert report['source_head']=='e59e693a0a2a86d4e0edb71cf3c8ae4e07c05a88' and report['registered_bit_count']==26
assert report['rx_cursor_local_reset_enabled'] and report['rx_local_lane_next_enabled']
assert report['configuration']['SOC_PCIE_RX_LOCAL_LANE_NEXT']=='1'
assert report['inputs']['hw/soc/rtl/pcie/soc_pcie_rx_credit.v']=='865d687a272faf4a5077f79af21ace3b4afbe5085b640dd20f3512c8a43ff7d5'
assert report['crc_select_enabled'] and len(report['cached_eop_register'])==1
assert report['ack_stale_prefix_enabled'] and report['configuration']['SOC_PCIE_ACK_STALE_PREFIX']=='1'
assert report['inputs']['hw/soc/rtl/pcie/soc_pcie_replay_tx.v']=='f5634cd4692abde4aa576aa11e392c4ef5c2787a35962aeec0ac444340ec4c7a'
assert report['rx_dllp_last_compare_enabled'] and report['configuration']['SOC_PCIE_RX_DLLP_LAST_COMPARE']=='1'
assert sum(report['macros'].values())==20 and report['macros']['RM_IHPSG13_2P_256x16_c2_bm_bist']==16
assert report['accepted'] is False and report['mapped_boot_passed'] is False
assert len(report['outputs'])>=63
assert report['status']=='MAPPED_ACK_PREFIX_RX_CURSOR_CRC_SELECT_EOP_CHIP_REQUIRES_GATE_BOOT_AND_PHYSICAL_IMPLEMENTATION'
assert report['outputs']['synthesis/soc_top.netlist.v']=='15f996437ae5c74079fcb77f48fc8fe55b8517f784744e9c0b9a609e562f00fc'
assert report['outputs']['synthesis/soc_top.mapped.json']=='13f96b84486caff79ce53b1e183d98443875208b26d962dfe9d95e62878d40d5'
assert report['cells']==115594 and len(report['credit_crc_registers'])==3
for flag in ('SOC_PCIE_CREDIT_DATA_SIGN_REG','SOC_PCIE_CRC_UPPER_COMPARE_REG','SOC_PCIE_CREDIT_PICK','SOC_PCIE_SEQ_RX_REG'):assert report['configuration'][flag]=='1'
q=report['credit_crc_qualification'];assert q['credit_formal']['passed'] and q['credit_mutation']['detected'] and all(c['passed']for c in q['crc_composition']['cases'])
for file,key in [('hw/soc/rtl/pcie/soc_pcie_credit_tx.v','credit_source_sha256'),('hw/soc/rtl/pcie/soc_pcie_lcrc_rx.v','crc_source_sha256')]:assert hashlib.sha256(P(file).read_bytes()).hexdigest()==q[key]
expected_artifacts={14183762961:'sha256:1b24d8847825b51f74dcc37a61b328d06a872cdddbbafc98351aee12b1a54b49',14183269751:'sha256:fd62b50ec843689ffd0fe1dca6ae0111db8024699fe192205fb1f8b6f96f8209'}
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
P('out').mkdir(exist_ok=True);P('out/source-binding.json').write_text(json.dumps({'source_run':43768772862,'source_head':report['source_head'],'authenticated_files':len(seen),'netlist_sha256':report['outputs']['synthesis/soc_top.netlist.v'],'mapped_json_sha256':report['outputs']['synthesis/soc_top.mapped.json'],'artifact_bindings':[{k:v for k,v in x.items() if k in ('id','name','digest','workflow_run')} for x in artifacts if x['name'] in ['credit-crc-mainchip-source-native-'+str(source_run),'credit-crc-mainchip-mapping-'+str(source_run)]],'accepted':False},indent=2))
