#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Isolated actual-C10-core directed ACK protocol experiment, not SoC acceptance.

Preparation is pure source copying/transformation. Native execution is cloud-only.
The actual Ibex, including LSU/PMP/ID/WB and its clock enable, generates requests.
The surrounding instruction/data memories are explicit ordered protocol models;
SoC fabric, SRAM/MBIST, peripherals and production clock-cell timing are absent.
No request/payload/PMP stability assumption is used in the observation harness.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tarfile

import prepare_core_ack_register as ack

ROOT=Path(__file__).resolve().parents[1]
EVIDENCE='docs/evidence/critical-path-prefix-analysis-20261002.json'
EVIDENCE_SHA='5005e6cd888cde913a7446bd287c4db5a1f2a7d6472d3f1cae65df58f41e8c70'
LOCK='hw/soc/pnr/alu-prefix-c10-input.lock.json'
LOCK_SHA='816eb1c44531345b1e8ad5b6fae5c099977ba30c5236e47a28e2bf1282a8006c'
TEMPLATE='hw/soc/tb/tb_core_ack_protocol.v.in'
FIRMWARE='hw/soc/tb/sw/core_ack_protocol.S'
OWN=('scripts/run_core_ack_protocol.py','sw/tests/test_core_ack_protocol.py',TEMPLATE,FIRMWARE,
     'scripts/prepare_core_ack_register.py','.github/workflows/timing-core-ack-protocol.yml',EVIDENCE,LOCK)
PROFILE=dict(CORE_REQ_REG=1,CORE_WB_STAGE=1,SYNPRE=1,MEM_RDREG=1,REQ_REG=1,WAKE_GNT=1)
# GCC 10 rejects the later `_zicsr` architecture spelling. This is assembly
# input, so use its known RV32IM spelling and explicitly select GAS ISA 2.2,
# where CSR instructions belong to I. Pass the ISA version to GAS with -Wa:
# GCC 10 itself also predates the driver's -misa-spec option. A real opcode
# gate below proves CSR/WFI/MRET encodings before compiling the workload.
FIRMWARE_FLAGS=('-march=rv32im','-mabi=ilp32','-Wa,-misa-spec=2.2')
FIRMWARE_PROBE=''' .option norvc
 .section .text
 .global _start
_start:
 csrr a0, mstatus
 csrw mstatus, a0
 wfi
 mret
'''
PROBE_WORDS=(0x30002573,0x30051073,0x10500073,0x30200073)
LIMITATIONS=[
    'Finite directed actual-core RTL simulation is not an exhaustive formal or sequential-equivalence proof.',
    'The actual C10 core/SECDED/LSU/PMP/ID/WB and clock-enable logic are used; the SoC fabric, peripherals, SRAM/MBIST and reset distribution are not instantiated.',
    'MEM_RDREG/REQ_REG/WAKE_GNT are preserved source-profile metadata, not parameters of the explicit external memory model.',
    'The clock gate uses the existing explicit SG13G2_ICG_BEHAVIOURAL RTL simulation branch, not a PDK timing model.',
    'Eight directed first/second split-beat faults, one software-interrupt WFI wakeup and three reset placements do not prove all IRQ/NMI/debug/CSR/PMP-update or exception-priority interleavings.',
    'No whole-SoC boot/MBIST, timing improvement, synthesis/layout, candidate adoption or manufacturing approval is claimed.',
]
LINKER='''OUTPUT_ARCH(riscv)
ENTRY(_start)
SECTIONS {
 .text.start 0x80 : { *(.text.start) }
 .text 0x200 : { *(.text) }
 .trapvec 0x1000 : { *(.trapvec) }
 /DISCARD/ : { *(.comment) *(.note*) *(.riscv.attributes) }
}
ASSERT(_start == 0x80, "wrong reset vector")
ASSERT(ADDR(.text)+SIZEOF(.text) <= 0x1000, "program overlaps trap vector")
ASSERT(trap_vectors == 0x1000, "wrong vectored trap base")
ASSERT(ADDR(.trapvec)+SIZEOF(.trapvec) < 0x2000, "program overlaps data")
'''
NEGATIVES={
 'unsolicited_grant':('assign gnt_o = rst_ni && ack_q;',
                     'assign gnt_o = rst_ni && !valid_q;',
                     'CORE_PROTOCOL ack without permission-qualified intent'),
 'early_downstream':('assign req_o = rst_ni && valid_q && !ack_q;',
                    'assign req_o = rst_ni && valid_q;',
                    'CORE_PROTOCOL exposed token before acknowledgement edge completes'),
 'corrupt_payload':('we_i, be_i, wdata_i};',"we_i, be_i, (wdata_i ^ 32'h1)};",
                    'CORE_PROTOCOL lost reordered corrupted or unacknowledged token'),
}
CLOCK_NEGATIVE='stuck_open_clock'
REJECTIONS={name:spec[2] for name,spec in NEGATIVES.items()} | {
    CLOCK_NEGATIVE:'CORE_PROTOCOL clock edge during asserted sleep'}


