#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Read and hash-check the exact existing codec proof in GitHub RAM; no simulation."""
import hashlib,io,json,os,subprocess,zipfile
from pathlib import Path,PurePosixPath
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/pcie-gen12-codec-proof-readback'
RUN=40099402878
HEAD='86dbe41b5383c29238b6a61f87783f3409e6cf3b'
ATTEMPT=1
ARTIFACT='pcie-gen12-codec-40099402878-1'
ARTIFACT_ID=12562423938
ARCHIVE_BYTES=174763
ARCHIVE_SHA='99e2e0e066229d608f00ce0805b5de45080d693ada9deffb3087c35a0fd82f55'
STATUS='PASS_GEN12_SINGLE_LANE_CODEC_TABLE_EXHAUSTIVE_STATE_SYNTHESIS_AND9_FAULTS'
FAULTS={'tx_bit_order','tx_invalid_K','tx_RD_constant','rx_code_error_hidden','rx_disparity_hidden','rx_RD_invalid_hold','rx_alternate7_reject','lane_enable_ignored','lane_reset_positive'}
def digest(b):return hashlib.sha256(b).hexdigest()
def api(path,binary=False):
 raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+path])
 return raw if binary else json.loads(raw)
def exact_sources():
 m=json.loads((ROOT/'scripts/pcie-gen12-codec-proof-readback-methods.json').read_text())
 for p,h in m['protected'].items():assert digest((ROOT/p).read_bytes())==h,p
 original=json.loads((ROOT/'scripts/pcie-gen12-codec-methods.json').read_text())
 for p,h in original['protected'].items():assert digest((ROOT/p).read_bytes())==h,p
 p=json.loads((ROOT/'third_party/chuck_benz_8b10b/provenance.json').read_text())
 for item in p['upstream']:assert digest((ROOT/item['path']).read_bytes())==item['sha256']
 for row in p['derivatives']:
  text=(ROOT/row['original_path']).read_text()
  for edit in row['edits']:
   assert text.count(edit['before'])==edit['count']
   text=text.replace(edit['before'],edit['after'])
  assert text==(ROOT/row['path']).read_text()and digest(text.encode())==row['sha256']
 return m,original,p
