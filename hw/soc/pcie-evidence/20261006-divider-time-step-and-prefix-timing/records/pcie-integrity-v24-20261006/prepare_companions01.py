from pathlib import Path
import ast,hashlib,json
R=Path.cwd();B=Path(__file__).resolve().parent
paths=[
'hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_integrity_v23.v',
'hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_continuous_rx_integrity_v23',
'scripts/check_pcie_gen3_continuous_rx_integrity_v23.py',
'hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v23.py',
'sw/tests/test_pcie_gen3_continuous_rx_integrity_v23.py',
'sw/tests/test_pcie_gen3_integrity_v23_miter.py',
'sw/tests/test_pcie_gen3_integrity_v23_block_burst.py',
]
for name in paths:
 old=R/name;new=R/name.replace('_v23','_v24');assert not new.exists()
 text=old.read_text().replace('v23','v24').replace('V23','V24').replace('v22','v23').replace('V22','V23')
 # V22 cache historical comments/counters changing names is harmless; V23 is now exact oracle.
 if name.endswith('miter.py'):
  text=text.replace('test_pcie_gen3_integrity_v24_header.py','test_pcie_gen3_integrity_v24_prefix.py')
 if name.endswith('block_burst.py'):
  text=text.replace('((22, "reference", "gold_"), (23, "candidate", ""))','((23, "reference", "gold_"), (24, "candidate", ""))').replace('for v in (22, 23):','for v in (23, 24):').replace('if v == 23 and fault:','if v == 24 and fault:')
 new.write_text(text)
# Component proof is now extracted from actual product function bytes, independent original V23 oracle.
text=(B/'test_matrix_relation01.py').read_text()
text=text.replace("B=Path(__file__).resolve().parent;R=B.parents[3]", "R=Path(__file__).resolve().parents[2];B=R/'hw/soc/rtl/pcie'")
text=text.replace("candidate=(B/'prefix_candidate01.vh').read_text()", "text=(B/'soc_pcie_gen3_framer_rx_integrity_v24.v').read_text()\n candidate=text[text.index('function automatic [95:0] token_prefix_context;'):text.index(' function automatic [383:0] block_token_context;')]")
text += '''\n\ndef test_exact_generated_inverse_and_wrapper_bridge():
 GEN=runpy.run_path(str(R/'scripts/generate_pcie_integrity_prefix_v24.py'))
 new=(B/'soc_pcie_gen3_framer_rx_integrity_v24.v').read_text()
 assert new==GEN['candidate']() and GEN['inverse'](new)==GEN['SOURCE'].read_text()
 for name in ('hw/soc/rtl/pcie/soc_pcie_gen3_continuous_rx_integrity_v23.v',
              'hw/soc/tb/cocotb/Makefile.soc_pcie_gen3_continuous_rx_integrity_v23',
              'scripts/check_pcie_gen3_continuous_rx_integrity_v23.py'):
  assert (R/name.replace('_v23','_v24')).read_text().replace('_v24','_v23')==(R/name).read_text()
 old=(R/'hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v23.py').read_text()
 bench=(R/'hw/soc/tb/cocotb/test_soc_pcie_gen3_continuous_rx_integrity_v24.py').read_text()
 assert bench.replace('v24','v23').replace('V24','V23')==old
'''
p=R/'sw/tests/test_pcie_gen3_integrity_v24_prefix.py';assert not p.exists();p.write_text(text)
for name in paths:
 p=R/name.replace('_v23','_v24')
 if p.suffix=='.py':ast.parse(p.read_text())
ast.parse(text)
print('Versioned seven companions and actual-product component/inverse proof source; no HDL executed.')
