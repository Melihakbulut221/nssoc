import os,json,subprocess,hashlib,io,zipfile
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
P='repos/Melihakbulut221/nssoc/'
def api(p):return json.loads(subprocess.check_output(['gh','api',P+p]))
run=api('actions/runs/43833471742');assert run['head_sha']=='9cd07809bb48f5bee9619e6cc044a3cc94cd3e01'and run['conclusion']=='success'and run['run_attempt']==1
aid=14210315699;digest='670feb4abe504f9b547e8ebaa15f872f73a8006d411ae137382df0d63743e510'
m=api('actions/artifacts/'+str(aid));assert m['digest']=='sha256:'+digest and not m['expired']and m['workflow_run']['id']==run['id']and m['workflow_run']['head_sha']==run['head_sha']
b=subprocess.check_output(['gh','api',P+'actions/artifacts/'+str(aid)+'/zip']);assert hashlib.sha256(b).hexdigest()==digest
z=zipfile.ZipFile(io.BytesIO(b));r=json.loads(z.read('result.json'))
assert r['source_head']==run['head_sha']and r['passed']and r['two_state_after_reset_equivalence']and r['normalized_source_equals_reference']
source=Path('hw/soc/rtl/pcie/soc_pcie_credit_tx.v');ref=Path('sw/tests/fixtures/pcie_credit_tx/pre-peer-ready.v')
assert hashlib.sha256(source.read_bytes()).hexdigest()==r['candidate_sha256']
assert hashlib.sha256(ref.read_bytes()).hexdigest()==r['reference_sha256']
assert z.read('normalized-reference.v')==ref.read_bytes()
assert r['invariant_run']==43831875078 and r['traffic_run']==43827501390 and r['traffic_cycles']==4800000 and r['output_truth_table_rows']==128
assert r['negative_controls']==['unrelated_state_logic','missing_reset_assignment','inverted_output']
# Re-run exact certificate against current checked-out source, including all
# upstream proof/traffic archive and per-file authentication.
subprocess.run(['python3','scripts/qualify_pcie_peer_ready_certificate.py'],check=True)
current=json.loads(Path('peer-ready-certificate/result.json').read_text())
assert current['passed']and current['candidate_sha256']==r['candidate_sha256']and current['reference_sha256']==r['reference_sha256']
out=Path('out');out.mkdir(exist_ok=True)
(out/'peer-ready-qualification-gate.json').write_text(json.dumps(dict(run=run['id'],source_head=run['head_sha'],artifact=aid,archive_sha256=digest,certificate=r,current=current,physical_accepted=False),indent=2))
