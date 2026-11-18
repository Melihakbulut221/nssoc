#!/usr/bin/env python3
"""Qualify native hierarchical SPEF accumulation; no product timing claim."""
import os,json,hashlib,subprocess,urllib.request,re
from pathlib import Path
from bootstrap_flow import verify
from cloud_core_only_postgrt import ROOT,sha
OUT=ROOT/'hw/soc/out/core-only-hierarchical-spef-qualification'
def main():
 assert os.environ.get('GITHUB_ACTIONS')=='true';OUT.mkdir(parents=True,exist_ok=False)
 r=dict(source_head=os.environ['GITHUB_SHA'],status='PREPARING',accepted=False,product_timing_proven=False)
 try:
  url='https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib'
  with urllib.request.urlopen(url,timeout=60)as response:data=response.read()
  assert hashlib.sha256(data).hexdigest()=='968b0cfdcefc49a88d9a5c48874769eaad9aba3509e1240b5e14a821bb07a3c4'
  (OUT/'std.lib').write_bytes(data)
  (OUT/'fixture.v').write_text('module core(input a,output z); sg13g2_buf_2 U1(.A(a),.X(z)); endmodule\nmodule top(input A,output Z); wire n; sg13g2_buf_2 U0(.A(A),.X(n)); core u_core(.a(n),.z(Z)); endmodule\n')
  def spef(design,body):
   return '*SPEF "IEEE 1481-1998"\n*DESIGN "'+design+'"\n*DATE "qualification"\n*VENDOR "nssoc"\n*PROGRAM "native hierarchy qualification"\n*VERSION "1"\n*DESIGN_FLOW "NAME_SCOPE LOCAL"\n*DIVIDER /\n*DELIMITER :\n*BUS_DELIMITER [ ]\n*T_UNIT 1 NS\n*C_UNIT 1 PF\n*R_UNIT 1 OHM\n*L_UNIT 1 HENRY\n'+body
  (OUT/'parent.spef').write_text(spef('top','*D_NET n 0.01\n*CONN\n*I U0:X O\n*I u_core:a I\n*CAP\n1 U0:X 0.005\n2 u_core:a 0.005\n*RES\n1 U0:X u_core:a 10\n*END\n'))
  (OUT/'core.spef').write_text(spef('core','*D_NET a 0.02\n*CONN\n*P a I\n*I U1:A I\n*CAP\n1 a 0.01\n2 U1:A 0.01\n*RES\n1 a U1:A 20\n*END\n'))
  protected={str(p):sha(p)for p in [Path(__file__),*OUT.iterdir()]}
  app=Path(os.environ['CLOUD_APPIMAGE']);verify(app,'x86_64');r['cases']={}
  def q(n):return '{'+str(OUT/n)+'}'
  for name,reads,expected in [('parent_then_core',['read_spef '+q('parent.spef'),'read_spef -path u_core '+q('core.spef')],0.03),('core_then_parent',['read_spef -path u_core '+q('core.spef'),'read_spef '+q('parent.spef')],0.01),('parent_only',['read_spef '+q('parent.spef')],0.01)]:
   script=OUT/(name+'.tcl')
   script.write_text('read_liberty '+q('std.lib')+'\nread_verilog '+q('fixture.v')+'\nlink_design top\n'+ '\n'.join(reads)+'\nreport_net -digits 9 n\nputs NSSOC_HIERARCHICAL_SPEF_FIXTURE_COMPLETE\nexit\n')
   protected[str(script)]=sha(script)
   with (OUT/(name+'.log')).open('w')as log:subprocess.run([str(app),'sta','-exit',str(script)],stdout=log,stderr=subprocess.STDOUT,check=True)
   log=(OUT/(name+'.log')).read_text();assert 'NSSOC_HIERARCHICAL_SPEF_FIXTURE_COMPLETE'in log
   assert not re.search(r'(?im)^\s*(?:Error|Warning)[: ]',log),log
   caps=re.findall(r'(?m)^\s*Wire capacitance:\s*([0-9.]+)(?:-([0-9.]+))?\s*$',log);assert len(caps)==1,log
   lo=float(caps[0][0]);hi=float(caps[0][1]or caps[0][0]);assert 0<=lo<=hi
   r['cases'][name]=dict(wire_capacitance_pf_min=lo,wire_capacitance_pf_max=hi,complete_expected_pf=0.03)
   if name=='parent_then_core':assert abs(lo-0.03)<1e-8 and abs(hi-0.03)<1e-8,(name,lo,hi)
   else:
    # Missing hierarchical load RC can produce a pin-cap-dependent range.
    # Both negative controls must lose the child's 0.02 pF contribution.
    assert hi<=0.01000001 and 0.03-hi>=0.01999999,(name,lo,hi)

  assert all(sha(p)==h for p,h in protected.items());r.update(status='PASS_NATIVE_HIERARCHICAL_RC_ACCUMULATION_AND_REVERSED_ORDER_NEGATIVE_CONTROL',sources_unchanged=True,protected_inputs=protected)
 except BaseException as e:r.update(status='FAIL_OR_INCOMPLETE',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p.name!='result.json'}
  (OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
if __name__=='__main__':main()
