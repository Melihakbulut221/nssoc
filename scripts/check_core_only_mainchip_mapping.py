import os,sys,json,hashlib
from pathlib import Path
assert os.environ.get('GITHUB_ACTIONS')=='true'
assert os.environ['SOC_RELEASE_PROFILE']=='core-only' and os.environ['SOC_PCIE_PROFILE']=='off' and os.environ['SOC_ETH_SRAM']=='0'
root=Path(sys.argv[1]);m=json.loads((root/'synthesis/soc_top.mapped.json').read_text())['modules']['soc_top']
assert not any(n.startswith(('pcie_','eth_')) for n in m['ports'])
assert all(not any(x in n for x in ('u_pcie.','u_pcie_cdc.','u_pcie_apb.','u_eth.')) for n in m['cells'])
macros={}
for c in m['cells'].values():
 if c['type'].startswith('RM_IHPSG13'):macros[c['type']]=macros.get(c['type'],0)+1
assert macros=={'RM_IHPSG13_1P_2048x64_c2_bm_bist':4},macros
for name in ['clk_i','spw_di_i','spw_do_o','i2c_scl_i','i2c_scl_oe_o','can_rx_i','can_tx_o','spi_sck_o','mbist_done_o','mbist_failed_o']:assert name in m['ports'],name
assert any('u_spw.'in n for n in m['cells']) and any('u_can.'in n for n in m['cells'])
assert any('mbist'in n.lower() for n in m['cells'])
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
Path('out').mkdir(exist_ok=True)
Path('out/mapping.json').write_text(json.dumps(dict(status='MAPPED_CORE_ONLY_REQUIRES_MAPPED_BOOT_AND_PHYSICAL_SIGNOFF',source_head=os.environ['GITHUB_SHA'],cells=len(m['cells']),macros=macros,ports=sorted(m['ports']),pcie_present=False,ethernet_present=False,accepted=False,mapped_boot_passed=False,final_timing_complete=False,outputs={str(p.relative_to(root)):sha(p)for p in root.rglob('*')if p.is_file()}),indent=2))
