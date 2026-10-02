# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
from pathlib import Path
import json
import re
import shutil
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import run_cloud_alu_boot_trace as trace


def fixture():
    lines=[]
    for name,width in trace.FIELDS:
        declaration=('\\'+name+' ') if '.' in name else name
        lines.append('  wire '+(f'[{width-1}:0] ' if width>1 else '')+declaration+';')
    for name in trace.GATES:lines.append('  sg13g2_lgcp_1 \\'+name+'  (\n    .CLK(clk_i)\n  );')
    for name in trace.SRAMS:lines.append('  RM_IHPSG13_1P_2048x64_c2_bm_bist \\'+name+'  (\n    .A_CLK(clk_i)\n  );')
    models={'sg13g2_stdcell.v':'''module sg13g2_lgcp_1 (GCLK, GATE, CLK);
wire delayed_CLK, int_fwire_int_GATE, notifier;
ihp_latch (int_fwire_int_GATE, notifier);
endmodule''', 'RM_IHPSG13_1P_2048x64_c2_bm_bist.v':') i_SRAM_1P_behavioral_bm_bist (',
    'RM_IHPSG13_1P_core_behavioral_bm_bist.v':'always @(posedge CLK_MUX) MEN_MUX WEN_MUX REN_MUX ADDR_MUX BM_MUX DIN_MUX'}
    return '\n'.join(lines),models


def test_all_aliases_and_native_instances_bound():
    text,models=fixture();result=trace.validate_bindings(text,models)
    assert result['packed_bits']==sum(w for _,w in trace.FIELDS)
    assert len(result['cells'])==7
    assert result['fields'][0]['expression']=='dut.rst_raw_n'
    assert trace.ref('u_scrub.cnt[0]')=='dut.\\u_scrub.cnt[0] '


@pytest.mark.parametrize('fault',['missing_alias','wrong_width','duplicate_alias','missing_gate','wrong_sram','wrong_edge'])
def test_binding_failure_closed(fault):
    text,models=fixture()
    if fault=='missing_alias':text=text.replace('  wire rst_raw_n;','')
    elif fault=='wrong_width':text=text.replace('wire [31:0] bus_data_addr;','wire [30:0] bus_data_addr;')
    elif fault=='duplicate_alias':text+='\n  wire rst_raw_n;'
    elif fault=='missing_gate':text=text.replace('\\'+trace.GATES[0]+' ','\\wrong_gate ')
    elif fault=='wrong_sram':text=text.replace('RM_IHPSG13_1P_2048x64_c2_bm_bist','different_model')
    else:models['RM_IHPSG13_1P_core_behavioral_bm_bist.v']=models['RM_IHPSG13_1P_core_behavioral_bm_bist.v'].replace('posedge','negedge')
    with pytest.raises(ValueError):trace.validate_bindings(text,models)


def test_instrumentation_preserves_every_original_statement():
    original='module tb_logicrom_gl;\nreg clk; integer cycles;\nendmodule\n'
    instrumented=trace.instrument(original)
    assert instrumented.replace(trace.bindings(),'')==original
    assert instrumented.count('trace.memory_sample(')==4
    assert 'i_SRAM_1P_behavioral_bm_bist.CLK_MUX' in instrumented
    assert "11'h7a7" in instrumented and "32'h00001e9c" in instrumented
    assert not re.search(r'\b(force|release|deposit)\b',instrumented)
    assert '.memory[' in instrumented and not re.search(r'\.memory\[.*?\]\s*(?:=|<=)',instrumented)
    assert trace.q.CYCLES==3_000_000 and trace.CYCLES==1_600_000
    assert trace.START==983_044


def test_duplicate_instrumentation_rejected():
    with pytest.raises(ValueError):trace.instrument(trace.instrument('module tb; endmodule\n'))


def test_all_frozen_methods_still_match():
    assert set(trace.BASE_PINS)==set(trace.q.SOURCES)
    assert set(trace.HELPER_PINS)=={'hw/soc/flow/sim_logic_boot_gl.py','hw/soc/flow/gen_logic_boot_rom.py'}
    for name,sha in (trace.BASE_PINS|trace.HELPER_PINS).items():assert trace.q.common.sha(ROOT/name)==sha


@pytest.mark.parametrize('helper',tuple(trace.HELPER_PINS))
def test_dynamic_helper_mismatch_rejected_before_frozen_preparation(monkeypatch,tmp_path,helper):
    monkeypatch.setenv('GITHUB_ACTIONS','true')
    original_root=trace.q.ROOT;original_sha=trace.q.common.sha;called=[]
    monkeypatch.setattr(trace.q.common,'sha',lambda p:'0'*64 if p==ROOT/helper else original_sha(p))
    monkeypatch.setattr(trace.q,'boot_prepare',lambda *a:called.append(a))
    with pytest.raises(ValueError,match='Frozen qualification method changed'):
        trace.prepare(tmp_path/'out',tmp_path/'work','candidate')
    assert called==[] and trace.q.ROOT==original_root


