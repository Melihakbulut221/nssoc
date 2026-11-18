#!/usr/bin/env python3
"""Actual two-level baseline STA to qualify integration; never current ECO signoff."""
import os,json,hashlib,subprocess,base64,re
from pathlib import Path
from bootstrap_flow import verify
from cloud_core_only_postgrt import ROOT,sha,completed,archive,api
OUT=ROOT/'hw/soc/out/core-only-hierarchical-baseline'
def authenticate(run,head,name,aid,digest):
 run=completed(run,head);z,m=archive(run,name)
 assert m['id']==aid and m['digest']=='sha256:'+digest
 report=json.loads(z.read('result.json'));assert report['source_head']==head and report['sources_unchanged'] and not report['accepted']
 for p,h in report['outputs'].items():assert hashlib.sha256(z.read(p)).hexdigest()==h,p
 # Authenticate historical scripts at their historical source head, not at this runner's head.
 sources={}
 for p,h in report['protected_inputs'].items():
  rel=p.removeprefix('/home/runner/work/nssoc/nssoc/');assert not rel.startswith('/')
  if rel.startswith('hw/soc/out/'):continue
  item=api('contents/'+rel+'?ref='+head)
  if item.get('encoding')!='base64':item=api('git/blobs/'+item['sha'])
  assert hashlib.sha256(base64.b64decode(item['content'])).hexdigest()==h,rel
  sources[rel]=h
 return z,report,dict(artifact=m,verified_outputs=len(report['outputs']),protected_repository_sources=sources)
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False,current_eco_validated=False,full_chip_timing_closed=False,qualified_rc_minmax=False,external_io_constraints_qualified=False,cdc_constraints_qualified=False,core_blackbox=False,core_baseline='original pre-ECO 104885-instance routed core; integration diagnostic only')
 try:
  cz,cr,cm=authenticate(44308129454,'78432b99eb354dcb2a7a2d3266ecbb445a31c9cc','core-only-canonical-extracted-timing-native-44308129454',14429028836,'de85c0ced40577188dcb7af6786736f4f6159025fc41ae9bcdbbd6ec8e57168a')
  (OUT/'core.v').write_bytes(cz.read('canonical.v'))
  (OUT/'core.spef').write_bytes(cz.read('extraction/1-nssoc-coreonlyroutercx/nom/soc_top.nom.spef'))
  assert sha(OUT/'core.v')=='975a8269b799cfef8a279ec34ebff0324a5db8f054f1df94495d39c6c3ca85fd'
  assert sha(OUT/'core.spef')=='0e81dc36b311d13efbd2d1106f5f76003c208e23a85f7c8a81798dd2f574a6f2'
  del cz
  pz,pr,pm=authenticate(44350414168,'eb62422fc2451c9ab1488faf7f69692b14cfb913','core-only-parent-perimeter-timing-44350414168',14449570443,'c4fff039998704cd8c94a35f5775ee9a6eca9129f82b11a6e15e7b66603f38de')
  for source,dest in [('chip-shell.nom.spef','parent.spef'),('shell-cts.sdc','parent.sdc'),('std.lib','std.lib'),('io.lib','io.lib')]:
   (OUT/dest).write_bytes(pz.read(source))
  assert pr['coverage']['parsed_nets']==2005
  rz,rr,rm=authenticate(44349370248,'c7b88e12d18ad6854cfbf7bb4e419adec13842ee','core-only-parent-perimeter-route-44349370248',14448476079,'6d17d6b447953a99e307a7ec473e53110ec2e07f566a79f35aa8600fa0f891ae')
  assert pr['outputs']['chip-detailedroute.odb']==rr['outputs']['chip-detailedroute.odb']
  (OUT/'parent.v').write_bytes(rz.read('chip-detailedroute.v'))
  assert rr['strict_identity']['instances']==2031
  # Typical 25 C only: do not mix the SRAM -55 C and stdcell -40 C fast libraries.
  pdk='c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c'
  libpath='ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_2048x64_c2_bm_bist_typ_1p20V_25C.lib'
  command=['gh','api','repos/IHP-GmbH/IHP-Open-PDK/contents/'+libpath+'?ref='+pdk]
  item=json.loads(subprocess.check_output(command));assert item['sha']=='356aeced2e73b43f1e9e7ed45d1a890e4cae2123'
  if item.get('encoding')!='base64':item=json.loads(subprocess.check_output(['gh','api','repos/IHP-GmbH/IHP-Open-PDK/git/blobs/'+item['sha']]))
  data=base64.b64decode(item['content'])
  assert hashlib.sha1(b'blob '+str(len(data)).encode()+bytes([0])+data).hexdigest()=='356aeced2e73b43f1e9e7ed45d1a890e4cae2123'
  (OUT/'sram.lib').write_bytes(data)
  r['sram_library']=dict(pdk=pdk,path=libpath,git_blob='356aeced2e73b43f1e9e7ed45d1a890e4cae2123',sha256=sha(OUT/'sram.lib'),temperature_c=25,production_characterization_qualified=False)
  core=(OUT/'core.v').read_text();parent=(OUT/'parent.v').read_text()
  assert re.findall(r'(?m)^\s*module\s+(\S+)',core)==['soc_top']
  assert re.findall(r'(?m)^\s*module\s+(\S+)',parent)==['nssoc_chip']
  assert len(re.findall(r'\bsoc_top\s+u_core\s*\(',parent))==1
  cells=re.findall(r'(?m)^\s*(sg13g2_\w+)\s+(\S+)\s*\(\s*\.(\w+)\(',core)
  macros=re.findall(r'(?m)^\s*(RM_IHPSG13_1P_2048x64_c2_bm_bist)\s+(\S+)\s*\(',core)
  assert len(cells)>100000 and len(macros)==4,(len(cells),len(macros))
  def q(p):
   p=str(p);assert '{'not in p and '}'not in p and chr(10)not in p;return '{'+p+'}'
  lines=['set_thread_count 1']+['read_liberty '+q(OUT/p)for p in ['std.lib','io.lib','sram.lib']]
  lines+=['read_verilog '+q(OUT/'core.v'),'read_verilog '+q(OUT/'parent.v'),'link_design nssoc_chip']
  representatives=['u_core/'+name+'/'+pin for master,name,pin in cells[:8]]
  representatives+=['u_core/'+name+'/A_CLK'for master,name in macros]
  for pin in representatives:lines+=['if {[llength [get_pins '+q(pin)+']] != 1} {error "Actual core leaf missing"}']
  lines+=['read_sdc '+q(OUT/'parent.sdc'),'read_spef '+q(OUT/'parent.spef'),'read_spef -path u_core '+q(OUT/'core.spef')]
  lines+=['if {[llength [all_clocks]] != 2} {error "Unexpected hierarchical clocks"}','foreach name {shell_main shell_test} {set c [get_clocks $name]; if {[llength $c]!=1 || abs([get_property $c period]-20)>1e-9 || ![get_property $c is_propagated]} {error "Clock changed"}}']
  lines+=['puts NSSOC_ACTUAL_CORE_AND_PARENT_LINKED','report_parasitic_annotation -report_unannotated','check_setup -verbose','report_worst_slack -max -digits 9','report_worst_slack -min -digits 9']
  for delay in ['max','min']:
   lines+=['report_checks -path_delay '+delay+' -group_path_count 100 -format full_clock_expanded -fields {capacitance slew fanout input_pin net} -digits 9 > '+q(OUT/(delay+'-paths.rpt'))]
  lines+=['report_check_types -max_delay -min_delay -max_slew -max_capacitance -max_fanout -violators -digits 9 > '+q(OUT/'violations.rpt'),'puts NSSOC_HIERARCHICAL_BASELINE_STA_COMPLETE']
  (OUT/'hierarchical.tcl').write_text(chr(10).join(lines)+chr(10))
  protected={str(p):sha(p)for p in [Path(__file__),*[p for p in OUT.iterdir()if p.is_file()]]}
  r.update(source_artifacts=[cm,pm,rm],protected_inputs=protected,representative_core_pins=representatives,status='RUNNING_ACTUAL_HIERARCHICAL_BASELINE')
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
  with (OUT/'native.log').open('w')as log:subprocess.run([str(app),'openroad','-exit',str(OUT/'hierarchical.tcl')],stdout=log,stderr=subprocess.STDOUT,check=True)
  text=(OUT/'native.log').read_text();assert 'NSSOC_HIERARCHICAL_BASELINE_STA_COMPLETE'in text
  r['worst_slack_ns']={}
  for delay in ['max','min']:
   matches=re.findall(r'(?m)^worst slack '+delay+r' ([+-]?[0-9]+(?:\.[0-9]+)?)\s*$',text);assert len(matches)==1
   r['worst_slack_ns'][delay]=float(matches[0])
   assert 'Startpoint:'in(OUT/(delay+'-paths.rpt')).read_text()
  assert all(sha(p)==h for p,h in protected.items())
  r.update(status='HIERARCHICAL_BASELINE_STA_EXECUTED_REQUIRES_COVERAGE_AND_CURRENT_ECO_VALIDATION',sources_unchanged=True)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'}
  (OUT/'result.json').write_text(json.dumps(r,indent=2)+chr(10))
if __name__=='__main__':main()
