from pathlib import Path
import json,hashlib,importlib.util,sys
R=Path.cwd();O=R/'hw/soc/out';B=O/'pcie-first91-clock-bias-screen-20261010';B.mkdir();A=O/'pcie-compact753-loaded-20261010';src=O/'pcie-gain-v2-physical753-20261010/includes01/divider-hybrid-open.spice';M=O/'pcie-tail115-connected570-source-20261006/compose_source01.py';sp=importlib.util.spec_from_file_location('composer',M);m=importlib.util.module_from_spec(sp);sp.loader.exec_module(m);sys.path.insert(0,str(R/'scripts'));import pcie_pll_native_fixture_v1 as n
s=src.read_text();root=[s.split('.subckt ')[1].split()[0].lower(),'xdiv',['0','clkn','clkp','dvdd','qn','qp','0','0','0']];rows,wires=m.expand(m.definitions({src.name:s}),root);assert len(rows)==91
extra=['v(clkp)','v(clkn)','v(qp)','v(qn)','i(vdd)'];allv=n.vectors(rows,[]);extra=[x for x in extra if x not in allv];vectors=n.vectors(rows,extra);nhbt=sum(x['model']=='npn13g2'for x in rows);count=len(vectors);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();(B/'divider-original.spice').write_text(s)
r=dict(status='PREPARED_ISOLATED_FIRST91_PARAMETER_SCREEN_NOT_LAYOUT',root=root,devices=rows,wires=wires,extra_vectors=extra,columns=count+1,hbts=nhbt,inputs={str(p):sha(p)for p in [src,M,A/'native02/closed-01/result.json',A/'loaded-clock-diagnosis05.json']},scope='Isolated first divider with original91 intrinsic devices and original component wire RC. Ideal8GHz clock 1.08V common-mode/0.14V single-side amplitude approximates measured loaded-parent source. Output50fF perpin is an explicit experimental load, NOT extracted parent load. Pullup resistance parameter-only screen; no new geometry or parent/mainchip/PHY acceptance.')
(B/'preparation01.json').write_text(json.dumps(r,indent=2)+'\n')
for name in ['header1648_01.py','startup753.py','save_batches_parent.py','engine_parent753.py']:
 s=(A/name).read_text()
 if name=='startup753.py':s=s.replace('len(flags) == 102',f'len(flags) == {nhbt}').replace('Exact 102 native',f'Exact {nhbt} native')
 if name=='save_batches_parent.py':s=s.replace('2131',str(count))
 if name=='engine_parent753.py':s=s.replace('width==2132*8',f'width=={count+1}*8').replace('== 753, "Every device screen retained"','== 91, "Every device screen retained"').replace('PARENT753','ISOLATED91_SCREEN').replace('Finite27C connected753;2131saved vectors/2132columns;240000-row cap;SSD4GiB point/5GiB aggregate;complete measured parentmetalRC included; ideal commonbulk unqualified; no lock/PVT/fullPHY qualification.','Isolated91 experimental drive and load,20ns/.25ps, all91bounds retained, no physical acceptance.')
 (B/name).write_text(s)
(B/'prepare01.py').write_bytes(Path(__file__).read_bytes());print(r['columns'],nhbt,len(wires))