def require(value,message):
    if not value:raise ValueError(message)


def pin(path):
    return dict(bytes=path.stat().st_size,sha256=ack.sha(path))


def save(path,row):
    path.write_text(json.dumps(row,indent=2)+'\n')


def source_contract(root=ROOT):
    require(ack.sha(root/EVIDENCE)==EVIDENCE_SHA and ack.sha(root/LOCK)==LOCK_SHA,
            'Pinned C10 evidence/lock changed')
    evidence=json.loads((root/EVIDENCE).read_text())
    lock=json.loads((root/LOCK).read_text())
    require(evidence['current_profile']==PROFILE==lock['source_parameters'],'C10 profile changed')
    sources=evidence['current_source_files_verified']
    require(len(sources)==81,'C10 source inventory changed')
    require(pin(root/lock['archive']['path'])=={k:lock['archive'][k] for k in ('bytes','sha256')},
            'Exact C10 source archive changed')
    pins={}
    for name,digest in sources.items():
        path=root/name
        expected=lock['files']['repo/'+name]
        require(expected['sha256']==digest,'C10 evidence/snapshot disagreement')
        # Generated Ibex sources are intentionally absent from a clean checkout.
        # Their authoritative bytes come from the exact captured archive, never
        # from a new sv2v conversion. A present but changed local file is rejected.
        require(not path.is_symlink(),'Linked current C10 source: '+name)
        if name in lock['tracked_sources'] or path.exists():
            require(path.is_file() and pin(path)==expected,'Current source differs from exact C10: '+name)
        pins[name]=expected
    return pins


def restore_sources(output,pins,root=ROOT):
    lock=json.loads((root/LOCK).read_text())
    seen=set();restored=set()
    with tarfile.open(root/lock['archive']['path'],'r:xz') as archive:
        for member in archive:
            name=member.name
            require(name not in seen and name in lock['files'] and member.isfile() and
                    not member.issparse() and member.size==lock['files'][name]['bytes'],
                    'Unsafe or changed C10 archive member')
            seen.add(name)
            short=name.removeprefix('repo/')
            if short not in pins:continue
            require(name=='repo/'+short and not Path(short).is_absolute() and '..' not in Path(short).parts,
                    'Unsafe selected C10 source path')
            raw=archive.extractfile(member).read(member.size+1)
            require(len(raw)==member.size and hashlib.sha256(raw).hexdigest()==pins[short]['sha256'],
                    'Captured C10 source bytes differ: '+short)
            dest=output/'sources'/short;dest.parent.mkdir(parents=True,exist_ok=True)
            dest.write_bytes(raw);restored.add(short)
    require(seen==set(lock['files']) and restored==set(pins),'Incomplete exact C10 source snapshot')


