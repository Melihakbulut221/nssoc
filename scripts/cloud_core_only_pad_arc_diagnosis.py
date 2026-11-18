#!/usr/bin/env python3
"""Read-only native decomposition of remaining bidirectional pad slew."""
import os,json,subprocess,re
from pathlib import Path
from cloud_core_only_hierarchical_baseline import authenticate
from cloud_core_only_postgrt import ROOT,sha
from bootstrap_flow import verify
OUT=ROOT/'hw/soc/out/core-only-pad-arc-diagnosis'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False,physical_mutation=False)
 try:
  z,source,meta=authenticate(44362003609,'3019df728554a279346dfd35fb8d6985935718ee','core-only-parent-corepad-timing-44362003609',14455801272,'5e03e4fc2cfbc8632248a5154cb47812e4a3cf7429b2022dc18fb4ba2d570206')
  files=['chip-detailedroute.odb','chip-shell.nom.spef','shell-cts.sdc','sg13g2_stdcell_slow_1p08V_125C.lib','sg13g2_io_slow_1p08V_3p0V_125C.lib']
  for p in files:(OUT/p).write_bytes(z.read(p))
  pins=[line.split()[0]for line in z.read('slow/violations.rpt').decode().splitlines()if '(VIOLATED)'in line]
  assert len(pins)==22 and all(p.startswith('u_pad_')and p.endswith('/pad')for p in pins)
  r['source_artifact']=meta;r['target_pins']=pins
  def q(p):return '{'+str(p)+'}'
  lines=['set_thread_count 1']+['read_liberty '+q(OUT/p)for p in files[3:]]
  lines+=['read_db '+q(OUT/files[0]),'read_sdc '+q(OUT/files[2]),'read_spef '+q(OUT/files[1])]
  lines+=['report_check_types -max_slew -violators -digits 9 > '+q(OUT/'violations.rpt')]
  reports=[]
  for i,pin in enumerate(pins):
   inst=pin.rsplit('/',1)[0]
   for source_pin in ['c2p','c2p_en']:
    output=OUT/(str(i)+'-'+source_pin+'.rpt');reports.append(output)
    lines+=['if {[llength [get_pins '+q(inst+'/'+source_pin)+']] != 1} {error "Missing pad input"}']
    lines+=['report_dcalc -from '+q(inst+'/'+source_pin)+' -to '+q(pin)+' -max -digits 9 > '+q(output)]
  lines+=['puts NSSOC_PAD_ARC_DIAGNOSIS_COMPLETE']
  script=OUT/'diagnose.tcl';script.write_text(chr(10).join(lines)+chr(10))
  protected={str(p):sha(p)for p in [Path(__file__),ROOT/'scripts/cloud_core_only_hierarchical_baseline.py',ROOT/'scripts/cloud_core_only_postgrt.py',*[OUT/f for f in files],script]}
  r['protected_inputs']=protected
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64')
  with (OUT/'native.log').open('w')as log:subprocess.run([str(app),'openroad','-exit',str(script)],stdout=log,stderr=subprocess.STDOUT,check=True)
  log=(OUT/'native.log').read_text();assert 'NSSOC_PAD_ARC_DIAGNOSIS_COMPLETE'in log and not re.search(r'(?im)^\s*(?:Error[: ]|\[ERROR)',log)
  for p in reports:assert '->'in p.read_text(),str(p)
  assert all(sha(p)==h for p,h in protected.items())
  r.update(status='NATIVE_PAD_ARCS_REPORTED_REQUIRES_ENGINEERING_REVIEW',sources_unchanged=True,reports=len(reports))
 except BaseException as error:r.update(status='FAIL_OR_INCOMPLETE',error=repr(error));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'}
  (OUT/'result.json').write_text(json.dumps(r,indent=2)+chr(10))
if __name__=='__main__':main()
