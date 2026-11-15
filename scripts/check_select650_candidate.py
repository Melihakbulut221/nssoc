import subprocess,json,hashlib,zipfile,io,sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()/'hw/soc/flow'))
from check_pcie_rx_cell import execute
from check_ihp_drc import record_result,digest
from prepare_ihp_drc import validate_lock,verify
P='repos/Melihakbulut221/nssoc/'
def api(s):return json.loads(subprocess.check_output(['gh','api',P+s]))
r=api('actions/runs/43744074899');assert r['conclusion']=='success' and r['head_sha']=='6ce9e9ad7df918a5163dba2cefaf084f63c97220' and r['run_attempt']==1
a=api('actions/artifacts/14172679027');assert a['workflow_run']['id']==r['id'] and a['digest']=='sha256:9e991786eaec22cca6268d31968d12309e24b4960cc0e82b374872f2d987df19' and not a['expired']
b=subprocess.check_output(['gh','api',P+'actions/artifacts/14172679027/zip']);assert 'sha256:'+hashlib.sha256(b).hexdigest()==a['digest'];z=zipfile.ZipFile(io.BytesIO(b))
assert json.loads(z.read('primitive-census.json'))==dict(physical_primitives=650,counts=dict(rppd=98,ptap1=221,npn13G2=124,nmos=200,cmim=7),hierarchy_preserved=True)
out=Path('select650-checks').resolve();out.mkdir()
for n,h in [('candidate650-select-width2.gds','8c42f6785d0b7ebac0a6d1b8f01d72943828a09ecf89b11f9ca05a3b4e771c77'),('schematic650-select-width2.cir','1cef658f121e0ab0dc33a2c0cacd2dd564ff440413e4a0ab6a4b91de66fca239')]:
 data=z.read(n);assert hashlib.sha256(data).hexdigest()==h;(out/n).write_bytes(data)
app=Path('hw/soc/tools/physical/librelane-3.0.5-x86_64.AppImage').resolve();assert digest(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
pins={app:digest(app)}
for typ in ['drc','lvs']:
 lockpath=Path('hw/soc/pnr/ihp-'+typ+'.lock.json');lock=json.loads(lockpath.read_text());validate_lock(lock);assert lock['commit']=='5e6d592e4002946a4616f798c357f0f3c06cf3b6';pins[lockpath.resolve()]=digest(lockpath)
 for row in lock['files']:
  path=Path('hw/soc/tools/ihp-'+typ+'-5e6d592')/row['path'];verify(path.read_bytes(),row);pins[path.resolve()]=row['sha256']
gds=out/'candidate650-select-width2.gds';ref=out/'schematic650-select-width2.cir';pins[gds]=digest(gds);pins[ref]=digest(ref)
TOP='nssoc_cdr_pd500_resistor_v59'
result=dict(status='RUNNING',steps={},full_phy_accepted=False,main_chip_integrated=False,fresh_rc=False)
def save():(out/'result.json').write_text(json.dumps(result,indent=2))
save()
try:
 for name in ['lvs','lvs_flat','wrong_resistor','drc']:
  directory=out/name;directory.mkdir();drc=name=='drc';schematic=ref
  if name=='wrong_resistor':
   t=ref.read_text();old='RSE_D0 DQP USP BULK rppd w=2u l=6u b=0 m=1';assert t.count(old)==1
   schematic=directory/'fault.cir';schematic.write_text(t.replace(old,old.replace('w=2u','w=1u')))
  typ='drc'if drc else'lvs';entry=Path('hw/soc/tools/ihp-'+typ+'-5e6d592/ihp-sg13g2/libs.tech/klayout/tech')/('drc/ihp-sg13g2.drc'if drc else'lvs/sg13g2.lvs')
  options=['input='+str(gds),'topcell='+TOP,'log='+str(directory/'deck.log'),'run_mode='+('flat'if name=='lvs_flat'else'deep')]
  options+=['report='+str(directory/'drc.lyrdb'),'threads=2','no_recommended=False','precheck_drc=False']if drc else['schematic='+str(schematic),'report='+str(directory/'result.lvsdb'),'target_netlist='+str(directory/'extracted.cir'),'thr=2','no_simplify=true','top_lvl_pins=true']
  command=[app,'klayout','-b','-zz','-r',entry.resolve()]
  for option in options:command+=['-rd',option]
  step={};result['steps'][name]=step;step['execution']=execute(command,directory,'run');save();assert step['execution']['returncode']==0
  if drc:
   measurement=record_result(directory,TOP,0,pins);step['measurement']=measurement;save();assert measurement['status']=='PASS' and measurement['category_count']==560
  else:
   step['audit_execution']=execute([app,'python',Path('hw/soc/flow/audit_klayout_lvs.py').resolve(),directory/'result.lvsdb','--top',TOP,'--deck-log',directory/'deck.log','--output',directory/'audit.json'],directory,'audit')
   audit=json.loads((directory/'audit.json').read_text());step['audit']=audit;save()
   if name=='wrong_resistor':assert audit['status']=='FAIL' and step['audit_execution']['returncode']==1 and 'Deck explicitly reported a mismatch'in audit['reasons']
   else:
    assert audit['status']=='PASS within comparison scope' and step['audit_execution']['returncode']==0 and not audit['extraction_diagnostics'] and audit['circuit_status_counts']=={'Match':1}
    assert len(audit['circuits'])==1 and all(audit['circuits'][0][k]==650 for k in ['layout_devices_recursive','schematic_devices_recursive'])
  step['status']='REJECTED_EXPECTED_FAULT'if name=='wrong_resistor'else'PASS';save();print(name,step['status'],flush=True)
 assert all(digest(path)==h for path,h in pins.items())
 result['status']='PASS_ACTUAL650_SELECT_WIDTH2_DRC_LVS_REQUIRES_FRESH_RC_AND_ELECTRICAL'
except BaseException as error:
 result['status']='FAIL';result['error']=repr(error);raise
finally:save()
