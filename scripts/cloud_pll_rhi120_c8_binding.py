#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Bind every actual PLL845 native device to pinned PDK model semantics."""
import argparse,ast,copy,json,math,os,re,shutil,subprocess,sys,tarfile
from collections import Counter
from decimal import Decimal
from pathlib import Path
import compare_cloud_routed_endpoints as reports
import build_pll845_native_models as models
from cloud_cdr_retime_data_v16_binding import geometry_readback_matches,geometry_readback_controls
from run_cloud_tx_layout_repair import fetch,sha
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'hw/soc/out/cloud-pll-rhi120-c8-binding'
TOP='nssoc_pll845_divider3p2_rhi120_c8_development'
MODEL='nssoc_pll845_native_compact_v1'
CENSUS=dict(sg13_lv_nmos=132,sg13_hv_nmos=57,sg13_lv_pmos=130,sg13_hv_pmos=58,
 npn13G2=102,rppd=89,cap_cmim=26,ntap1=60,ptap1=191)
def native_export():
 import pya
 path=OUT/'inputs/source/parent/physical/lvs_flat/result.lvsdb'
 N=pya.LayoutVsSchematic();N.read(str(path));c=N.netlist().top_circuit()
 assert c.name==TOP and c.pin_count()==17 and N.internal_layout().dbu==.001
 devices=[]
 for d in c.each_device():
  cls=d.device_class()
  row=dict(native_id=d.id(),model=cls.name,terminals={t.name:d.net_for_terminal(t.id()).name for t in cls.terminal_definitions()},
   native_clusters={t.name:d.net_for_terminal(t.id()).cluster_id for t in cls.terminal_definitions()},
   parameters={p.name:d.parameter(p.id())for p in cls.parameter_definitions()})
  if cls.name in ('ptap1','ntap1'):
   term=next(t for t in cls.terminal_definitions()if t.name=='TIE')
   pieces=N.shapes_of_terminal(d.terminal_ref(term.id()));assert pieces
   reg=pya.Region()
   for region in pieces.values():reg+=region
   reg=reg.merged();box=reg.bbox();assert not reg.is_empty()
   row['tap_geometry']=dict(area_dbu2=reg.area(),perimeter_dbu=reg.perimeter(),
    bbox_dbu=[box.left,box.bottom,box.right,box.top],rectangular=(reg^pya.Region(box)).is_empty(),
    polygons=[p.to_s()for p in reg.each()])
  devices.append(row)
 assert Counter(d['model']for d in devices)==CENSUS
 assert sum(len(d['terminals'])for d in devices)==2737
 (OUT/'native-devices.json').write_text(json.dumps(dict(devices=devices,inputs={str(path):sha(path)}),indent=2)+'\n')
def pdk_tap_function(path,tech):
 tree=ast.parse(path.read_text())
 functions=[n for n in tree.body if isinstance(n,ast.FunctionDef)and n.name=='CbTapCalc'];assert len(functions)==1
 code=ast.fix_missing_locations(ast.Module(body=functions,type_ignores=[]))
 env=dict(techparams=tech,Numeric=lambda v:float(models.number(v)),sqrt=math.sqrt)
 exec(compile(code,str(path),'exec'),env)
 return env['CbTapCalc']
