import subprocess,json,hashlib,zipfile,io
from pathlib import Path
P='repos/Melihakbulut221/nssoc/'
out=Path('current-gate-binding');out.mkdir()
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
def archive(run,head,aid,digest):
 r=api('actions/runs/'+str(run));assert r['conclusion']=='success'and r['head_sha']==head and r['run_attempt']==1
 m=api('actions/artifacts/'+str(aid));assert m['workflow_run']['id']==run and m['workflow_run']['head_sha']==head and m['digest']=='sha256:'+digest and not m['expired']
 b=subprocess.check_output(['gh','api',P+'actions/artifacts/'+str(aid)+'/zip']);assert hashlib.sha256(b).hexdigest()==digest
 return zipfile.ZipFile(io.BytesIO(b))
new=archive(43748923684,'e7aef3e3e4b3d7b2c93190649d0981cdee1b9bd5',14175890238,'5495ebccb905ede137d893a1d8a43b448dc988b370c0c58cdd03307ff2b63e4a')
old=archive(43695818962,'8fc405e96adafb355d85e6da401df25b6ac22bfc',14153204757,'e9233feee1c10354794dc7646b73b8fe9247113e3a1c070a8d0295d7c42e208f')
newid=archive(43748580179,'4602a2710cea2b2322cb035750dad9738d9583f4',14175207602,'0e41bbf406fb1518a17ee41e49814758ebd32ad9fc880e5adaaa864ae00630bc')
oldid=archive(43695470421,'d58ae1163bf3ba50206437c5c17cf63e299414a9',14154183456,'864aa69a2c72e061126c25841f46abfc17d4d2422a4e6a8b6fcdd5b604f8026a')
ng=json.loads(new.read('gate-poly-access.json'));og=json.loads(old.read('gate-poly-access.json'))
na=json.loads(new.read('view/wire/anchors08.json'));oa=json.loads(old.read('terminal-anchors.json'))
ni=json.loads(newid.read('lvs_flat-identity.json'));oi=json.loads(oldid.read('lvs_flat-identity.json'))
assert len(ng['gates'])==len(og['gates'])==200
newg={r['device']:r for r in ng['gates']};oldg={r['device']:r for r in og['gates']}
newmos={p['layout']['id']:p for p in ni['pairs']if p['layout']['model']=='sg13_lv_nmos'}
oldmos={p['layout']['id']:p for p in oi['pairs']if p['layout']['model']=='sg13_lv_nmos'}
keys=['label','metal','point_dbu','native_cluster','wire_component']
def contacts(a):return {r['label']:{k:r[k]for k in keys}for r in a['anchors']if 'gate_contact'in r['detail']}
checks=dict(same_gate_ids=set(newg)==set(oldg),same_complete_gate_geometry_and_owners=newg==oldg,same_actual_gate_groups=na['gate_groups']==oa['gate_groups'],same_all_contact_locations_and_owners=contacts(na)==contacts(oa),same_actual_200_MOS_identities=newmos==oldmos)
assert len(contacts(na))==len(contacts(oa))==200 and len(newmos)==len(oldmos)==200
report=dict(status='PASS_EXACT_CURRENT_GATE_GEOMETRY_AND_NATIVE_IDENTITY'if all(checks.values())else'FAIL_GATE_BINDING_REQUIRES_RECOMPUTATION',checks=checks,new_geometry='5f66ce0cb46acfb580b517ba02b10f66560ba4200d9cfbba0b633a839cc59c5a',qualified_previous_geometry='6023cf16271d3d49307b3967b056b4b11bfaa5534254dc89ba60f3dc21b6f82a',different_gate_ids=[i for i in set(newg)|set(oldg)if newg.get(i)!=oldg.get(i)],different_MOS_ids=[i for i in set(newmos)|set(oldmos)if newmos.get(i)!=oldmos.get(i)],different_contact_labels=[i for i in set(contacts(na))|set(contacts(oa))if contacts(na).get(i)!=contacts(oa).get(i)],gate_model_reduction_loaded=False,full_phy_accepted=False)
(out/'result.json').write_text(json.dumps(report,indent=2));assert all(checks.values()),checks
