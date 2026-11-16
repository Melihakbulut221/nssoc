"""Supplemental derived-model four-state gate boot; never native timing acceptance."""
import os,sys,pathlib,json,hashlib
ROOT=pathlib.Path.cwd()
assert os.environ.get('GITHUB_ACTIONS')=='true'
sys.path.insert(0,str(ROOT/'hw/soc/flow'))
from sim_logic_boot_gl import boot_checks,run_logged,digest
from ihp_zero_delay_aliases import adapt,SOURCE_SHA
out=ROOT/'out/cvc-chip-boot';out.mkdir(parents=True,exist_ok=False)
r=dict(source_head=os.environ['GITHUB_SHA'],passed=False,native_gate_boot_accepted=False,full_phy_accepted=False,final_timing_complete=False,
 scope='Supplemental four-state zero-delay derived-standard-cell functional gate boot. No native/SDF/timing acceptance; SRAM simulator equivalence not independently established. No simultaneous-transition equivalence claim.')
def save():(out/'result.json').write_text(json.dumps(r,indent=2)+'\n')
try:
 q=json.loads((ROOT/'cvc-cell-qualification/result.json').read_text())
 assert q['passed'] and q['source_unchanged'] and len(q['cells'])==16 and q['mutation']['mismatches']>0
 assert q['total_reference_trace_rows']==374784
 assert q['derived_sha256']=='b1280e76c1e322681066805af26b7405d93cae36b58de079045c85342b5b101f'
 for c in q['cells']:
  assert c['iverilog-derived_mismatch_count']==c['cvc-derived_mismatch_count']==0
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
 # Add exact mapped CSR/register operands; require both classes before simulation.
 import re
 csr_suffixes={'csr_addr_i','csr_wdata_i','csr_op_i','csr_we_int','mtvec_q','mepc_q','csr_save_cause_i','csr_save_id_i','csr_save_if_i'}
 reg_suffixes={'rf_raddr_a','rf_raddr_b','rf_rdata_a','rf_rdata_b','rf_waddr_wb','rf_wdata_wb','rf_we_wb','rf_wdata_wb_ecc','branch_decision_i','branch_taken','pc_set_o'}
 extras=[];groups={'csr':0,'reg':0}
 for name,net in sorted(mapped['core_signals'].items()):
  leaf=name.rsplit('.',1)[-1];group='csr'if leaf in csr_suffixes else'reg'if leaf in reg_suffixes else None
  if group is None or not name.startswith('u_ibex.') or not 1<=len(net['bits'])<=39:continue
  if any(name==n for _,n,_ in signals):continue
  label=group+str(groups[group]);groups[group]+=1;extras.append((label,name,len(net['bits'])))
 assert groups['csr']>=3 and groups['reg']>=3,('Missing first-divergence observability',groups)
 assert len(extras)<=80,('Unexpected signal ambiguity',len(extras))
 signals+=extras
 r['extra_signal_groups']=groups
 for label,name,width in signals:
  assert name in mapped["core_signals"] and len(mapped["core_signals"][name]["bits"])==width
 fields=" ".join(label+"=%h" for label,name,width in signals)
 refs=", ".join("tb_logicrom_gl.dut.\\"+name+" " for label,name,width in signals)
 observer=out/"boot_observer.v"
 observer.write_text(chr(96)+'timescale 1ns/1ps\nmodule nssoc_cloud_boot_observer;\nalways @(negedge tb_logicrom_gl.clk) begin\n if (tb_logicrom_gl.rst_n && (tb_logicrom_gl.cycles<300 || tb_logicrom_gl.cycles%1000==0 || (tb_logicrom_gl.cycles>=2179000 && tb_logicrom_gl.cycles<=2185000) || (tb_logicrom_gl.cycles>=2370000 && tb_logicrom_gl.cycles<=2374000)))\n  $display("NSSOC_BOOT_TRACE cycle=%0d '+fields+'", tb_logicrom_gl.cycles, '+refs+');\nend\nendmodule\n')
 r["observer"]=dict(sha256=digest(observer),signals=signals,source_map_run=43768772862,source_map_sha256=digest(mapped_path),read_only=True,cycle_bound_unchanged=4000000,dense_cycle_windows=[[2179000,2185000],[2370000,2374000]],purpose='Diagnose first app copy-loop divergence and first trap, preserving original firmware/netlist/watchdog')
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