def core_instance(top):
    require(top.count('  ibex_top #(\n')==1,'Ambiguous actual-core instance')
    start=top.index('  ibex_top #(\n')
    end=top.index('\n  );',start)+len('\n  );')
    block=top[start:end]
    require(block.count(') u_ibex (')==1 and '.WritebackStage  (CORE_WB_STAGE)' in block
            and '.BranchTargetALU (CORE_WB_STAGE)' in block,'Actual core configuration differs')
    return block


def compiled_core_sources(names):
    extras={'hw/soc/genp/ibex_top.v','hw/soc/rtl/ibex_regfile_secded.v',
            'hw/soc/rtl/prim_clock_gating.v','hw/rtl/secded_enc.v','hw/rtl/secded_dec.v'}
    selected=sorted(n for n in names if (n.startswith('hw/soc/gen/') and n.endswith('.v')) or n in extras)
    require(extras<=set(selected) and not any(n.endswith('/ibex_register_file_ff.v') for n in selected),
            'Actual hardened core source selection differs')
    return selected


def prepare(output,root=ROOT):
    pins=source_contract(root)
    template=(root/TEMPLATE).read_text()
    require(template.count('@@CORE_INSTANCE@@')==1,'Ambiguous harness instance slot')
    output.mkdir(parents=True,exist_ok=False)
    restore_sources(output,pins,root)
    body=template.replace('@@CORE_INSTANCE@@',core_instance((output/'sources/hw/soc/rtl/soc_top.v').read_text()))
    ack.prepare(output/'sources/hw/soc/rtl/soc_req_pipe.v',output/'ack')
    (output/'tb_core_ack_protocol.v').write_text(body)
    shutil.copyfile(root/FIRMWARE,output/'firmware.S')
    (output/'link.ld').write_text(LINKER)
    result=dict(schema=1,status='PREPARED_ACTUAL_CORE_HARNESS_NOT_YET_EXECUTED',
        original_c10_sources=pins,selected_core_sources=compiled_core_sources(pins),
        source_origin='Exact pinned C10 archive; all tracked and any present generated checkout files cross-checked.',
        core_parameters_from_soc_instance_verbatim=True,source_profile=PROFILE,
        source_methods={n:pin(root/n) for n in OWN},
        prepared_files={str(p.relative_to(output)):pin(p) for p in sorted(output.rglob('*')) if p.is_file()},
        limitations=LIMITATIONS,actual_core_protocol_proved=False,whole_soc_verified=False,
        sequential_equivalence_proved=False,candidate_adopted=False,timing_accepted=False)
    save(output/'preparation.json',result)
    return result


def verify_prepared(prepared,root=ROOT):
    row=json.loads((prepared/'preparation.json').read_text())
    require(row['original_c10_sources']==source_contract(root),'Source contract changed after preparation')
    require(row['source_methods']=={n:pin(root/n) for n in OWN},'Harness method changed after preparation')
    require(row['selected_core_sources']==compiled_core_sources(row['original_c10_sources']) and
            row['source_profile']==PROFILE and row['limitations']==LIMITATIONS,'Harness scope changed')
    for name,expected in row['original_c10_sources'].items():
        require(pin(prepared/'sources'/name)==expected,'Copied actual core source differs: '+name)
    expected_bench=(root/TEMPLATE).read_text().replace('@@CORE_INSTANCE@@',
                  core_instance((root/'hw/soc/rtl/soc_top.v').read_text()))
    require((prepared/'tb_core_ack_protocol.v').read_text()==expected_bench and
            (prepared/'firmware.S').read_bytes()==(root/FIRMWARE).read_bytes() and
            (prepared/'link.ld').read_text()==LINKER,'Harness/firmware/linker differs from reviewed method')
    require(not any(p.is_symlink() for p in prepared.rglob('*')),'Linked prepared artifact')
    actual={str(p.relative_to(prepared)):pin(p) for p in sorted(prepared.rglob('*'))
            if p.is_file() and p!=prepared/'preparation.json'}
    require(actual==row['prepared_files'],'Prepared source inventory changed')
    ack.verify_prepared(prepared/'ack')
    require(not any(row[n] for n in ('actual_core_protocol_proved','whole_soc_verified',
            'sequential_equivalence_proved','candidate_adopted','timing_accepted')),
            'Preparation cannot grant architectural or production acceptance')
    return row


