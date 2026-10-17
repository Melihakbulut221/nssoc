#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Physical pins and extracted capacitance reference must stay distinct."""
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts'))
from review_cloud_pll_loop import validate_ports,reference_ports
class PortContract(unittest.TestCase):
    def test_distinct_reference_and_continuation(self):
        pins=['p'+str(i) for i in range(17)]
        text='.subckt child a b\n.ends\n.subckt pll '+' '.join(pins[:8])+'\n+ '+' '.join(pins[8:])+'\n.ends pll\n'
        self.assertEqual(reference_ports(text,'pll'),pins)
        validate_ports(pins+['wire_cref'],pins)
    def test_reject_lost_renamed_or_duplicated_physical_port(self):
        pins=['p'+str(i) for i in range(17)]
        for bad in [pins, pins[:-1]+['other','wire_cref'], pins[:-1]+[pins[0],'wire_cref'], pins+['wire_cref','extra']]:
            with self.subTest(bad=bad),self.assertRaises(AssertionError):validate_ports(bad,pins)
    def test_reject_reference_as_physical_port(self):
        pins=['p'+str(i) for i in range(16)]+['wire_cref']
        with self.assertRaises(AssertionError):validate_ports(pins+['extra'],pins)
if __name__=='__main__':unittest.main()