def test_real_tiny_monitor_positive_masked_and_high_bit_negative_controls(tmp_path):
    # Tiny observer only. This never instantiates or runs the actual SoC.
    iverilog=shutil.which('iverilog');vvp=shutil.which('vvp')
    assert iverilog and vvp,'Icarus is required for the bounded trace observer controls'
    results=trace.tiny_controls(Path(iverilog),Path(vvp),tmp_path/'controls')
    assert results['known']['observation']['first_unknown'] is None
    assert results['masked_unknown']['observation']['first_unknown'] is None
    assert results['sample_high_bit']['observation']['first_unknown'][2]=='sample_mask_80000000'
    assert results['active_unknown']['observation']['first_unknown'][2]=='active_sram_bank_0'
    assert results['clock_unknown']['observation']['first_unknown'][2]=='clock_gate_unknown'
    known=tmp_path/'controls/known';text=(known/'run.log').read_text()
    with pytest.raises(ValueError,match='summary'):trace.validate_log(text.replace('TRACE_SUMMARY','MISSING'),known,boot=False)
    with pytest.raises(ValueError,match='summary'):trace.validate_log(text+text,known,boot=False)
    (known/'trace-samples.log').write_text('')
    with pytest.raises(ValueError,match='incomplete'):trace.validate_log(text,known,boot=False)


def test_full_soc_entrypoints_reject_local_execution(monkeypatch,tmp_path):
    monkeypatch.delenv('GITHUB_ACTIONS',raising=False)
    with pytest.raises(ValueError,match='cloud-only'):trace.prepare(tmp_path/'out',tmp_path/'work','candidate')
    with pytest.raises(ValueError,match='cloud-only'):trace.run(tmp_path/'out')


def test_generated_exact_named_bindings_compile_in_tiny_namespace(tmp_path):
    iverilog=shutil.which('iverilog');assert iverilog
    declarations,_=fixture()
    stub='''module sg13g2_lgcp_1(input CLK);
wire GCLK,GATE,delayed_CLK,int_fwire_int_GATE;reg notifier;
endmodule
module SRAM_1P_behavioral_bm_bist;
wire CLK_MUX,MEN_MUX,WEN_MUX,REN_MUX;wire [10:0] ADDR_MUX;
wire [63:0] BM_MUX,DIN_MUX;reg [63:0] memory[0:2047];
endmodule
module RM_IHPSG13_1P_2048x64_c2_bm_bist(input A_CLK);
wire [63:0] A_DOUT;SRAM_1P_behavioral_bm_bist i_SRAM_1P_behavioral_bm_bist();
endmodule
module namespace_dut(input clk_i);
'''+declarations+'\nendmodule\n'
    bench=trace.instrument('module tb_logicrom_gl; reg clk=0;integer cycles=0;namespace_dut dut(clk);\nendmodule\n')
    source=tmp_path/'namespace.v';source.write_text(stub+bench)
    execution=trace.q.alu.execute([iverilog,'-g2005-sv','-s','tb_logicrom_gl','-o',tmp_path/'namespace.vvp',ROOT/trace.MONITOR,source],tmp_path,'compile')
    assert execution['returncode']==0,(tmp_path/'compile.log').read_text()
    assert 'expects' not in (tmp_path/'compile.log').read_text()


