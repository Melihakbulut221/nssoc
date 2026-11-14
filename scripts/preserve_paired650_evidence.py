"""Preserve exact measured intermediate artifacts; never a product release."""
import os,json,subprocess,hashlib
from pathlib import Path
REPO='Melihakbulut221/nssoc';P='repos/'+REPO+'/'
SOURCES=[
 (43621748603,'0d90e18e09678eb1733123d97f41942dace720b3',[(14124466665,'726986be12be609ba674d4622b6011b30d3392a2ff70e6e69578a552984705ce'),(14124521775,'84bbb918af34605e7c6f14598fc68e7d5bb811a3d32d6c22bb294c0a51623ac6')]),
 (43622190993,'8274b540b6223e6a9bd2c7aa7b3d2c5046b09a7f',[(14125115411,'0d9b23019c89ab327ef3a296437a1bd61c180491954d09274c225814a69dc674'),(14124657803,'bf981a5887f0fd69167f41e1ce6b8065662202d1fe9f8b2de201df210eb408ec')]),
 (43622884786,'e0a87989915cb7d65a20176de33649859f013393',[(14125295448,'d8376d4009da54acbe52569fd119add9f07f4f13d8120ebc65bd5fa193c899ac'),(14125325353,'b29785a0ad74a923e6c250f564a3f57da8d876e58992d57b5800e18ab4176b47')]),
 (43623472892,'54a4766e9256d2cd0a3f93f5441ca5d1c238c7ce',[(14124672969,'a3e3b980b8d03f8ef38d854b414649a40496711d532f4824957184fc9082c199'),(14124873759,'0bf3857c86266eb8628545faea5b3a2794b80abaa6f06a09d7c8d1f9c785f422')]),
 (43623877135,'ca7922a41bb122ec714a23cd2ca5b7ea63d197ba',[(14125052605,'26bccc7db4231b610aa780e128fea159424bafdf5b3cc32da3a3a4474f0d506c'),(14125201998,'1443428cee3752ae7c9b14aa65d01e614520ca5547e79abf8e406ff3c56617fb')]),
 (43625413974,'bc78aa9667a0915c7dc31b244b714a1d2166a362',[(14124829951,'15c92cb7f9ca584c69e116dfa957abd2612f25f8efc5cc3cfea933538ccd88fc'),(14125203854,'0485478594d39baa2bec3e3b769b4cf3b33ad1c19a95bce5bd50b6ed2e9ccba8')]),
 (43625754764,'0308a08571969e629fb567c811414edb925a0dbc',[(14125119960,'b49bb48108f0a6499016092c5ccfd83795bd25af1b88773fbcc55d22ff8d258f'),(14125304132,'60749878a9146a9115289993ba0b3227ba3952678a3e2a0200ed0eb6e33476c1')]),
 (43627389964,'d4569fbeb75818b37d41b7ba8fcacbe84eab5acb',[(14126747208,'c874d25604a057d33f796e44d3cacd56ac97aa0a8259e6aee49d5edf93f13976')])]
def api(s,data=None):
 args=['gh','api',P+s]+(['--input','-']if data is not None else[])
 raw=subprocess.check_output(args,input=json.dumps(data).encode()if data is not None else None,timeout=90)
 return json.loads(raw)if raw else None
def sha(path):
 with path.open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
 assert os.environ['GITHUB_ACTIONS']=='true'and os.environ['RUNNER_ENVIRONMENT']=='github-hosted'
 assert os.environ['GITHUB_REPOSITORY']==REPO and os.environ['GITHUB_REF']=='refs/heads/codex/preserve-paired650-evidence'
 assert os.environ['GITHUB_EVENT_NAME']=='workflow_dispatch'and os.environ['GITHUB_RUN_ATTEMPT']=='1'
 head=os.environ['GITHUB_SHA'];assert subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()==head
 out=Path('preservation');out.mkdir();cache=Path('archive-cache');cache.mkdir()
 manifest={'schema':'paired650-source-bound-artifact-preservation-v1','publisher_run':int(os.environ['GITHUB_RUN_ID']),'publisher_source':head,'status':'RUNNING','full_phy_accepted':False,'final_timing_complete':False,'production_approved':False,'scope':'Exact intermediate measurement archives only. Individual scopes and limitations remain in original results; no combined signoff.','artifacts':[]}
 def save():(out/'result.json').write_text(json.dumps(manifest,indent=2)+'\n')
 save()
 try:
  # Validate every source and archive metadata before creating any release.
  rows=[]
  for run,source,items in SOURCES:
   r=api('actions/runs/'+str(run));assert r['head_sha']==source and r['status']=='completed'and r['conclusion']=='success'and r['run_attempt']==1
   for aid,digest in items:
    m=api('actions/artifacts/'+str(aid));assert m['workflow_run']['id']==run and m['workflow_run']['head_sha']==source and not m['expired']and m['digest']=='sha256:'+digest
    rows.append({'run':run,'source':source,'artifact':aid,'sha256':digest,'original_metadata':m,'asset_name':f'run-{run}-artifact-{aid}.zip'})
  assert len(rows)==15 and len({r['artifact']for r in rows})==15
  tag='cloud-results-'+os.environ['GITHUB_RUN_ID']+'-1-paired650-evidence'
  api('git/refs',{'ref':'refs/tags/'+tag,'sha':head})
  release=api('releases',{'tag_name':tag,'target_commitish':head,'name':'Paired650 intermediate evidence — not PHY or production approval','body':'Source-bound preservation of eight measured intermediate stages. Original run, commit, archive digest and scope remain in the manifest. This is not a chip release or signoff.','draft':False,'prerelease':True,'make_latest':'false'})
  assert release['target_commitish']==head and release['prerelease']and not release['draft']and not release['assets']
  manifest.update(release_id=release['id'],release_url=release['html_url'],tag=tag);save()
  for row in rows:
   path=cache/row['asset_name']
   with path.open('xb')as f:subprocess.run(['gh','api',P+'actions/artifacts/'+str(row['artifact'])+'/zip'],stdout=f,check=True,timeout=600)
   assert sha(path)==row['sha256'];row['bytes']=path.stat().st_size
   subprocess.run(['gh','release','upload',tag,str(path),'--repo',REPO],check=True,timeout=600)
   assets=api('releases/'+str(release['id'])+'/assets');hits=[x for x in assets if x['name']==path.name];assert len(hits)==1
   asset=hits[0];assert asset['state']=='uploaded'and asset['digest']=='sha256:'+row['sha256']and asset['size']==row['bytes']
   row['release_asset_id']=asset['id'];row['download_url']=asset['browser_download_url'];manifest['artifacts'].append(row);save();path.unlink()
   print('PRESERVED',row['artifact'],row['bytes'],flush=True)
  assert len(manifest['artifacts'])==15
  manifest['status']='COMPLETE_EXACT_ARCHIVE_PRESERVATION_NOT_SIGNOFF';save()
  index=out/'archive-index.json';index.write_text(json.dumps(manifest,indent=2)+'\n')
  subprocess.run(['gh','release','upload',tag,str(index),'--repo',REPO],check=True,timeout=120)
  assets=api('releases/'+str(release['id'])+'/assets');assert {x['name']for x in assets}=={x['asset_name']for x in rows}|{'archive-index.json'}
  item=next(x for x in assets if x['name']=='archive-index.json');assert item['digest']=='sha256:'+sha(index)
  manifest.update(index_asset_id=item['id'],index_sha256=sha(index));save()
 except BaseException as error:
  manifest.update(status='FAIL_OR_ERROR',error=repr(error));save();raise
if __name__=='__main__':main()
