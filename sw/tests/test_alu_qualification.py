# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Pure fail-closed source, SRAM mapping and mapped-boot contract tests."""
import copy
import importlib.util
import io
import json
from pathlib import Path
import shlex
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
try:
    SPEC=importlib.util.spec_from_file_location('alu_qualification',ROOT/'scripts/run_cloud_alu_qualification.py')
    Q=importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(Q)
finally:
    sys.path.pop(0)


@pytest.fixture
def lock():
    return json.loads((ROOT/Q.LOCK).read_text())


@pytest.fixture
def bundle(tmp_path,lock):
    out=tmp_path/'inputs'
    Q.restore_inputs(lock,out)
    return out


def test_original_metadata_and_immutable_source_bundle(bundle,lock):
    run=json.loads((bundle/'provenance/producer-run.json').read_text())
    info=json.loads((bundle/'provenance/producer-artifact.json').read_text())['artifacts'][0]
    Q.artifact.validate_metadata(Q.PRODUCER,run,info)
    assert Q.PRODUCER['url'].endswith('closure-alu-prefix-36998734236-20261002.zip')
    assert len(lock['files'])==35 and len(lock['tracked_sources'])==9
    physical=json.loads((bundle/'physical-config.json').read_text())
    manifest=json.loads((ROOT/Q.alu.MANIFEST).read_text())
    Q.common.verify_file(bundle/'physical-config.json',manifest['files'][manifest['config']])
    assert physical['CLOCK_PERIOD']==20
    assert sum(len(m['instances']) for m in physical['MACROS'].values())==32


def test_exact_current_loader_regenerates_exact_c10_rom(tmp_path,bundle,lock):
    generator=Q.module(ROOT/'hw/soc/flow/gen_logic_boot_rom.py','qualified_generator')
    manifest=generator.generate(bundle/'firmware/test_soc.bin',tmp_path/'rom')
    assert manifest['image_bytes']==3120
    assert manifest['image_sha256']==lock['loader_sha256']
    assert manifest['rtl_sha256']==lock['rom_sha256']
    assert manifest==json.loads((bundle/'c10-rom/manifest.json').read_text())
    assert (tmp_path/'rom/soc_logic_boot_rom.v').read_bytes()==(bundle/'c10-rom/soc_logic_boot_rom.v').read_bytes()


def test_changed_source_pin_rejected(tmp_path,lock):
    lock['tracked_sources']['hw/soc/techmap/independent_sram_map.v']['sha256']='0'*64
    with pytest.raises(ValueError,match='tracked pin differs'):
        Q.restore_inputs(lock,tmp_path/'changed')


def test_old_loader_contract_rejected(tmp_path,lock):
    lock['loader_sha256']='ab7440619ca719358e6598b0cf291a268c8ccf13357b50ef3a89cbe583e71801'
    with pytest.raises(ValueError,match='loader/ROM identity changed'):
        Q.restore_inputs(lock,tmp_path/'wrong')


def test_only_literal_path_relocation_of_original_map_recipe(tmp_path,bundle):
    synlock=Q.alu.validate_lock(json.loads((ROOT/Q.alu.LOCK).read_text()))
    snapshot=tmp_path/'c10'
    Q.alu.restore(ROOT/synlock['archive']['path'],snapshot,synlock)
    netlist=tmp_path/'source.v';netlist.write_text('source path fixture')
    out=tmp_path/'output';out.mkdir()
    template=(bundle/'recipe/original-map.ys').read_text()
    recipe=Q.mapping_recipe(template,netlist,out,bundle,snapshot,synlock)
    assert recipe.count(str(netlist))==1
    assert synlock['original_repo'] not in recipe and synlock['original_pdk'] not in recipe
    for line in recipe.splitlines():
        if line.startswith(('read_liberty ','read_verilog ')):
            for token in shlex.split(line)[1:]:
                if not token.startswith('-'):assert Path(token).is_file(),token
    for instruction in ['setattr -set keep 1 t:sg13g2_*', 'select -assert-count 16 t:SP6TSRAM512x64',
                        'select -assert-count 16 t:DP8TSRAMDP256x16', 'select -assert-none t:RM_IHPSG13_*',
                        'check -assert', ' -D 20\n']:
        assert instruction in template and instruction in recipe


