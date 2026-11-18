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
# Flattening/ABC renames cells. Bind named state bits to actual mapped FF Qs.
for prefix in ('u_pcie.','u_pcie_cdc.','u_pcie_apb.','u_eth.'):
 assert not any(n.startswith(prefix) for n in m['netnames']),prefix
qdrivers={}
for name,c in m['cells'].items():
 if c['type'].startswith('sg13g2_df'):
  for bit in c['connections'].get('Q',[]):qdrivers.setdefault(bit,[]).append(name)
retained={}
for net in ['u_spw.imask','u_can.u_bridge.rdata_q','u_ram.g_ram_2048x64_ecc.u_test_port.u_mbist.state_q']:
 bits=m['netnames'][net]['bits'];assert bits and all(isinstance(b,int) and len(qdrivers.get(b,[]))==1 for b in bits),net
 retained[net]=[qdrivers[b][0] for b in bits]
for name in ['spw_do_o','spw_so_o','can_tx_o']:
 bits=m['ports'][name]['bits'];assert all(isinstance(b,int) for b in bits),name
 for bit in bits:
  drivers=[n for n,c in m['cells'].items() for port,bs in c['connections'].items() if c['port_directions'][port]=='output' and bit in bs]
  assert len(drivers)==1,(name,drivers)
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
Path('out').mkdir(exist_ok=True)
Path('out/mapping.json').write_text(json.dumps(dict(status='MAPPED_CORE_ONLY_REQUIRES_MAPPED_BOOT_AND_PHYSICAL_SIGNOFF',source_head=os.environ['GITHUB_SHA'],cells=len(m['cells']),macros=macros,ports=sorted(m['ports']),retained_state_drivers=retained,pcie_present=False,ethernet_present=False,accepted=False,mapped_boot_passed=False,final_timing_complete=False,outputs={str(p.relative_to(root)):sha(p)for p in root.rglob('*')if p.is_file()}),indent=2))
