#!/usr/bin/env python3
"""Measure routed parent mailbox paths with actual nominal SPEF; not CDC signoff."""
import os,json,hashlib,subprocess
from pathlib import Path
from bootstrap_flow import verify
from cloud_core_only_postgrt import ROOT,sha,completed,archive
OUT=ROOT/'hw/soc/out/core-only-parent-cdc-paths'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False,full_chip_timing=False,cdc_timing_qualified=False,metastability_qualified=False,qualified_rc_minmax=False)
 try:
  run=completed(44314493056,'4ef92164139e6bcdea2310487f2f02b242064d9b')
  z,m=archive(run,'core-only-chip-gpio-repaired-timing-native-44314493056')
  assert m['id']==14431513763 and m['digest']=='sha256:a97e5bc8f94389c3dfc4a83206f3f09b773029ab3800150cbfa1ef5f11774bf7'
  sz,sm=archive(run,'core-only-chip-gpio-repaired-timing-summary-44314493056')
  assert sm['id']==14431858560 and sm['digest']=='sha256:8b70ee125031bea964988260f342c871f37c24e60a5c7fbebdc5e57b59ce8eb9'
  assert z.read('result.json')==sz.read('result.json');source=json.loads(z.read('result.json'));assert source['sources_unchanged']
  for p,h in source['outputs'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h,p
  for p,h in source['protected_inputs'].items():
   rel=p.removeprefix('/home/runner/work/nssoc/nssoc/');assert not rel.startswith('/')
   if not rel.startswith('hw/soc/out/'):assert sha(ROOT/rel)==h,p
  ca=source['coverage'];assert ca['parsed_nets']==ca['expected_wired_multiterminal_nets']==1949
  assert not any(ca[k]for k in ['missing_wired_nets','unexpected_spef_nets','terminal_mismatches','resistance_graph_disconnections'])
  libs={'typ':['std.lib','io.lib'],'slow':['sg13g2_stdcell_slow_1p08V_125C.lib','sg13g2_io_slow_1p08V_3p0V_125C.lib'],'fast':['sg13g2_stdcell_fast_1p32V_m40C.lib','sg13g2_io_fast_1p32V_3p6V_m40C.lib']}
  names=['chip-detailedroute.odb','chip-shell.nom.spef','shell-cts.sdc']+[p for ps in libs.values()for p in ps]
  for p in names:(OUT/p).write_bytes(z.read(p))
  assert sha(OUT/'chip-detailedroute.odb')=='29d6d93b168ef0d33aa06235d8d8578dc30b979ac026d8c4af6a3e811e3821a5'
  assert sha(OUT/'chip-shell.nom.spef')=='90a663aef4bac35f5552d01e6dd6d22f8de21452cabc38539c18edaa73fe32a7'
  assert sha(OUT/'shell-cts.sdc')=='d28e30613e4e2cc9da6f4303c2e49c361fcbc46b60a6389bbf36f6d100200736'
  sr=completed(44268658068,'8e3e1d4192178ebce2eb83ec4a7430a0bb80bac5')
  shell,shellmeta=archive(sr,'core-only-shell-map-44268658068')
  assert shellmeta['id']==14410678768 and shellmeta['digest']=='sha256:8bda874049c1183108258285d4b3dbd8782c6df175d3c5faa2875691058a0d15'
  shellreport=json.loads(shell.read('core-only-shell-map/result.json'));assert shellreport['sources_unchanged']
  for p,h in shellreport['outputs'].items():assert hashlib.sha256(shell.read('core-only-shell-map/'+p)).hexdigest()==h,p
  (OUT/'shell.json').write_bytes(shell.read('core-only-shell-map/nssoc_chip.mapped.json'))
  script=ROOT/'scripts/inspect_core_only_parent_cdc_paths.py'
  protected={str(p):sha(p)for p in [Path(__file__),script,OUT/'shell.json',*[OUT/n for n in names]]}
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
  with (OUT/'inventory.log').open('w')as log:subprocess.run([str(app),'openroad','-exit','-python',str(script)],env=dict(os.environ,NSSOC_PARENT_CDC_OUT=str(OUT)),stdout=log,stderr=subprocess.STDOUT,check=True)
  inv=json.loads((OUT/'cdc-path-inventory.json').read_text())
  r.update(status='MEASURING_PARENT_CDC_PATHS',source_artifacts=[m,sm,shellmeta],protected_inputs=protected,inventory=inv,corners={})
  def q(x):
   x=str(x);assert not any(c in x for c in '{}'+chr(10));return '{'+x+'}'
  for corner in ['slow','typ','fast']:
   folder=OUT/corner;folder.mkdir()
   lines=['set_thread_count 1']+['read_liberty '+q(OUT/p)for p in libs[corner]]
   lines+=['read_db '+q(OUT/'chip-detailedroute.odb'),'read_sdc '+q(OUT/'shell-cts.sdc'),'read_spef '+q(OUT/'chip-shell.nom.spef')]
   lines+=['if {[llength [all_clocks]] != 2} {error "Unexpected shell clocks"}','foreach name {shell_main shell_test} {set c [get_clocks $name]; if {[llength $c]!=1 || abs([get_property $c period]-20)>1e-9 || ![get_property $c is_propagated]} {error "Shell clock constraint changed"}}','report_parasitic_annotation -report_unannotated']
   cases=[]
   for row in inv['payload']:
    cases.append(('payload-'+str(row['position']).zfill(3)+'-max',row,'max'))
   for row in inv['synchronizer_chains']:
    for delay in ['max','min']:cases.append(('sync-'+row['name']+'-'+delay,row,delay))
   for label,row,delay in cases:
    a=q(row['source']);b=q(row['destination'])
    lines+=['if {[llength [get_pins '+a+']] != 1 || [llength [get_pins '+b+']] != 1} {error "Missing or ambiguous CDC endpoint"}']
    lines+=['report_checks -from [get_pins '+a+'] -to [get_pins '+b+'] -path_delay '+delay+' -group_path_count 1 -format full_clock_expanded -fields {capacitance slew fanout input_pin net} -digits 9 > '+q(folder/(label+'.rpt'))]
   lines+=['puts NSSOC_CDC_PATH_REPORTS_COMPLETE']
   tcl=folder/'paths.tcl';tcl.write_text(chr(10).join(lines)+chr(10));protected[str(tcl)]=sha(tcl)
   with (folder/'native.log').open('w')as log:subprocess.run([str(app),'openroad','-exit',str(tcl)],stdout=log,stderr=subprocess.STDOUT,check=True)
   assert 'NSSOC_CDC_PATH_REPORTS_COMPLETE'in(folder/'native.log').read_text()
   for label,row,delay in cases:
    text=(folder/(label+'.rpt')).read_text();assert text.count('Startpoint:')==text.count('Endpoint:')==1,(corner,label)
   r['corners'][corner]=dict(payload_paths=162,synchronizer_paths=8,nominal_rc_only=True,clock_phase_assumption='Unchanged provisional shell_main/shell_test SDC; no CDC timing waiver or qualified handshake margin')
  assert all(sha(p)==h for p,h in protected.items())
  r.update(status='PARENT_CDC_PATHS_MEASURED_REQUIRES_HANDSHAKE_BUDGET_AND_METASTABILITY_QUALIFICATION',sources_unchanged=True)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'};(OUT/'result.json').write_text(json.dumps(r,indent=2)+chr(10))
if __name__=='__main__':main()
