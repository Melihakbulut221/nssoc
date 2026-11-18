#!/usr/bin/env python3
import unittest
from check_antenna_netlist_export import identifier,check_added_antennas
class Export(unittest.TestCase):
 def test_simple(self):self.assertEqual(identifier(' n_1 '),'n_1')
 def test_escaped_dot(self):self.assertEqual(identifier('\\u_boot.crash_valid_q '),'u_boot.crash_valid_q')
 def test_missing_escape_terminator(self):
  with self.assertRaises(ValueError):identifier('\\u_boot.crash_valid_q')
 def test_unescaped_dot(self):
  with self.assertRaises(ValueError):identifier('u_boot.crash_valid_q')
 def test_expression(self):
  with self.assertRaises(ValueError):identifier('a & b')
 def fixture(self):return {'ANTENNA_1':dict(master='sg13g2_antennanp',signal_terms=[dict(pin='A',net='u.signal')])}
 def test_real_escape(self):self.assertFalse(check_added_antennas('sg13g2_antennanp ANTENNA_1 (.A(\\u.signal ));',self.fixture())['signal_connection_mismatches'])
 def test_wrong_connection(self):self.assertTrue(check_added_antennas('sg13g2_antennanp ANTENNA_1 (.A(wrong));',self.fixture())['signal_connection_mismatches'])
 def test_missing(self):self.assertEqual(check_added_antennas('',self.fixture())['missing_diodes'],['ANTENNA_1'])
 def test_duplicate(self):self.assertEqual(check_added_antennas('sg13g2_antennanp ANTENNA_1 (.A(n));\n'*2,self.fixture())['duplicate_diodes'],['ANTENNA_1'])
 def test_duplicate_pin(self):
  with self.assertRaises(AssertionError):check_added_antennas('sg13g2_antennanp ANTENNA_1 (.A(n),.A(m));',self.fixture())
 def test_many_instances_order_and_prefixes(self):
  cells={f'ANTENNA_{i}':dict(master='sg13g2_antennanp',signal_terms=[dict(pin='A',net=f'n_{i}')])for i in range(1000)}
  text='\n'.join(f'sg13g2_antennanp ANTENNA_{i} (.A(n_{i}));'for i in reversed(range(1000)))
  result=check_added_antennas(text,cells)
  self.assertEqual(result['new_diodes_exported'],1000);self.assertFalse(result['missing_diodes']);self.assertFalse(result['duplicate_diodes']);self.assertFalse(result['signal_connection_mismatches'])
 def test_other_master_rejected(self):self.assertEqual(check_added_antennas('wrong_master ANTENNA_1 (.A(n));',self.fixture())['missing_diodes'],['ANTENNA_1'])
if __name__=='__main__':unittest.main(verbosity=2)
