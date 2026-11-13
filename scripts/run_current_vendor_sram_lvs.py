# SPDX-License-Identifier: Apache-2.0
"""Bound vendor SRAM LVS diagnostic. Native data remains on cloud runner."""
import hashlib,json,os,pathlib,subprocess,sys,tarfile,time
P=pathlib.Path
case=sys.argv[1];assert case in ('sp','dp')
top={'sp':'RM_IHPSG13_1P_2048x64_c2_bm_bist','dp':'RM_IHPSG13_2P_256x16_c2_bm_bist'}[case]
pins={'sp':('48be5102bf97e56daee4cda1f63eaf6e7bb3450a68d48a2825060b1172011d00','734647f8383209c7e08fc8e66a2914a3acaa33e1848b9ff33b6a4a2ed3c2ec61'),'dp':('420b5223d14e2f873a2464849e3decbbec2b5b16b3c6a0f8cd2bb21b0d52365b','1b307d5bd84ba57087717c1d1e631959352c6d20a27167b3ed08f637e3d312a8')}[case]
out=P('out');native=out/'native';derived=out/'derived'
native.mkdir(parents=True);derived.mkdir()
def sha(p):
 with p.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
r={'status':'PREPARING','top':top,'run_id':os.environ.get('GITHUB_RUN_ID'),'source_sha':os.environ.get('GITHUB_SHA'),'current_vendor_macro_lvs_passed':False,'full_chip_lvs_passed':False,'manufacturing_approval':False,'scope':'Exact frozen current macro; original PDK deck with no added exclusions or tolerance changes. Existing deck ignores R above 1e9 and C below 1e-18; this is not complete parasitic/foundry qualification.'}
rc=2
try:
 assert sha(P('pkg.tgz'))=='822dab7067d901fa79dabffffff784baf5c9965f0a5091eba67acdc48b9956f4'
 with tarfile.open('pkg.tgz','r:gz') as t:
  cs=[m for m in t.getmembers() if m.isfile() and m.name.endswith('/input-contract.json')];assert len(cs)==1
  c=json.loads(t.extractfile(cs[0]).read());prefix=str(P(cs[0].name).parent)+'/files/';restored={}
  for name,info in c['input_files'].items():
   if '/libs.tech/klayout/' not in name and not (name.endswith('/'+top+'.gds') or name.endswith('/'+top+'.cdl')):continue
   rel=P(name);assert not rel.is_absolute() and '..' not in rel.parts
   data=t.extractfile(prefix+name).read();assert hashlib.sha256(data).hexdigest()==info['sha256']
   dest=native/'inputs'/rel;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(data);restored[name]=info['sha256']
 (native/'restored-inputs.json').write_text(json.dumps(restored,indent=2))
 def unique(suffix):
  paths=[native/'inputs'/n for n in restored if n.endswith(suffix)];assert len(paths)==1;return paths[0].resolve()
 gds=unique('/'+top+'.gds');cdl=unique('/'+top+'.cdl');deck=unique('/lvs/sg13g2.lvs')
 assert (sha(gds),sha(cdl))==pins
 app=P('librelane.AppImage').resolve();assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
 r.update(gds_sha256=sha(gds),cdl_sha256=sha(cdl),deck_sha256=sha(deck),restored_inputs_sha256=sha(native/'restored-inputs.json'),runtime_sha256=sha(app))
 env=dict(os.environ);env.pop('GH_TOKEN',None);env.pop('GITHUB_TOKEN',None);env['APPIMAGE_EXTRACT_AND_RUN']='1';env['QT_QPA_PLATFORM']='offscreen'
 switches=dict(input=gds,schematic=cdl,topcell=top,report=(native/'lvs.lvsdb').resolve(),log=(native/'deck.log').resolve(),target_netlist=(native/'extracted.cir').resolve(),run_mode='deep',no_simplify='true',no_series_res='true',no_parallel_res='true',combine_devices='false',allow_unmatched_ports='false',purge='false',purge_nets='false',top_lvl_pins='false',net_only='false',verbose='false')
 r['switches']={k:str(v) for k,v in switches.items()};cmd=[str(app),'klayout','-b','-zz','-r',str(deck)]
 for k,v in switches.items():cmd+=['-rd',f'{k}={v}']
 (native/'command.json').write_text(json.dumps(cmd));start=time.monotonic()
 with (native/'run.log').open('w') as f:
  p=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=18000)
 r['extraction_returncode']=p.returncode;r['elapsed_seconds']=time.monotonic()-start
 if p.returncode!=0:raise RuntimeError('KLayout execution failed; native log retained in cloud')
 audit=[str(app),'python','hw/soc/flow/audit_klayout_lvs.py',str(native/'lvs.lvsdb'),'--top',top,'--deck-log',str(native/'deck.log'),'--output',str(derived/'audit.json')]
 with (native/'audit.log').open('w') as f:a=subprocess.run(audit,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=900)
 r['audit_returncode']=a.returncode
 if not (derived/'audit.json').exists():raise RuntimeError('Independent result audit failed to produce report')
 report=json.loads((derived/'audit.json').read_text());passed=(a.returncode==0 and report['status']=='PASS within comparison scope' and not report['reasons'])
 r['current_vendor_macro_lvs_passed']=passed;r['status']='PASS_FROZEN_MACRO_COMPARISON_SCOPE_ONLY' if passed else 'FAIL_FROZEN_MACRO_LVS';rc=0 if passed else 1
except Exception as e:r['status']='ERROR_OR_INCOMPLETE_LVS';r['error']=type(e).__name__+': '+str(e)
finally:
 r['native_outputs']={str(p.relative_to(native)):{'bytes':p.stat().st_size,'sha256':sha(p)} for p in native.iterdir() if p.is_file()}
 (derived/'result.json').write_text(json.dumps(r,indent=2));print(json.dumps(r));sys.exit(rc)
