"""Supplemental derived-model four-state gate boot; never native timing acceptance."""
import os,sys,pathlib,json,hashlib
ROOT=pathlib.Path.cwd()
assert os.environ.get('GITHUB_ACTIONS')=='true'
sys.path.insert(0,str(ROOT/'hw/soc/flow'))
from sim_logic_boot_gl import boot_checks,run_logged,digest
from ihp_functional_nba import adapt,SOURCE_SHA
out=ROOT/'out/cvc-chip-boot';out.mkdir(parents=True,exist_ok=False)
r=dict(source_head=os.environ['GITHUB_SHA'],passed=False,native_gate_boot_accepted=False,full_phy_accepted=False,final_timing_complete=False,
 scope='Supplemental four-state zero-delay derived-standard-cell functional gate boot. NBA-output functional diagnostic ONLY. Native zero-delay library differs on deep clock compositions; compiled CVC wide X/Z comparison defect is independently documented. Replayed directed SRAM/cell gates do not establish whole-chip native or SDF equivalence. No physical/timing acceptance.')
def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
try:
 # Fresh monitor proof is mandatory before the four-million-cycle boot.
 monitor=ROOT/'hw/soc/tb/mapped_mbist_boot_monitor.v'
 proof_path=ROOT/'mbist-monitor-probe/result.json'
 proof=json.loads(proof_path.read_text())
 assert proof['source_head']==os.environ['GITHUB_SHA']
 assert proof['status']=='PASS_SIGNED32_AND_BITWISE_UNKNOWN_MONITOR_CONTROLS'
 assert digest(monitor)==proof['fixed_sha256']=='6d6b7c1aa116ba428cc7d7401cecec23c3ee66645254dd7550a81460ffbff7df'
 assert len(proof['cases'])==10 and len(proof['controls'])==8 and len(proof['unknown_truth_table'])==5
 assert all(c['identical_to_original_iverilog'] and c['returncode']==0 and c['rows']==210 for c in proof['cases']if c['label'].startswith('fixed-'))
 assert all(c['detected'] for c in proof['controls'])
 assert all(c['rows']==16384 and c['mismatch_count']==0 and c['returncode']==0 for c in proof['unknown_truth_table'])
 for name,sha in proof['outputs'].items():
  path=ROOT/'mbist-monitor-probe'/name
  assert path.resolve().is_relative_to((ROOT/'mbist-monitor-probe').resolve())
  assert digest(path)==sha
 r['fresh_monitor_proof']=dict(sha256=digest(proof_path),monitor_sha256=digest(monitor),scope='Observer only; no DUT or native-model equivalence claim')
 q=json.loads((ROOT/'cvc-cell-qualification/result.json').read_text())
 assert q['passed'] and q['source_unchanged'] and len(q['cells'])==16 and q['mutation']['mismatches']>0
 assert q['total_reference_trace_rows']==374784
 assert q['derived_sha256']=='45b335d8e543ab7b70afa0d269e6b59b08fd85227420dfe20f4255862c4c7a34'
 for c in q['cells']:
  assert c['iverilog-derived_mismatch_count']==c['iverilog-derived-enabled_mismatch_count']==c['cvc-derived_mismatch_count']==0
 # Bind this diagnostic to fresh directed gates, without promoting model equivalence.
 seq=json.loads((ROOT/'sram-sequence-qualification/result.json').read_text())
 assert seq['source_head']==os.environ['GITHUB_SHA'] and seq['passed'] and seq['sources_unchanged'] and seq['identical_traces'] and len(seq['cases'])==8
 assert all(c.get('detected') and c.get('meaningful_control') if c['mutation']else c.get('passed') and c.get('trace_rows')==12289 for c in seq['cases'])
 ram=json.loads((ROOT/'cvc-sram-qualification/result.json').read_text())
 assert ram['source_head']==os.environ['GITHUB_SHA'] and ram['passed'] and ram['sources_unchanged'] and len(ram['cases'])==2
 assert all(c['mismatches']==0 and c['mutation_mismatches']>0 for c in ram['cases'])
 diagnostic=json.loads((ROOT/'out/nba-diagnostic-scope.json').read_text());assert diagnostic['native_model_equivalent'] is False and diagnostic['derived_ideal_composition_passed']
 r['fresh_directed_gates']={p:digest(ROOT/p)for p in ['sram-sequence-qualification/result.json','cvc-sram-qualification/result.json','out/nba-diagnostic-scope.json']}
 r['native_model_equivalent']=False;r['compiler_known_wide_case_defect']=True
 inp=ROOT/'out/cvc-boot-preparation/inputs.json';record=json.loads(inp.read_text())
 assert record['simulator']=='iverilog' and record['cycle_bound']==4000000
 command=record['compile_command'];defines=[s for s in command if s.startswith('-D')]
 assert all('-D'+x in defines for x in ['FUNCTIONAL','NSSOC_GL_MBIST','NSSOC_GL_PCIE','NSSOC_GL_PCIE_ASYNC'])
 for p,info in record['sources'].items():assert digest(p)==info['sha256'] and pathlib.Path(p).stat().st_size==info['bytes']
 sources=[s for s in command if s.endswith('.v')]
 assert str(monitor) in sources or any(pathlib.Path(s).resolve()==monitor for s in sources)
 libs=[s for s in sources if s.endswith('/sg13g2_stdcell.v')];assert len(libs)==1
 lib=pathlib.Path(libs[0]);assert digest(lib)==SOURCE_SHA
 derived,changes=adapt(lib.read_text());model=out/'derived-functional-standard-cells.v';model.write_text(derived)
 assert digest(model)==q['derived_sha256'] and len(changes)==16
 exe=out/'sim';cvc=ROOT/'cvc-source/build64/cvc64'
 cc=[str(cvc),'-sv','+nospecify','+define+NSSOC_CVC_ZERO_DELAY','-o',str(exe)]
 cc+=['+define+'+d[2:]for d in defines]+[s for s in sources if s!=str(lib)]+['-v',str(model)]

 # Observe this exact new ACK map. No inherited historical signal inventory.
 binding=json.loads((ROOT/'out/source-binding.json').read_text())
 assert binding['source_run']==43812773466 and binding['source_head']=='990f37537d3d82f7a97c418fc144727abb18e655'
 assert binding['accepted'] is False
 mapped_path=ROOT/'hw/soc/out/corrpre-pcie-mbist-native-boot/synthesis/soc_top.mapped.json'
 assert digest(mapped_path)==binding['mapped_json_sha256']=='e6b2b44049da71b74e9dd2adb30a551f7bb0883072f21d83e9bac93b70bc2ecd'
 assert binding['netlist_sha256']=='5b4f45a0919975a9a5da7d9dd11f4c59349dc17b361fa32282bf170a2db00165'
 mapped_json=json.loads(mapped_path.read_text())
 module=mapped_json['modules']['soc_top']
 signals=[("pc","u_ibex.u_ibex_core.exs_id_pc_id",32),
          ("insn","u_ibex.u_ibex_core.exs_id_instr_rdata_alu_id",32),
          ("cause","u_ibex.u_ibex_core.cs_registers_i.mcause_q",7),
          ("mtvec","u_ibex.u_ibex_core.cs_registers_i.csr_mtvec_o",32),
          ("addr","bus_data_addr",32),("req","bus_data_req",1)]
 for label,name,width in signals:
  assert name in module['netnames'] and len(module['netnames'][name]['bits'])==width
 macros={n:c['type'] for n,c in module['cells'].items()if c['type'].startswith('RM_IHPSG13')}
 assert len(macros)==20
 fields=" ".join(label+"=%h"for label,name,width in signals)
 refs=", ".join("tb_logicrom_gl.dut."+chr(92)+name+" "for label,name,width in signals)
 observer=out/'boot_observer.v'
 observer.write_text("\n".join([chr(96)+"timescale 1ns/1ps","module nssoc_cloud_boot_observer;",
  "always @(negedge tb_logicrom_gl.clk) begin",
  " if (tb_logicrom_gl.rst_n && (tb_logicrom_gl.cycles<300 || tb_logicrom_gl.cycles%1000==0))",
  '  $display("NSSOC_BOOT_TRACE cycle=%0d '+fields+'",tb_logicrom_gl.cycles,'+refs+');',
  "end","endmodule"])+"\n")
 r['observer']=dict(sha256=digest(observer),signals=signals,mapped_sha256=digest(mapped_path),
  read_only=True,cycle_bound_unchanged=4000000,
  scope='Current ACK map only. Diagnostic PC/CSR/bus sampling; original bench retains firmware, watchdog, PCIe idle and system/Ethernet MBIST acceptance.')
 r['source_binding']=binding
 r['macro_inventory']=macros
 cc.append(str(observer))

 r.update(qualification_sha256=digest(ROOT/'cvc-cell-qualification/result.json'),input_manifest_sha256=digest(inp),derived_sha256=digest(model),compiler_sha256=digest(cvc))
 save();r['compile']=run_logged(cc,out/'compile.log',1800);save()
 assert r['compile']['returncode']==0 and exe.is_file(),'CVC whole-chip compile failed'
 assert len(record['run_commands'])==1
 plus=[s for s in record['run_commands'][0]if s.startswith('+')]
 assert len(plus)==1 and plus[0].startswith('+flash0=')
 r['run']=run_logged([str(exe)]+plus,out/'run.log',14400)
 r['checks']=boot_checks((out/'run.log').read_text(),r['run']['returncode'],'packet-async','system-ethernet')
 r['sources_unchanged']=all(digest(p)==info['sha256']for p,info in record['sources'].items())
 r['observer_unchanged']=digest(observer)==r['observer']['sha256']
 assert r['observer_unchanged']
 r['trace_rows']=sum(line.startswith('NSSOC_BOOT_TRACE ')for line in (out/'run.log').read_text().splitlines())
 assert r['trace_rows']>0
 r['passed']=r['checks']['passed'] and r['sources_unchanged']
 assert r['passed'],'Supplemental whole-chip functional gate boot failed'
except BaseException as e:
 r['error']=repr(e);raise
finally:
 r['logs']={p.name:dict(sha256=digest(p),bytes=p.stat().st_size)for p in out.glob('*.log')}
 save()
