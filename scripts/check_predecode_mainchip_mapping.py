"""Verify actual main-chip mapping, never claim boot or physical acceptance."""
import collections,hashlib,json,os,pathlib,sys
P=pathlib.Path;out=P(sys.argv[1]);syn=out/'synthesis'
def sha(p):
 h=hashlib.sha256()
 with P(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
assert os.environ['SOC_PCIE_REPLAY_WRITE_PREDECODE']=='1'
ys=(syn/'soc_top_syn.ys').read_text();assert '-DSOC_PCIE_REPLAY_WRITE_PREDECODE' in ys
assert os.environ['SOC_PCIE_REPLAY_EOP_CACHE']=='1' and '-DSOC_PCIE_REPLAY_EOP_CACHE' in ys
assert sha('hw/soc/rtl/pcie/soc_pcie_replay_tx.v')=='e478d785013174a7a7ce63b6fcbd8aa609736e65e292748eb8c0311e453f69e8'
m=json.loads((syn/'soc_top.mapped.json').read_text())['modules']['soc_top']
cached=[{'name':n,'type':c['type'],'src':c['attributes'].get('src','')} for n,c in m['cells'].items() if c['type'].startswith('sg13g2_df') and 'hw/soc/rtl/pcie/soc_pcie_replay_tx.v:310.5-322.8' in c['attributes'].get('src','').split('|')]
assert len(cached)==1,cached
selected={name:net for name,net in m['netnames'].items() if name.endswith(('.write_low','.write_group'))}
assert len(selected)==2,sorted(selected)
widths={name:len(net['bits']) for name,net in selected.items()}
assert sorted(widths.values())==[10,16],widths
assert all(all(isinstance(b,int) for b in n['bits']) for n in selected.values())
bits={b for n in selected.values() for b in n['bits']};assert len(bits)==26
qdrivers={}
for name,cell in m['cells'].items():
 for port,conn in cell['connections'].items():
  if cell['port_directions'][port]=='output':
   for bit in conn:
    if bit in bits:qdrivers.setdefault(bit,[]).append({'cell':name,'type':cell['type'],'port':port})
assert set(qdrivers)==bits
assert all(len(v)==1 and v[0]['type'].startswith('sg13g2_') and v[0]['port']=='Q' and 'CLK' in m['cells'][v[0]['cell']]['connections'] for v in qdrivers.values()),qdrivers
counts=collections.Counter(c['type'] for c in m['cells'].values());macros={k:v for k,v in counts.items() if k.startswith('RM_IHPSG13')}
assert sum(macros.values())==20 and macros.get('RM_IHPSG13_2P_256x16_c2_bm_bist')==16,macros
result={'status':'MAPPED_NEW_EOP_CACHE_CHIP_REQUIRES_GATE_BOOT_AND_PHYSICAL_IMPLEMENTATION','accepted':False,'source_head':os.environ['GITHUB_SHA'],'selected_widths':widths,'registered_bit_count':len(qdrivers),'cached_eop_register':cached,'macros':macros,'cells':sum(counts.values()),'mapped_boot_passed':False,'final_timing_complete':False,'full_phy_accepted':False,'configuration':{k:v for k,v in os.environ.items() if k.startswith(('SOC_','IBEX_','NATIVE_'))},'inputs':{p:sha(p) for p in ['hw/soc/rtl/pcie/soc_pcie_replay_tx.v','hw/soc/flow/syn_soc_top.sh','hw/soc/flow/sim_soc.sh','scripts/prepare_predecode_mainchip.sh']},'outputs':{str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}}
P('out').mkdir(exist_ok=True);P('out/mapping.json').write_text(json.dumps(result,indent=2))
