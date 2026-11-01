from pathlib import Path
import json,shutil,hashlib,sys,importlib.util
R=Path.cwd();O=R/'hw/soc/out';A=O/'pcie-first28-physical91-20261010';B=O/'pcie-first28-supply-boundary91-20261010';B.mkdir();source=A/'divider-physical.spice';s=source.read_text();h=next(x.split()for x in s.splitlines()if x.startswith('.subckt'));old=json.loads((A/'preparation01.json').read_text());root=old['root'];assert root[2][h[2:].index('AVSS')]=='0';root[2][h[2:].index('AVSS')]='vgnd'
M=O/'pcie-tail115-connected570-source-20261006/compose_source01.py';sp=importlib.util.spec_from_file_location('composer',M);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);rows,wires=m.expand(m.definitions({source.name:s}),root);assert len(rows)==91;sys.path.insert(0,str(R/'scripts'));import pcie_pll_native_fixture_v1 as n
extra=[x for x in ['v(clkp)','v(clkn)','v(qp)','v(qn)','i(vdd)','i(vgnd)']if x not in n.vectors(rows,[])];count=len(n.vectors(rows,extra));P=dict(old,root=root,devices=rows,wires=wires,extra_vectors=extra,columns=count+1);P['inputs'].update({str(p):hashlib.sha256(p.read_bytes()).hexdigest()for p in [source,A/'preparation01.json',Path(__file__),M]});P['scope']='Same physical91 model under explicit hypothetical supply-boundary diagnostic:2.42V VDD/0.08V AVSS, ideal8GHz1.08Vcommon/.14Vsingle-side150fF load,20ns/.25ps27C. Motivated by observed additional approximate80mV supply/ground shifts in live parent relative to completed component. Not actual parent stimulus/PVT/nominal8GHz qualification. All91 original electrical and division/swing criteria retained.';(B/'preparation01.json').write_text(json.dumps(P,indent=2)+'\n');shutil.copyfile(source,B/source.name);shutil.copyfile(Path(__file__),B/'prepare01.py')
for name in ['engine_parent753.py','header1648_01.py','startup753.py','save_batches_parent.py']:
 s=(A/name).read_text().replace('width==306*8',f'width=={count+1}*8')
 if name=='save_batches_parent.py':s=s.replace('305',str(count))
 (B/name).write_text(s)
s=(A/'run01.py').read_text().replace("'VDD dvdd 0 PWL(0 0 500p 2.5)'","'VDD dvdd 0 PWL(0 0 500p 2.42)','VGND vgnd 0 PWL(0 0 500p 0.08)'").replace('CQP qp 0 50f','CQP qp 0 150f').replace('CQN qn 0 50f','CQN qn 0 150f').replace('layout_changed=True','layout_changed=False').replace('first28_new_physical91_8GHz','first28_supply_boundary91_8GHz');(B/'run01.py').write_text(s)
for name in ['review-functional02.py','review-electrical02.py']:
 s=(A/name).read_text().replace('width==306',f'width=={count+1}');(B/name).write_text(s)
s='''from pathlib import Path
import time,json,subprocess,shutil
B=Path(__file__).resolve().parent;R=Path.cwd();prior=B.parent/'pcie-first28-boundary91-20261010/result03.json'
while not prior.exists()or json.loads(prior.read_text())['status']!='COMPLETE_THREE_BOUNDARY_POINTS_INDEPENDENTLY_REVIEWED':time.sleep(20)
while shutil.disk_usage(B).free<12*1024**3:time.sleep(20)
for name in ['run01.py','review-functional02.py','review-electrical02.py']:
 with (B/(name+'.log')).open('x')as f:subprocess.run([R/'.venv/bin/python',B/name],stdout=f,stderr=subprocess.STDOUT,check=True)
r=json.loads((B/'native01/nominal-01/result.json').read_text());(B/'after-native03.json').write_text(json.dumps(dict(status='COMPLETE_SUPPLY_BOUNDARY91_INDEPENDENTLY_REVIEWED',native_status=r['status'],checks=r['measurement']['checks'],electrical_passed=r['safety']['passed'],parent_accepted=False,full_phy_accepted=False),indent=2)+'\\n')
''';(B/'start03.py').write_text(s);print('PREPARED',count+1)
