import os,json,hashlib
from cloud_core_only_postgrt import ROOT,completed,archive,sha
OUT=ROOT/'hw/soc/out/core-only-combined-electrical-reports'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 run=completed(44448236669,'720ad3910edaa210b56b946d6cd0e9ced9454a77');assert run['run_attempt']==1
 z,m=archive(run,'core-only-combined-timing-extraction-44448236669');assert m['id']==14494314980 and m['digest']=='sha256:4f2b81dfa242d40fee5eb0b38ed89274c7d65ae10d3163d2a99fc7f1d254f038'
 r=json.loads(z.read('result.json'));assert r['source_head']==run['head_sha']
 assert set(n for n in z.namelist()if not n.endswith('/')and n!='result.json')==set(r['outputs'])
 for n,h in r['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
 selected=[]
 for n in r['outputs']:
  if '/2-nssoc-coreonlyextractedsta/'in n and (n.endswith('.rpt')or n.endswith('.json')):
   p=OUT/n;assert p.resolve().is_relative_to(OUT.resolve());p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n));selected.append(n)
 assert sum(n.endswith('/checks.rpt')for n in selected)==3
 (OUT/'source-result.json').write_bytes(z.read('result.json'))
 result=dict(source_head=os.environ['GITHUB_SHA'],source_run=run['id'],source_commit=run['head_sha'],source_artifact=m,verified_source_outputs=len(r['outputs']),selected_reports=selected,accepted=False,scope='Read-only exact report subset of prior combined timing candidate, before two-driver setup resize. No new simulation or signoff.')
 result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()}
 (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
