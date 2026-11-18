#!/usr/bin/env python3
"""Compare stock ngspice47 source build and published binary, no model patches."""
import os,subprocess,json,hashlib,math,urllib.request,shutil,zipfile,io
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/native-diode-derivative-experiment'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def run(cmd,log,cwd=None,env=None):
 with log.open('w')as f:p=subprocess.run(cmd,cwd=cwd,env=env,stdout=f,stderr=subprocess.STDOUT)
 return p.returncode

def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False);r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,status='PREPARING',simulator_patched=False,models_modified=False)
 try:
  def evidence_api(path,raw=False):
   data=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+path])
   return data if raw else json.loads(data)
  baseline=evidence_api('actions/runs/44390258723');assert baseline['status']=='completed'and baseline['conclusion']=='success'and baseline['head_sha']=='569086f1abcf060a418786557805018e307a8db9'and baseline['run_attempt']==1
  aid=int(os.environ['BASELINE_ARTIFACT_ID']);digest=os.environ['BASELINE_ARTIFACT_DIGEST'];assert len(digest)==64
  meta=evidence_api('actions/artifacts/'+str(aid));assert meta['workflow_run']['id']==baseline['id']and meta['digest']=='sha256:'+digest
  raw=evidence_api('actions/artifacts/'+str(aid)+'/zip',True);assert hashlib.sha256(raw).hexdigest()==digest
  archive=zipfile.ZipFile(io.BytesIO(raw));prior=json.loads(archive.read('result.json'));assert prior['status']=='UNMODIFIED_SOURCE_AND_PUBLISHED_BINARY_REPRODUCE_DIODE_FAILURE'and prior['sources_unchanged']
  for n,h in prior['outputs'].items():assert hashlib.sha256(archive.read(n)).hexdigest()==h
  r['baseline_admission']=dict(run=baseline['id'],head=baseline['head_sha'],artifact=aid,digest=digest)
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
  candidate_dir=ROOT/'hw/soc/analog/diagnostics/darea-release';manifest_path=candidate_dir/'derivative-candidate.json';patch_path=candidate_dir/'ngspice47-voltage-derivative.patch'
  manifest=json.loads(manifest_path.read_text());assert manifest['experimental_only']and r['source_archives']==manifest['source_archives']==prior['source_archives']
  target=source/manifest['source_file'];assert sha(target)==manifest['before_sha256']and sha(patch_path)==manifest['patch_sha256']
  protected.update({str(p):sha(p)for p in [manifest_path,patch_path]})
  c_sources={str(p):sha(p)for p in source.rglob('*')if p.is_file()and p.suffix in ['.c','.h']}
  assert run(['patch','--batch','--fuzz=0','-p1','-i',str(patch_path)],OUT/'candidate-patch.log',cwd=source)==0
  assert sha(target)==manifest['after_sha256']
  assert all(sha(p)==h for p,h in c_sources.items()if Path(p)!=target)
  r.update(simulator_patched=True,candidate_patch_manifest=manifest,baseline_reproduced_before_patch=True)
  assert run(['make','-j2'],OUT/'candidate-make.log',cwd=source)==0
  assert run(['make','install'],OUT/'candidate-install.log',cwd=source)==0
  shutil.make_archive(str(OUT/'candidate-runtime'),'gztar',root_dir=install)
  case=OUT/'candidate';case.mkdir();shutil.copyfile(original/'bench.cir',case/'bench.cir');shutil.copyfile(original/'spinit',case/'spinit')
  assert run([str(built),'--version'],case/'version.log')==0
  code=run([str(built),'-b','bench.cir'],case/'native.log',cwd=case,env=dict(os.environ,SPICE_SCRIPTS=str(case)))
  text=(case/'native.log').read_text(errors='replace');wave=case/'wave.dat';rows=[]
  if wave.exists():
   for line in wave.read_text().splitlines()[1:]:
    if line.strip():
     row=[float(x)for x in line.split()];assert len(row)==3 and all(math.isfinite(x)for x in row);rows.append(row)
  assert rows and all(rows[i][0]>=rows[i-1][0]for i in range(1,len(rows)))
  completed=code==0 and abs(rows[-1][0]-50e-9)<1e-15 and 'timestep too small'not in text.lower()and 'simulation(s) aborted'not in text.lower()
  r['candidate']=dict(returncode=code,binary_sha256=sha(built),samples=len(rows),last_time=rows[-1][0],equal_printed_timestamps=sum(rows[i][0]==rows[i-1][0]for i in range(1,len(rows))),completed_50ns=completed,version=(case/'version.log').read_text())
  assert 'NSSOC_DIODE_SOLVER_READBACK'in text and 'NSSOC_DIODE_CAPTURE_END'in text and 'KLU'in text
  assert all(sha(p)==h for p,h in protected.items())
  r.update(status='DERIVATIVE_CANDIDATE_COMPLETES_SINGLE_FIXTURE_REQUIRES_FULL_QUALIFICATION'if completed else 'DERIVATIVE_CANDIDATE_DOES_NOT_CLOSE_SINGLE_FIXTURE',sources_unchanged=True,production_runtime_replaced=False,pad_timing_closed=False)
  assert completed,'Candidate did not complete the original 50ns fixture; preserve evidence and investigate'

 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:
  subprocess.run(['dpkg-query','-W'],stdout=(OUT/'installed-packages.txt').open('w'),check=False)
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
