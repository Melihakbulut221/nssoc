# SPDX-License-Identifier: Apache-2.0
"""Replay frozen DP inputs with bounded ambiguity search; diagnostic only."""
import hashlib,json,zipfile,tarfile,io,pathlib,subprocess,os,time,sys
P=pathlib.Path
out=P('out');out.mkdir(exist_ok=True);derived=out/'derived';derived.mkdir(exist_ok=True)
native=out/'native'
def sha(p):
 with P(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
r={'source_run':43562021054,'accepted':False,'manufacturing_approval':False,'full_chip_lvs_passed':False,'scope':'Explicit 32cell_block correspondence and resource-bounded comparison diagnosis. All native devices, connections, dimensions and strict port checks retained. Limit exhaustion is failure, never a match waiver.'}
rc=2
try:
 controls=json.loads((out/'comparison-controls.json').read_text());assert controls['status']=='PASS' and len(controls['cases'])==15
 r['controls']=controls
 assert sha('/tmp/klayout.deb')=='0bb6b913fd6a32581d50b08be744b522a2a477baa1ed7e253c97cc18ce248a24'
 assert subprocess.check_output(['klayout','-b','-v'],text=True).strip()=='KLayout 0.30.13'
 assert sha('/usr/bin/klayout')=='288ed7a513436fac79255686914ff71b1d351fd79bd98f2eb6f9fecd14e149f7'
 assert sha('native.zip')=='d0109ba41e2d146d25a90f7dcaeba2602b87168cbe9b0d01a175b57b1734658e'
 z=zipfile.ZipFile('native.zip');assert z.namelist()==['native-dp.tgz']
 with tarfile.open(fileobj=io.BytesIO(z.read('native-dp.tgz')),mode='r:gz') as t:
  for m in t.getmembers():
   assert not P(m.name).is_absolute() and '..' not in P(m.name).parts and P(m.name).parts[0]=='native'
   assert m.isfile() or m.isdir()
  t.extractall(out,filter='data')
 assert sha(native/'command.json')=='db39410a14ac3266146756e757afcf8538e60817843a81700fee1ab6438a5fd1'
 cmd=json.loads((native/'command.json').read_text());assert cmd[:4]==['/usr/bin/klayout','-b','-zz','-r']
 deck=P(cmd[4]);assert deck.is_file() and deck.is_relative_to(P.cwd()/'out/native')
 assert sha(deck)=='48fb77c91708f55121d9d801b917eab1364b778fd3b49deb944ba29a0cbc527c'
 assert sha(deck.parent/'rule_decks/custom_reader.lvs')=='87a75b402b35d7306153a66089c0f0105b4e50c4816c7c553d97219af6c41519'
 assert sha(native/'engineering-reference-v1.cdl')=='1b8f2b6d11af2956fa0caf074b8329bf2e49722a4c5ce954c2119ad9ae4992b0'
 options=dict(v.split('=',1) for v in cmd[5:] if '=' in v)
 assert options['allow_unmatched_ports']=='false' and options['no_simplify']=='true' and options['no_series_res']=='true' and options['no_parallel_res']=='true'
 assert sha(options['input'])=='420b5223d14e2f873a2464849e3decbbec2b5b16b3c6a0f8cd2bb21b0d52365b'
 assert not P(options['report']).exists()
 from namespace_sram_macro import namespace_macro,namespace_deck
 ns=namespace_macro(options['input'],native/'engineering-reference-v1.cdl',options['topcell'],'NSDP_',derived/'namespace-proof.json')
 r['namespace']=ns
 assert cmd.count('top_lvl_pins=false')==1
 cmd[cmd.index('top_lvl_pins=false')]='top_lvl_pins=true'
 (native/'effective-command.json').write_text(json.dumps(cmd))
 r['command_change']={'top_lvl_pins':{'before':False,'after':True},'allow_unmatched_ports':False}
 text=deck.read_text();lines=text.splitlines(keepends=True)
 hits=[i for i,l in enumerate(lines) if 'logger.info' in l and 'Starting SG13G2 LVS Comparison with flag_missing_ports' in l]
 assert len(hits)==1,hits
 i=hits[0];indent=lines[i][:len(lines[i])-len(lines[i].lstrip())]
 insertion=indent+'max_branch_complexity(512) # diagnostic search bound, no acceptance change\n'
 assert 'max_branch_complexity' not in text
 revised=''.join(lines[:i])+insertion+''.join(lines[i:]);assert revised.replace(insertion,'',1)==text
 import re
 matches=list(re.finditer(r'(?m)^(\s*)align\s*$',revised))
 assert len(matches)==1,[(m.start(),m.group()) for m in matches]
 m=matches[0];indent2=m.group(1)
 mapping='same_circuits("RM_IHPSG13_2P_BITKIT_16x2_SRAM", "RM_IHPSG13_256x16_c2_2P_BITKIT_16x2_SRAM")'
 guard='raise "Missing physical 32cell_block" unless netlist.circuit_by_name("RM_IHPSG13_2P_BITKIT_16x2_SRAM")\nraise "Missing reference 32cell_block" unless schematic.circuit_by_name("RM_IHPSG13_256x16_c2_2P_BITKIT_16x2_SRAM")'
 addition='\n'.join(indent2+l for l in (guard+'\n'+mapping).splitlines())+'\n'
 pairs=[('RM_IHPSG13_2P_COLUMN_64','RM_IHPSG13_256x16_c2_2P_COLUMN_pcell_0'),('RM_IHPSG13_2P_MATRIX_64x32','RM_IHPSG13_256x16_c2_2P_MATRIX_pcell_1')]
 for layout_name,reference_name in pairs:
  ruby=[f'raise "Missing layout circuit {layout_name}" unless netlist.circuit_by_name("{layout_name}")',f'raise "Missing reference circuit {reference_name}" unless schematic.circuit_by_name("{reference_name}")',f'same_circuits("{layout_name}", "{reference_name}")']
  addition+='\n'.join(indent2+line for line in ruby)+'\n'
 r['additional_explicit_pairs']=pairs
 revised=revised[:m.start()]+addition+revised[m.start():]
 assert revised.replace(addition,'',1).replace(insertion,'',1)==text
 r['explicit_cell_pair']=['RM_IHPSG13_2P_BITKIT_16x2_SRAM','RM_IHPSG13_256x16_c2_2P_BITKIT_16x2_SRAM']
 r['correspondence_scope']='Three hierarchy-name pairs before align only. Both cell contents still compared; no blanking, nil mapping, net or pin equivalence.'

 extra_ruby='nssoc_layout_top = netlist.circuit_by_name("RM_IHPSG13_2P_256x16_c2_bm_bist")\nnssoc_reference_top = schematic.circuit_by_name("RM_IHPSG13_2P_256x16_c2_bm_bist")\nnssoc_before = [nssoc_device_count(nssoc_layout_top), nssoc_device_count(nssoc_reference_top)]\nnssoc_extra_names = ["RSC_IHPSG13_INVX2", "RSC_IHPSG13_NAND2X2", "RSC_IHPSG13_CINVX4"]\n[netlist, schematic].each do |nl|\n  nssoc_extra_names.each do |name|\n    cell = nl.circuit_by_name(name)\n    raise "Missing normalization circuit #{name}" unless cell\n    nl.flatten_circuit(cell)\n  end\nend\nnssoc_after = [nssoc_device_count(nssoc_layout_top), nssoc_device_count(nssoc_reference_top)]\nnssoc_lp = nssoc_layout_top.each_pin.map { |pin| pin.name }\nnssoc_rp = nssoc_reference_top.each_pin.map { |pin| pin.name }\nFile.write("out/derived/top-port-and-extra-flatten.json", JSON.pretty_generate({\'before\'=>nssoc_before,\'after\'=>nssoc_after,\'flattened_cells_both_sides\'=>nssoc_extra_names,\'layout_pins\'=>nssoc_lp,\'reference_pins\'=>nssoc_rp,\'accepted\'=>false}))\nraise "Primitive conservation failed" unless nssoc_before == [70110,70110] && nssoc_after == nssoc_before\nraise "Top port contract differs" unless nssoc_lp.size == 215 && nssoc_rp.size == 215 && nssoc_lp.map(&:upcase).sort == nssoc_rp.map(&:upcase).sort\n'
 compare_anchor=indent+'max_branch_complexity(512) # diagnostic search bound, no acceptance change\n'
 assert revised.count(compare_anchor)==1
 extra_block='\n'.join(indent+line for line in extra_ruby.splitlines())+'\n'
 revised=revised.replace(compare_anchor,extra_block+compare_anchor,1)
 # Preserve native external pin creation before align can promote internal labels.
 port_lines=['netlist.make_top_level_pins if TOP_LVL_PINS\n','schematic.make_top_level_pins if TOP_LVL_PINS\n']
 for port_line in port_lines:
  assert revised.count(port_line)==1
  revised=revised.replace(port_line,'',1)
 assert revised.count(addition)==1
 revised=revised.replace(addition,''.join(port_lines)+addition,1)
 r['top_port_construction_stage']='Before align; native named-net creation unchanged, avoiding promotion of child internal labels to external pins.'
 revised=namespace_deck(revised,ns['renames'])
 deck.write_text(revised)
 r['deck_before_sha256']=hashlib.sha256(text.encode()).hexdigest();r['deck_after_sha256']=sha(deck)
 r['comparison_settings']={'max_branch_complexity':512,'max_depth':'unchanged default','native_timeout_seconds':1800}
 env=dict(os.environ);env.pop('GH_TOKEN',None);env.pop('GITHUB_TOKEN',None);env['QT_QPA_PLATFORM']='offscreen'
 start=time.monotonic()
 try:
  with (native/'bounded-run.log').open('w') as f:proc=subprocess.run(cmd,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=1800)
  r['returncode']=proc.returncode;r['elapsed_seconds']=time.monotonic()-start
 except subprocess.TimeoutExpired:
  r['elapsed_seconds']=time.monotonic()-start;raise
 if proc.returncode!=0:raise RuntimeError('Native run failed')
 audit=[sys.executable,'hw/soc/flow/audit_klayout_lvs.py',options['report'],'--top',options['topcell'],'--deck-log',options['log'],'--output',str(derived/'audit.json')]
 with (native/'bounded-audit.log').open('w') as f:a=subprocess.run(audit,env=env,stdout=f,stderr=subprocess.STDOUT,timeout=300)
 r['audit_returncode']=a.returncode
 assert (derived/'audit.json').is_file()
 report=json.loads((derived/'audit.json').read_text())
 r['comparison_passed_within_diagnostic_scope']=a.returncode==0 and report['status']=='PASS within comparison scope' and not report['reasons']
 r['status']='DIAGNOSTIC_COMPARISON_COMPLETE';rc=0
except Exception as e:r['status']='ERROR_OR_INCOMPLETE_DIAGNOSIS';r['error']=type(e).__name__+': '+str(e)
finally:
 r['native_outputs']={p.name:{'bytes':p.stat().st_size,'sha256':sha(p)} for p in native.glob('*') if p.is_file()}
 r['log_tail']={name:(native/name).read_text(errors='replace').splitlines()[-100:] for name in ['bounded-run.log','deck.log','bounded-audit.log'] if (native/name).is_file()}
 (derived/'bounded-result.json').write_text(json.dumps(r,indent=2));print(r['status']);sys.exit(rc)
