"""Measure a single equivalent OR4 resize on exact guarded replay DB; no signoff claim."""
import os,json,subprocess,zipfile,hashlib,stat,re
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
P='repos/Melihakbulut221/nssoc/'
out=Path('out');out.mkdir();native=out/'native';native.mkdir()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
run=api('actions/runs/43633349306');assert run['conclusion']=='success' and run['head_sha']=='470ff1618470f9c2875aa6b021db85591e1e8c0c'
def acquire(aid,digest):
 m=api('actions/artifacts/'+str(aid));assert m['workflow_run']['id']==run['id'] and m['workflow_run']['head_sha']==run['head_sha'] and m['digest']=='sha256:'+digest and not m['expired']
 p=Path(str(aid)+'.zip')
 with p.open('xb')as f:subprocess.run(['gh','api',P+'actions/artifacts/'+str(aid)+'/zip'],stdout=f,check=True)
 assert sha(p)==digest
 return zipfile.ZipFile(p)
z=acquire(14129275553,'b9b6166a75a2889ee88f952abaf8b9e00f2fb151f4654d4dd9a0ceab290551c4')
assert len(z.namelist())==len(set(z.namelist()))
for i in z.infolist():
 p=Path(i.filename);assert not p.is_absolute() and '..'not in p.parts and not stat.S_ISLNK(i.external_attr>>16)
 if i.is_dir():continue
 d=native/p;d.parent.mkdir(parents=True,exist_ok=True);d.write_bytes(z.read(i))
safe=acquire(14129230698,'9772aa9f3b23a62bbaa900a028fec6417812e3890dffef89968d8a419b8bf3b9')
prior=json.loads(safe.read('continuation.json'))
app=Path('/mnt/s/librelane.AppImage');assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
# Compare logical pin functions and directions in every frozen corner library.
def block(s,start):
 i=s.index('{',start);depth=1;j=i+1
 while depth:
  depth+=(s[j]=='{')-(s[j]=='}');j+=1
 return s[i+1:j-1]
def logic(s,name):
 m=re.search(r'\bcell\s*\(\s*"?'+re.escape(name)+r'"?\s*\)',s);assert m
 c=block(s,m.end());r={}
 for p in re.finditer(r'\bpin\s*\(\s*"?([^"\s)]+)"?\s*\)',c):
  b=block(c,p.end());direction=re.search(r'\bdirection\s*:\s*([^;]+)',b);fun=re.search(r'\bfunction\s*:\s*([^;]+)',b)
  assert direction;r[p[1]]=(direction[1].strip(),fun[1].strip() if fun else None)
 assert r;return r
for c in ['slow','typ','fast']:
 s=(native/(c+'.lib')).read_text();assert logic(s,'sg13g2_or4_1')==logic(s,'sg13g2_or4_2')
odb=native/'cache/guarded_hold.odb';assert odb.is_file()
src=(native/'cache/place.tcl').read_text();header=src.split('global_placement -density 0.6')[0]
old='read_verilog out/native/cache-opensta.v\nlink_design soc_pcie_replay_tx';assert header.count(old)==1
header=header.replace(old,'read_db '+str(odb))
for l in ['initialize_floorplan -die_area {0 0 620 620} -core_area {10 10 610 610} -site CoreSite\n','make_tracks\n','place_pins -hor_layers Metal3 -ver_layers Metal2\n']:
 assert header.count(l)==1;header=header.replace(l,'')
result={'source_run':run['id'],'source_head':run['head_sha'],'source_odb_sha256':sha(odb),'accepted':False,'scope':'Single OR4 equivalent resize, exact ideal-clock block database, unchanged constraints and layer RC; not mainchip or routed signoff.','cases':{},'logical_pin_functions_match_all_corners':True}
def save():(out/'eco.json').write_text(json.dumps(result,indent=2))
save()
for case in ['control','or4_2']:
 folder=out/case;folder.mkdir();saved=native/case;saved.mkdir()
 commands="""
set inst [[ord::get_db_block] findInst _06640_]
if {$inst eq "NULL" || [[$inst getMaster] getName] ne "sg13g2_or4_1"} {error "Original cell mismatch"}
"""
 if case=='or4_2':commands+="""
set master [[ord::get_db] findMaster sg13g2_or4_2]
if {$master eq "NULL"} {error "Missing equivalent master"}
$inst swapMaster $master
if {[[$inst getMaster] getName] ne "sg13g2_or4_2"} {error "Resize failed"}
detailed_placement
"""
 commands+='check_placement -verbose\nestimate_parasitics -placement\n'
 commands+='foreach c {slow typ fast} {\n report_checks -corner $c -path_delay max -group_path_count 10000 -fields {slew cap fanout} -digits 9 > FOLDER/all-$c-max.rpt\n report_checks -corner $c -path_delay min -group_path_count 10000 -fields {slew cap fanout} -digits 9 > FOLDER/all-$c-min.rpt\n}\n'.replace('FOLDER',str(folder))
 commands+='report_check_types -max_slew -max_capacitance -max_fanout -violators > '+str(folder/'electrical.rpt')+'\n'
 commands+='write_db '+str(saved/'final.odb')+'\nwrite_verilog '+str(saved/'final.v')+'\nputs NSSOC_OR4_ECO_MEASURED_NOT_SIGNOFF\n'
 tcl=saved/'measure.tcl';tcl.write_text(header+commands)
 env=dict(os.environ);env.pop('GH_TOKEN',None);env.pop('GITHUB_TOKEN',None)
 with (folder/'native.log').open('w')as f:code=subprocess.call([str(app),'openroad','-exit',str(tcl)],stdout=f,stderr=subprocess.STDOUT,env=env)
 if code:print((folder/'native.log').read_text()[-5000:],flush=True)
 assert code==0
 rows={}
 for p in folder.glob('all-*.rpt'):
  values=re.findall(r'([-+]?[0-9]+\.[0-9]+)\s+slack\s+\((?:MET|VIOLATED)\)',p.read_text());assert values
  rows[p.name]={'worst_reported_slack_ns':min(map(float,values)),'sha256':sha(p)}
 assert len(rows)==6
 if case=='control':
  for name,row in rows.items():assert abs(row['worst_reported_slack_ns']-prior['cases']['cache']['reports'][name]['worst_reported_slack_ns'])<=0.000002,(name,row)
 result['cases'][case]={'reports':rows,'odb_sha256':sha(saved/'final.odb'),'netlist_sha256':sha(saved/'final.v')};save()
assert sha(odb)==result['source_odb_sha256']
result['status']='MEASURED_NOT_SIGNOFF';save()
