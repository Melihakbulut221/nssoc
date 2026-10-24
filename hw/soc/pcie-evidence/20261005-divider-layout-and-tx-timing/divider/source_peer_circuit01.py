# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Independent graph/placement/bridge source inspection only; no PCell or EDA execution."""
from pathlib import Path
import hashlib,json,ast,datetime,runpy,collections
B=Path(__file__).resolve().parent;R=B.parents[3]
def pin(p):
 b=Path(p).read_bytes();return dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest())
bridge=B/'source-bridge.json';contract=B/'predeclared-contract.json'
assert pin(bridge)==dict(bytes=141051,sha256='215b9503862cc3e9e20c12aeeb488c8cf06d4357ddd3c79b363503014b2d1894')
assert pin(contract)==dict(bytes=31811,sha256='0775bc95768f24e6ff1f318a986a5e198b6cfb22765c39a29e845f36307a457a')
j=json.loads(contract.read_text());changes=json.loads(bridge.read_text())
for pair in changes['pairs']:
 for side in ['before','after']:
  text=''.join(x[side] for x in pair['opcodes']);h=dict(bytes=len(text.encode()),sha256=hashlib.sha256(text.encode()).hexdigest());assert h=={k:pair[side][k] for k in ['bytes','sha256']};ast.parse(text)
  if side=='before' or 'make_' in pair[side]['path']:assert pin(R/pair[side]['path'])==h
for p,h in j['actual_schematic_inputs'].items():assert pin(R/p)==h
# Independent hierarchy parser: starts from literal declared top pins and expands
# primitive records into full formal/actual identity; no maker or analog parser.
defs={}
for file in j['actual_schematic_inputs']:
 active=None
 for raw in (R/file).read_text().splitlines():
  w=raw.upper().split()
  if not w or w[0].startswith('*'):continue
  if w[0]=='.SUBCKT':assert active is None and w[1] not in defs;active=w[1];defs[active]=(w[2:],[])
  elif w[0]=='.ENDS':assert w==['.ENDS',active];active=None
  else:assert active and w[0].startswith('X');defs[active][1].append(w)
 assert active is None
rows=[]
def expand(name,path,nodes):
 form,body=defs[name];assert len(form)==len(nodes);mapping=dict(zip(form,nodes))
 for w in body:
  ident=path+'__'+w[0]
  def net(n):return mapping[n] if n in mapping else path+'__'+n
  if w[-1] in defs:expand(w[-1],ident,[net(n) for n in w[1:-1]]);continue
  ix=next(i for i,v in enumerate(w) if v in ['NPN13G2','RPPD','CAP_CMIM']);model=w[ix];params=dict(z.split('=') for z in w[ix+1:]);row=dict(kind={'NPN13G2':'hbt','RPPD':'resistor','CAP_CMIM':'capacitor'}[model],name=ident,nets=[net(n) for n in w[1:ix]],source_subcircuit=name,source_instance=w[0])
  if model=='NPN13G2':assert set(params)=={'NX'};row['nx']=int(params['NX'])
  else:
   row.update(width_um=float(params['W'][:-1]),length_um=float(params['L'][:-1]));assert params['W'].endswith('U') and params['L'].endswith('U')
   if model=='RPPD':assert params['B']=='0' and params['SW_ET']=='1'
  rows.append(row)
