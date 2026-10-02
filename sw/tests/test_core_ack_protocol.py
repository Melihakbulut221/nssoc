# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Pure preparation and evidence rejection; these tests do not execute Ibex."""
import json
from pathlib import Path
import struct
import shutil
import sys

import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts'))
import run_core_ack_protocol as core  # noqa: E402


def test_preparation_copies_actual_c10_core_without_regeneration(tmp_path):
    before=core.source_contract()
    out=tmp_path/'prepared';row=core.prepare(out)
    assert row==core.verify_prepared(out)
    assert core.source_contract()==before and len(before)==81
    assert core.core_instance((ROOT/'hw/soc/rtl/soc_top.v').read_text()) in (out/'tb_core_ack_protocol.v').read_text()
    assert 'hw/soc/gen/ibex_load_store_unit.v' in row['selected_core_sources']
    assert 'hw/soc/gen/ibex_pmp.v' in row['selected_core_sources']
    assert 'hw/soc/rtl/ibex_regfile_secded.v' in row['selected_core_sources']
    assert not any('ibex_register_file_ff.v' in s for s in row['selected_core_sources'])
    assert not row['actual_core_protocol_proved'] and not row['whole_soc_verified']


def test_clean_cloud_checkout_does_not_need_ignored_generated_ibex(tmp_path):
    checkout=tmp_path/'checkout'
    lock=json.loads((ROOT/core.LOCK).read_text())
    for name in set(core.OWN)|set(lock['tracked_sources'])|{lock['archive']['path']}:
        dest=checkout/name;dest.parent.mkdir(parents=True,exist_ok=True)
        shutil.copyfile(ROOT/name,dest)
    assert not (checkout/'hw/soc/gen/ibex_core.v').exists()
    out=tmp_path/'prepared'
    row=core.prepare(out,checkout)
    assert row==core.verify_prepared(out,checkout)
    assert core.pin(out/'sources/hw/soc/gen/ibex_core.v')==lock['files']['repo/hw/soc/gen/ibex_core.v']
    assert not (checkout/'hw/soc/gen').exists()


@pytest.mark.parametrize('target',['sources/hw/soc/gen/ibex_load_store_unit.v','tb_core_ack_protocol.v',
                                  'firmware.S','link.ld','ack/candidate.v'])
def test_repinning_mutated_method_or_actual_core_does_not_make_it_valid(tmp_path,target):
    out=tmp_path/'prepared';core.prepare(out)
    changed=out/target;changed.write_text(changed.read_text()+'\n')
    row=json.loads((out/'preparation.json').read_text())
    row['prepared_files'][target]=core.pin(changed)
    (out/'preparation.json').write_text(json.dumps(row))
    with pytest.raises(ValueError):core.verify_prepared(out)


@pytest.mark.parametrize('field',['actual_core_protocol_proved','whole_soc_verified',
                                'sequential_equivalence_proved','candidate_adopted','timing_accepted'])
def test_preparation_cannot_claim_native_or_product_acceptance(tmp_path,field):
    out=tmp_path/'prepared';core.prepare(out)
    row=json.loads((out/'preparation.json').read_text());row[field]=True
    (out/'preparation.json').write_text(json.dumps(row))
    with pytest.raises(ValueError,match='acceptance'):core.verify_prepared(out)


COUNTS=dict(reset_phase=0,cycles=900,accepted=20,delivered=20,cancelled=0,responses=20,
            cancelled_responses=0,held=5,stalls=9,pmp_first=2,pmp_second=2,split_second=8,
            bus_errors=4,stopped_clock=8,traps=8,irq=1)


def fixture_log(values):
    return 'PASS_ACTUAL_CORE_DIRECTED_PROTOCOL '+' '.join(f'{n}={v}' for n,v in values.items())+'\n'


def test_parser_accepts_complete_directed_coverage_fixture():
    assert core.parse_positive(0,fixture_log(COUNTS),0)==COUNTS


@pytest.mark.parametrize('field,value',[('accepted',21),('responses',19),('reset_phase',1),
    ('pmp_first',0),('pmp_second',0),('split_second',0),('bus_errors',3),('stopped_clock',0),('stopped_clock',5),
    ('traps',7),('irq',0),('cycles',30001),('held',0),('stalls',0)])
def test_parser_rejects_missing_reachable_scenarios_or_accounting(field,value):
    values=dict(COUNTS);values[field]=value
    with pytest.raises(ValueError):core.parse_positive(0,fixture_log(values),0)


@pytest.mark.parametrize('code,suffix',[(1,''),(0,'FATAL: fault'),(0,fixture_log(COUNTS))])
def test_exit_failure_fatal_and_duplicate_pass_rejected(code,suffix):
    with pytest.raises(ValueError):core.parse_positive(code,fixture_log(COUNTS)+suffix,0)


def test_memory_signature_must_include_actual_firmware_results(tmp_path):
    words=[0]*2048
    words[(0x3fe0-0x2000)//4]=8;words[(0x3fe4-0x2000)//4]=1
    words[(0x3ff0-0x2000)//4]=0x600dc0de
    p=tmp_path/'signature.hex';p.write_text('\n'.join(f'{w:08x}' for w in words)+'\n')
    assert len(core.read_signature(p))==64
    words[(0x3fe0-0x2000)//4]=7
    p.write_text('\n'.join(f'{w:08x}' for w in words)+'\n')
    with pytest.raises(ValueError,match='selfcheck'):core.read_signature(p)
    p.write_text('xxxxxxxx\n')
    with pytest.raises(ValueError,match='Unknown'):core.read_signature(p)


def test_firmware_entry_architecture_and_data_boundary_checked(tmp_path):
    elf=tmp_path/'test.elf';binary=tmp_path/'test.bin'
    header=bytearray(52);header[:6]=b'\x7fELF\x01\x01'
    struct.pack_into('<H',header,18,243);struct.pack_into('<I',header,24,0x80)
    elf.write_bytes(header);binary.write_bytes(b'\x13\0\0\0')
    image=core.firmware_hex(binary,elf).splitlines()
    assert len(image)==4096 and image[32]=='00000013'
    struct.pack_into('<I',header,24,0x100);elf.write_bytes(header)
    with pytest.raises(ValueError,match='reset vector'):core.firmware_hex(binary,elf)
    struct.pack_into('<I',header,24,0x80);elf.write_bytes(header)
    binary.write_bytes(b'\0'*8192)
    with pytest.raises(ValueError,match='overlaps data'):core.firmware_hex(binary,elf)


def test_compiler_opcode_control_checks_real_instruction_encodings():
    # Explicit RISC-V encodings, independently stated rather than generated by
    # the verifier: CSR read, CSR write, WFI and MRET, all 32-bit little-endian.
    raw=bytes.fromhex('73250030731005307300501073002030')
    result=core.verify_firmware_probe(raw)
    assert result['status']=='PASS_EXACT_RV32_CSR_WFI_MRET_ENCODINGS'
    assert result['words']==['30002573','30051073','10500073','30200073']
    for changed in (raw[:-1],raw+b'\0',bytes([raw[0]^1])+raw[1:],raw[::-1]):
        with pytest.raises(ValueError,match='opcode'):core.verify_firmware_probe(changed)


def test_no_native_local_run_without_reviewed_cloud_context(tmp_path,monkeypatch):
    monkeypatch.delenv('GITHUB_ACTIONS',raising=False)
    with pytest.raises(ValueError,match='cloud-only'):core.run(tmp_path/'missing',tmp_path/'result')
    assert not (tmp_path/'result').exists()