def validate_success(result):
 assert result['status']==STATUS and result['sources_unchanged']
 assert result['icarus']=='PASS_INDEPENDENT_TABLE_AND_STATE_TESTS'
 assert result['verilator']=='PASS_SAME_INDEPENDENT_VECTORS'
 c=result['coverage']
 for k,v in {'encode_cases':1024,'valid_encode':536,'invalid_K_cases':488,'decode_cases':2048,'legal_code_patterns':464,'allowed_code_RD_pairs':536,'four_symbol_chain_cases':2048,'lane_cycles':4096}.items():assert c[k]==v,k
 assert c['all_codes_both_disparities']and c['all_RX_RD_updates_from_received_subblocks']
 assert min(c['lane_coverage'].values())>0 and len(c['alternate_D7_cases'])==6
 assert {(x['rd'],x['data'])for x in c['alternate_D7_cases']}=={(0,241),(0,242),(0,244),(1,235),(1,237),(1,238)}
 faults=result['negative_controls']
 assert len(faults)==9 and {x['name']for x in faults}==FAULTS and all(x['rejected']for x in faults)
 assert set(result['synthesis'])=={'soc_pcie_gen12_8b10b_encode','soc_pcie_gen12_8b10b_decode','soc_pcie_gen12_codec_lane'}
 for name,row in result['synthesis'].items():
  assert row['cells']>0 and row['yosys_check_assert']
  assert result['outputs'][name+'.json']==row['netlist_sha256']
 table=json.loads((ROOT/'sw/tests/data/pcie_gen12_ieee8023z_codes.json').read_text())
 assert result['primary_oracle']['sha256']==table['source']['sha256']
 assert result['primary_oracle']['url']==table['source']['url']
 assert result['primary_oracle']['rows']==268 and result['primary_oracle']['independent_published_table_exact']
 for k in ('LTSSM_implemented','comma_alignment_implemented','low_rate_PMA_qualified','full_PHY_accepted'):assert result[k]is False
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true' and os.environ.get('RUNNER_ENVIRONMENT')=='github-hosted'
 assert os.environ['GITHUB_REPOSITORY']=='Melihakbulut221/nssoc'
 OUT.mkdir(parents=True,exist_ok=False)
 proof={'status':'RUNNING','readback_source':os.environ['GITHUB_SHA'],'readback_run':os.environ['GITHUB_RUN_ID'],'native_run':RUN,'native_source':HEAD,'native_attempt':ATTEMPT,'no_new_simulation':True,'full_PHY_accepted':False}
 try:
  methods,original,provenance=exact_sources()
  run=api('actions/runs/'+str(RUN))
  assert run['head_sha']==HEAD and run['run_attempt']==ATTEMPT
  assert run['head_branch']=='codex/pcie-gen12-training' and run['path']=='.github/workflows/pcie-gen12-codec-cloud.yml'
  assert run['status']=='completed' and run['conclusion']in ('success','failure')
  jobs=api('actions/runs/'+str(RUN)+'/jobs?filter=latest&per_page=100')['jobs']
  native=[x for x in jobs if x['name']=='exhaustive-native-rtl'];assert len(native)==1
  assert native[0]['status']=='completed' and native[0]['conclusion']==run['conclusion']
  artifacts=api('actions/runs/'+str(RUN)+'/artifacts?per_page=100')
  assert artifacts['total_count']==len(artifacts['artifacts'])
  selected=[x for x in artifacts['artifacts']if x['name']==ARTIFACT]
  assert len(selected)==1;meta=selected[0]
  assert not meta['expired'] and meta['workflow_run']['id']==RUN and meta['workflow_run']['head_sha']==HEAD
  assert meta['id']==ARTIFACT_ID and meta['size_in_bytes']==ARCHIVE_BYTES
  assert meta['digest']=='sha256:'+ARCHIVE_SHA
  raw=api('actions/artifacts/'+str(meta['id'])+'/zip',True)
  assert len(raw)==ARCHIVE_BYTES and digest(raw)==ARCHIVE_SHA
  z=zipfile.ZipFile(io.BytesIO(raw));info=z.infolist()
  assert len(info)<4000 and sum(x.file_size for x in info)<=512*1024*1024
  names=[x.filename for x in info if not x.is_dir()]
  assert len(names)==len(set(names))and 'result.json'in names
  for n in names:
   p=PurePosixPath(n);assert not p.is_absolute()and '..'not in p.parts
  result_bytes=z.read('result.json');result=json.loads(result_bytes)
  assert result['source_head']==HEAD and int(result['run_id'])==RUN
  assert set(names)==set(result['outputs'])|{'result.json'}
  for name,sha in result['outputs'].items():assert digest(z.read(name))==sha,name
  proof.update(native_job=native[0]['id'],native_conclusion=run['conclusion'],
   artifact=dict(id=meta['id'],name=meta['name'],metadata_digest=meta.get('digest'),archive_sha256=digest(raw),archive_bytes=len(raw),files=len(names),all_recorded_member_hashes_verified=True),
   result_sha256=digest(result_bytes),original_result=result,protected_sources=original['protected'],
   upstream_and_vendor_provenance=provenance)
  if run['conclusion']=='success':
   validate_success(result)
   proof.update(status='PASS_EXACT_CODEC_NATIVE_ARTIFACT_SOURCES_TABLE_AND_ALL_GATES',codec_RTL_accepted=True)
  else:
   assert result['status']=='FAIL_OR_ERROR'
   proof.update(status='OBSERVED_EXACT_NATIVE_CODEC_REJECTION',codec_RTL_accepted=False)
  assert exact_sources()[0]==methods
 except BaseException as exc:
  proof.update(status='READBACK_ERROR',error=repr(exc),codec_RTL_accepted=False);raise
 finally:
  data=json.dumps(proof,indent=2)+'\n'
  (OUT/'codec-proof.json').write_text(data)
  (OUT/'codec-proof.sha256').write_text(digest(data.encode())+'  codec-proof.json\n')
  print(json.dumps({k:v for k,v in proof.items()if k not in ('original_result','protected_sources','upstream_and_vendor_provenance')},indent=2))
if __name__=='__main__':main()
