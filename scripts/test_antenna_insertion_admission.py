#!/usr/bin/env python3
"""Fault injection for additive antenna identity admission, no native tool emulation."""
import copy,importlib.util,json,sys,types,unittest
from pathlib import Path
from unittest.mock import patch
root=Path(__file__).resolve().parents[1]
a=types.ModuleType('audit_core_only_route_identity');a.snapshot=None
b=types.ModuleType('buffer_core_only_chip_controls');b.load=None
with patch.dict(sys.modules,{'audit_core_only_route_identity':a,'buffer_core_only_chip_controls':b}):
 spec=importlib.util.spec_from_file_location('antenna_audit',root/'scripts/audit_core_only_antenna_insertion.py')
 mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
class Admission(unittest.TestCase):
 def setUp(self):
  self.before=dict(instances={'original':(('sg13g2_buf_1','R0',0,0,1,1),'PLACED')},terminals={('original','A'):'n1'},special_and_ports=('power','ports'),nets={'n1':'SIGNAL','n2':'SIGNAL','VDD':'POWER','VSS':'GROUND'},die=(0,0,100,100))
  self.after=copy.deepcopy(self.before);self.after['instances']['ANTENNA_1']=(('sg13g2_antennanp','R0',1,0,2,1),'PLACED')
  terms=[dict(pin='A',type='SIGNAL',net='n1'),dict(pin='VDD',type='POWER',net='VDD'),dict(pin='VSS',type='GROUND',net='VSS')]
  self.cells={'ANTENNA_1':dict(master='sg13g2_antennanp',placement='PLACED',terms=terms,signal_terms=[terms[0]])}
  self.after['terminals'].update({('ANTENNA_1',t['pin']):t['net']for t in terms})
 def check(self):return mod.compare(self.before,self.after,self.cells)
 def reject(self):
  with self.assertRaises(AssertionError):self.check()
 def test_additive_diode(self):
  r=self.check();self.assertEqual(r['new_diodes'],1);self.assertFalse(r['accepted']);self.assertFalse(r['signal_wire_geometry_checked'])
 def test_original_removed(self):del self.after['instances']['original'];self.reject()
 def test_original_moved(self):self.after['instances']['original']=(('sg13g2_buf_1','R0',1,0,2,1),'PLACED');self.reject()
 def test_original_resized(self):self.after['instances']['original']=(('sg13g2_buf_2','R0',0,0,1,1),'PLACED');self.reject()
 def test_original_status_changed(self):self.after['instances']['original']=(self.after['instances']['original'][0],'FIRM');self.reject()
 def test_original_reconnected(self):self.after['terminals'][('original','A')]='n2';self.reject()
 def test_power_geometry_changed(self):self.after['special_and_ports']=('changed','ports');self.reject()
 def test_net_added(self):self.after['nets']['new']='SIGNAL';self.reject()
 def test_die_changed(self):self.after['die']=(0,0,101,100);self.reject()
 def test_wrong_new_master(self):self.cells['ANTENNA_1']['master']='sg13g2_buf_1';self.reject()
 def test_unplaced_diode(self):self.cells['ANTENNA_1']['placement']='UNPLACED';self.reject()
 def test_floating_diode(self):self.cells['ANTENNA_1']['terms'][0]['net']=None;self.reject()
 def test_wrong_power_net(self):self.cells['ANTENNA_1']['terms'][1]['net']='VSS';self.reject()
 def test_signal_on_supply(self):self.cells['ANTENNA_1']['terms'][0]['net']='VDD';self.reject()
 def test_inventory_missing(self):self.cells={};self.reject()
 def test_unknown_net(self):self.cells['ANTENNA_1']['terms'][0]['net']='unknown';self.reject()
 def test_wrong_signal_pin(self):self.cells['ANTENNA_1']['terms'][0]['pin']='B';self.reject()
if __name__=='__main__':unittest.main(verbosity=2)