def firmware_hex(binary,elf):
    data=elf.read_bytes()
    require(data[:6]==b'\x7fELF\x01\x01' and struct.unpack_from('<H',data,18)[0]==243
            and struct.unpack_from('<I',data,24)[0]==0x80,'Firmware ELF is not RV32 at reset vector')
    raw=b'\0'*0x80+binary.read_bytes()
    require(len(raw)<=0x2000,'Firmware overlaps data region')
    raw+=b'\0'*(16384-len(raw))
    return ''.join(f'{word:08x}\n' for word, in struct.iter_unpack('<I',raw))


def validate_compile_log(code,log):
    require(code==0,'Actual-core harness did not compile')
    require(re.search(r'(?im)\bwarning: Port \d+[^\n]*\bexpects \d+ bits?, got \d+',log) is None,
            'Actual-core port-width mismatch in compiler log')


def parse_positive(code,log,reset):
    lines=[line for line in log.splitlines() if line.startswith('PASS_ACTUAL_CORE_DIRECTED_PROTOCOL ')]
    require(code==0 and len(lines)==1 and 'FATAL:' not in log,'Actual core protocol workload failed/incomplete')
    pairs=re.findall(r'(\w+)=(\d+)',lines[0])
    counts={n:int(v) for n,v in pairs}
    keys={'reset_phase','cycles','accepted','delivered','cancelled','responses','cancelled_responses',
          'held','stalls','pmp_first','pmp_second','split_second','bus_errors','stopped_clock','traps','irq'}
    require(set(counts)==keys and len(pairs)==len(keys),'Native core coverage inventory differs')
    require(counts['reset_phase']==reset and 0<counts['cycles']<=30000 and counts['accepted']>0
            and counts['accepted']==counts['delivered']+counts['cancelled']
            and counts['delivered']==counts['responses']+counts['cancelled_responses']
            and counts['held']>=1 and counts['stalls']>=5 and counts['pmp_first']>=2
            and counts['pmp_second']>=2 and counts['split_second']>=8 and counts['bus_errors']==4
            and counts['stopped_clock']>=6 and counts['traps']==8 and counts['irq']==1,
            'Missing actual core coverage/accounting')
    return counts


