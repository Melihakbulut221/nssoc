import os,json,hashlib
from cloud_core_only_postgrt import ROOT,completed,archive,sha
OUT=ROOT/'hw/soc/out/core-only-load-electrical-comparison'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 sources=[]
 for label,rid,head,name,aid,digest in [
  ('spacing',44482078997,'85c2c5b0c18f83bb8ea7a722c29956b35f9996cf','core-only-slew-spacing-antenna-extraction-44482078997',14508759821,'72228851b81ed0d082ef3342a9fefa037f4cb07507f4fef5d43f8de5d77730bd'),
  ('load',44502914675,'f598bfab9e5aca3548c5c51df96ff477b1b0b609','core-only-spacing-load-antenna-extraction-44502914675',14519695416,'1dcb18436e79ca0c6aa5d5e07f57fb6a09858cf76acb548c6702b50cdc48fae1')]:
  run=completed(rid,head);assert run['run_attempt']==1
  z,m=archive(run,name);assert m['id']==aid and m['digest']=='sha256:'+digest
  r=json.loads(z.read('result.json'));assert r['source_head']==head and r['sources_unchanged']
  assert set(n for n in z.namelist()if not n.endswith('/')and n!='result.json')==set(r['outputs'])
  for n,h in r['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h,n
  selected=[]
  for n in r['outputs']:
   if '/2-nssoc-coreonlyextractedsta/'in n and (n.endswith('.rpt')or n.endswith('.json')):
    p=OUT/label/n;assert p.resolve().is_relative_to(OUT.resolve());p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(z.read(n));selected.append(n)
  assert sum(n.endswith('/checks.rpt')for n in selected)==3
  (OUT/label/'source-result.json').write_bytes(z.read('result.json'))
  sources.append(dict(label=label,run=rid,head=head,artifact=m,verified_outputs=len(r['outputs'])))
 result=dict(source_head=os.environ['GITHUB_SHA'],sources=sources,accepted=False,scope='Exact source-verified reports for electrical regression analysis; no new simulation or signoff.')
 result['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()}
 (OUT/'result.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
