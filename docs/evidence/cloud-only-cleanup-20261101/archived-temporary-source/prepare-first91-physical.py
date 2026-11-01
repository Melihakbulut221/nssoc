from pathlib import Path
import json,hashlib,sys,importlib.util
R=Path.cwd();O=R/'hw/soc/out';A=O/'pcie-first91-clock-bias-screen-20261010';L=O/'pcie-divider-first28-layout-20261010';B=O/'pcie-first28-physical91-20261010';B.mkdir();C=L/'wire01/composition-controls01.json';assert json.loads(C.read_text())['status']=='PASS_ALL91_NATIVE_DEVICES_FRESH_WIRES_AND_SIX_COMPOSITION_FAULTS';G=L/'check02/result.json';assert json.loads(G.read_text())['status'].startswith('PASS')
source=L/'wire01/divider91-wire01.spice';s=source.read_text();h=next(x.split()for x in s.splitlines()if x.startswith('.subckt'));mapping={x:x.lower()for x in h[2:]};mapping.update(AVSS='0',SUB='0',DIV_AVDD='dvdd',wire_cref='0');root=[h[1],'xdiv',[mapping[n]for n in h[2:]]];M=O/'pcie-tail115-connected570-source-20261006/compose_source01.py';sp=importlib.util.spec_from_file_location('composer',M);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);rows,wires=m.expand(m.definitions({source.name:s}),root);assert len(rows)==91;sys.path.insert(0,str(R/'scripts'));import pcie_pll_native_fixture_v1 as n
extra=[x for x in ['v(clkp)','v(clkn)','v(qp)','v(qn)','i(vdd)']if x not in n.vectors(rows,[])];vectors=n.vectors(rows,extra);count=len(vectors);(B/'divider-physical.spice').write_text(s)
P=dict(status='PREPARED_NEW_FIRST28_PHYSICAL91_COMPONENT_RC_TRANSIENT',root=root,devices=rows,wires=wires,extra_vectors=extra,columns=count+1,inputs={str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [source,G,C,L/'wire01/audit02.json',L/'wire01/native-mutations01.json',L/'binding01.json',M,A/'run01.py']},scope='New first28 physical91 geometry, nativeDRC/hier+flatLVS, fresh379R646C,13rawRCfaults+6compositionfaults. Same isolated20ns/.25ps/27C ideal8GHz1.08Vcommon/.14Vsingle-side50fFoutputboundary as parametertrial. All91devicechecks andstrictstartup. No actualparentload, foundryPEX/PVT/fullPHY/mainchipacceptance.')
(B/'preparation01.json').write_text(json.dumps(P,indent=2)+'\n');(B/'prepare01.py').write_bytes(Path(__file__).read_bytes())
for name in ['engine_parent753.py','header1648_01.py','startup753.py','save_batches_parent.py']:
 s=(A/name).read_text().replace('width==305*8',f'width=={count+1}*8')
 if name=='save_batches_parent.py':s=s.replace('304',str(count))
 s=s.replace('ISOLATED91_SCREEN','PHYSICAL91_COMPONENT');(B/name).write_text(s)
s=(A/'run01.py').read_text();ma=s[s.index('def measurement('):s.index('e.config=config;')]
header='''from pathlib import Path
import json,hashlib,sys,shutil,copy
import numpy as np
R=Path.cwd();B=Path(__file__).resolve().parent;P=json.loads((B/'preparation01.json').read_text());sys.path.insert(0,str(R/'scripts'));import engine_parent753 as e
import save_batches_parent as batch
e.batch=batch;e.NATIVE_ROOT=B/'native01';e.SOURCE=B/'divider-physical.spice';e.MAX_ROWS=100000;e.POINT_LIMIT=400*1024**2;e.AGGREGATE_LIMIT=500*1024**2;e.OWN_LIMIT=e.AGGREGATE_LIMIT;e.SSD_FLOOR=9*1024**3;e.OBS=['time','v(clkp)','v(clkn)','v(qp)','v(qn)']
def config(value=.7,fault=''):
 assert value==.7 and not fault
 for p,h in P['inputs'].items():assert hashlib.sha256(Path(p).read_bytes()).hexdigest()==h
 rows=copy.deepcopy(P['devices']);texts={'divider.spice':e.SOURCE.read_text()}
 fixture=['VDD dvdd 0 PWL(0 0 500p 2.5)','BCP clkp 0 V=min(time/500p,1)*(1.08+0.14*sin(2*pi*8e9*time))','BCN clkn 0 V=min(time/500p,1)*(1.08-0.14*sin(2*pi*8e9*time))','CQP qp 0 50f','CQN qn 0 50f']
 c=dict(case='first28_new_physical91_8GHz',sources=[str(p)for p in B.glob('*.py')]+[str(B/'preparation01.json'),str(e.SOURCE)],roots=[P['root']],fixture=fixture,step_s=.25e-12,stop_s=20e-9,window_s=[4e-9,20e-9],extra_vectors=P['extra_vectors'],maximum_rows=e.MAX_ROWS,layout_changed=True,full_pll_layout_complete=False,scope=P['scope'])
 assert len(rows)==91 and len(e.n.vectors(rows,c['extra_vectors']))+1==P['columns'];return c,rows,texts
'''
(B/'run01.py').write_text(header+ma+"\ne.config=config;e.measurement=measurement\nif __name__=='__main__':\n assert shutil.disk_usage(B).free>10*1024**3\n r=e.run(e.NATIVE_ROOT/'nominal-01',.7);print(r['status'],flush=True)\n")
for name in ['review-functional02.py','review-electrical02.py']:
 s=(A/name).read_text().replace("N=B/'native01'/('pullup'+sys.argv[1]+'-01')", "N=B/'native01/nominal-01'").replace("('functional-review02-'+sys.argv[1]+'.json')", "'functional-review02.json'").replace("('electrical-review02-'+sys.argv[1]+'.json')", "'electrical-review02.json'").replace('ISOLATED91_SCREEN','PHYSICAL91_COMPONENT').replace('width==305',f'width=={count+1}');(B/name).write_text(s)
print('PREPARED',count+1,len(wires))
