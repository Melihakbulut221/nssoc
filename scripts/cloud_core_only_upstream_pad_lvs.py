#!/usr/bin/env python3
"""Strict diagnostic of current matched official I/O layout, CDL and LVS deck."""
import os,json,subprocess,hashlib,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'hw/soc/flow'))
import run_io_parent_lvs as native
from run_coherent_io_lvs import normalize_main_taps
from io_cell_schematic import select_io_cdl
from bootstrap_flow import verify
OUT=ROOT/'hw/soc/out/core-only-upstream-pad-lvs';PIN='cc9afba57e0ec1b5ba77e6bbb638ba9dbe5866b8';TOP='sg13g2_IOPadInOut4mA'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False,manufacturing_approval=False,top=TOP,upstream_commit=PIN,cases={})
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 try:
  checkout=Path(os.environ['RUNNER_TEMP'])/'ihp-matched-pad';checkout.mkdir()
  cmds=[['git','init'],['git','remote','add','origin','https://github.com/IHP-GmbH/IHP-Open-PDK.git'],['git','config','core.sparseCheckout','true']]
  with (OUT/'checkout.log').open('w')as log:
   for cmd in cmds:subprocess.run(cmd,cwd=checkout,stdout=log,stderr=subprocess.STDOUT,check=True)
   (checkout/'.git/info/sparse-checkout').write_text('/ihp-sg13g2/libs.tech/klayout/tech/lvs/\n/ihp-sg13g2/libs.ref/sg13g2_io/\n')
   for cmd in [['git','fetch','--depth=1','--filter=blob:none','origin',PIN],['git','checkout','--detach','FETCH_HEAD']]:subprocess.run(cmd,cwd=checkout,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
  assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=checkout,text=True).strip()==PIN
  base=checkout/'ihp-sg13g2';io=base/'libs.ref/sg13g2_io';deckdir=base/'libs.tech/klayout/tech/lvs';deck=deckdir/'sg13g2.lvs'
  gds=io/'gds/sg13g2_io.gds';cdl=io/'cdl/sg13g2_io.cdl'
  assert sha(gds)=='25ecbd87d8286d273fbdd3d24cf819d480fb479d6636bcd8cea721de75a57815'
  gitblob=subprocess.check_output(['git','hash-object',str(cdl)],cwd=checkout,text=True).strip();assert gitblob=='730fa3f30f0be37e2ab0bbca7920de21b7eafcd8'
  raw=cdl.read_text();adapted,changes=normalize_main_taps(raw)
  selected,cells,globals_=select_io_cdl(adapted,TOP)
  schematic=OUT/'schematic.cir';schematic.write_text(selected)
  r['reference_preparation']=dict(source_cdl_sha256=sha(cdl),source_gds_sha256=sha(gds),dialect_changes=changes,selected_cells=list(cells),explicit_globals=globals_,globals_inferred=False,ordered_nodes_changed=False,tap_parameters_changed=False)
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
  protected={str(p):sha(p)for p in [Path(__file__),app,gds,cdl,schematic,ROOT/'scripts/run_coherent_io_lvs.py',native.AUDIT,*[p for p in deckdir.rglob('*')if p.is_file()]]}
  r['protected_inputs']=protected
  controls=OUT/'controls'
  with (OUT/'controls.log').open('w')as log:subprocess.run([str(app),'python',str(native.CONTROL),str(controls)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
  r['controls']=native.validate_controls(controls/'result.json');save()
  for mode in ['deep','flat']:
   folder=OUT/mode;folder.mkdir();r['status']='RUNNING_'+mode.upper();save()
   values=dict(input=gds,schematic=schematic,topcell=TOP,report=folder/'lvs.lvsdb.gz',log=folder/'deck.log',target_netlist=folder/'extracted.cir',run_mode=mode,thr=1,disable_tap_extraction='false',ignore_top_ports_mismatch='false',implicit_nets='',net_only='false')
   cmd=[str(app),'klayout','-b','-zz','-r',str(deck)]
   for k,v in values.items():cmd+=['-rd',str(k)+'='+str(v)]
   with (folder/'run.log').open('w')as log:code=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,timeout=1800).returncode
   r['cases'][mode]=dict(native_returncode=code,command=cmd);save()
   assert code==0 and all((folder/n).is_file()and (folder/n).stat().st_size for n in ['lvs.lvsdb.gz','deck.log','extracted.cir'])
   with (folder/'audit.log').open('w')as log:auditcode=subprocess.run([str(app),'python',str(native.AUDIT),str(folder/'lvs.lvsdb.gz'),'--top',TOP,'--deck-log',str(folder/'deck.log'),'--output',str(folder/'audit.json')],stdout=log,stderr=subprocess.STDOUT,timeout=300).returncode
   audit=json.loads((folder/'audit.json').read_text());assert audit['top']==TOP and audit['circuits']
   replay=native.assess(audit['circuits'],TOP,(folder/'deck.log').read_text(),audit.get('extraction_diagnostics',[]));assert all(audit.get(k)==v for k,v in replay.items())
   assert (audit['status']=='PASS within comparison scope'and auditcode==0 and not audit['reasons'])or(audit['status']=='FAIL'and auditcode==1 and audit['reasons'])
   r['cases'][mode].update(audit_returncode=auditcode,audit=audit);save()
  assert all(sha(p)==h for p,h in protected.items())
  subprocess.run(['git','diff','--exit-code','HEAD'],cwd=checkout,check=True,stdout=subprocess.DEVNULL)
  passed=all(v['audit']['status']=='PASS within comparison scope'for v in r['cases'].values())
  r.update(status='UPSTREAM_PAD_NATIVE_LVS_PASS_REQUIRES_DRC_AND_CHIP_MIGRATION'if passed else 'UPSTREAM_PAD_NATIVE_LVS_MISMATCH',sources_unchanged=True,cell_lvs_passed=passed)
  save()
  if not passed:raise RuntimeError('Native matched-view LVS mismatch; inspect reports without waivers')
 except BaseException as e:
  if r['status']!='UPSTREAM_PAD_NATIVE_LVS_MISMATCH':r['status']='FAIL_OR_INCOMPLETE'
  r['error']=repr(e);raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