def read_signature(path):
    words=[]
    for line in path.read_text().splitlines():
        line=line.split('//',1)[0].strip()
        if line:
            require(re.fullmatch('[0-9a-fA-F]{8}',line),'Unknown or invalid architectural signature word')
            words.append(int(line,16))
    require(len(words)==2048,'Incomplete architectural memory signature')
    require(words[(0x3fe0-0x2000)//4]==8 and words[(0x3fe4-0x2000)//4]==1
            and words[(0x3ff0-0x2000)//4]==0x600dc0de,'Missing firmware architectural selfcheck')
    return hashlib.sha256(b''.join(struct.pack('<I',w) for w in words)).hexdigest()


def execute(command,directory,name):
    with (directory/(name+'.log')).open('w') as log:
        result=subprocess.run(list(map(str,command)),stdout=log,stderr=subprocess.STDOUT,
                              stdin=subprocess.DEVNULL,check=False)
    row=dict(command=list(map(str,command)),returncode=result.returncode,log=pin(directory/(name+'.log')))
    save(directory/(name+'-execution.json'),row)
    return row


def verify_firmware_probe(raw):
    require(raw==struct.pack('<4I',*PROBE_WORDS),'Compiler CSR/WFI/MRET opcode control failed')
    return dict(status='PASS_EXACT_RV32_CSR_WFI_MRET_ENCODINGS',
                flags=list(FIRMWARE_FLAGS),words=[f'{w:08x}' for w in PROBE_WORDS],
                bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())


def firmware_toolchain_probe(gcc,objcopy,output):
    output.mkdir()
    source=output/'probe.S';source.write_text(FIRMWARE_PROBE)
    compiled=execute([gcc,*FIRMWARE_FLAGS,'-nostdlib','-Wl,--build-id=none','-Wl,--no-relax',
                      '-Wl,-Ttext=0x80','-Wl,-e,_start',source,'-o',output/'probe.elf'],output,'compile')
    require(compiled['returncode']==0,'Compiler cannot assemble required RV32 CSR instructions')
    copied=execute([objcopy,'-j','.text','-O','binary',output/'probe.elf',output/'probe.bin'],output,'objcopy')
    require(copied['returncode']==0,'Compiler opcode control extraction failed')
    # This also verifies the actual RV32 ELF machine, endianness and entry.
    firmware_hex(output/'probe.bin',output/'probe.elf')
    result=verify_firmware_probe((output/'probe.bin').read_bytes())
    result.update(compile=compiled,objcopy=copied)
    save(output/'result.json',result)
    return result


def run(prepared,output):
    require(os.environ.get('GITHUB_ACTIONS')=='true' and re.fullmatch('[0-9a-f]{40}',os.environ.get('GITHUB_SHA','')),
            'Actual-core RTL workloads are cloud-only after source review')
    preparation=verify_prepared(prepared)
    tools={name:Path(shutil.which(name) or '') for name in
           ('iverilog','vvp','riscv64-unknown-elf-gcc','riscv64-unknown-elf-objcopy')}
    require(all(p.is_file() for p in tools.values()),'Required RTL/firmware tools unavailable')
    output.mkdir(parents=True,exist_ok=False)
    row=dict(schema=1,status='EXECUTING_ACTUAL_CORE_DIRECTED_PROTOCOL',github_source_commit=os.environ['GITHUB_SHA'],
             preparation=pin(prepared/'preparation.json'),methods=preparation['source_methods'],cases={},compilations={},
             runtime={n:dict(path=str(p.resolve()),**pin(p)) for n,p in tools.items()},
             limitations=LIMITATIONS,actual_core_protocol_proved=False,whole_soc_verified=False,
             sequential_equivalence_proved=False,candidate_adopted=False,timing_accepted=False)
    save(output/'result.json',row)
    try:
        for name,path in tools.items():
            execution=execute([path,'-V' if name in ('iverilog','vvp') else '--version'],output,name+'-version')
            require(execution['returncode']==0,'Tool version capture failed: '+name)
        row['firmware_toolchain_probe']=firmware_toolchain_probe(tools['riscv64-unknown-elf-gcc'],
            tools['riscv64-unknown-elf-objcopy'],output/'firmware-toolchain-probe')
        compiled=execute([tools['riscv64-unknown-elf-gcc'],*FIRMWARE_FLAGS,'-nostdlib',
            '-Wl,--build-id=none','-Wl,--no-relax','-Wl,-T,'+str(prepared/'link.ld'),
            prepared/'firmware.S','-o',output/'firmware.elf'],output,'firmware-compile')
        require(compiled['returncode']==0,'Directed firmware did not compile')
        copied=execute([tools['riscv64-unknown-elf-objcopy'],'-O','binary',output/'firmware.elf',
                        output/'firmware.bin'],output,'firmware-objcopy')
        require(copied['returncode']==0,'Directed firmware extraction failed')
        (output/'firmware.hex').write_text(firmware_hex(output/'firmware.bin',output/'firmware.elf'))
        core=[prepared/'sources'/n for n in preparation['selected_core_sources']]
        variants={'original':(prepared/'ack/original.v').read_text(),
                  'candidate':(prepared/'ack/candidate.v').read_text()}
        for name,(before,after,_) in NEGATIVES.items():
            require(variants['candidate'].count(before)==1,'Ambiguous negative-control mutation')
            variants[name]=variants['candidate'].replace(before,after,1)
        variants[CLOCK_NEGATIVE]=variants['candidate']
        for name,text in variants.items():
            directory=output/name;directory.mkdir()
            pipe=directory/'soc_req_pipe.v';pipe.write_text(text)
            selected=list(core)
            if name==CLOCK_NEGATIVE:
                gate=prepared/'sources/hw/soc/rtl/prim_clock_gating.v'
                body=gate.read_text();before='  assign clk_o = en_latch & clk_i;'
                require(body.count(before)==1,'Ambiguous stuck-open clock negative control')
                changed=directory/'prim_clock_gating.v'
                changed.write_text(body.replace(before,'  assign clk_o = clk_i;',1))
                selected=[changed if p==gate else p for p in selected]
            command=[tools['iverilog'],'-g2012','-s','tb_core_ack_protocol','-DSG13G2_ICG_BEHAVIOURAL',
                     '-o',directory/'simulation.vvp']
            if name!='original':command+=['-DACK_CANDIDATE']
            build=execute(command+[prepared/'tb_core_ack_protocol.v',pipe,*selected],directory,'compile')
            row['compilations'][name]=dict(execution=build,log=pin(directory/'compile.log'))
            save(output/'result.json',row)
            validate_compile_log(build['returncode'],(directory/'compile.log').read_text())
            for reset in (range(4) if name=='candidate' else (0,)):
                key=name+'-reset'+str(reset)
                directory=output/key;directory.mkdir()
                command=[tools['vvp'],output/name/'simulation.vvp','+image='+str(output/'firmware.hex'),
                         '+signature='+str(directory/'signature.hex'),'+reset_phase='+str(reset)]
                native=execute(command,directory,'native')
                log=(directory/'native.log').read_text()
                result=dict(execution=native,variant=name,reset_phase=reset,passed=False)
                try:
                    if name in REJECTIONS:
                        require(native['returncode']!=0 and REJECTIONS[name] in log and
                                'PASS_ACTUAL_CORE_DIRECTED_PROTOCOL' not in log,'Actual-core negative control not rejected')
                        result.update(passed=True,expected_rejection=REJECTIONS[name])
                    else:
                        result.update(counters=parse_positive(native['returncode'],log,reset),
                                      signature_sha256=read_signature(directory/'signature.hex'),passed=True)
                except (ValueError,OSError) as error:
                    result['error']=str(error)
                row['cases'][key]=result
                save(output/'result.json',row)
        require(len(row['cases'])==9 and all(c['passed'] for c in row['cases'].values()),'One or more real core cases failed')
        signatures={c['signature_sha256'] for c in row['cases'].values() if 'signature_sha256' in c}
        require(len(signatures)==1,'Baseline/candidate/reset architectural memory signatures differ')
        verify_prepared(prepared)
        require(all(pin(path)=={k:row['runtime'][name][k] for k in ('bytes','sha256')}
                    for name,path in tools.items()),'Principal runtime tool changed during execution')
        row.update(status='PASS_FINITE_ACTUAL_CORE_PROTOCOL_CASES_ONLY',directed_actual_core_cases_passed=True,
                   matching_architectural_signature=signatures.pop())
    except Exception as error:
        row.update(status='FAILED_PRESERVED',error=f'{type(error).__name__}: {error}')
        raise
    finally:
        row['outputs']={str(p.relative_to(output)):pin(p) for p in sorted(output.rglob('*'))
                        if p.is_file() and p!=output/'result.json'}
        save(output/'result.json',row)
    return row


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=('prepare','run'))
    parser.add_argument('--prepared',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.mode=='prepare':row=prepare(args.output.resolve())
    else:
        require(args.prepared is not None,'--prepared is required for run')
        row=run(args.prepared.resolve(),args.output.resolve())
    print(row['status'])


if __name__=='__main__':main()
