import os,json,subprocess,zipfile,stat,hashlib,traceback
from pathlib import Path
import cloud_predecode_postcts as prior
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'credit-crc-driver-trial';OUT.mkdir()
r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,final_timing_complete=False,full_phy_accepted=False,status='RUNNING')
def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
try:
 assert os.environ['GITHUB_ACTIONS']=='true'
 prior.OUT=OUT/'restore';prior.OUT.mkdir();prior.restore(None,{})
 run=prior.api('actions/runs/43771562041');assert run['head_sha']=='a13718c4fb20b0aaea2a5fefd92aa951b14f5df3' and run['conclusion']=='success' and run['run_attempt']==1
 def archive(aid,digest,label):
  m=prior.api('actions/artifacts/'+str(aid));assert m['workflow_run']['id']==run['id'] and m['workflow_run']['head_sha']==run['head_sha'] and m['digest']=='sha256:'+digest and not m['expired']
  p=OUT/(label+'.zip')
  with p.open('xb') as dest:subprocess.run(['gh','api',prior.REPO+'actions/artifacts/'+str(aid)+'/zip'],stdout=dest,check=True)
  assert prior.sha(p)==digest
  return zipfile.ZipFile(p)
 safe=archive(14186226268,'586b8a9db44e4de004a3e929d5aec7b91fe2fb62dec4ff11c112d79bb926608f','derived')
 native=archive(14185713649,'c96320d0a80ee8b032fdeddace5e659c7d028019a5924f7e37c652f6669ca9c1','native')
 report=json.loads(safe.read('result.json'));assert report['source_head']==run['head_sha'] and report['sources_unchanged'] and report['returncode']==0 and report['accepted'] is False
 assert report['repaired_odb_sha256']=='d4b55e0c8753f4c4ee0ed48cd1033fea40112db057b9f1000e619061383d5256'
 source=ROOT/'hw/soc/out/cloud-predecode-postcts';source.mkdir()
 assert len(native.namelist())==len(set(native.namelist()))
 assert {n for n in native.namelist()if not n.endswith('/')}==set(report['outputs'])|{'result.json'}
 for info in native.infolist():
  name=prior.relative(info.filename);assert not stat.S_ISLNK(info.external_attr>>16)
  if info.is_dir():continue
  data=native.read(info);expected=hashlib.sha256(safe.read('result.json')).hexdigest()if info.filename=='result.json'else report['outputs'][info.filename]
  assert hashlib.sha256(data).hexdigest()==expected
  dest=source/name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data)
 member='run/6-nssoc-corrprebankedafterslow/max.rpt';data=safe.read(member);assert hashlib.sha256(data).hexdigest()==report['outputs'][member]
 first=data.decode().split('Startpoint:')[1].split('data arrival time')[0].split('/Q (',1)[1]
 targets=[('$abc$735191$auto$blifparse.cc:397:parse_blif$740611','sg13g2_buf_1','sg13g2_buf_4'),('fanout8587','sg13g2_buf_1','sg13g2_buf_4'),('$abc$735191$auto$blifparse.cc:397:parse_blif$760683','sg13g2_nor4_1','sg13g2_nor4_2')]
 for cell,old,new in targets:assert cell+'/' in first and '('+old+')' in first
 r.update(source_run=run['id'],source_odb_sha256=report['repaired_odb_sha256'],targets=targets,source_before=report['measurements']['after'],path_report_sha256=report['outputs'][member]);save()
 safe.close();native.close()
 state=json.loads((source/report['repaired_state']).read_text());odb=Path(state['odb']);assert odb.is_relative_to(source) and prior.sha(odb)==r['source_odb_sha256'];state['metrics']={}
 initial=OUT/'initial.json';initial.write_text(json.dumps(state))
 config=json.loads((source/'trial-config.json').read_text());assert config['CLOCK_PERIOD']==20 and config['TIME_DERATING_CONSTRAINT']==5.0 and config['SETUP_VIOLATION_CORNERS']==config['HOLD_VIOLATION_CORNERS']==['*']
 cfg=OUT/'config.json';cfg.write_text(json.dumps(config));app=Path(os.environ['CLOUD_APPIMAGE']);prior.verify(app,'x86_64')
 # Recover actual violating internal endpoint PINs, not instance-only names.
 import io,re
 producer=prior.api('actions/runs/43782739036')
 assert producer['conclusion']=='success' and producer['head_sha']=='c7dac385cf8f42e685f57315b3845e2afc79b3c6' and producer['run_attempt']==1
 meta=prior.api('actions/artifacts/14189336194');dh='e79d1f340e67090110fcb020ca5226cca80a258978dd7af393c4bf9e74a11b2e'
 assert meta['workflow_run']['id']==43782739036 and meta['digest']=='sha256:'+dh and not meta['expired']
 db=subprocess.check_output(['gh','api',prior.REPO+'actions/artifacts/14189336194/zip']);assert hashlib.sha256(db).hexdigest()==dh
 with zipfile.ZipFile(io.BytesIO(db)) as dz:
  dr=json.loads(dz.read('result.json'));member='run/4-nssoc-sizedfast/min.rpt';data=dz.read(member)
  assert hashlib.sha256(data).hexdigest()==dr['outputs'][member]
 endpoints={}
 for path in data.decode().split('Startpoint:')[1:]:
  ep=re.search(r'^Endpoint: (.*)',path,re.M);slack=re.search(r'(-?[0-9.]+)\s+slack \(VIOLATED\)',path)
  if not slack or 'input port'in path.split('Endpoint:')[0] or 'output port'in ep[1]:continue
  lines=path.split('data arrival time',1)[0].splitlines()
  cells=[re.search(r'\s(\S+/\S+) \(([^)]+)\)\s*$',line)for line in lines]
  cells=[x for x in cells if x];assert cells,path[-500:]
  pin=cells[-1][1];assert pin.startswith(ep[1]+'/') and all(c not in pin for c in '{}\n\r\\'),pin
  endpoints[pin]=min(float(slack[1]),endpoints.get(pin,0))
 assert 240<=len(endpoints)<=243,len(endpoints)
 commands=[];catalog=[]
 for i,(pin,slack) in enumerate(sorted(endpoints.items())):
  label='internal_'+str(i);catalog.append(dict(label=label,pin=pin,source_fast_hold_slack=slack))
  commands+=['set target [get_pins {'+pin+'}]','if {[llength $target]!=1} {error "Missing internal endpoint"}','foreach mode {max min} {',' puts "%OL_CREATE_REPORT targeted_'+label+'_${mode}.rpt"',' report_checks -to $target -path_delay $mode -format full_clock_expanded -digits 6 -group_path_count 3 -endpoint_path_count 2',' puts "%OL_END_REPORT"','}']
 # Measure all endpoints through each short self-feedback branch, not only its original FF.
 feedback={}
 for path in data.decode().split('Startpoint:')[1:]:
  start=path.splitlines()[0].strip();end=re.search(r'^Endpoint: (.*)',path,re.M)
  if not end or end[1]!=start or not re.search(r'slack \(VIOLATED\)',path):continue
  cells=[re.search(r'\s(\S+/\S+) \(([^)]+)\)\s*$',line)for line in path.split('data arrival time',1)[0].splitlines()]
  cells=[m for m in cells if m];indices=[j for j,m in enumerate(cells)if m[1]==start+'/Q'];assert len(indices)==1
  j=indices[0];assert j+1<len(cells);pin=cells[j+1][1]
  assert pin!=start+'/D' and all(c not in pin for c in '{}\n\r\\')
  if pin in feedback:assert feedback[pin]==start+'/Q'
  feedback[pin]=start+'/Q'
 assert feedback
 fc=[]
 for i,(pin,driver)in enumerate(sorted(feedback.items())):
  label='feedback_'+str(i);fc.append(dict(label=label,pin=pin,expected_driver=driver));instance,terminal=pin.rsplit('/',1)
  commands+=['set inst [[ord::get_db_block] findInst {'+instance+'}]','if {$inst eq "NULL"} {error "Feedback instance missing"}',
   'set pin [$inst findITerm {'+terminal+'}]','if {$pin eq "NULL" || [$pin getIoType] ne "INPUT"} {error "Feedback input missing"}',
   'set net [$pin getNet]','if {$net eq "NULL" || [$net getSigType] ne "SIGNAL"} {error "Feedback net invalid"}',
   'set drivers {}','foreach p [$net getITerms] {if {[$p getIoType] eq "OUTPUT"} {lappend drivers "[[$p getInst] getName]/[[$p getMTerm] getName]"}}',
   'if {[llength $drivers]!=1 || [lindex $drivers 0] ne {'+driver+'} || [llength [$net getBTerms]]!=0} {error "Feedback source mismatch"}',
   'set target [get_pins {'+pin+'}]','if {[llength $target]!=1} {error "Feedback pin not unique"}',
   'foreach mode {max min} {',' puts "%OL_CREATE_REPORT targeted_'+label+'_${mode}.rpt"',
   ' report_checks -through $target -path_delay $mode -format full_clock_expanded -digits 6 -group_path_count 10 -endpoint_path_count 2',
   ' puts "%OL_END_REPORT"','}']
 (OUT/'feedback-targets.json').write_text(json.dumps(fc,indent=2));r['feedback_branch_count']=len(fc)
 (OUT/'internal-targets.tcl').write_text('\n'.join(commands)+'\n')
 (OUT/'internal-targets.json').write_text(json.dumps(catalog,indent=2))
 r['internal_endpoint_count']=len(catalog);r['internal_endpoint_source']=dict(run=43782739036,artifact=14189336194,sha256=dh)
 flow=ROOT/'hw/soc/pnr/credit_crc_driver_flow.py';protected={str(p):prior.sha(p)for p in [odb,initial,cfg,flow,OUT/'internal-targets.tcl',OUT/'internal-targets.json',OUT/'feedback-targets.json',Path(__file__),prior.SOURCE/'prepared/physical.sdc']}
 command=[str(app),'python',str(flow),'--flow','AckChipResetSized','--pdk-root',str(ROOT/'hw/soc/tools/ciel-corrpre'),'--pdk','ihp-sg13g2','--scl','sg13g2_stdcell','--force-run-dir',str(OUT/'run'),'--with-initial-state',str(initial),str(cfg)]
 (OUT/'run').mkdir()
 with (OUT/'native.log').open('w')as log:code=subprocess.call(command,stdout=log,stderr=subprocess.STDOUT)
 r['returncode']=code;assert code==0
 assert 'NSSOC_ENDPOINT_DELAY_STRUCTURAL_PASS ports=18 cells=20' in (OUT/'native.log').read_text()
 assert 'NSSOC_ETH_OUTPUT_DELAY_STRUCTURAL_PASS ports=9 cells=18' in (OUT/'native.log').read_text()
 assert all(prior.sha(Path(p))==h for p,h in protected.items())
 measurements={}
 for short,corner in prior.CORNERS:
  dirs=list((OUT/'run').glob('*-nssoc-sized'+short));assert len(dirs)==1
  assert not(dirs[0]/'unpropagated.rpt').read_text().strip()
  for label in ['training', 'rx_error', 'rx_data7', 'rx_valid', 'rx_sop', 'rx_eop', 'rx_dllp', 'rx_data0', 'rx_data1', 'rx_data2', 'rx_data3', 'rx_data4', 'rx_data5', 'rx_data6', 'function_id3', 'function_id7', 'function_id8', 'function_id13', 'eth0', 'eth1', 'eth2', 'eth3', 'eth4', 'eth5', 'eth6', 'eth7', 'eth_enable']:
   for mode in ['max','min']:
    targeted=(dirs[0]/('targeted_'+label+'_'+mode+'.rpt')).read_text();assert 'Startpoint:' in targeted and 'Endpoint:' in targeted, (corner,label,mode,'Targeted report missing path')
  for item in catalog+fc:
   for mode in ['max','min']:
    content=(dirs[0]/('targeted_'+item['label']+'_'+mode+'.rpt')).read_text();assert 'Startpoint:' in content and 'Endpoint:' in content
  state=json.loads((dirs[0]/'state_out.json').read_text());measurements[corner]={k:v for k,v in state['metrics'].items()if k.endswith('__corner:'+corner)}
 r.update(measurements=measurements,candidate_odb_sha256=prior.sha(Path(state['odb'])),sources_unchanged=True,status='MEASURED_EXPANDED_IO_DELAY_REQUIRES_LOGIC_AND_TIMING_REVIEW',scope='Three driver resizes plus twenty exact PCIe D-branch delay cells and eighteen isolated Ethernet output delay cells; native incidence guards and legal placement. Three-corner propagated placement-RC STA; no automatic adoption, no routed timing or full PHY qualification.')
except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e),traceback=traceback.format_exc());raise
finally:
 r['outputs']={str(p.relative_to(OUT)):prior.sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'and p.suffix!='.zip'};save()
