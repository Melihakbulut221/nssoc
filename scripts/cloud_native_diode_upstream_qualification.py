#!/usr/bin/env python3
"""Qualify an immutable upstream diode model, never rewrite production PDK."""
import os,json,hashlib,subprocess,urllib.request,math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'hw/soc/out/native-diode-upstream-qualification'
PIN='013bb30bb7c8f9d3c85173378597ac992ef7a272'
MODEL_HASH='e6211bd0318122fbeb707498ede893223c332098cbb21c441b28b9d8c365e83d'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def download(url,path,h):
 with urllib.request.urlopen(url,timeout=120) as f:raw=f.read()
 assert hashlib.sha256(raw).hexdigest()==h;path.write_bytes(raw)
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],accepted=False,production_pdk_replaced=False,pad_timing_closed=False,status='PREPARING')
 try:
  original=ROOT/'hw/soc/analog/diagnostics/darea-release';bench=(original/'bench.cir').read_text()
  assert sha(original/'bench.cir')=='6ed5c2504ba8b949a8736fb203a9568901486b52f9ef5bca43183018bb660470'
  protected={str(p):sha(p)for p in [Path(__file__),original/'bench.cir',original/'spinit']}
  library=OUT/'upstream-diodes.lib';url='https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/'+PIN+'/ihp-sg13g2/libs.tech/ngspice/models/diodes.lib'
  download(url,library,MODEL_HASH)
  deb=Path(os.environ['RUNNER_TEMP'])/'ngspice47.deb'
  download('https://deb.debian.org/debian/pool/main/n/ngspice/ngspice_47+ds-1~bpo13+1_amd64.deb',deb,'400d2ebaefc1dcaaaf9693ac4731535d910fa2c0544552736970aa9ebaad760b')
  with (OUT/'install.log').open('w')as log:subprocess.run(['apt-get','install','-y','--no-install-recommends',str(deb)],stdout=log,stderr=subprocess.STDOUT,check=True,timeout=300)
  binary=Path('/usr/bin/ngspice');r['binary_sha256']=sha(binary)
  r['upstream']=dict(commit=PIN,url=url,sha256=MODEL_HASH,fix_pr='https://github.com/IHP-GmbH/IHP-Open-PDK/pull/1294',issue='https://github.com/IHP-GmbH/IHP-Open-PDK/issues/1288')
  marker='*#######################################################################'
  prefix=bench[:bench.index(marker)];tail=bench[bench.index('Vdrive gate 0 PWL'):]
  assert prefix.count('.temp 125')==1 and tail.count('D1 0 gate darea area=0.3072')==1
  r['cases']={}
  for label,temp,old in [('original_125',125,True),('upstream_m40',-40,False),('upstream_27',27,False),('upstream_125',125,False)]:
   case=OUT/label;case.mkdir();deck=bench if old else prefix.replace('.temp 125','.temp '+str(temp))+library.read_text()+'\n'+tail
   (case/'bench.cir').write_text(deck);(case/'spinit').write_bytes((original/'spinit').read_bytes())
   try:
    with (case/'native.log').open('w')as log:code=subprocess.run([str(binary),'-b','bench.cir'],cwd=case,env=dict(os.environ,SPICE_SCRIPTS=str(case)),stdout=log,stderr=subprocess.STDOUT,timeout=120).returncode
    text=(case/'native.log').read_text(errors='replace');rows=[]
    for line in (case/'wave.dat').read_text().splitlines()[1:]:
     if line.strip():
      v=[float(x)for x in line.split()];assert len(v)==3 and all(math.isfinite(a)for a in v);rows.append(v)
    assert rows and all(rows[i][0]>=rows[i-1][0]for i in range(1,len(rows)))
    assert 'KLU'in text and 'NSSOC_DIODE_CAPTURE_END'in text and 'NSSOC_DIODE_SOLVER_READBACK'in text
    complete=code==0 and abs(rows[-1][0]-50e-9)<1e-15 and 'timestep too small'not in text.lower()and 'simulation(s) aborted'not in text.lower()
    reproduced='timestep too small'in text.lower()and abs(rows[-1][0]-2.13261685e-8)<1e-12
    r['cases'][label]=dict(temperature=temp,samples=len(rows),last_time=rows[-1][0],returncode=code,completed_50ns=complete,original_failure_reproduced=reproduced,deck_sha256=sha(case/'bench.cir'))
   except BaseException as e:r['cases'][label]=dict(error=repr(e),completed_50ns=False,original_failure_reproduced=False)
  assert r['cases']['original_125']['original_failure_reproduced']
  assert all(r['cases'][k]['completed_50ns']for k in ['upstream_m40','upstream_27','upstream_125'])
  assert all(sha(p)==h for p,h in protected.items())and sha(library)==MODEL_HASH
  r.update(status='UPSTREAM_MODEL_CLOSES_REDUCED_TRANSIENT_AT_THREE_TEMPERATURES_REQUIRES_FULL_PAD_QUALIFICATION',sources_unchanged=True,protected_inputs=protected)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'}
  (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