def module_pair():
    before=dict(cells={},netnames={'q':dict(bits=[2]),'d':dict(bits=[3]),'clk':dict(bits=[4])},
                ports={'result':dict(direction='output',bits=[2])})
    before['cells']['ff']=dict(type='sg13g2_dfrbpq_1',parameters={},connections={'Q':[2],'D':[3],'CLK':[4]})
    for number in range(20):
        dp=number>=4
        before['cells']['m'+str(number)]=dict(type=('RM_IHPSG13_2P_256x16_c2_bm_bist' if dp else
            'RM_IHPSG13_1P_2048x64_c2_bm_bist'),connections=dict(A_BIST_EN=['0'],B_BIST_EN=['0'],
                A_DLY=['0'],B_DLY=['0'],A_BM=['1']*(16 if dp else 64),B_BM=['1']*16))
    after=dict(cells={'ff':dict(type='sg13g2_dfrbpq_1',parameters={},
                              connections={'Q':[22],'D':[23],'CLK':[24]})},
               netnames={'q':dict(bits=[22]),'d':dict(bits=[23]),'clk':dict(bits=[24])},
               ports={'result':dict(direction='output',bits=[22])})
    physical=dict(MACROS={m:dict(instances={m+str(i):{} for i in range(16)})
                         for m in ('SP6TSRAM512x64','DP8TSRAMDP256x16')})
    for master,entry in physical['MACROS'].items():
        for name in entry['instances']:after['cells'][name]=dict(type=master,connections={})
    return before,after,physical


def test_retained_cell_equations_and_32_exact_instances():
    row=Q.mapping_contract(*module_pair())
    assert row['retained_nonmemory_cells']==1 and len(row['macros'])==32


@pytest.mark.parametrize('mutation',['data','clock','master','params','port','alias','macro_name','macro_missing',
                                     'vendor_retained','bist','mask','dp_delay','dp_mask','macro_before_missing'])
def test_mapping_contract_rejects_real_connectivity_or_interface_change(mutation):
    before,after,physical=module_pair()
    if mutation=='data':after['cells']['ff']['connections']['D']=[22]
    elif mutation=='clock':after['cells']['ff']['connections']['CLK']=['0']
    elif mutation=='master':after['cells']['ff']['type']='sg13g2_inv_1'
    elif mutation=='params':after['cells']['ff']['parameters']['WIDTH']=2
    elif mutation=='port':after['ports']['result']['direction']='input'
    elif mutation=='alias':before['netnames']['alias']=dict(bits=[2]);after['netnames']['alias']=dict(bits=[23])
    elif mutation=='macro_name':after['cells']['wrong']=after['cells'].pop('SP6TSRAM512x640')
    elif mutation=='macro_missing':del after['cells']['SP6TSRAM512x640']
    elif mutation=='vendor_retained':after['cells']['retained']=before['cells']['m0']
    elif mutation=='bist':before['cells']['m0']['connections']['A_BIST_EN']=['1']
    elif mutation=='mask':before['cells']['m0']['connections']['A_BM'][3]='0'
    elif mutation=='dp_delay':before['cells']['m4']['connections']['B_DLY']=['1']
    elif mutation=='dp_mask':before['cells']['m4']['connections']['B_BM']=['0']*16
    else:del before['cells']['m0']
    with pytest.raises(ValueError):Q.mapping_contract(before,after,physical)


@pytest.mark.parametrize('memory',['vendor','independent'])
def test_boot_bench_observation_only_and_mbist_gate(bundle,memory):
    original=(bundle/'repo/hw/soc/tb/tb_soc_logic_boot_gl.v').read_text()
    text=Q.prepare_boot_bench(original,memory)
    assert text.count('soc_top dut')==original.count('soc_top dut')
    assert text.count('QUALIFICATION_MBIST PASS')==1
    assert 'dut.eth_mbist_done_o !== 2\'b11' in text
    assert 'Mapped boot did not preserve successful power-on MBIST' in text
    assert 'ram_word(`CHECKS_ADDR)!==32\'d28' in text
    assert 'force ' not in text
    assert text.count('$readmemh') == original.count('$readmemh') == 1
    assert '$readmemh(flash_fname, u_flash0.mem);' in text
    assert 'repeat(20) @(negedge clk);\n    rst_n=1;' in text
    if memory=='independent':
        assert text.count('.mem .mem[widx[8:0]]')==16
        assert 'i_SRAM_1P_behavioral_bm_bist.memory' not in text
    else:assert text.count('i_SRAM_1P_behavioral_bm_bist.memory')==4


def test_changed_bench_cannot_bypass_completion_guard(bundle):
    original=(bundle/'repo/hw/soc/tb/tb_soc_logic_boot_gl.v').read_text()
    with pytest.raises(ValueError,match='completion contract'):
        Q.prepare_boot_bench(original.replace('LOGICROM_GL PASS checks=28','other PASS'),'vendor')


@pytest.mark.parametrize('code,text,expected',[
    (0,'QUALIFICATION_MBIST PASS cycles=983048\nLOGICROM_GL PASS checks=28\n',True),
    (1,'QUALIFICATION_MBIST PASS cycles=983048\nLOGICROM_GL PASS checks=28\n',False),
    (0,'LOGICROM_GL PASS checks=28\n',False),
    (0,'QUALIFICATION_MBIST PASS cycles=983048\n',False),
    (0,'QUALIFICATION_MBIST PASS cycles=983048\nLOGICROM_GL PASS checks=28\nFATAL: late failure',False),
    (0,'QUALIFICATION_MBIST PASS cycles=1\nQUALIFICATION_MBIST PASS cycles=2\nLOGICROM_GL PASS checks=28\n',False),
])
def test_boot_requires_mbist_firmware_and_process_success(code,text,expected):
    assert Q.passed_boot(code,text) is expected


