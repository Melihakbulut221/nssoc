import json,subprocess,hashlib,zipfile,stat,os,re
from pathlib import Path
P='repos/Melihakbulut221/nssoc/'
out=Path('out');out.mkdir();native=out/'native';native.mkdir()
def sha(p):
 with Path(p).open('rb')as f:return hashlib.file_digest(f,'sha256').hexdigest()
def api(p):return json.loads(subprocess.check_output(['gh','api',P+p]))
def acquire(aid,digest):
 meta=api('actions/artifacts/'+str(aid));assert meta['workflow_run']['id']==43631139914 and meta['workflow_run']['head_sha']=='3e15b59941f5de46718a7fa94ed7426c0e4b85d6' and meta['digest']=='sha256:'+digest
 p=Path(str(aid)+'.zip')
 with p.open('xb')as f:subprocess.run(['gh','api',P+'actions/artifacts/'+str(aid)+'/zip'],stdout=f,check=True)
 assert sha(p)==digest
 return zipfile.ZipFile(p)
r=api('actions/runs/43631139914');assert r['conclusion']=='success'
z=acquire(14128122304,'a997c6d23fe7c5af22a5887830141297f09a3e253da12f86ca2dfde47ff68ae6')
assert len(z.namelist())==len(set(z.namelist()))
for item in z.infolist():
 p=Path(item.filename);assert not p.is_absolute() and '..'not in p.parts and not stat.S_ISLNK(item.external_attr>>16)
 if item.is_dir():continue
 target=native/p;target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(item))
safe=acquire(14127987571,'73154f72f8b9f946118c4fdbea2207a61a1a44167a69d4de1bf64f6cf3ffba39');original=json.loads(safe.read('placement-comparison.json'))
app=Path('/mnt/s/librelane.AppImage');assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
result={'status':'RUNNING','source_run':43631139914,'source_head':r['head_sha'],'accepted':False,'scope':'Continuation of exact repaired isolated block ODB. Original ideal clock, libraries and estimated RC; not CTS/routed/full chip signoff.','cases':{}}
def save():(out/'continuation.json').write_text(json.dumps(result,indent=2))
save()
for label in ['baseline','cache']:
 folder=out/label;folder.mkdir()
 source=(native/label/'place.tcl').read_text();header=source.split('global_placement -density 0.6')[0]
 old=f'read_verilog out/native/{label}-opensta.v\nlink_design soc_pcie_replay_tx';assert header.count(old)==1
 header=header.replace(old,f'read_db out/native/{label}/hold_repair.odb')
 for line in ['initialize_floorplan -die_area {0 0 620 620} -core_area {10 10 610 610} -site CoreSite\n','make_tracks\n','place_pins -hor_layers Metal3 -ver_layers Metal2\n']:
  assert header.count(line)==1;header=header.replace(line,'')
 assert 'create_clock -name pcie_clk_i -period 4.0' in header and 'set_timing_derate -early 0.95' in header and 'set_timing_derate -late 1.05' in header
 procedure=source[source.index('proc reports {phase}'):source.index('reports placed')]
 commands='check_placement -verbose\nestimate_parasitics -placement\nreports resumed_before\nrepair_timing -setup -max_iterations 600\ndetailed_placement\ncheck_placement -verbose\nestimate_parasitics -placement\nreports continued_setup\nrepair_timing -hold -max_iterations 1000 -max_buffer_percent 40\ndetailed_placement\ncheck_placement -verbose\nestimate_parasitics -placement\nreports continued_hold\nputs NSSOC_RESUMED_REPAIR_COMPLETE_NOT_SIGNOFF\n'
 script=native/label/'continue.tcl';script.write_text(header+procedure+commands)
 env=dict(os.environ);env.pop('GH_TOKEN',None);env.pop('GITHUB_TOKEN',None)
 with (folder/'native.log').open('w')as log:code=subprocess.call([str(app),'openroad','-exit',str(script)],stdout=log,stderr=subprocess.STDOUT,env=env)
 if code:print((folder/'native.log').read_text()[-5000:],flush=True)
 assert code==0
 rows={}
 for p in folder.glob('*.rpt'):
  values=re.findall(r'([-+]?[0-9]+\.[0-9]+)\s+slack\s+\((?:MET|VIOLATED)\)',p.read_text());assert values,p
  rows[p.name]={'worst_reported_slack_ns':min(map(float,values)),'sha256':sha(p)}
 assert len(rows)==18
 for name,row in rows.items():
  if name.startswith('resumed_before-'):
   prior=original['cases'][label][name.replace('resumed_before-','hold_repair-')]['worst_reported_slack_ns']
   assert abs(row['worst_reported_slack_ns']-prior)<=0.000002,(name,row,prior)
 result['cases'][label]={'reports':rows,'source_odb_sha256':sha(native/label/'hold_repair.odb'),'resumed_measurements_match':True};save()
result['status']='COMPLETE_NATIVE_CONTINUATION_NOT_SIGNOFF';save()
