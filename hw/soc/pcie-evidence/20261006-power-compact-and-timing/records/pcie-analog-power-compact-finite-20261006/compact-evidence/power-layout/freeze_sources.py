from pathlib import Path
import hashlib,json,xml.etree.ElementTree as E,ast
R=Path.cwd();B=R/'hw/soc/out/pcie-divider-v7-power-v1-20261005';D=R/'hw/soc/out/pcie-divider-v7-layout-20261005';L=R/'hw/soc/out/pcie-vco-v6-divider-wire-v1-20261005'
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return {'bytes':p.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
old=json.loads((D/'launch-manifest02.json').read_text());inputs={}
for p,w in old['inputs'].items():
 got=pin(p);assert got==w,(p,got,w);inputs[p]=got
product=[R/'hw/soc/flow'/n for n in ['make_pcie_clock_div4_v7_power_v1.py','check_pcie_clock_div4_v7_power_v1.py','audit_pcie_clock_div4_v7_power_v1.py']]+[R/'sw/tests'/n for n in ['test_pcie_clock_div4_v7_power_v1_layout.py','test_pcie_clock_div4_v7_power_v1_native.py']]
extras=[*product,B/'prepare_sources.py',B/'source-bridge-initial-generator.json',B/'source-bridge.json',B/'launch01.py',Path(__file__),B/'source-controls01.log',B/'source-controls02.log',D/'native02-peer-rx/review.json',L/'result-does-not-exist']
extras=extras[:-1]+[L/'release-06-01.json',L/'saved-wave-diagnosis06.json',L/'diagnose_saved06.py',Path('/dev/shm/nssoc-vco-v6-divider-wire-06-01/result.json'),Path('/dev/shm/nssoc-div4-v7-layout-01/result.json'),Path('/dev/shm/nssoc-div4-v7-layout-01/nssoc_clock_div4_v7_layout.gds')]
extras+=list((B/'pytest-controls02').rglob('*'))
for p in extras:
 if p.is_file() and not p.is_symlink():inputs[str(p)]=pin(p)
lyp=Path(old['pdk'])/'libs.tech/klayout/tech/sg13g2.lyp'; layers={x.findtext('name')[:-8]:int(x.findtext('source').split('/')[0]) for x in E.parse(lyp).getroot().iter('properties') if x.findtext('name','').endswith('.drawing')}
assert {layers[n] for n in ['Metal4','Metal5','TopMetal1','TopMetal2','Via4','TopVia1','TopVia2']}=={50,67,126,134,66,125,133}
# Independently inspect exact unchanged lifetime/parser bodies in the two checkers.
a=ast.parse((R/'hw/soc/flow/check_pcie_clock_div4_v7_v2.py').read_text());b=ast.parse(product[1].read_text());fa={x.name:ast.dump(x) for x in a.body if isinstance(x,ast.FunctionDef)};fb={x.name:ast.dump(x) for x in b.body if isinstance(x,ast.FunctionDef)}
assert all(fa[n]==fb[n] for n in fa if n!='main')
frozen={'status':'FROZEN_POWER_ONLY_LAYOUT_SOURCE_BEFORE_NATIVE_GENERATION','product_sources':{str(p):pin(p) for p in product},'inputs':inputs,'launcher':pin(B/'launch01.py'),'layers':{n:layers[n] for n in ['Metal4','Metal5','TopMetal1','TopMetal2','Via4','TopVia1','TopVia2']},'controls':{'status':'PASS','count':60,'raw_directory':str(B/'pytest-controls02'),'log':pin(B/'source-controls02.log'),'rerun_reason':'Final checker adds independent actual GDS geometry gate; inherited lifecycle methods remain byte-AST-identical.'},'expected_geometry':{'intrinsic_primitives':73,'finite_substrate_taps':18,'ports':7,'old_drawing_subsets_preserved':True,'all_unallowed_layer_geometry_exact':True,'power_rails':['DIV_AVDD','AVSS'],'power_straps':8,'power_branch_terminals':{'DIV_AVDD':15,'AVSS':24},'native_power_via_arrays':47,'width_um':6,'topmetal1_trunk_x_um':[96,112],'original_signal_routes_and_primitive_topology_unchanged':True},'measured_parent_failure':{'vco_GHz':8.102380710,'feedback_frequency_Hz':None,'project_HBT_headroom_failures':4,'AVSS_peak_V':0.345529,'DIV_AVDD_min_V':2.160232,'native_failure_retained':True},'native_not_executed':True,'scope':'Physical power-only derivative. Source controls are separate from native generation, actual GDS inverse audit, three geometry fault controls, DRC, deep/flat LVS, LEF and old native fault suite. Fresh RC and all455 loaded device measurements remain required. No qualified PEX or full PHY acceptance.'}
p=B/'source-freeze.json';assert not p.exists();p.write_text(json.dumps(frozen,indent=2)+'\n');print(pin(p),len(inputs));print(json.dumps(frozen['product_sources'],indent=2))
