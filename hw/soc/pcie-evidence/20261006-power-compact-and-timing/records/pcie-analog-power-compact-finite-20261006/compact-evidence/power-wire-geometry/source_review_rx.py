from pathlib import Path
import ast,hashlib,json
B=Path(__file__).resolve().parent;W=B.parent/'pcie-divider-v7-power-v2-wire-20261005';R=B.parents[3]
def pin(p):
 p=Path(p)
 with p.open('rb') as f:return {'bytes':p.stat().st_size,'sha256':hashlib.file_digest(f,'sha256').hexdigest()}
f=B/'geometry-source-freeze.json';assert pin(f)==dict(bytes=73350,sha256='5c5751a02f73789956afd43c56d03f4b691f303321b8d7adef75ef1778ec25fb')
x=json.loads(f.read_text());assert len(x['inputs'])==336
for p,v in x['inputs'].items():assert pin(p)==v,p
bridges=[]
for root in [W,B]:
 ledger=json.loads((root/'draft-source-bridge.json').read_text());assert len(ledger)==7
 for row in ledger:
  for k in ['before','after']:
   p=Path(row[k]['path']);assert pin(p)=={v:row[k][v]for v in ['bytes','sha256']}
   assert ''.join(o[k]for o in row['opcodes'])==p.read_text()
  if root==B:
   old=Path(row['before']['path']).read_text();new=Path(row['after']['path']).read_text()
   expected=old.replace('power-v2-wire-geometry-01','power-v2-wire-geometry-02').replace('power-v2-wire-native-01','power-v2-wire-native-02')
   if Path(row['after']['path']).name=='prepare_anchors.py':expected=expected.replace('8484a6f3db8e91923ec6e5d2184bf6ba80570b2c894b5e4f563b637e0165ee3f','663b60fc14cc9c8e2b4d9a5a758aee6bcd61bdf307c6b3a69a28e63bc470340c')
   if Path(row['after']['path']).name=='probe_wire_components.py':
    expected=expected.replace('assert ACTIVE_METALS==[8,10,30,50,67,126]','assert ACTIVE_METALS==[8,10,30,50,67,126,134]').replace('assert regions[134].is_empty() and regions[133].is_empty()','assert not regions[134].is_empty() and not regions[133].is_empty()')
   assert expected==new,row['after']['path']
 bridges.append({'path':str(root/'draft-source-bridge.json'),**pin(root/'draft-source-bridge.json'),'whole_forward_inverse_count':7})
assert (B/'native_unsimplified.lvs').read_bytes()==(R/'hw/soc/out/pcie-divider-v7-wire-v4-20261005/native_unsimplified.lvs').read_bytes()
s=(B/'run_geometry.py').read_text();p=ast.parse(s)
nsassign=next(n for n in ast.walk(p)if isinstance(n,ast.Call)and isinstance(n.func,ast.Name)and n.func.id=='dict'and any(k.arg=='SCRATCH_ROOTS'for k in n.keywords))
settings={k.arg:ast.unparse(k.value)for k in nsassign.keywords};assert settings['CPU']=='10' and settings['SCRATCH_ROOTS']=='(B, W, N)' and settings['SCRATCH_LIMIT']=='80 * 1024 ** 2' and settings['ENTRY_FREE']=='1024 ** 3' and settings['SHARED_FLOOR']=='512 * 1024 ** 2'
checker=R/'hw/soc/flow/check_pcie_clock_div4_v7_v2.py';assert pin(checker)['sha256']=='24c89628c6d61226344214e077b5fa535c5570e4a7853fbd109e8cb1b1fcd163'
for t in ["no_simplify='True'","net_only='True'","combine_devices='False'","purge='False'","purge_nets='False'","purge_devices='False'","disable_tap_extraction='False'","run_mode='flat'","native_peer['checks'] == pin(C / 'result.json')","native_peer['geometry'] == pin(C / 'power-geometry.json')"]:assert t in s,t
assert x['source_expected_census']==dict(devices=91,terminals=283,metal_terminals=198,body_terminals=85,anchors=205,ports=7,conductors=37)
assert x['complete_native_cluster_partition_expected']==dict(raw=72,electrical=38,body_only=1,auxiliary=34)
for n in ['nssoc-div4-v7-power-v2-wire-native-02','nssoc-div4-v7-power-v2-wire-geometry-02']:assert not(Path('/dev/shm')/n).exists()
assert not(B/'geometry-execution.json').exists()
r={'status':'PASS_SOURCE_ONLY_DIVIDER_V7_WIRE_GEOMETRY','freeze':pin(f),'findings':[],'inputs_rehashed':len(x['inputs']),'producer_sources':x['producer_sources'],'bridges_verified':bridges,'prior_findings_preserved':{'path':str(W/'geometry-source-peer-findings01-rx.json'),**pin(W/'geometry-source-peer-findings01-rx.json')},'review':[
'Full seven producer bodies and native wrapper inspected. Both complete forward/inverse ledgers reproduced from independently read old/new files. V2 differs only in fresh roots and two explicit corrections of stale source assumptions; original rejected source/freeze remains unchanged.',
'Exact PowerV2 GDS identity now replaces the old baseline hash. All seven real metal layers including TopMetal2 and nonempty TopVia2 are required; every nonempty polygon is still unioned and inventoried before conductor binding.',
'Native leaf count725 and634 via_stack leaves preserve91 electrical devices. Fresh official-deck extraction is flat/net_only, no simplify/combine/purge, finite contacts retained, actual LayoutToNetlist explicitly exported; no comparison result is invented.',
'All283 terminal shapes require unique actual PCell enclosure, exact198 metal/85 body dispositions,205 real anchors and full91-device/38-net source location/parameter/net bijection. All72 raw clusters remain;34 auxiliary clusters must contain no metal/device terminal/public pin. No merge-by-label or net deletion.',
'Run gates prior actualPowerV2 zeroDRC/deep-flatLVS/strictGDS47-array peer and all336 frozen inputs. Exact inherited checked lifecycle ASTs are cloned into private namespace with fresh scratch roots only; CPU10,2GiB,80MiB+24MiB reservation,1GiB entry/512MiB floor and no healthy timeout remain.',
'Own controller executes and reaps each native stage before the next; input maps rehashed before/after stages. A failed actual census/bijection stops and retains output. Source predeclarations are not actual new geometry/RC acceptance.'
],'native_or_reviewed_methods_executed':False,'fresh_native_roots_absent':True,'scope':'Source-only approval for fresh exact physical geometry extraction. No new RC, loaded division, qualified PEX, full PHY or main-chip acceptance.','method':pin(__file__)}
q=B/'geometry-source-only-peer.json';assert not q.exists();q.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(pin(q)))
