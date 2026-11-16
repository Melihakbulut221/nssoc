import os,json,subprocess,hashlib,zipfile,io,stat,pathlib
import cloud_predecode_postcts as prior
P=pathlib.Path;ROOT=P.cwd();OUT=ROOT/'eop-route-resume';OUT.mkdir()
r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,full_phy_accepted=False,status='RUNNING')
def save():(OUT/'result.json').write_text(json.dumps(r,indent=2))
def archive(aid,h,runid,head):
 run=prior.api('actions/runs/'+str(runid));assert run['head_sha']==head and run['run_attempt']==1 and run['status']=='completed'
 m=prior.api('actions/artifacts/'+str(aid));assert not m['expired'] and m['digest']=='sha256:'+h and m['workflow_run']['id']==runid and m['workflow_run']['head_sha']==head
 b=subprocess.check_output(['gh','api',prior.REPO+'actions/artifacts/'+str(aid)+'/zip']);assert hashlib.sha256(b).hexdigest()==h
 return zipfile.ZipFile(io.BytesIO(b))
try:
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 audit=archive(14194554319,'7bf685644b6f550900fa418416b152f1c7aa1415ddb75b96c051417478f35fdb',43797316134,'6f39e1f209bc7862693fdd44feaaf1698c4f88e5')
 ar=json.loads(audit.read('result.json'));assert ar['audit_passed'] and ar['returncode']==0 and ar['accepted'] is False
 assert ar['guide_inventory']['guide_count']==1350552 and ar['guide_inventory']['nets_with_guides']==162053 and not ar['guide_inventory']['connected_nets_without_guides']
 assert ar['odb_sha256']=='07c930798fd1a8d595be9990d59a165647171dacdef972c51cd87b1bd0750828'
 prior.OUT=OUT/'restore';prior.OUT.mkdir();prior.restore(None,{})
 z=archive(14194108006,'c6c6f10140841c0cc6a115853c17ca823b30a2c3443b6753a68dd64de7d9efe1',43793553628,'fc1b53d5641b2ca885ac3fac661984c366352e06')
 report=json.loads(z.read('result.json'));assert report['returncode']==0 and report['error']=='AssertionError({})' and 'assert len(guides)==1,guides' in report['traceback']
 source=ROOT/'credit-crc-driver-trial';source.mkdir();assert len(z.namelist())==len(set(z.namelist()))
 for info in z.infolist():
  name=prior.relative(info.filename);assert not stat.S_ISLNK(info.external_attr>>16)
  if info.is_dir():continue
  if info.filename=='result.json':continue
  data=z.read(info);assert hashlib.sha256(data).hexdigest()==report['outputs'][info.filename]
  dest=source/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
 states=list((source/'run').glob('*-nssoc-validatedglobalrouting/state_out.json'));assert len(states)==1
 state=json.loads(states[0].read_text());odb=P(state['odb']);assert odb.is_relative_to(source) and prior.sha(odb)==ar['odb_sha256']
 # Recover only the last fully saved, zero-DRC database, not the interrupted run-3 state.
 cancelled=prior.api('actions/runs/43798359649')
 assert cancelled['conclusion']=='cancelled' and cancelled['status']=='completed'
 recovery=archive(14212421939,'c2a45567ff4e7040e087ed78d42e16d7472e2ce1c2860db1dc84dff1b4741ad7',43798359649,'8d4e9c784bafd367c3e32cf47f48ded675ce5d74')
 names=recovery.namelist();assert len(names)==len(set(names))
 stale=json.loads(recovery.read('result.json'))
 assert stale['source_head']=='8d4e9c784bafd367c3e32cf47f48ded675ce5d74' and stale['accepted'] is False
 member='run/1-openroad-detailedrouting/drt-run-2/soc_top.odb'
 completed_drc='run/1-openroad-detailedrouting/drt-run-2/soc_top.drc'
 assert recovery.read(completed_drc)==b''
 data=recovery.read(member)
 digest='fac99b5bf4a980c6a82da5aa52eb9f1b271f8bf1fb461f5563783f3f420a0c64'
 assert len(data)==230640663 and hashlib.sha256(data).hexdigest()==digest
 odb=OUT/'checkpoint.odb';odb.write_bytes(data);state['odb']=str(odb)
 # ODB is authoritative; discard stale global-route views and all timing evidence.
 for key in ['def','nl','pnl','spef','sdf']:
  state.pop(key,None)
 state['metrics']={}
 r['recovery']=dict(run=43798359649,artifact=14212421939,archive_sha256='c2a45567ff4e7040e087ed78d42e16d7472e2ce1c2860db1dc84dff1b4741ad7',member=member,odb_sha256=digest,completed_drc_bytes=0,checkpoint_index=2,interrupted_run_3_not_recovered=True)

 initial=OUT/'initial.json';initial.write_text(json.dumps(state));config=json.loads((source/'config.json').read_text())
 assert config['CLOCK_PERIOD']==20 and config['TIME_DERATING_CONSTRAINT']==5.0 and config['SETUP_VIOLATION_CORNERS']==config['HOLD_VIOLATION_CORNERS']==['*']
 config['DRT_ANTENNA_REPAIR_ITERS']=1
 r['antenna_round_budget']=1
 cfg=OUT/'config.json';cfg.write_text(json.dumps(config));app=P(os.environ['CLOUD_APPIMAGE']);prior.verify(app,'x86_64')
 flow=ROOT/'hw/soc/pnr/replay_onehot_detailed_route_flow.py';protected={str(p):prior.sha(p)for p in [odb,initial,cfg,flow,P(__file__),prior.SOURCE/'prepared/physical.sdc']}
 r.update(parent_run=43793553628,guide_audit_run=43797316134,source_odb_sha256=ar['odb_sha256'],protected_inputs=protected,scope='Resume last completed native DRT checkpoint through standard DRT and one antenna repair round, then independently report residual antennas and disconnected pins. Round budget is operational slicing, never a waiver. No full PHY, boot, routed STA or production acceptance.');save()
 cmd=[str(app),'python',str(flow),'--flow','ReplayOnehotDetailedRoute','--pdk-root',str(ROOT/'hw/soc/tools/ciel-corrpre'),'--pdk','ihp-sg13g2','--scl','sg13g2_stdcell','--force-run-dir',str(OUT/'run'),'--with-initial-state',str(initial),str(cfg)]
 (OUT/'run').mkdir()
 with (OUT/'native.log').open('w')as log:r['returncode']=subprocess.call(cmd,stdout=log,stderr=subprocess.STDOUT)
 assert r['returncode']==0
 assert all(prior.sha(p)==h for p,h in protected.items());r['sources_unchanged']=True
 final=OUT/'run/final/state_out.json'
 if not final.is_file():
  final_states=sorted((OUT/'run').glob('*/state_out.json'));assert final_states;final=final_states[-1]
 fs=json.loads(final.read_text());candidate=P(fs['odb']);assert candidate.is_relative_to(OUT/'run') and candidate.is_file()
 nl=P(fs['nl']);assert nl.is_relative_to(OUT/'run') and nl.is_file()
 r['fresh_netlist_sha256']=prior.sha(nl)
 r.update(status='RESUMED_ROUTE_REQUIRES_ZERO_DRC_ANTENNA_CONNECTIVITY_AND_EXTRACTED_STA_REVIEW',candidate_odb_sha256=prior.sha(candidate),final_state=str(final.relative_to(OUT)),metrics=fs['metrics'])
except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
finally:
 r['outputs']={str(p.relative_to(OUT)):prior.sha(p) for p in (OUT/'run').rglob('*') if p.is_file()};save()