def build(native_text,devices,geometry,tech,ports_expected,tapcalc):
 statements=models.statements(native_text)
 assert statements[0][:2]==['.SUBCKT',TOP]and statements[-1]==['.ENDS',TOP]
 ports=statements[0][2:];assert len(ports)==len(set(ports))==17 and set(ports)==set(ports_expected)
 native={}
 for row in statements[1:-1]:
  match=re.fullmatch(r'[QRCMXD]\$(\d+)',row[0]);assert match
  did=int(match[1]);assert did not in native;native[did]=row
 assert len(native)==845 and set(native)=={d['native_id']for d in devices}
 assert Counter(d['model']for d in devices)==CENSUS
 geom={d['native_id']:d for d in geometry['device_terminal_inventory']}
 assert set(geom)==set(native)
 node_map={n:n if n in ports else 'n_'+n.removeprefix('$')for d in devices for n in d['terminals'].values()}
 assert len(node_map)==len({n.lower()for n in node_map.values()})
 bindings=[];tap_proofs=[];mos_census=Counter()
 out=['* Exact native PLL845 compact binding. No distributed RC or substrate spreading.','.subckt '+MODEL+' '+' '.join(ports)]
 for d in devices:
  kind=d['model'];order=models.NATIVE_ORDER[kind];line=native[d['native_id']];g=geom[d['native_id']]
  assert g['model']==kind and g['parameters']==d['parameters']
  assert {t['terminal']:t['native_net']for t in g['terminals']}==d['terminals']
  assert {t['terminal']:t['native_cluster']for t in g['terminals']}==d['native_clusters']
  assert set(d['terminals'])==set(order)and line[len(order)+1]==kind
  assert [n.removeprefix('\\')for n in line[1:len(order)+1]]==[d['terminals'][t]for t in order]
  fields=line[len(order)+2:];params=dict(x.split('=')for x in fields)
  assert len(params)==len(fields)and set(params)==set(d['parameters'])
  canonical={}
  for k,v in d['parameters'].items():
   exponent=-12 if k in ('A','AS','AD')else -6 if k in ('w','l','ps','we','le','P','L','W','PS','PD')else 0
   value=models.number(params[k])/Decimal(10)**exponent
   assert geometry_readback_matches(value,v),(d['native_id'],k,str(value),v)
   canonical[k]=value
  sim={k.lower():v for k,v in models.model_params(dict(d,parameters=canonical),tech).items()}
  if kind in models.MOS:mos_census[kind,str(canonical['L']),str(canonical['W'])]+=1
  if kind in ('ptap1','ntap1'):
   shape=d['tap_geometry']
   assert canonical['A']==Decimal(shape['area_dbu2'])/Decimal(1000000),'Tap area differs from actual native terminal geometry'
   assert canonical['P']==Decimal(shape['perimeter_dbu'])/Decimal(1000),'Tap perimeter differs from actual native terminal geometry'
   proof=dict(native_id=d['native_id'],model=kind,area_um2=str(canonical['A']),perimeter_um=str(canonical['P']),
    resistance_ohm=sim['r'],geometry=shape,area_perimeter_source='original native SPICE and actual native TIE polygon',
    substrate_spreading_modeled=False,pdk_subcircuit_w_l_unused=True)
   if shape['rectangular']:
    box=shape['bbox_dbu'];w=Decimal(box[2]-box[0])/Decimal(1000000000);l=Decimal(box[3]-box[1])/Decimal(1000000000)
    actual=tapcalc('R',0,float(l),float(w),kind)
    exact=models.number(sim['r'])
    assert math.isfinite(actual)and abs(exact-Decimal.from_float(actual))<=8*Decimal.from_float(math.ulp(actual))
    proof.update(pinned_pdk_function_checked=True,pdk_float_R_ohm=actual,pdk_equation_roundoff_bound_ulps=8)
   else:proof['pinned_pdk_function_checked']=False
   tap_proofs.append(proof)
  nets=[node_map[d['terminals'][t]]for t in models.MODEL_ORDER[kind]]
  model='npn13g2'if kind=='npn13G2'else kind;name=f'XD{d["native_id"]:04d}'
  row=dict(instance=name,native_id=d['native_id'],model=model,native_model=kind,native_terminal_order=order,
   compact_model_order=models.MODEL_ORDER[kind],native_nodes=d['terminals'],native_clusters=d['native_clusters'],
   compact_nodes=nets,parameters=sim,native_parameters={k:str(v)for k,v in canonical.items()})
  out.append(' '.join([name,*nets,model,*[k+'='+v for k,v in sim.items()]]));bindings.append(row)
 assert len(tap_proofs)==251 and sum(len(d['native_nodes'])for d in bindings)==2737
 return '\n'.join(out+['.ends '+MODEL,'']),dict(native_ports=ports,devices=bindings,node_map=node_map,census=CENSUS,
  native_terminal_count=2737,tap_geometry_proofs=tap_proofs,
  mos_geometry_census=[dict(model=k[0],L_um=k[1],W_um=k[2],count=v)for k,v in sorted(mos_census.items())])
