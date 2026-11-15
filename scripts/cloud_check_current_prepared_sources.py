# SPDX-License-Identifier: Apache-2.0
"""Test newly published replay with unchanged structural gates and stale-hash refusal."""
import os,sys,subprocess,json,hashlib,zipfile,xml.etree.ElementTree as ET,traceback,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'prepared-current-guards';OUT.mkdir()
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
r=dict(status='RUNNING',accepted=False,full_phy_accepted=False,source_head=os.environ.get('GITHUB_SHA'))
def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
try:
 assert os.environ.get('GITHUB_ACTIONS')=='true' and shutil.which('yosys')
 run=api('actions/runs/43717961699');assert run['conclusion']=='success' and run['head_sha']=='374b0cc6dd4548c9f7f3d79d0a22985c65a5d695' and run['run_attempt']==1
 artifacts=api('actions/runs/43717961699/artifacts')['artifacts'];entries=[x for x in artifacts if x['name']=='prepared-source-publication-derived-43717961699'];assert len(entries)==1
 artifact=entries[0];assert not artifact['expired'] and artifact['workflow_run']['head_sha']==run['head_sha']
 archive=OUT/'published-derived.zip'
 with archive.open('xb')as f:subprocess.run(['gh','api',P+'actions/artifacts/'+str(artifact['id'])+'/zip'],stdout=f,check=True,timeout=120)
 assert 'sha256:'+sha(archive)==artifact['digest']
 with zipfile.ZipFile(archive)as z:
  receipt=json.loads(z.read('result.json'));assert receipt['status']=='PUBLISHED_AND_REDOWNLOADED_HASH_VERIFIED_NOT_YET_CI_INTEGRATED'
  assert receipt['producer_run']==43716663208 and receipt['producer_head']=='589540e861dbd006d98f1de7622c0079ebd921ad'
  name='prepared-sources-current-20261115.json';raw=z.read(name);assert hashlib.sha256(raw).hexdigest()==receipt['metadata_sha256']
  metadata=ROOT/'docs/evidence'/name;assert not metadata.exists();metadata.write_bytes(raw)
  record=json.loads(raw);assert record['archive']['sha256']=='08e629ada48eb210c3dc32a964b8e10864844d7e8b8f2a697862e23ba4d9a4b4'
  assert record['release_assets']['release_tag']=='prepared-sources-20261115-43716663208'
  notice=record['component_notices'];data=z.read(notice['file']);assert hashlib.sha256(data).hexdigest()==notice['sha256'];dest=metadata.parent/notice['file'];assert not dest.exists();dest.write_bytes(data)
  for path,digest in record['transform_sha256'].items():assert sha(ROOT/path)==digest
 tracked=subprocess.check_output(['git','ls-files','-z'],cwd=ROOT).decode().split('\0');protected={f:sha(ROOT/f)for f in tracked if f and (ROOT/f).is_file()}
 tests=['sw/tests/test_soc_regfile_guards.py::test_upstreams_own_file_measures_the_data_flip_flops_only','sw/tests/test_soc_regfile_guards.py::test_the_substitute_declares_upstreams_ports_in_upstreams_order','sw/tests/test_soc_regfile_guards.py::test_the_substitute_accepts_every_parameter_ibex_top_overrides','sw/tests/test_soc_synthesis_guards.py::test_the_ibex_top_patch_applies_to_the_pinned_output','sw/tests/test_soc_synthesis_guards.py::test_the_whole_soc_elaborates_as_one_design','sw/tests/test_no_orphan_modules.py::test_register_file_external_entry_contract']
 results=[]
 for profile in ['base','full']:
  xml=OUT/(profile+'.xml');log=OUT/(profile+'.log')
  with log.open('w')as stream:code=subprocess.call([sys.executable,'-m','pytest','-q','--junitxml='+str(xml),*tests],cwd=ROOT,env={**os.environ,'SOC_INTERFACE_PROFILE':profile},stdout=stream,stderr=subprocess.STDOUT)
  rows=ET.parse(xml).findall('.//testcase');assert code==0 and len(rows)==6 and all(not any(c.tag in ['failure','error','skipped']for c in x)for x in rows),(profile,code,log.read_text()[-5000:])
  results.append(dict(profile=profile,passed=len(rows),returncode=code,xml_sha256=sha(xml)))
 bad=json.loads(raw);bad['transform_sha256']['hw/soc/flow/adapt_eth_mbist.py']='1a3a9a0a734eb41d5886d05a08592b8062c58de074a9d086be9f76097489e576'
 metadata.write_text(json.dumps(bad))
 try:
  log=OUT/'stale-hash.log';xml=OUT/'stale-hash.xml'
  with log.open('w')as stream:code=subprocess.call([sys.executable,'-m','pytest','-q','--junitxml='+str(xml),tests[0]],cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT)
  assert code!=0 and 'Dependency transform changed; regenerate source snapshot: hw/soc/flow/adapt_eth_mbist.py'in log.read_text()
  rows=ET.parse(xml).findall('.//testcase');assert len(rows)==1 and rows[0].find('error')is not None and rows[0].find('skipped')is None
 finally:metadata.write_bytes(raw)
 assert all(sha(ROOT/f)==h for f,h in protected.items())
 assert not subprocess.check_output(['git','diff','--name-only'],cwd=ROOT,text=True).strip()
 (OUT/name).write_bytes(raw);(OUT/notice['file']).write_bytes(data)
 r.update(status='PASS_CURRENT_BASE_FULL_STRUCTURAL_GUARDS_AND_STALE_HASH_REFUSAL',results=results,negative_control_rejected=True,sources_unchanged=True,publication_run=run['id'],publication_artifact=artifact['id'],metadata_sha256=sha(metadata),scope='Structural dependency compatibility and whole-SoC elaboration with memories blackboxed. Not mapped gate boot, PCIe serial integration, timing or production acceptance.')
except BaseException:r.update(status='FAIL_OR_ERROR',traceback=traceback.format_exc());raise
finally:
 r['outputs']={str(f.relative_to(OUT)):sha(f)for f in OUT.rglob('*')if f.is_file()and f.name!='result.json'};save()
