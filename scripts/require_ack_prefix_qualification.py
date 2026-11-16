import os,json,subprocess,hashlib,zipfile,io,re
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s],timeout=90))
run=43696035080;head='13ce1bfba1a3238f8b08415c55df4f2bdec5d8a9';aid=14154810806;digest='9d104d50fd232005f67e1431051c650ff4a919adfcbcfa083709ba3455a47ed6'
r=api('actions/runs/'+str(run));assert r['head_sha']==head and r['status']=='completed' and r['conclusion']=='success' and r['run_attempt']==1
a=api('actions/artifacts/'+str(aid));assert a['workflow_run']['id']==run and a['workflow_run']['head_sha']==head and not a['expired'] and a['digest']=='sha256:'+digest
raw=subprocess.check_output(['gh','api',P+'actions/artifacts/'+str(aid)+'/zip'],timeout=120);assert hashlib.sha256(raw).hexdigest()==digest
z=zipfile.ZipFile(io.BytesIO(raw));result=json.loads(z.read('result.json'))
# The legacy proof applies to the unchanged baseline; the new proof above
# independently binds the sole arithmetic substitution to the current source.
subprocess.run(['python3','scripts/require_ack_delta_qualification.py'],check=True)
current_source=Path('hw/soc/rtl/pcie/soc_pcie_replay_tx.v').read_bytes()
source=Path('hw/soc/tb/ack_delta_original.v').read_bytes()
assert hashlib.sha256(source).hexdigest()==result['rtl_sha256']=='f5634cd4692abde4aa576aa11e392c4ef5c2787a35962aeec0ac444340ec4c7a'
assert result['source_head']==head and result['status']=='PASS_24BIT_EQUIVALENCE_TWO_MUTANTS_AND_REPLAY_TRAFFIC'
assert [(c['case'],c['status'])for c in result['cases']]==[('exact','PASS'),('mutant_half_distance','REJECTED_EXPECTED_MUTANT'),('mutant_borrow','REJECTED_EXPECTED_MUTANT')]
common=['SOC_PCIE_REPLAY_INBANK','SOC_PCIE_REPLAY_AHEAD','SOC_PCIE_RESET_COPIES','SOC_PCIE_REPLAY_WRITE_PREDECODE','SOC_PCIE_REPLAY_EOP_CACHE','SOC_PCIE_REPLAY_CRC_SELECT']
assert result['common_defines']==common
assert all(os.environ.get(k)=='1'for k in common+['SOC_PCIE_ACK_STALE_PREFIX'])
want=[(4,38,256,1),(4,38,256,2),(4,38,1024,3),(4,38,256,4),(2,22,128,5),(2,22,128,6)]
assert [(x['depth'],x['max_bytes'],x['timeout'],x['seed'])for x in result['traffic']]==want
for x in result['traffic']:
 assert x['status']=='PASS' and x['cycles']==300000
 name=f"traffic-d{x['depth']}-b{x['max_bytes']}-t{x['timeout']}-s{x['seed']}.log"
 text=z.read(name).decode()
 assert re.search(r'^RESULT PASS',text,re.M) and not re.search(r'MISMATCH|FATAL|RESULT FAIL',text)
 assert [l for l in text.splitlines()if l.startswith(('SUMMARY','RESULT'))]==x['summary']
out=Path('out');out.mkdir(exist_ok=True)
(out/'ack-prefix-qualification-gate.json').write_text(json.dumps(dict(run=run,source=head,artifact=aid,archive_sha256=digest,current_source_sha256=hashlib.sha256(current_source).hexdigest(),legacy_reference_sha256=hashlib.sha256(source).hexdigest(),delta_qualification=json.loads((out/'ack-delta-qualification-gate.json').read_text()),qualification=result,physical_accepted=False),indent=2)+'\n')
