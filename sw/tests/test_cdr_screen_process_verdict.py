# SPDX-License-Identifier: Apache-2.0
"""Exercise the actual circuit-screen report with failed simulator processes."""
import importlib.util,json,pathlib,sys,tempfile,unittest
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'scripts'))
import cdr_n1_divider_whatif as screen
class ScreenVerdict(unittest.TestCase):
 def exercise(self,rc,wave_ok):
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp)/'root'; native=root/'native'
   for folder in ['composition-n1','loaded-n1-nominal_late','models/source/runtime']:
    (native/folder).mkdir(parents=True)
   (root/'derived').mkdir()
   (root/'derived/loaded-n1-nominal_late.json').write_text(json.dumps(dict(vectors=[],binding={},source_bits=[],data_offset_s=0)))
   (native/'composition-n1/model.cir').write_text('* test control circuit')
   (native/'loaded-n1-nominal_late/bench.cir').write_text('* test bench')
   (native/'models/source/runtime/patched-ngspice').write_text('test stub')
   def measure(*args):
    result=args[6];result.update(data_passed=wave_ok,devices_passed=True,phase_passed=True,phase_average_v=.04)
    if not wave_ok:raise AssertionError('injected data failure')
   with patch.object(screen.subprocess,'run') as run, patch.object(screen.loaded,'read_streamed_wave',return_value=(np.array([0.,1.]),{},dict(header_rows=2,raw_sha256='test'))), patch.object(screen.loaded,'measure_wave',side_effect=measure), patch.object(screen.np,'savez_compressed'):
    run.return_value.returncode=rc
    screen.main(root,'control',pathlib.Path(tmp)/'out')
   result=json.loads((pathlib.Path(tmp)/'out/result.json').read_text())
   self.assertEqual(result['passed'],rc==0 and wave_ok)
   self.assertEqual(result['waveform_passed'],wave_ok)
   self.assertEqual(result['simulator_passed'],rc==0)
   self.assertFalse(result['electrical_acceptance'])
   self.assertFalse(result['new_layout'])
 def test_successful_process_and_wave(self):self.exercise(0,True)
 def test_failed_process_with_good_wave(self):self.exercise(1,True)
 def test_killed_process_with_good_wave(self):self.exercise(-9,True)
 def test_good_process_with_bad_wave(self):self.exercise(0,False)
 def test_failed_process_and_bad_wave(self):self.exercise(1,False)
if __name__=='__main__':unittest.main()
