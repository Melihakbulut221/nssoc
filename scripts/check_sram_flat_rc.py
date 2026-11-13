# SPDX-License-Identifier: Apache-2.0
import copy,json,pathlib,unittest
from audit_sram_flat_rc import audit,parse,Rejected
CC=""".subckt cell a b g vss
M1 a g b vss nmos w=1u l=0.13u
C1 a b 1p
.ends cell
"""
RC=""".subckt cell a b g vss
M1 n g b vss nmos w=1u l=0.13u
R1 a n 10
C1 n b 0.4p
C2 a b 0.6p
.ends cell
"""
class Controls(unittest.TestCase):
 def setUp(self):self.cc=parse(CC);self.rc=parse(RC)
 def test_valid_split_capacitance(self):self.assertTrue(audit(self.cc,self.rc,1)[1])
 def test_explicit_wrong_device_count(self):
  with self.assertRaises(Rejected):audit(self.cc,self.rc,2)
 def test_removed_bridge(self):
  self.rc['R'].clear()
  with self.assertRaises(Rejected):audit(self.cc,self.rc,1)
 def test_short_between_terminals(self):
  self.rc['R']['rshort']=('a','b',1)
  with self.assertRaises(Rejected):audit(self.cc,self.rc,1)
 def test_removed_coupling(self):
  del self.rc['C']['c1'];self.assertFalse(audit(self.cc,self.rc,1)[1])
 def test_changed_geometry(self):
  self.rc['mos']['m1']['params']['w']='2u'
  with self.assertRaises(Rejected):audit(self.cc,self.rc,1)
 def test_unanchored_network(self):
  self.rc['R']['rfloating']=('x','y',1)
  with self.assertRaises(Rejected):audit(self.cc,self.rc,1)
 def test_reordered_ports(self):
  self.rc['ports'].reverse()
  with self.assertRaises(Rejected):audit(self.cc,self.rc,1)
 def test_invalid_passives(self):
  for value in ['-1','0','nan','inf','1e999']:
   with self.subTest(value=value):
    with self.assertRaises(Rejected):parse(RC.replace('a n 10','a n '+value))
 def test_long_adversarial_resistance_chain(self):
  # Ordered to create a deep parent chain in the former recursive union.
  self.rc['R']={f'r{i}':(f'n{i+1}',f'n{i}',1) for i in range(20000)}
  self.rc['R']['rstart']=('n0','a',1)
  self.rc['R']['rend']=('n20000','n',1)
  result,ok=audit(self.cc,self.rc,1)
  self.assertTrue(ok);self.assertEqual(result['rc_resistors'],20002)
if __name__=='__main__':
 result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(Controls))
 pathlib.Path('out').mkdir(exist_ok=True)
 pathlib.Path('out/scalable-audit-controls.json').write_text(json.dumps({'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':len(result.skipped),'passed':result.wasSuccessful(),'scope':'Synthetic adversarial checks of flat topology and capacitor conservation; actual leaf replay is a separate workflow step. No full-macro or manufacturing acceptance.'},indent=2))
 raise SystemExit(0 if result.wasSuccessful() else 1)
