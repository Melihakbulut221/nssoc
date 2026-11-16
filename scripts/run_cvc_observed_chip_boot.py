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
 libs=[s for s in sources if s.endswith('/sg13g2_stdcell.v')];assert len(libs)==1
 lib=pathlib.Path(libs[0]);assert digest(lib)==SOURCE_SHA
 derived,changes=adapt(lib.read_text());model=out/'derived-functional-standard-cells.v';model.write_text(derived)
 assert digest(model)==q['derived_sha256'] and len(changes)==16
 exe=out/'sim';cvc=ROOT/'cvc-source/build64/cvc64'
 cc=[str(cvc),'-sv','+nospecify','+define+NSSOC_CVC_ZERO_DELAY','-o',str(exe)]
 cc+=['+define+'+d[2:]for d in defines]+[s for s in sources if s!=str(lib)]+['-v',str(model)]

 # Observe exact mapped signals without altering firmware, netlist or bench.
 import subprocess,zipfile,io
 def api(path):return json.loads(subprocess.check_output(["gh","api","repos/Melihakbulut221/nssoc/"+path]))
 # Exact new mapped signal identities, no old map artifact.
 mapped_path=ROOT/'hw/soc/out/corrpre-pcie-mbist-native-boot/synthesis/soc_top.mapped.json'
 assert digest(mapped_path)=='13f96b84486caff79ce53b1e183d98443875208b26d962dfe9d95e62878d40d5'
 mapped_json=json.loads(mapped_path.read_text());assert 'soc_top'in mapped_json['modules']
 mapped={'core_signals':mapped_json['modules']['soc_top']['netnames']}
 signals=[
 ("pc","u_ibex.u_ibex_core.exs_id_pc_id",32),
 ("insn","u_ibex.u_ibex_core.exs_id_instr_rdata_alu_id",32),
 ("cause","u_ibex.u_ibex_core.cs_registers_i.mcause_q",7),
 ("mtvec","u_ibex.u_ibex_core.cs_registers_i.csr_mtvec_o",32),
 ("addr","bus_data_addr",32),("req","bus_data_req",1)]
 # Exact named operands from authenticated inventory; never accept empty selectors.
 inventory_run=api('actions/runs/43783831123')
 assert inventory_run['head_sha']=='63500c3cecadb6658b3709afdbcf98b5fe446a5d' and inventory_run['conclusion']=='success' and inventory_run['run_attempt']==1
 meta=api('actions/artifacts/14189567411')
 ihash='f1a0d6137d88855f4297973d05449ac3a064bf71428dc1414e64474bf3c6886a'
 assert meta['workflow_run']['id']==43783831123 and meta['digest']=='sha256:'+ihash and not meta['expired']
 ib=subprocess.check_output(['gh','api','repos/Melihakbulut221/nssoc/actions/artifacts/14189567411/zip'])
 assert hashlib.sha256(ib).hexdigest()==ihash
 inventory=json.loads(zipfile.ZipFile(io.BytesIO(ib)).read('result.json'))
 assert inventory['mapped_sha256']==digest(mapped_path)
 extras=[('x1', 'u_ibex.gen_regfile_ff.register_file_i.g_plain_rf.g_rf_flops[1].rf_reg_q', 32), ('x2', 'u_ibex.gen_regfile_ff.register_file_i.g_plain_rf.g_rf_flops[2].rf_reg_q', 32), ('x3', 'u_ibex.gen_regfile_ff.register_file_i.g_plain_rf.g_rf_flops[3].rf_reg_q', 32), ('x5', 'u_ibex.gen_regfile_ff.register_file_i.g_plain_rf.g_rf_flops[5].rf_reg_q', 32), ('x6', 'u_ibex.gen_regfile_ff.register_file_i.g_plain_rf.g_rf_flops[6].rf_reg_q', 32), ('x7', 'u_ibex.gen_regfile_ff.register_file_i.g_plain_rf.g_rf_flops[7].rf_reg_q', 32), ('x28', 'u_ibex.gen_regfile_ff.register_file_i.g_plain_rf.g_rf_flops[28].rf_reg_q', 32), ('raddr_a', 'u_ibex.gen_regfile_ff.register_file_i.raddr_a_i', 5), ('raddr_b', 'u_ibex.gen_regfile_ff.register_file_i.raddr_b_i', 5), ('waddr', 'u_ibex.gen_regfile_ff.register_file_i.waddr_a_i', 5), ('wraddr', 'u_ibex.gen_regfile_ff.register_file_i.g_plain_rf.wr_addr', 5), ('csraddr', 'u_ibex.u_ibex_core.cs_registers_i.csr_addr', 12), ('id_valid', 'u_ibex.u_ibex_core.exs_id_instr_valid_id', 1), ('ex_valid', 'u_ibex.u_ibex_core.g_ex_stage.exs_ex_valid_q', 1), ('ex_insn', 'u_ibex.u_ibex_core.g_ex_stage.exs_ex_instr_rdata_alu_id_q', 32), ('ex_compressed', 'u_ibex.u_ibex_core.g_ex_stage.exs_ex_instr_is_compressed_id_q', 1), ('branch_raw', 'u_ibex.u_ibex_core.id_stage_i.branch_set_raw', 1), ('branch_done', 'u_ibex.u_ibex_core.id_stage_i.branch_jump_set_done_q', 1)]
 for label,name,width in extras:
  actual=mapped['core_signals'][name];known=inventory['signals'][name]
  assert known['width']==width and len(actual['bits'])==width and actual['bits']==known['bits'],name
 signals+=extras
 r['operand_inventory']=dict(run=43783831123,artifact=14189567411,sha256=ihash,exact_extra_signals=len(extras))
 # Bind every boundary observation to the exact restored mapped net inventory.
 # Primary combinational IF aliases were removed by synthesis. Observe retained
 # FIFO state and native SRAM ports, without claiming full IF handshake coverage.
 boundary=[('data_we', 'bus_data_we', 1), ('data_wdata', 'bus_data_wdata', 32), ('fetch_addr', 'u_ibex.u_ibex_core.if_stage_i.gen_prefetch_buffer.prefetch_buffer_i.fetch_addr_q', 32), ('stored_addr', 'u_ibex.u_ibex_core.if_stage_i.gen_prefetch_buffer.prefetch_buffer_i.stored_addr_q', 32), ('fetch_fifo_words', 'u_ibex.u_ibex_core.if_stage_i.gen_prefetch_buffer.prefetch_buffer_i.fifo_i.rdata_q', 96), ('fetch_fifo_errors', 'u_ibex.u_ibex_core.if_stage_i.gen_prefetch_buffer.prefetch_buffer_i.fifo_i.err_q', 3), ('fetch_outstanding', 'u_ibex.u_ibex_core.if_stage_i.gen_prefetch_buffer.prefetch_buffer_i.rdata_outstanding_q', 2), ('fetch_valid_req', 'u_ibex.u_ibex_core.if_stage_i.gen_prefetch_buffer.prefetch_buffer_i.valid_req_q', 1), ('fetch_discard_req', 'u_ibex.u_ibex_core.if_stage_i.gen_prefetch_buffer.prefetch_buffer_i.discard_req_q', 1)]
 r['fetch_observation_scope']='Retained prefetch FIFO state and SRAM macro ports; original IF request/response aliases absent. Not full boundary handshake coverage.'
 r['fetch_inventory']=dict(run=43797213202,artifact=14194957387,sha256='acf4d1bfe724714e585bf421a23b2e927cd05882f3de3f7494f8c8dde3a5c39d')
 signals+=boundary
 suffixes={"row_en","row_we","row_addr","row_din","row_bm","row_dout",
           "func_row_en","func_row_we","func_row_addr","func_row_din","func_row_bm",
           "bank_q","rd_word","raw_q","req_i","addr_i","rvalid_o","rdata_o"}
 memory_names=sorted(n for n in mapped["core_signals"] if n.startswith("u_ram.") and n.rsplit(".",1)[-1] in suffixes)
 assert 1<=len(memory_names)<=96, memory_names
 macro_cells={n:c for n,c in mapped_json["modules"]["soc_top"]["cells"].items() if c["type"]=="RM_IHPSG13_1P_2048x64_c2_bm_bist"}
 assert len(macro_cells)==4 and all(n.startswith("u_ram.") for n in macro_cells),list(macro_cells)
 macro_signals=[]
 for i,(name,cell) in enumerate(sorted(macro_cells.items())):
  for port,width in [("A_ADDR",11),("A_DOUT",64),("A_DIN",64),("A_BM",64),("A_MEN",1),("A_WEN",1),("A_REN",1)]:
   assert len(cell["connections"][port])==width,(name,port)
   macro_signals.append(("ram"+str(i)+"_"+port.lower(),name,port,width))
 r["native_macro_port_inventory"]=dict(mapped_sha256=digest(mapped_path),signals=macro_signals,connections={n:c["connections"]for n,c in macro_cells.items()},read_only=True)
 for i,name in enumerate(memory_names):
  width=len(mapped["core_signals"][name]["bits"])
  assert 1<=width<=64,(name,width)
  signals.append(("mem_"+str(i),name,width))
 r["memory_boundary_inventory"]=dict(mapped_sha256=digest(mapped_path),signals=boundary+signals[-len(memory_names):],read_only=True)
 for label,name,width in signals:
  assert name in mapped["core_signals"] and len(mapped["core_signals"][name]["bits"])==width
 fields=" ".join(label+"=%h" for label,name,width in signals)
 refs=", ".join("tb_logicrom_gl.dut.\\"+name+" " for label,name,width in signals)
 fields+=" "+" ".join(label+"=%h" for label,cell,port,width in macro_signals)
 refs+=", "+", ".join("tb_logicrom_gl.dut."+chr(92)+cell+" ."+port for label,cell,port,width in macro_signals)
 observer=out/"boot_observer.v"
 prefix="tb_logicrom_gl.dut."+chr(92)
 actual_write=next(name for label,name,width in boundary if label=="data_we")
 write_condition="("+prefix+"bus_data_req  && "+prefix+actual_write+"  && ("+prefix+"bus_data_addr  < 32'h00000080))"
 lines=[chr(96)+"timescale 1ns/1ps","module nssoc_cloud_boot_observer;",
        "always @(negedge tb_logicrom_gl.clk) begin",
        " if (tb_logicrom_gl.rst_n && ("+write_condition+" || tb_logicrom_gl.cycles<300 || tb_logicrom_gl.cycles%1000==0 || (tb_logicrom_gl.cycles>=2179000 && tb_logicrom_gl.cycles<=2185000) || (tb_logicrom_gl.cycles>=2370000 && tb_logicrom_gl.cycles<=2374000)))",
        '  $display("NSSOC_BOOT_TRACE cycle=%0d '+fields+'", tb_logicrom_gl.cycles, '+refs+');',
        "end","endmodule"]
 observer.write_text(chr(10).join(lines)+chr(10))

 r["observer"]=dict(sha256=digest(observer),signals=signals,source_map_run=43768772862,source_map_sha256=digest(mapped_path),read_only=True,cycle_bound_unchanged=4000000,dense_cycle_windows=[[2179000,2185000],[2370000,2374000]],purpose='Observe retained prefetch FIFO state and native SRAM row ports plus low-address firmware writes; full IF handshake aliases unavailable. Preserve original firmware/netlist/watchdog and four-million-cycle acceptance.')
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
