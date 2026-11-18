#!/usr/bin/env python3
"""Observe the stock diode boundary without changing native device equations."""
import os,subprocess,json,hashlib,math,urllib.request,shutil
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/native-diode-branch-trace'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(cmd,log,cwd=None,env=None):
 with log.open('w')as f:p=subprocess.run(cmd,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=600)
 return p.returncode

def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False);r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,status='PREPARING',simulator_patched=False,models_modified=False)
 try:
  tmp=Path(os.environ['RUNNER_TEMP'])/'ngspice47-baseline';tmp.mkdir();source=tmp/'source';install=tmp/'install'
  assert run(['apt-get','source','--download-only','ngspice=47+ds-1~bpo13+1'],OUT/'apt-source.log',cwd=tmp)==0,'Signed Debian source retrieval failed'
  dsc=list(tmp.glob('ngspice_47+ds-1~bpo13+1.dsc'));assert len(dsc)==1
  r['source_archives']={p.name:sha(p)for p in tmp.iterdir()if p.is_file()}
  assert r['source_archives']=={'ngspice_47+ds.orig-doc.tar.gz': 'c6b4b63b57c7c3702ed08cdec207796bdfb371458cdad3dc7bf920aaba1797ed', 'ngspice_47+ds.orig.tar.gz': '004b2f7af4c862ed56a89a353e87889b58c21a5a56d13f45a9138d681c3f5dad', 'ngspice_47+ds-1~bpo13+1.dsc': '00ae58e4877677c5560fb1b98dceea05e4e9c67a7cc0023e8bef915d2f7d61dc', 'ngspice_47+ds-1~bpo13+1.debian.tar.xz': '17c4ad73f91b553e475b63ade69b38617134df6887e03c831aeef6efb06e1393'},'Source archives differ from independently verified signed Debian baseline'
  (OUT/'source.dsc').write_bytes(dsc[0].read_bytes())
  assert run(['dpkg-source','-x',str(dsc[0]),str(source)],OUT/'source-unpack.log')==0
  for p in ['src/spicelib/devices/dio/dioload.c','src/include/ngspice/const.h']:
   target=OUT/Path(p).name;target.write_bytes((source/p).read_bytes())
  configure=source/'configure'
  if not configure.exists():assert run(['./autogen.sh'],OUT/'autogen.log',cwd=source)==0
  assert run(['./configure','--with-x=no','--enable-klu','--disable-debug','--prefix='+str(install)],OUT/'configure.log',cwd=source,env=dict(os.environ,CFLAGS='-O2 -g'))==0
  assert run(['make','-j2'],OUT/'make.log',cwd=source)==0
  assert run(['make','install'],OUT/'install.log',cwd=source)==0
  built=install/'bin/ngspice';assert built.is_file()
  shutil.make_archive(str(OUT/'source-runtime'),'gztar',root_dir=install)
  deb=tmp/'published.deb';url='https://deb.debian.org/debian/pool/main/n/ngspice/ngspice_47+ds-1~bpo13+1_amd64.deb'
  with urllib.request.urlopen(url,timeout=120)as f:deb.write_bytes(f.read())
  assert sha(deb)=='400d2ebaefc1dcaaaf9693ac4731535d910fa2c0544552736970aa9ebaad760b'
  assert run(['apt-get','install','-y','--no-install-recommends',str(deb)],OUT/'binary-dependencies.log')==0,'Published binary dependencies unavailable'
  published=tmp/'published';assert run(['dpkg-deb','-x',str(deb),str(published)],OUT/'binary-unpack.log')==0
  original=ROOT/'hw/soc/analog/diagnostics/darea-release';protected={str(original/n):sha(original/n)for n in ['bench.cir','spinit']};protected[str(Path(__file__))]=sha(Path(__file__));r['protected_inputs']=protected;r['cases']={}
  for label,binary in [('published',published/'usr/bin/ngspice'),('source_build',built)]:
   try:
    case=OUT/label;case.mkdir();shutil.copyfile(original/'bench.cir',case/'bench.cir');shutil.copyfile(original/'spinit',case/'spinit')
    assert run([str(binary),'--version'],case/'version.log')==0
    env=dict(os.environ,SPICE_SCRIPTS=str(case))
    code=run([str(binary),'-b','bench.cir'],case/'native.log',cwd=case,env=env)
    text=(case/'native.log').read_text(errors='replace');wave=case/'wave.dat';rows=[]
    if wave.exists():
     for line in wave.read_text().splitlines()[1:]:
      if line.strip():
       row=[float(x)for x in line.split()];assert len(row)==3 and all(math.isfinite(x)for x in row);rows.append(row)
    assert rows and all(rows[i][0]>=rows[i-1][0]for i in range(1,len(rows)))
    equal_times=sum(rows[i][0]==rows[i-1][0]for i in range(1,len(rows)))
    expected='timestep too small'in text.lower()and 20e-9<rows[-1][0]<24e-9
    r['cases'][label]=dict(returncode=code,binary_sha256=sha(binary),samples=len(rows),equal_printed_timestamps=equal_times,partial_failed_waveform=True,last_time=rows[-1][0],timestep_failure_reproduced=expected,klu_selected='klu'in text.lower(),version=(case/'version.log').read_text())
    assert 'NSSOC_DIODE_SOLVER_READBACK'in text and 'NSSOC_DIODE_CAPTURE_END'in text
   except BaseException as e:r['cases'][label]=dict(error=repr(e),timestep_failure_reproduced=False,klu_selected=False)
  assert all(x['timestep_failure_reproduced']and x['klu_selected']for x in r['cases'].values()),'Unchanged baseline behavior not reproduced; inspect before any patch'
  assert abs(r['cases']['published']['last_time']-r['cases']['source_build']['last_time'])<1e-12,'Baseline failure times differ by more than one maximum time step'
  target=source/'src/spicelib/devices/dio/dioload.c'
  before=target.read_text();assert sha(target)=='865bbecef98de2237a1cceccf088fb77e6d868f9f913023827ac910232c35b38'
  anchor='next2:      *(ckt->CKTstate0 + here->DIOvoltage) = vd;'
  assert before.count(anchor)==1
  trace="""next2:
            {
                static unsigned long nssoc_trace_count = 0;
                if (ckt->CKTtime >= 21.325e-9 && ckt->CKTtime <= 21.34e-9
                    && fabs(vd + 3*vte) < 2e-6 && nssoc_trace_count < 20000) {
                    fprintf(stderr, "NSSOC_DIO_TRACE %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g %d\\n",
                        ckt->CKTtime, ckt->CKTdelta, vd, -3*vte,
                        cd, gd, here->DIOcap,
                        *(ckt->CKTstate0 + here->DIOcapCharge),
                        *(ckt->CKTstate0 + here->DIOvoltage), ckt->CKTnoncon);
                    nssoc_trace_count++;
                }
            }
            *(ckt->CKTstate0 + here->DIOvoltage) = vd;"""
  csources={str(p):sha(p)for p in source.rglob('*')if p.is_file()and p.suffix in ['.c','.h']}
  component_anchor='                    diffcap = here->DIOtTransitTime*gd;'
  assert before.count(component_anchor)==1
  component_trace="""
                    {
                        static unsigned long nssoc_component_count = 0;
                        if (ckt->CKTtime >= 21.325e-9 && ckt->CKTtime <= 21.34e-9
                            && fabs(vd+3*vte)<2e-6 && nssoc_component_count<20000) {
                            fprintf(stderr,"NSSOC_DIO_COMPONENT %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g %.17g\\n",
                                ckt->CKTtime,ckt->CKTdelta,vd,cd,gd,deplcharge,diffcharge,deplcap,diffcap,CONSTe,
                                (double)(vd>=-3*vte ? 0 : ((!model->DIObreakdownVoltageGiven || vd>=-here->DIOtBrkdwnV) ? 1 : 2)),
                                here->DIOtBrkdwnV,here->DIOtSatCur,here->DIOtRecSatCur,vtebrk,here->DIOtTransitTime,here->DIOtemp);
                            nssoc_component_count++;
                        }
                    }
"""
  target.write_text(before.replace(anchor,trace).replace(component_anchor,component_anchor+component_trace))
  assert all(sha(p)==h for p,h in csources.items()if Path(p)!=target)
  (OUT/'instrumented-dioload.c').write_bytes(target.read_bytes())
  r['instrumentation']=dict(before_sha256=csources[str(target)],after_sha256=sha(target),only_changed_source=str(target.relative_to(source)),equations_changed=False,trace_limit=20000)
  assert run(['make','-j2'],OUT/'trace-make.log',cwd=source)==0
  assert run(['make','install'],OUT/'trace-install.log',cwd=source)==0
  case=OUT/'trace';case.mkdir()
  for n in ['bench.cir','spinit']:shutil.copyfile(original/n,case/n)
  code=run([str(built),'-b','bench.cir'],case/'native.log',cwd=case,env=dict(os.environ,SPICE_SCRIPTS=str(case)))
  text=(case/'native.log').read_text(errors='replace')
  rows=[]
  for line in (case/'wave.dat').read_text().splitlines()[1:]:
   if line.strip():
    row=[float(x)for x in line.split()];assert len(row)==3 and all(math.isfinite(x)for x in row);rows.append(row)
  assert rows and all(rows[i][0]>=rows[i-1][0]for i in range(1,len(rows)))
  assert 'timestep too small'in text.lower() and 'KLU'in text and 'NSSOC_DIODE_CAPTURE_END'in text
  assert abs(rows[-1][0]-r['cases']['source_build']['last_time'])<1e-12
  traces=[]
  for line in text.splitlines():
   if line.startswith('NSSOC_DIO_TRACE '):
    values=[float(x)for x in line.split()[1:]];assert len(values)==10 and all(math.isfinite(x)for x in values);traces.append(values)
  assert traces and len(traces)<20000,'Missing or saturated boundary trace'
  (OUT/'boundary-trace.json').write_text(json.dumps(dict(columns=['time','delta','vd','boundary','integrated_cd','integrated_gd','cap','charge','previous_vd','noncon'],rows=traces),indent=2)+'\n')
  components=[]
  for line in text.splitlines():
   if line.startswith('NSSOC_DIO_COMPONENT '):
    values=[float(x)for x in line.split()[1:]];assert len(values)==17 and all(math.isfinite(x)for x in values);components.append(values)
  assert components and len(components)<20000
  (OUT/'component-trace.json').write_text(json.dumps(dict(columns=['time','delta','vd','dc_current','dc_conductance','depletion_charge','diffusion_charge','depletion_cap','diffusion_cap','CONSTe','branch_0_forward_1_reverse_2_breakdown','adjusted_breakdown_voltage','sat_current','recombination_sat_current','vte_breakdown','transit_time','temperature'],rows=components),indent=2)+'\n')
  r['component_trace_rows']=len(components)
  r['trace_result']=dict(returncode=code,binary_sha256=sha(built),samples=len(rows),last_time=rows[-1][0],trace_rows=len(traces),forward_rows=sum(v[2]>=v[3]for v in traces),reverse_rows=sum(v[2]<v[3]for v in traces),min_delta=min(v[1]for v in traces),baseline_failure_preserved=True)
  assert all(sha(p)==h for p,h in protected.items())
  assert all(sha(original/n)==sha(case/n)for n in ['bench.cir','spinit'])
  r.update(status='STOCK_EQUATION_BRANCH_TRACE_CAPTURED_NOT_A_FIX',sources_unchanged=True,simulator_patched=True,production_runtime_replaced=False,pad_timing_closed=False)

 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:
  subprocess.run(['dpkg-query','-W'],stdout=(OUT/'installed-packages.txt').open('w'),check=False)
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
