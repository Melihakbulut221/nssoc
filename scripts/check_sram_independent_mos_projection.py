# SPDX-License-Identifier: Apache-2.0
import copy,hashlib,io,json,pathlib,sys,unittest,zipfile
sys.path.insert(0,'hw/soc/flow')
from mos_graph_equivalence import prove_mos_graph,load_mos_netlist
from audit_sram_flat_rc import parse,Rejected
from sram_independent_mos_projection import graph_from_flat,canonical_reference
BASE=""".subckt inv a y vdd vss
mn y a vss vss sg13_lv_nmos w=0.2u l=0.13u
mp y a vdd vdd sg13_lv_pmos w=0.5u l=0.13u
.ends inv
"""
def graph():return graph_from_flat(parse(BASE),2)
class Controls(unittest.TestCase):
 def test_case_only_and_drain_source(self):
  a=graph();b=copy.deepcopy(a)
  b['nets']={n.upper():n.upper() for n in b['nets']};b['pins']={n.upper():p.upper() for n,p in b['pins'].items()}
  for d in b['devices']:
   for k in ['D','G','S','B']:d[k]=d[k].upper()
   d['D'],d['S']=d['S'],d['D'];d['model']=d['model'].upper()
  prove_mos_graph(a,canonical_reference(b))
 def test_changed_bulk(self):
  a=graph();b=copy.deepcopy(a);b['devices'][0]['B']='vdd'
  with self.assertRaises(ValueError):prove_mos_graph(a,b)
 def test_changed_gate(self):
  a=graph();b=copy.deepcopy(a);b['devices'][0]['G']='y'
  with self.assertRaises(ValueError):prove_mos_graph(a,b)
 def test_changed_dimensions(self):
  a=graph();b=copy.deepcopy(a);b['devices'][0]['w']*=2
  with self.assertRaises(ValueError):prove_mos_graph(a,b)
 def test_changed_model(self):
  a=graph();b=copy.deepcopy(a);b['devices'][0]['model']='other'
  with self.assertRaises(ValueError):prove_mos_graph(a,b)
 def test_port_alias(self):
  a=graph();b=copy.deepcopy(a);b['pins']['vss']='sub!'
  with self.assertRaises(ValueError):prove_mos_graph(a,b)
 def test_case_collision(self):
  a=graph();a['nets']['VSS']='VSS'
  with self.assertRaises(Rejected):canonical_reference(a)
 def test_multiplicity(self):
  for key in ['m','nf']:
   m=parse(BASE);m['mos']['mn']['params'][key]='2'
   with self.assertRaises(Rejected):graph_from_flat(m,2)
 def test_unknown_parameter(self):
  m=parse(BASE);m['mos']['mn']['params']['unknown']='1'
  with self.assertRaises(Rejected):graph_from_flat(m,2)
 def test_uncollapsed_resistance(self):
  m=parse(BASE);m['R']['r1']=('y','a',1.)
  with self.assertRaises(Rejected):graph_from_flat(m,2)
 def test_wrong_count(self):
  with self.assertRaises(Rejected):graph_from_flat(parse(BASE),3)
out=pathlib.Path('out');out.mkdir(exist_ok=True)
r={'full_macro_lvs':False,'manufacturing_approval':False,'scope':'Projection controls and independent-reference self-bijection only. Actual extracted macro still requires separate comparison.'}
try:
 suite=unittest.defaultTestLoader.loadTestsFromTestCase(Controls);res=unittest.TextTestRunner(verbosity=2).run(suite)
 r['controls']={'tests':res.testsRun,'failures':len(res.failures),'errors':len(res.errors),'skipped':len(res.skipped)}
 assert res.wasSuccessful() and not res.skipped,'projection controls failed'
 raw=pathlib.Path('reference.zip').read_bytes();assert hashlib.sha256(raw).hexdigest()=='124f6a92fa56346b1c471efb84750878180ef0c8056b2c940c5c6fce0e41e29b'
 z=zipfile.ZipFile(io.BytesIO(raw));names=[n for n in z.namelist() if n.endswith('reference.spice')];assert len(names)==1
 raw=z.read(names[0]);assert hashlib.sha256(raw).hexdigest()=='64d041383d0ebee7b54dab0bc10d651d31262a2a41ccd15a9c0727dac06e0dd9'
 p=pathlib.Path('reference.spice');p.write_bytes(raw);a=canonical_reference(load_mos_netlist(p));assert len(a['devices'])==37076
 # Rename every internal net and reverse device order; external named pins fixed.
 mapping={n:n if n in a['pins'] else 'renamed_internal_'+str(i) for i,n in enumerate(a['nets'])}
 assert len(set(mapping.values()))==len(mapping),'rename collision'
 b=copy.deepcopy(a);b['nets']={mapping[n]:mapping[n] for n in a['nets']}
 b['devices']=list(reversed(b['devices']))
 for d in b['devices']:
  for k in ['D','G','S','B']:d[k]=mapping[d[k]]
 proof=prove_mos_graph(a,b);proof.pop('mapping');r['full_reference_renamed_bijection']=proof
 r['status']='PASS_PROJECTION_CONTROLS_AND_REFERENCE_BIJECTION'
except Exception as e:r.update(status='FAIL_OR_INCONCLUSIVE',error=type(e).__name__+': '+str(e))
(out/'projection-controls.json').write_text(json.dumps(r,indent=2));print(json.dumps(r));raise SystemExit(0 if r['status'].startswith('PASS_') else 1)