def test_native_work_is_cloud_only(tmp_path,monkeypatch):
    monkeypatch.delenv('GITHUB_ACTIONS',raising=False)
    with pytest.raises(ValueError,match='cloud-only'):Q.prepare(tmp_path/'out',tmp_path/'work')
    assert not (tmp_path/'out').exists()


def test_producer_wrong_status_fails_before_native(tmp_path):
    (tmp_path/'result.json').write_text(json.dumps(dict(github_source_commit=Q.PRODUCER['source_commit'],status='RUNNING')))
    with pytest.raises(ValueError,match='Incomplete or wrong'):Q.verify_producer(tmp_path)


def test_changed_artifact_output_rejected(tmp_path,monkeypatch):
    (tmp_path/'result.json').write_text('{}')
    (tmp_path/'netlist.v').write_text('correct')
    row=dict(outputs={'netlist.v':Q.pin(tmp_path/'netlist.v')},methods={})
    Q.verify_outputs(tmp_path,row)
    (tmp_path/'netlist.v').write_text('altered')
    with pytest.raises(ValueError):Q.verify_outputs(tmp_path,row)
    row=copy.deepcopy(row);row['outputs']={}
    with pytest.raises(ValueError,match='inventory'):Q.verify_outputs(tmp_path,row)


def startup_fixture(tmp_path,monkeypatch):
    monkeypatch.setenv('GITHUB_ACTIONS','true')
    monkeypatch.setenv('GITHUB_SHA','fixture-source')
    out=tmp_path/'out';out.mkdir()
    compiled=tmp_path/'sim.vvp';compiled.write_text('compiled fixture')
    runtime=tmp_path/'vvp';runtime.write_text('runtime fixture')
    (out/'firmware').mkdir()
    flash=out/'firmware/flash0.hex';flash.write_text('00\n')
    row=dict(status='COMPILED_READY_FOR_FOUR_STATE_BOOT',github_source_commit='fixture-source',
             producer=Q.PRODUCER,cycle_bound=Q.CYCLES,methods={},
             sources={str(flash):Q.pin(flash)},compiled_simulation_path=str(compiled),
             compiled_simulation=Q.pin(compiled),runtime=dict(tools=dict(vvp=Q.pin(runtime))),
             boot_command=[str(runtime),'-i',str(compiled),'+flash0='+str(flash)],
             outputs={'firmware/flash0.hex':Q.pin(flash)})
    (out/'result.json').write_text(json.dumps(row))
    return out,compiled


@pytest.mark.parametrize('native_fail',[False,True])
def test_prepared_stage_runs_and_preserves_immutable_progress(tmp_path,monkeypatch,native_fail):
    out,_=startup_fixture(tmp_path,monkeypatch)
    monkeypatch.setenv('GH_TOKEN','must-not-reach-child')
    text=('LOGICROM_GL progress cycles=10000 uart=0\n'
          'QUALIFICATION_MBIST PASS cycles=983048\n'
          'LOGICROM_GL progress cycles=990000 uart=0\n'
          'LOGICROM_GL PASS checks=28\n')
    if native_fail:text+='FATAL: actual simulation failed\n'
    class Child:
        stdout=io.StringIO(text)
        def wait(self):return 1 if native_fail else 0
    def start(command,**kwargs):
        assert 'GH_TOKEN' not in kwargs['env']
        assert command[1]=='-i'
        return Child()
    monkeypatch.setattr(Q.subprocess,'Popen',start)
    if native_fail:
        with pytest.raises(ValueError,match='boot failed'):Q.boot_resume(out)
    else:Q.boot_resume(out)
    result=json.loads((out/'result.json').read_text())
    assert result['status']==('FAILED_PRESERVED' if native_fail else 'PASS_FOUR_STATE_MAPPED_BOOT_AND_POWER_ON_MBIST_ONLY')
    assert (out/'boot.log').read_text()==text
    progress=sorted((out/'progress').glob('*.json'))
    assert len(progress)==2
    for p in progress:
        event=json.loads(p.read_text())
        prefix=(out/'boot.log').read_bytes()[:event['log_prefix']['bytes']]
        assert Q.hashlib.sha256(prefix).hexdigest()==event['log_prefix']['sha256']
        assert event['elapsed_s']>=0


def test_changed_compiled_stage_cannot_start_simulation(tmp_path,monkeypatch):
    out,compiled=startup_fixture(tmp_path,monkeypatch)
    compiled.write_text('changed binary')
    def should_not_start(*args,**kwargs):pytest.fail('Mutated executable started')
    monkeypatch.setattr(Q.subprocess,'Popen',should_not_start)
    with pytest.raises(ValueError):Q.boot_resume(out)
    assert json.loads((out/'result.json').read_text())['status']=='FAILED_PRESERVED'
    assert not (out/'boot.log').exists()