def verify(text,binding):
 rows=models.statements(text);assert rows[0]==['.subckt',MODEL,*binding['native_ports']]and rows[-1]==['.ends',MODEL]
 seen={}
 for row in rows[1:-1]:assert row[0]not in seen;seen[row[0]]=row
 assert set(seen)=={d['instance']for d in binding['devices']}
 for d in binding['devices']:
  row=seen[d['instance']];n=len(d['compact_model_order'])
  assert row[1:n+1]==d['compact_nodes']and row[n+1]==d['model']
  params=dict(x.split('=')for x in row[n+2:]);assert len(params)==len(row[n+2:])and set(params)==set(d['parameters'])
  assert all(models.number(params[k])==models.number(v)for k,v in d['parameters'].items())
 return True
def controls(text,binding):
 verify(text,binding);original=models.statements(text);out=[]
 for kind in CENSUS:
  device=next(d for d in binding['devices']if d['native_model']==kind)
  for fault in ('missing_instance','changed_parameter','changed_terminal'):
   rows=copy.deepcopy(original);i=next(i for i,r in enumerate(rows)if r[0]==device['instance'])
   if fault=='missing_instance':del rows[i]
   elif fault=='changed_terminal':rows[i][1]='FAULT_UNBOUND_NODE'
   else:
    key='r'if kind in ('ptap1','ntap1')else'nx'if kind=='npn13G2'else'w'
    j=next(j for j,x in enumerate(rows[i])if x.startswith(key+'='))
    rows[i][j]=key+'='+str(models.number(rows[i][j].split('=')[1])*2)
   mutant='\n'.join(' '.join(r)for r in rows)+'\n'
   try:verify(mutant,binding)
   except (AssertionError,ValueError):out.append(dict(model=kind,fault=fault,rejected=True))
   else:raise AssertionError('Accepted '+kind+' '+fault)
 for kind in models.MOS:
  device=next(d for d in binding['devices']if d['native_model']==kind and d['compact_nodes'][1]!=d['compact_nodes'][2])
  for fault in ('swapped_gate_source','changed_body'):
   rows=copy.deepcopy(original);i=next(i for i,r in enumerate(rows)if r[0]==device['instance'])
   if fault=='swapped_gate_source':rows[i][2],rows[i][3]=rows[i][3],rows[i][2]
   else:rows[i][4]='FAULT_UNBOUND_BODY'
   try:verify('\n'.join(' '.join(r)for r in rows)+'\n',binding)
   except (AssertionError,ValueError):out.append(dict(model=kind,fault=fault,rejected=True))
   else:raise AssertionError('Accepted '+kind+' '+fault)
 assert len(out)==35
 return out
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--native-export',action='store_true');args=parser.parse_args()
 assert os.environ.get('GITHUB_ACTIONS')=='true'
 if args.native_export:native_export();return
 OUT.mkdir(parents=True,exist_ok=False);reports.OUT=OUT
 r=dict(status='RUNNING',source_head=os.environ['GITHUB_SHA'],native_simulation_passed=False,
  qualified_pex=False,wire_rc_included=False,full_phy_accepted=False,closed_loop_accepted=False,
  controller_sha256=sha(Path(__file__)),converter_sha256=sha(Path(models.__file__)),
  base_converter_sha256=sha(Path(models.base.__file__)))
 def save():(OUT/'result.json').write_text(json.dumps(r,indent=2)+'\n')
 save()
 try:
  names=['source/parent/integrated/result.json','source/parent/physical/lvs_flat/result.lvsdb',
   'source/parent/physical/lvs_flat/extracted.cir','source/parent/physical/lvs_flat/audit.json',
   'source/native-mim-geometry.json','anchors.json']
  prior,proof=reports.restore_report('pll-rhi120-c8-terminals',39915871064,
   '558a1d37cb69163ed67d4641b91d56467a8fb998f378e9d2dec6e6370beebe0a',
   '29844ac319e058685a56248eff381a224b14686d83327b85e3a0099129a4ea74',OUT/'inputs',names)
  assert prior['source_head']=='8098380e227c959c39403c33cd309bc1702eb551'and prior['sources_unchanged']
  assert prior['status']=='PASS_ALL2737_PLL_TERMINAL_IDENTITIES_AND_ACTUAL_METAL_REFERENCES_REQUIRES_FULL_RC'
  r['physical_source']=proof
  electrical=json.loads((ROOT/'docs/evidence/pcie-tx-cloud-input-20261013.json').read_text())
  m=OUT/'model-inputs';m.mkdir();packed=OUT/'models.tar.gz'
  fetch(electrical['receipt']['url'],electrical['receipt']['sha256'],packed)
  with tarfile.open(packed)as tar:tar.extractall(m,filter='data')
  packed.unlink();manifest=json.loads((m/'manifest.json').read_text())
  assert all(sha(m/n)==v['sha256']for n,v in manifest['files'].items())
  pdk=OUT/'pdk';target=pdk/'libs.tech/ngspice/models';target.parent.mkdir(parents=True,exist_ok=True)
  shutil.copytree(m/'models',target)
  base='https://raw.githubusercontent.com/IHP-GmbH/IHP-Open-PDK/c4b8b4e5e7a05f375cca3815d51b3a37721fbf5c/ihp-sg13g2/'
  for rel,digest in models.MODEL_PINS.items():
   path=pdk/rel
   if not path.exists():path.parent.mkdir(parents=True,exist_ok=True);fetch(base+rel,digest,path)
   assert sha(path)==digest
  r['model_source_hashes']=models.MODEL_PINS;r['model_archive_source']=electrical['receipt']
  tech_path=pdk/'libs.tech/klayout/python/sg13g2_pycell_lib/sg13g2_tech.json'
  utility=pdk/'libs.tech/klayout/python/sg13g2_pycell_lib/ihp/utility_functions.py'
  tech=json.loads(tech_path.read_text())['techParams'];tapcalc=pdk_tap_function(utility,tech)
  for kind in models.MOS:
   path=target/('sg13g2_moslv_mod.lib'if '_lv_'in kind else'sg13g2_moshv_mod.lib')
   lines=[row for row in models.statements(path.read_text())if row[0].lower()=='.subckt'and row[1]==kind]
   assert len(lines)==1 and lines[0][2:6]==['d','g','s','b']
  resistor_text=(target/'resistors_mod.lib').read_text()
  for kind in ('ptap1','ntap1'):
   block=re.search(r'(?ms)^\.subckt '+kind+r'\b(.*?)^\.ends '+kind+r'\b',resistor_text).group(1)
   assert 'R1 1 2 R=R'in block and '* The value of R is calculated by schematic capture tool.'in resistor_text
  app=Path(os.environ['CLOUD_APPIMAGE']);assert sha(app)=='d6a349ec65be11456e96c4981d35f63ca34d3c85daf79a51e1ccb907bb5d7466'
  with(OUT/'native-export.log').open('w')as log:rc=subprocess.call([str(app),'python',str(Path(__file__).resolve()),'--native-export'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
  r['native_export_returncode']=rc;save()
  if rc:print((OUT/'native-export.log').read_text()[-14000:],flush=True)
  assert rc==0
  raw=(OUT/'inputs/source/parent/physical/lvs_flat/extracted.cir').read_text()
  devices=json.loads((OUT/'native-devices.json').read_text())['devices']
  geometry=json.loads((OUT/'inputs/source/native-mim-geometry.json').read_text())
  ports=json.loads((OUT/'inputs/source/parent/integrated/result.json').read_text())['ports']
  r['geometry_readback_controls']=geometry_readback_controls()
  text,binding=build(raw,devices,geometry,tech,ports,tapcalc)
  verify(text,binding);r['controls']=controls(text,binding)
  (OUT/'pll845-compact.spice').write_text(text);(OUT/'binding.json').write_text(json.dumps(binding,indent=2)+'\n')
  r['binding']=binding
  assert all(sha(OUT/'inputs'/n)==prior['outputs'][n]for n in names)
  assert all(sha(m/n)==v['sha256']for n,v in manifest['files'].items())
  assert all(sha(target/p.relative_to(m/'models'))==sha(p)for p in (m/'models').rglob('*')if p.is_file())
  assert all(sha(pdk/rel)==digest for rel,digest in models.MODEL_PINS.items())
  assert sha(Path(__file__))==r['controller_sha256']and sha(Path(models.__file__))==r['converter_sha256']and sha(Path(models.base.__file__))==r['base_converter_sha256']
  r.update(status='PASS_PLL845_ALL_NATIVE_MODELS_AND35_CONTROLS_REQUIRES_WIRE_COMPOSITION_AND_LOADED_WAVES',sources_unchanged=True)
 except BaseException as e:r.update(status='FAIL_OR_ERROR',error=repr(e));raise
 finally:
  r['outputs']={str(p.relative_to(OUT)):sha(p)for p in OUT.rglob('*')if p.is_file()and p!=OUT/'result.json'};save()
if __name__=='__main__':main()