expand('NSSOC_CLOCK_DIV4_HBT_V7','DIV',['CLKP','CLKN','QP','QN','DIV_AVDD','AVSS','SUB'])
assert rows==j['graph'] and len(rows)==73
assert collections.Counter(x['kind'] for x in rows)==dict(hbt=34,resistor=33,capacitor=6)
maker=R/'hw/soc/flow/make_pcie_clock_div4_v7.py';assert pin(maker)==j['source_pins'][str(maker.relative_to(R))];m=runpy.run_path(str(maker));assert m['devices'](R)==rows
plan,starts,nets=m['placement_plan'](rows);assert {k:list(v) for k,v in plan.items()}==j['placement'];assert {str(k):v for k,v in starts.items()}==j['row_starts'];assert {str(k):v for k,v in nets.items()}==j['row_nets']
ref=m['physical_reference'](R);assert hashlib.sha256(ref.encode()).hexdigest()==j['physical_reference_sha256'];assert ref.count('ptap1 A=4p P=8u')==18;assert not any(x in ref for x in ['VCO_AVDD','NWELL','OSC__','VCTRL','pmos','ntap'])
life=R/j['lifecycle']['path'];assert pin(life)=={k:j['lifecycle'][k] for k in ['bytes','sha256']};selected=[x for x in ast.parse(life.read_text()).body if isinstance(x,(ast.FunctionDef,ast.ClassDef)) and x.name in j['lifecycle']['selected_definitions']];assert len(selected)==4
record=dict(status='PASS_EXACT_CIRCUIT_PLACEMENT_SOURCE_REVIEW_WITH_TWO_LIFECYCLE_FINDINGS',utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),reviewer='/root/rx_route_resume',contract=pin(contract),source_bridge=pin(bridge),initial_source_pins=j['source_pins'],method=pin(__file__),independent_graph_equal=True,graph_census=dict(hbt=34,rppd=33,cmim=6),physical_ptaps=18,expected_normalized_native_devices=74,normalization_is_actual_future_gate=True,observations=['All source bridge before/after bytes reconstruct declared whole-file hashes and parse. Independent schematic hierarchy expansion matches all73 source identities, nets, models and geometry exactly; no oscillator/PMOS/NWELL or ideal source remains.','L4 conditioning XUP/XUN, exact3rows30/17/26, mirror rows0/2 and7ports checked against predeclared graph/reference. Actual native HBT/rppd/MIM pin-purpose/plate introspection, via PCells, row band checks and cross-row trunks remain required, with no dummy substitute.','18real2um-square ptaps connect SUB to extracted substrate BULK. SumA72p/P144u and normalized74 are fail-closed expected native checks, not source-derived proof of LVS. Auxiliary unmultiplied HBT/passive census supplements actual deep/flat topology LVS.','Actual physical mutation source cuts right-edge CLKP Metal5, differentialS1P/S1N Metal4 trunks, toggle-feedback Metal3 and output/supply shorts; exact geometry preconditions and changedGDS guard remain. Reference8 faults include currentL4→6.4um conditioner. No native rejection assumed from source.','Strict main560rule DRC plus offgrid diagnostic, independent deep+flatLVS, native74-device/7port checks and LEFpin/direction/obstruction negatives required. Qualified PEX, extracted division and chip/PHY/manufacturing acceptance all remain false.','Four exact tested ProcessOwner definitions are isolated from simulation module globals. CPU10,2GiBAS,1GiBentry,512MiBcontinuous,80MiBown+24MiBentryreserve,nohealthytimeout and5scleanup are declared. Existing39 controls include normal long-ish healthy wait, real cancellation and live-resource failure, but not terminal boundaries below.'],findings=[dict(id='terminal_signal_loss',where='execute(): after owner.complete and ProcessOwner context exit',reason='Cancellation delivered during completion/teardown may occur after last owner.check; __exit__ cleanup does not raise, so execute may return0 and next stage starts fresh.',required='Propagate owner cancellation after context restoration; preserve actual completion-boundary SIGTERM control.'),dict(id='terminal_resource_guard',where='execute(): child has exited between poll intervals',reason='Scratch/shared-floor checks only while process.poll() is None; fast terminal writes can exceed limits then escape all checks on final stage.',required='Post-completion own/shared resource guards and actual fast-exit control; keep resource contract unchanged.')],native_executed=False,tests_rerun=False,physical_acceptance=False)
p=B/'source-only-peer01-circuit-and-findings.json';p.write_text(json.dumps(record,indent=2)+'\n');print(pin(p))
