#!/usr/bin/env python3
"""Native DC branch diagnostics on authenticated stock/candidate runtimes."""
import os,json,subprocess,hashlib,zipfile,tarfile,io,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/native-diode-dc-boundary'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def api(p):return json.loads(subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/'+p]))
def run(binary,folder,bench,spinit):
 folder.mkdir();(folder/'bench.cir').write_text(bench);(folder/'spinit').write_bytes(spinit)
 with (folder/'native.log').open('w')as log:p=subprocess.run([str(binary),'-b','bench.cir'],cwd=folder,env=dict(os.environ,SPICE_SCRIPTS=str(folder)),stdout=log,stderr=subprocess.STDOUT)
 text=(folder/'native.log').read_text();assert p.returncode==0 and 'NSSOC_DC_CAPTURE_END'in text and 'KLU'in text
 assert not any(x in text.lower()for x in ['simulation(s) aborted','timestep too small','error:','singular matrix'])
 rows=[]
 for line in (folder/'wave.dat').read_text().splitlines()[1:]:
  if line.strip():
   row=[float(x)for x in line.split()];assert len(row)==8 and all(math.isfinite(x)for x in row);rows.append(row)
 assert len(rows)>100
 return rows

def deck(original,start,stop,step):
 prefix=original.split('.control')[0];prefix='\n'.join('Vdrive gate 0 0'if line.startswith('Vdrive ')else line for line in prefix.splitlines())+'\n'
 vectors='v(gate) i(vdrive) @d1[vd] @d1[id] @d1[gd] @d1[cd] @d1[charge]'
 return prefix+'.control\nset wr_singlescale\nset wr_vecnames\nset numdgt=17\nsave '+vectors+'\noption method=gear maxord=2 itl4=100\ndc Vdrive '+str(start)+' '+str(stop)+' '+str(step)+'\noption\nwrdata wave.dat '+vectors+'\necho NSSOC_DC_CAPTURE_END\nquit\n.endc\n.end\n'

def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False);r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,status='PREPARING',production_equivalent=False,probe='DC excitation replaces release waveform; unchanged PDK model and solver tolerances')
 try:
  source=api('actions/runs/44391317766');assert source['status']=='completed'and source['conclusion']=='failure'and source['head_sha']=='d70786a5925f585719fa3f7fedcf6fbd36ef97cc'and source['run_attempt']==1
  meta=api('actions/artifacts/14468157113');digest='f72629053a14778180cbce47d2d680f041abde71b9309d04bc71563720685e66';assert meta['digest']=='sha256:'+digest and meta['workflow_run']['id']==source['id']
  raw=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/artifacts/14468157113/zip']);assert hashlib.sha256(raw).hexdigest()==digest
  z=zipfile.ZipFile(io.BytesIO(raw));prior=json.loads(z.read('result.json'));assert prior['simulator_patched']and prior['candidate']['completed_50ns']is False and prior['baseline_reproduced_before_patch']
  for n,h in prior['outputs'].items():assert hashlib.sha256(z.read(n)).hexdigest()==h
  tmp=Path(os.environ['RUNNER_TEMP'])/'native-diode-dc';tmp.mkdir();fixture=ROOT/'hw/soc/analog/diagnostics/darea-release';original=(fixture/'bench.cir').read_text();spinit=(fixture/'spinit').read_bytes()
  protected={str(p):sha(p)for p in [Path(__file__),fixture/'bench.cir',fixture/'spinit']};r.update(protected_inputs=protected,source_admission=dict(run=source['id'],artifact=meta['id'],digest=digest),cases={})
  boundary=-3*1.009*1.38064852e-23*398.15/1.6021766208e-19;r['junction_boundary_v']=boundary
  for label,archive,key in [('stock','source-runtime.tar.gz','source_build'),('derivative','candidate-runtime.tar.gz','candidate')]:
   try:
    runtime=tmp/label;runtime.mkdir()
    with tarfile.open(fileobj=io.BytesIO(z.read(archive)),mode='r:gz')as tf:tf.extractall(runtime,filter='data')
    binary=runtime/'bin/ngspice';expected=prior['cases'][key]['binary_sha256']if key=='source_build'else prior['candidate']['binary_sha256'];assert sha(binary)==expected
    protected[str(binary)]=sha(binary)
    coarse=run(binary,OUT/(label+'-coarse'),deck(original,0.08,0.13,1e-6),spinit)
    crossings=[i for i in range(len(coarse)-1)if (coarse[i][3]-boundary)*(coarse[i+1][3]-boundary)<=0];assert len(crossings)==1
    mid=(coarse[crossings[0]][0]+coarse[crossings[0]+1][0])/2;lo=mid-3e-6;hi=mid+3e-6
    fine=run(binary,OUT/(label+'-fine'),deck(original,lo,hi,1e-9),spinit)
    assert abs(fine[0][0]-lo)<1e-12 and abs(fine[-1][0]-hi)<2e-9
    crossings=[i for i in range(len(fine)-1)if (fine[i][3]-boundary)*(fine[i+1][3]-boundary)<=0];assert len(crossings)==1;k=crossings[0]
    slopes=[]
    for i in [k-3,k-2,k-1,k+2,k+3,k+4]:
     a,b=fine[i-1],fine[i+1];dv=b[3]-a[3];assert dv!=0
     slopes.append(dict(junction_v=fine[i][3],region='forward'if fine[i][3]>=boundary else 'reverse',current_slope=(b[4]-a[4])/dv,native_gd=fine[i][5],charge_slope=(b[7]-a[7])/dv,native_cap=fine[i][6]))
    r['cases'][label]=dict(binary_sha256=expected,coarse_samples=len(coarse),fine_samples=len(fine),crossing_index=k,bracket_rows=fine[k-1:k+3],slopes=slopes,columns=['sweep','gate_v','drive_current','junction_v','diode_current','conductance','capacitance','charge'])
   except BaseException as e:r['cases'][label]=dict(error=repr(e))
  assert len(r['cases'])==2 and all('error'not in x for x in r['cases'].values())
  assert all(sha(p)==h for p,h in protected.items());r.update(status='NATIVE_DC_BOUNDARY_SAMPLED_REQUIRES_ANALYSIS_NOT_MODEL_QUALIFICATION',sources_unchanged=True)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
