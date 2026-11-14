"""Verify actual main-chip mapping, never claim boot or physical acceptance."""
import collections,hashlib,json,os,pathlib,sys,subprocess,re
P=pathlib.Path;out=P(sys.argv[1]);syn=out/'synthesis'
def sha(p):
 h=hashlib.sha256()
 with P(p).open('rb') as f:
  for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
assert os.environ['SOC_PCIE_REPLAY_WRITE_PREDECODE']=='1'
ys=(syn/'soc_top_syn.ys').read_text();assert '-DSOC_PCIE_REPLAY_WRITE_PREDECODE' in ys
assert os.environ['SOC_PCIE_REPLAY_EOP_CACHE']=='1' and '-DSOC_PCIE_REPLAY_EOP_CACHE' in ys
assert sha('hw/soc/rtl/pcie/soc_pcie_replay_tx.v')=='a5891101ff12672cf6da0fa5da09c638e44fc7a5d4fc94b445535e7b00834d45'
m=json.loads((syn/'soc_top.mapped.json').read_text())['modules']['soc_top']
assert os.environ['SOC_PCIE_REPLAY_CRC_SELECT']=='1' and '-DSOC_PCIE_REPLAY_CRC_SELECT' in ys
assert os.environ['SOC_PCIE_RX_CURSOR_LOCAL_RESET']=='1' and '-DSOC_PCIE_RX_CURSOR_LOCAL_RESET' in ys
assert sha('hw/soc/rtl/pcie/soc_pcie_rx_credit.v')=='6e8736695b6fe059716fd90b5b8d969ca80a326f6c3a4705325bb5b7ec8831c0'
assert json.loads(P('out/rx-qualification-gate.json').read_text())['source_sha256']=='6e8736695b6fe059716fd90b5b8d969ca80a326f6c3a4705325bb5b7ec8831c0'
assert '-DSOC_PCIE_RX_READ2' in ys and '-DSOC_PCIE_RESET_COPIES' in ys
# Source span is obtained from actual lowered RTL, never inherited line numbers.
rtl=P('hw/soc/rtl/pcie/soc_pcie_replay_tx.v')
declared=set(re.findall(r'`(?:ifdef|ifndef)\s+(\w+)',rtl.read_text()))
enabled=sorted(k for k in declared if os.environ.get(k)=='1')
assert set(enabled)=={'SOC_PCIE_REPLAY_CRC_SELECT','SOC_PCIE_REPLAY_EOP_CACHE','SOC_PCIE_REPLAY_WRITE_PREDECODE','SOC_PCIE_REPLAY_AHEAD','SOC_PCIE_REPLAY_INBANK','SOC_PCIE_RESET_COPIES'}
flags=' '.join('-D '+k for k in enabled)
lowered_path=out/'replay-origin.lowered.json'
lower_script=out/'replay-origin.ys'
lower_script.write_text(f'read_verilog -sv {flags} hw/soc/rtl/pcie/soc_pcie_crc32_byte.v {rtl}; hierarchy -check -top soc_pcie_replay_tx; proc; write_json {lowered_path}\n')
with (out/'replay-origin.log').open('w')as stream:
 subprocess.run(['yosys','-Q','-T','-s',str(lower_script)],stdout=stream,stderr=subprocess.STDOUT,check=True)
lower=json.loads(lowered_path.read_text())['modules']['soc_pcie_replay_tx']
bits=lower['netnames']['replay_eop_q']['bits']
drivers=[c for c in lower['cells'].values()if c['type']=='$adff'and c['connections']['Q']==bits]
assert len(drivers)==1
origins=set(drivers[0]['attributes']['src'].split('|'))
assert len(origins)==1 and all(x.startswith(str(rtl)+':')for x in origins)
def same_origin(attributes):
 return any(token==origin or token.endswith('/'+origin)for token in attributes.split('|')for origin in origins)
cached=[{'name':n,'type':c['type'],'src':c['attributes'].get('src','')}for n,c in m['cells'].items()if c['type'].startswith('sg13g2_df')and same_origin(c['attributes'].get('src',''))]
assert len(cached)==1,cached
assert m["cells"][cached[0]["name"]]["connections"]["CLK"]==m["ports"]["pcie_clk_i"]["bits"]
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
result={'status':'MAPPED_RX_CURSOR_CRC_SELECT_EOP_CHIP_REQUIRES_GATE_BOOT_AND_PHYSICAL_IMPLEMENTATION','accepted':False,'source_head':os.environ['GITHUB_SHA'],'selected_widths':widths,'registered_bit_count':len(qdrivers),'cached_eop_register':cached,'lowered_eop_origins':sorted(origins),'crc_select_enabled':True,'rx_cursor_local_reset_enabled':True,'macros':macros,'cells':sum(counts.values()),'mapped_boot_passed':False,'final_timing_complete':False,'full_phy_accepted':False,'configuration':{k:v for k,v in os.environ.items() if k.startswith(('SOC_','IBEX_','NATIVE_'))},'inputs':{p:sha(p) for p in ['hw/soc/rtl/pcie/soc_pcie_rx_credit.v','hw/soc/rtl/pcie/soc_pcie_replay_tx.v','hw/soc/flow/syn_soc_top.sh','hw/soc/flow/sim_soc.sh','scripts/prepare_predecode_mainchip.sh']},'outputs':{str(p.relative_to(out)):sha(p) for p in out.rglob('*') if p.is_file()}}
P('out').mkdir(exist_ok=True);P('out/mapping.json').write_text(json.dumps(result,indent=2))