def test_actual_generated_request_monitor_masks_only_inactive_bytes(tmp_path):
    iverilog=shutil.which('iverilog');vvp=shutil.which('vvp');assert iverilog and vvp
    assert trace.request_unknown() in trace.bindings()
    source=tmp_path/'request-mask.v'
    source.write_text('''module fixture;
reg \\g_core_req_reg.u_data_request.valid_q ;
reg [31:0] bus_data_addr,bus_data_wdata;reg [3:0]bus_data_be;reg bus_data_we;
endmodule
module tiny;fixture dut();wire bad='''+trace.request_unknown()+''';
initial begin
  dut.\\g_core_req_reg.u_data_request.valid_q =1;dut.bus_data_addr=32'h1e9c;
  dut.bus_data_we=1;dut.bus_data_be=4'b0001;dut.bus_data_wdata=32'hxxxxxx12;
  #1;if(bad!==0)$fatal(1,"Inactive byte X must not trigger");
  dut.bus_data_wdata=32'hxxxxxx1x;
  #1;if(bad!==1)$fatal(1,"Active byte X must trigger");
  dut.bus_data_be=4'b1000;dut.bus_data_wdata=32'h12xxxxxx;
  #1;if(bad!==0)$fatal(1,"High active byte was masked incorrectly");
  dut.bus_data_be=4'bx001;
  #1;if(bad!==1)$fatal(1,"Unknown byte enables must trigger");
  dut.\\g_core_req_reg.u_data_request.valid_q =0;
  #1;if(bad!==0)$fatal(1,"Inactive payload must not trigger");
  $display("SOURCE_REQUEST_MASK_GATE PASS");$finish;
end
endmodule
''')
    compile_result=trace.q.alu.execute([iverilog,'-g2005-sv','-s','tiny','-o',tmp_path/'request.vvp',source],tmp_path,'compile')
    assert compile_result['returncode']==0,(tmp_path/'compile.log').read_text()
    execution=trace.q.alu.execute([vvp,'-i',tmp_path/'request.vvp'],tmp_path,'run')
    assert execution['returncode']==0,(tmp_path/'run.log').read_text()
    assert 'SOURCE_REQUEST_MASK_GATE PASS' in (tmp_path/'run.log').read_text()


def test_real_run_controller_preserves_native_boot_failure(monkeypatch,tmp_path):
    # Stub only the child and external input validation, not the run controller.
    monkeypatch.setenv('GITHUB_ACTIONS','true');monkeypatch.setenv('GITHUB_SHA','abc')
    output=tmp_path/'result';output.mkdir();(output/'firmware').mkdir()
    row=dict(status='COMPILED_SOURCE_BOUND_DIAGNOSTIC_TRACE',github_source_commit='abc',
        diagnostic_cycle_bound=trace.CYCLES,original_qualification_cycle_bound=trace.q.CYCLES,
        cycle_bound=trace.q.CYCLES,producer=trace.q.PRODUCER,variant='candidate',memory='vendor',
        methods={n:dict(sha256=sha) for n,sha in (trace.BASE_PINS|trace.HELPER_PINS).items()} | {n:{} for n in trace.OWN},
        sources={},compiled_simulation_path=str(tmp_path/'sim.vvp'),compiled_simulation={},runtime={'tools':{'vvp':{}}},
        candidate_adopted=False,timing_accepted=False,manufacturing_approval=False,mapped_core_equivalence_accepted=False,
        full_soc_functional_accepted=False)
    row['boot_command']=['/bin/fake-vvp','-i',row['compiled_simulation_path'],'+flash0='+str(output/'firmware/flash0.hex'),'+trace_dir='+str(output)]
    (output/'result.json').write_text(json.dumps(row))
    monkeypatch.setattr(trace.q,'verify_outputs',lambda *a:None)
    monkeypatch.setattr(trace.q.common,'verify_file',lambda *a:None)
    def child(command,**kwargs):
        assert command==row['boot_command'] and kwargs['stdin']==trace.subprocess.DEVNULL
        (output/'trace-samples.log').write_text('S cycle=1565000 time=1 unknown=1 data=x\n')
        (output/'trace-events.log').write_text('CLOCK cycle=1565000 time=1 clk=x\n')
        (output/'trace-milestones.log').write_text('')
        class Process:
            stdout=iter(['QUALIFICATION_MBIST PASS cycles=983043\n','TRACE_FIRST_X cycle=1565000 time=1 cause=clock_gate_unknown\n',
                'FATAL: preserved native boot failure\n',
                'TRACE_SUMMARY triggered=1 first_cycle=1565000 triggers=1 samples=2000 events=4000 saved_samples=1 saved_events=1\n',
                'TRACE_MILESTONES count=0\n'])
            def wait(self):return 1
        return Process()
    monkeypatch.setattr(trace.subprocess,'Popen',child)
    trace.run(output)
    saved=json.loads((output/'result.json').read_text())
    assert saved['status']=='DIAGNOSTIC_CAPTURE_COMPLETE_NOT_ACCEPTANCE'
    assert saved['boot_failure_preserved'] is True and saved['observed_boot_pass'] is False
    assert saved['boot_execution']['returncode']==1 and saved['candidate_adopted'] is False
    assert saved['trace_observation']['first_unknown'][2]=='clock_gate_unknown'


def test_tiny_first_x_controls_do_not_claim_boot_or_physical_acceptance():
    source=(ROOT/'scripts/run_cloud_alu_boot_trace.py').read_text()
    assert "status='DIAGNOSTIC_CAPTURE_COMPLETE_NOT_ACCEPTANCE'" in source
    assert 'native_execution_timeout' not in source
    assert 'trace_observation' in source
    assert 'q.passed_boot(code,' in source
