# SPDX-License-Identifier: Apache-2.0
"""Diagnose synthesized selector mismatch without accepting a restricted proof."""
import json,pathlib,subprocess,sys
out=pathlib.Path('out');gold=out/'gold';gold.mkdir(parents=True,exist_ok=True)
base='e6e887d858f30730da11fbe575c4b07550225257';p='hw/soc/rtl/pcie/soc_pcie_lcrc_tx.v'
subprocess.run(['git','fetch','--depth=1','origin',base],check=True)
(gold/'soc_pcie_lcrc_tx.v').write_bytes(subprocess.check_output(['git','show',base+':'+p]))
probe=subprocess.run([sys.executable,'scripts/check_pcie_selector_semantics.py',str(gold/'soc_pcie_lcrc_tx.v'),p])
record=json.loads((out/'selector-controls.json').read_text())
assert record['four_state_cases']==32768 and record['simulation_fault_rejected']
miter="""
module miter(input [255:0] data,input [3:0] cursor_word,input [1:0] cursor_byte,output [7:0] gold_value,gate_value,output mismatch);
gold g(data,cursor_word,cursor_byte,gold_value);
gate n(data,cursor_word,cursor_byte,gate_value);
assign mismatch=(gold_value !== gate_value);
endmodule
"""
(out/'selector-miter.v').write_text(miter)
results=[]
for index in [None,*range(16)]:
 label='all' if index is None else str(index)
 constraint='' if index is None else f'-set cursor_word {index}'
 ys=f'read_verilog -sv out/selector.v out/selector-miter.v; hierarchy -top miter; proc; flatten; memory_map; opt -keepdc; sat -enable_undef -set-def-inputs {constraint} -prove mismatch 0 -show-inputs -show-outputs;'
 script=out/f'selector-cex-{label}.ys';script.write_text(ys.replace(';',';\n'))
 x=subprocess.run(['yosys','-s',str(script)],capture_output=True,text=True,timeout=90)
 log=x.stdout+x.stderr;(out/f'selector-cex-{label}.log').write_text(log)
 assert x.returncode==0,log[-1000:]
 passed='SAT proof finished - no model found: SUCCESS!' in log
 failed='SAT proof finished - model found: FAIL!' in log
 assert passed != failed,log[-1000:]
 results.append(dict(cursor_word=index,all_binary_inputs_equivalent=passed,counterexample_found=failed))
 print(json.dumps(results[-1]),flush=True)
r=dict(status='DIAGNOSTIC_COMPLETE_NOT_FULL_EQUIVALENCE',source_base=base,selector_controls=record,queries=results,scope='Direct synthesized four-state-equality miter with binary-defined input data and indices. Per-index queries localize a counterexample; they do not waive invalid-address behavior or constitute full-module equivalence.',formal_equivalence_proven=False,manufacturing_approval=False)
(out/'result.json').write_text(json.dumps(r,indent=2))
