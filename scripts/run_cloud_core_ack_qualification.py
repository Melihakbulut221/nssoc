#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Isolated C10 ACK-retiming synthesis, exact SRAM mapping and full-SoC boot.

The ACK changes latency. Finite protocol/boot tests are not sequential
equivalence or physical acceptance; every product/adoption gate stays false.
Existing ALU helpers are reused read-only, never parameter-patched.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import zipfile

import bootstrap_oss
import prepare_core_ack_register as ack
import run_core_ack_protocol as protocol
import run_cloud_alu_prefix as alu
import run_cloud_alu_qualification as qualified
import run_cloud_eco_logic_proof as artifact
import run_cloud_timing_experiment as common
import timing_process_guard as process

ROOT=Path(__file__).resolve().parents[1]
# Corrected full-width observer run, independently replayed from complete ZIP.
# The earlier nine-case run with a truncated RF alert observer is not accepted.
PROTOCOL_PRODUCER=dict(run_id=37012329552,source_commit='1c46e6c88f1aeec53be08b6dcb08aca0d5460787',
    artifact_id=11228850191,artifact_name='core-ack-protocol-1',bytes=2530369,
    sha256='a92a1ec730f35aaefc3e1f56cc43c14f42c28bfdfaadeedf39b4a09bfb24a97b',
    url='https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20260927-chip-io/'
        'closure-core-ack-full-width-37012329552-20261002.zip',
    result=dict(bytes=51135,sha256='d5a4d69f1dc3e95e083cebcca0de7e5c0a61802b61f990c28abb0324a5f0618a'),
    firmware=dict(bytes=4228,sha256='23891593617bf95f7a4f4577e59af33e7960797589bd8b3e9b0641543f652382'),
    signature_sha256='70ef3becdad7f7b96bcdf33b717c9a40ec3ef48bc75cf77d6d8c984e8898a2c1')
CANDIDATE_SHA='f1a8197ef15ff6ce98ccb78eed39c3a0297edbc4db9cf38164f6311d0f515b5c'
PIPE='hw/soc/rtl/soc_req_pipe.v'
PREREQUISITE_LOCK='hw/soc/pnr/core-ack-qualification-input.lock.json'
PREREQUISITE_LOCK_SHA='b208c9d5c6115990680be96e183eecc9ca723f262658e92a5a843cf94c2640c7'
QUALIFICATION_LOCK_SHA='5848b42bbdf8817205d629d7db2ef9619f82a62f12d8667fd85e749f219511c2'
SOURCES=tuple(dict.fromkeys((*alu.SOURCES,*qualified.SOURCES,*protocol.OWN,
    'scripts/run_cloud_core_ack_qualification.py','sw/tests/test_core_ack_qualification.py',
    '.github/workflows/timing-core-ack-qualification.yml','scripts/timing_process_guard.py',PREREQUISITE_LOCK)))
GATES=('candidate_adopted','timing_accepted','manufacturing_approval',
       'sequential_equivalence_proved','actual_core_protocol_proved','full_soc_functional_accepted')
CONTROL_FILES={'launch.json','observer.json','worker.log','worker-final.json'}
MAP_STATUS='PASS_ACK_SYNTHESIS_AND_EXACT_SRAM_MAPPING_ONLY'
BOOT_STATUS='PASS_ACK_FINITE_FOUR_STATE_SOC_BOOT_AND_MBIST_ONLY'
LIMITATIONS=[
    'Exactly one request-pipe source changes; the original C10 ALU and all other 80 RTL/header inputs remain byte-identical.',
    'The queue adds one cycle before upstream acknowledgement and downstream exposure; same-cycle equivalence is neither asserted nor waived.',
    'The required actual-core run proves only nine directed cases, not all reachable core hazards or interrupt/debug/PMP-update interleavings.',
    'Full-SoC boot uses the immutable C10 loader, native functional cells and explicit SRAM models; no SDF or transistor/analog timing.',
    'A successful 28-check boot and system/Ethernet MBIST are finite workload evidence, not exhaustive architectural refinement.',
    'No default RTL adoption, physical timing/RC, DRC/LVS or manufacturing acceptance follows from this experiment.',
]
require=alu.require
pin=alu.pin


def cloud_only():
    require(os.environ.get('GITHUB_ACTIONS')=='true' and
            re.fullmatch('[0-9a-f]{40}',os.environ.get('GITHUB_SHA','')),'Full ACK qualification is cloud-only')


def qualification_lock():
    require(common.sha(ROOT/qualified.LOCK)==QUALIFICATION_LOCK_SHA,'Original qualification lock differs')
    return json.loads((ROOT/qualified.LOCK).read_text())


def own_inventory(directory):
    require(not any(p.is_symlink() for p in directory.rglob('*')),'Linked qualification output')
    return {str(p.relative_to(directory)):pin(p) for p in sorted(directory.rglob('*'))
            if p.is_file() and str(p.relative_to(directory))!='result.json' and str(p.relative_to(directory)) not in CONTROL_FILES
            and p.suffix!='.tmp'}


def finish(output,row):
    row['outputs']=own_inventory(output)
    common.save(output/'result.json',row)


def verify_outputs(output,row):
    require(own_inventory(output)==row['outputs'],'Qualification output inventory differs')
    require(row['github_source_commit']==os.environ['GITHUB_SHA'],'Same-workflow source differs')
    require(set(row['methods'])==set(SOURCES),'Qualification method inventory differs')
    for name,expected in row['methods'].items():
        common.verify_file(output/'methods'/name,expected)
        raw=artifact.git_bytes(row['github_source_commit'],name)
        require(dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())==expected,
                'Method is not immutable workflow Git source: '+name)
        common.verify_file(ROOT/name,expected)
    require(all(row.get(n) is False for n in GATES) and row['limitations']==LIMITATIONS,
            'Qualification cannot grant product acceptance')


def synthesis_recipe(template,bundle,output,pipe,lock):
    require(hashlib.sha256(template.encode()).hexdigest()==lock['files']['recipe/c10.ys']['sha256'],
            'Original C10 synthesis instructions changed')
    old=lock['original_repo']+'/'+PIPE
    require(template.count(old)==1,'Request-pipe input selection is ambiguous')
    replacements={old:str(pipe),lock['original_synthesis']:str(output),
                  lock['original_repo']:str(bundle/'repo'),lock['original_pdk']:str(bundle/'pdk')}
    pattern='|'.join(re.escape(p) for p in sorted(replacements,key=len,reverse=True))
    return re.sub(pattern,lambda m:replacements[m.group()],template)


def verify_protocol_tree(directory,producer):
    prepared=directory/'core-ack-prepared';result=directory/'core-ack-result'
    row=json.loads((result/'result.json').read_text())
    common.verify_file(result/'result.json',producer['result'])
    require(row['github_source_commit']==producer['source_commit'] and
            row['status']=='PASS_FINITE_ACTUAL_CORE_PROTOCOL_CASES_ONLY',
            'Corrected actual-core native result missing')
    preparation=protocol.verify_prepared(prepared)
    require(row['preparation']==pin(prepared/'preparation.json') and
            row['methods']==preparation['source_methods'],'Protocol preparation binding differs')
    for name,expected in row['methods'].items():
        raw=artifact.git_bytes(producer['source_commit'],name)
        require(dict(bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())==expected,
                'Protocol method is not its immutable producer source')
    actual={str(p.relative_to(result)):pin(p) for p in sorted(result.rglob('*'))
            if p.is_file() and p!=result/'result.json'}
    require(not any(p.is_symlink() for p in result.rglob('*')) and actual==row['outputs'],
            'Protocol native output closure differs')
    common.verify_file(result/'firmware.bin',producer['firmware'])
    require((result/'firmware.hex').read_text()==protocol.firmware_hex(result/'firmware.bin',result/'firmware.elf'),
            'Actual protocol firmware memory image differs')
    probe=protocol.verify_firmware_probe((result/'firmware-toolchain-probe/probe.bin').read_bytes())
    require(all(row['firmware_toolchain_probe'][name]==value for name,value in probe.items()) and
            all(row['firmware_toolchain_probe'][name]['returncode']==0 for name in ('compile','objcopy')),
            'Native firmware opcode gate differs')
    variants={'original','candidate',*protocol.REJECTIONS}
    require(set(row.get('compilations',{}))==variants,'Full-width native compilation gates missing')
    for name,compiled in row['compilations'].items():
        log=result/name/'compile.log'
        common.verify_file(log,compiled['log'])
        protocol.validate_compile_log(compiled['execution']['returncode'],log.read_text())
    expected={'original-reset0',*(f'candidate-reset{n}' for n in range(4)),
              *(name+'-reset0' for name in protocol.REJECTIONS)}
    require(set(row['cases'])==expected,'Nine actual-core cases differ')
    signatures=set()
    for name,case in row['cases'].items():
        log=result/name/'native.log';common.verify_file(log,case['execution']['log'])
        text=log.read_text();code=case['execution']['returncode']
        require(case['passed'] is True,'A required actual-core case did not pass')
        if case['variant'] in protocol.REJECTIONS:
            require(code!=0 and protocol.REJECTIONS[case['variant']] in text and
                    'PASS_ACTUAL_CORE_DIRECTED_PROTOCOL' not in text,'Negative native control not rejected')
        else:
            counters=protocol.parse_positive(code,text,case['reset_phase'])
            require(counters==case['counters'],'Native counters do not match raw log')
            signature=protocol.read_signature(result/name/'signature.hex')
            require(signature==case['signature_sha256'],'Native signature differs')
            signatures.add(signature)
    require(len(signatures)==1 and row['matching_architectural_signature']==producer['signature_sha256']
            and row['matching_architectural_signature'] in signatures,
            'Native architectural signatures differ')
    require(all(row[n] is False for n in ('actual_core_protocol_proved','whole_soc_verified',
            'sequential_equivalence_proved','candidate_adopted','timing_accepted')),
            'Finite protocol run cannot grant architectural acceptance')
    require(pin(prepared/'ack/candidate.v')['sha256']==CANDIDATE_SHA,'Observed ACK candidate differs')
    return row


def protocol_provenance():
    require(common.sha(ROOT/PREREQUISITE_LOCK)==PREREQUISITE_LOCK_SHA,'Captured protocol provenance differs')
    captured=json.loads((ROOT/PREREQUISITE_LOCK).read_text())
    artifact.validate_metadata(PROTOCOL_PRODUCER,captured['run'],captured['artifact'])
    return captured


def check_live_provenance(run,info,captured):
    if run is not None:artifact.validate_metadata(PROTOCOL_PRODUCER,run,captured['artifact'])
    if info is not None:
        require(all(info.get(n)==captured['artifact'][n] for n in ('id','name','size_in_bytes','digest'))
                and info.get('workflow_run',{}).get('id')==PROTOCOL_PRODUCER['run_id']
                and info.get('workflow_run',{}).get('head_sha')==PROTOCOL_PRODUCER['source_commit']
                and type(info.get('expired')) is bool,'Live protocol artifact identity differs')


def get_protocol(work,output):
    require(PROTOCOL_PRODUCER is not None,'Corrected actual-core producer pin pending')
    captured=protocol_provenance();live={};observations={}
    for name,endpoint in (('run',f'actions/runs/{PROTOCOL_PRODUCER["run_id"]}'),
                          ('artifact',f'actions/artifacts/{PROTOCOL_PRODUCER["artifact_id"]}')):
        response=subprocess.run(['gh','api',f'repos/{artifact.REPOSITORY}/{endpoint}'],
                                capture_output=True,text=True,check=False)
        live[name]=json.loads(response.stdout) if response.returncode==0 else None
        observations[name]=dict(returncode=response.returncode,available=live[name] is not None,
            source='Live API metadata' if live[name] is not None else 'Pinned captured provenance; live metadata unavailable')
    check_live_provenance(live['run'],live['artifact'],captured)
    common.save(output/'protocol-provenance.json',dict(captured=captured,live=live,observation=observations,
        byte_source='Permanent release copy; exact original Actions ZIP length and SHA required even after artifact expiration.'))
    archive=work/'protocol.zip'
    common.download(PROTOCOL_PRODUCER,archive)
    with zipfile.ZipFile(archive) as zipped:
        require(len(zipped.infolist())<=256 and sum(i.file_size for i in zipped.infolist())<=32*1024**2,
                'Protocol artifact exceeds compact evidence budget')
    directory=work/'protocol'
    extraction=artifact.extract_zip(archive,directory)
    row=verify_protocol_tree(directory,PROTOCOL_PRODUCER)
    common.save(output/'protocol-result.json',row)
    return dict(producer=PROTOCOL_PRODUCER,result=pin(directory/'core-ack-result/result.json'),
                checked_cases=9,checked_compilations=6,extraction=extraction,
                scope='Finite directed actual-core protocol prerequisite only; not architectural equivalence.')


def initialize(output,work,check_protocol=False):
    cloud_only()
    require(PROTOCOL_PRODUCER is not None,'Corrected actual-core producer pin pending')
    output=common.fresh_directory(output);work=common.fresh_directory(work)
    row=dict(schema=1,status='PREPARING_ISOLATED_ACK_QUALIFICATION',
             github_source_commit=os.environ['GITHUB_SHA'],profile=alu.PROFILE,
             limitations=LIMITATIONS,**{n:False for n in GATES})
    common.save(output/'result.json',row)
    try:
        row['methods']={}
        for name in SOURCES:
            target=output/'methods'/name;target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/name,target);row['methods'][name]=pin(target)
        row['original_c10_sources']=protocol.source_contract()
        lock=alu.validate_lock(json.loads((ROOT/alu.LOCK).read_text()))
        require(common.sha(ROOT/alu.MANIFEST)==lock['c10_manifest_sha256'],'Original C10 physical manifest differs')
        snapshot=work/'c10';alu.restore(ROOT/lock['archive']['path'],snapshot,lock)
        bootlock=qualification_lock()
        bundle=work/'qualification';qualified.restore_inputs(bootlock,bundle)
        row.update(source_snapshot=lock['archive'],qualification_inputs=bootlock['archive'])
        if check_protocol:row['actual_core_prerequisite']=get_protocol(work,output)
        tools=bootstrap_oss.install(work/'oss-cad-suite')
        for name,digest in [('yosys',lock['synthesis_yosys_sha256']),
                            ('iverilog',bootlock['iverilog_sha256']),('vvp',bootlock['vvp_sha256'])]:
            require(common.sha(tools/'bin'/name)==digest,'Original runtime tool differs: '+name)
        version=subprocess.check_output([str(tools/'bin/yosys'),'-V'],text=True).strip()
        require('Yosys 0.67+146 ' in version,'Original C10 synthesis runtime version differs')
        row['runtime']=dict(archive_sha256=bootstrap_oss.ARCHIVE_SHA256,
            archive_bytes=bootstrap_oss.ARCHIVE_SIZE,url=bootstrap_oss.URL,yosys_version=version,
            tools={n:pin(tools/'bin'/n) for n in ('yosys','iverilog','vvp')})
        return output,work,row,lock,snapshot,bootlock,bundle,tools
    except BaseException as error:
        row.update(status='FAILED_PRESERVED',error=f'{type(error).__name__}: {error}')
        finish(output,row)
        raise


def synthesize_and_map(output,work):
    output,work,row,lock,snapshot,bootlock,bundle,tools=initialize(output,work,check_protocol=True)
    try:
        ack.prepare(snapshot/'repo'/PIPE,output/'prepared')
        require(common.sha(output/'prepared/candidate.v')==CANDIDATE_SHA,'ACK source changed')
        row.update(status='SYNTHESIZING_MATCHED_C10_ACK',synthesis={},mapping={})
        physical=json.loads((bundle/'physical-config.json').read_text())
        manifest=json.loads((ROOT/alu.MANIFEST).read_text())
        common.verify_file(bundle/'physical-config.json',manifest['files'][manifest['config']])
        original_relative=Path(lock['original_synthesis']).relative_to(lock['original_repo'])
        for name in ('original','candidate'):
            directory=output/('synthesis-'+name);directory.mkdir()
            shutil.copytree(snapshot/'repo'/original_relative/'boot-rom',directory/'boot-rom')
            shutil.copyfile(snapshot/'repo'/original_relative/'abc.constr',directory/'abc.constr')
            script=directory/'synthesis.ys';pipe=output/'prepared'/(name+'.v')
            script.write_text(synthesis_recipe((snapshot/'recipe/c10.ys').read_text(),snapshot,directory,pipe,lock))
            inputs=alu.validate_recipe_inputs(script.read_text(),snapshot,directory,pipe)
            require(inputs[str(snapshot/lock['original_alu'])]==lock['files'][lock['original_alu']],
                    'The original C10 ALU was replaced')
            common.save(directory/'read-inputs.json',inputs)
            common.save(output/'result.json',row)
            execution=alu.execute([tools/'bin/yosys','-s',script],directory,'synthesis')
            require(execution['returncode']==0,'ACK '+name+' synthesis failed')
            netlist=directory/'soc_top.netlist.v'
            require(netlist.is_file() and netlist.stat().st_size>1_000_000,'Full-SoC netlist absent')
            row['synthesis'][name]=dict(execution=execution,netlist=pin(netlist),recipe=pin(script),
                                       area_report=pin(directory/'area.rpt'))
            if name=='original':
                row['baseline_reproduction']=dict(observed=pin(netlist),expected_sha256=lock['baseline_netlist_sha256'])
                common.save(output/'result.json',row)
                require(common.sha(netlist)==lock['baseline_netlist_sha256'],
                        'Original C10 synthesis did not reproduce byte-for-byte')
            mapped=output/('mapping-'+name);mapped.mkdir();recipe=mapped/'map.ys'
            recipe.write_text(qualified.mapping_recipe((bundle/'recipe/original-map.ys').read_text(),
                                                       netlist,mapped,bundle,snapshot,lock))
            execution=alu.execute([tools/'bin/yosys','-s',recipe],mapped,'mapping')
            require(execution['returncode']==0,'Exact SRAM mapping failed: '+name)
            before=json.loads((mapped/'before.json').read_text())['modules']['soc_top']
            after=json.loads((mapped/'after.json').read_text())['modules']['soc_top']
            checks=qualified.mapping_contract(before,after,physical);del before,after
            row['mapping'][name]=dict(execution=execution,checks=checks,
                netlist=pin(mapped/'soc_top.netlist.v'),recipe=pin(recipe))
            common.save(output/'result.json',row)
            if name=='original':
                require(row['mapping'][name]['netlist']['sha256']==bootlock['original_mapping_sha256'],
                        'Original 32-SRAM mapped baseline did not reproduce byte-for-byte')
        verify_input_trees(snapshot,lock,bundle,bootlock,row)
        for name,expected in row['runtime']['tools'].items():common.verify_file(tools/'bin'/name,expected)
        row.update(status=MAP_STATUS,upstream_ack_latency_added_cycles=1,
                   downstream_request_latency_added_cycles=1,
                   next_required=['Four original/candidate vendor/independent SoC boot and MBIST cases',
                     'Reachable architectural refinement with IRQ/debug/PMP/reset interleavings',
                     'Fresh placement/routing and original all-corner physical timing/RC/DRC/LVS'])
    except BaseException as error:
        row.update(status='FAILED_PRESERVED',error=f'{type(error).__name__}: {error}')
        raise
    finally:finish(output,row)


def verify_input_trees(snapshot,lock,bundle,bootlock,row):
    for name,expected in lock['files'].items():common.verify_file(snapshot/name,expected)
    for name,expected in bootlock['files'].items():common.verify_file(bundle/name,expected)
    require(protocol.source_contract()==row['original_c10_sources'],'Default C10 RTL changed during experiment')


def verify_map(directory):
    row=json.loads((directory/'result.json').read_text());verify_outputs(directory,row)
    lock=alu.validate_lock(json.loads((ROOT/alu.LOCK).read_text()))
    bootlock=qualification_lock()
    require(row['status']==MAP_STATUS and row['profile']==alu.PROFILE and
            row['original_c10_sources']==protocol.source_contract(),'Completed ACK source profile differs')
    require(row['actual_core_prerequisite']['producer']==PROTOCOL_PRODUCER and
            row['actual_core_prerequisite']['checked_cases']==9 and
            row['actual_core_prerequisite']['checked_compilations']==6,'Corrected protocol prerequisite absent')
    require(row['baseline_reproduction']['observed']['sha256']==lock['baseline_netlist_sha256']==
            row['baseline_reproduction']['expected_sha256'],'Byte-identical original synthesis missing')
    require(set(row['synthesis'])==set(row['mapping'])=={'original','candidate'},'Missing paired outputs')
    require(row['mapping']['original']['netlist']['sha256']==bootlock['original_mapping_sha256'],
            'Original SRAM byte reproduction missing')
    ack.verify_prepared(directory/'prepared')
    require(common.sha(directory/'prepared/candidate.v')==CANDIDATE_SHA,'ACK candidate differs')
    for name in ('original','candidate'):
        for kind in ('synthesis','mapping'):
            require(row[kind][name]['execution']['returncode']==0,'Failed native synthesis/map')
            common.verify_file(directory/(kind+'-'+name)/'soc_top.netlist.v',row[kind][name]['netlist'])
    return row


def boot_prepare(output,work,name,memory,mapped):
    cloud_only()
    require(name in ('original','candidate') and memory in ('vendor','independent'),'Unknown boot case')
    mapped=mapped.resolve();producer=verify_map(mapped)
    output,work,row,lock,snapshot,bootlock,bundle,tools=initialize(output,work)
    try:
        row.update(variant=name,memory=memory,status='PREPARING_EXACT_ACK_SOC_BOOT',
            cycle_bound=qualified.CYCLES,actual_core_prerequisite=producer['actual_core_prerequisite'],
            synthesis_mapping_result=pin(mapped/'result.json'),synthesis_mapping_commit=producer['github_source_commit'])
        common.save(output/'synthesis-mapping-result.json',producer)
        gl=qualified.module(ROOT/'hw/soc/flow/sim_logic_boot_gl.py','ack_qualification_gl')
        generator=qualified.module(ROOT/'hw/soc/flow/gen_logic_boot_rom.py','ack_qualification_rom')
        firmware=output/'firmware';shutil.copytree(bundle/'firmware',firmware)
        rom=generator.generate(firmware/'test_soc.bin',firmware/'boot-rom')
        require(rom['rtl_sha256']==bootlock['rom_sha256'] and rom['image_sha256']==bootlock['loader_sha256']
                and rom==json.loads((bundle/'c10-rom/manifest.json').read_text()),'Original C10 loader/ROM differs')
        nm=shutil.which('nm');require(nm is not None,'ELF symbol reader missing')
        symbols=gl.read_symbols(nm,firmware/'app.elf')
        row.update(symbols=symbols,nm=dict(path=nm,**pin(Path(nm)),
            version=subprocess.check_output([nm,'--version'],text=True).splitlines()[0]))
        version=subprocess.run([str(tools/'bin/iverilog'),'-V'],capture_output=True,text=True,check=True).stdout
        require(re.search(r'Icarus Verilog version (?:1[3-9]|[2-9]\d)',version),'Icarus>=13 required')
        (output/'iverilog-version.log').write_text(version)
        gate=gl.check_native_cell('iverilog',str(tools/'bin/iverilog'),bundle/'models/sg13g2_stdcell.v',output/'native-cell-gate')
        row['native_cell_gate']=gate;require(gate['passed'],'Native standard-cell gate failed')
        kind='synthesis' if memory=='vendor' else 'mapping'
        source=mapped/(kind+'-'+name)/'soc_top.netlist.v'
        common.verify_file(source,producer[kind][name]['netlist'])
        models=([bundle/'models'/n for n in gl.SRAM_MODELS] if memory=='vendor'
                else [bundle/'models/sp.v',bundle/'models/dp.v'])
        bench=output/'tb_qualification_boot.v'
        bench.write_text(qualified.prepare_boot_bench((bundle/'repo/hw/soc/tb/tb_soc_logic_boot_gl.v').read_text(),memory))
        files=[bench,source,bundle/'repo/hw/soc/tb/flash_w25q128jv.v',bundle/'models/sg13g2_stdcell.v',*models]
        pins={str(p):pin(p) for p in [*files,firmware/'app.elf',firmware/'flash0.hex',firmware/'test_soc.bin']}
        command=[tools/'bin/iverilog','-g2005-sv','-s','tb_logicrom_gl','-o',work/'sim.vvp',
                 '-DFUNCTIONAL',f'-DTIMEOUT_CYCLES={qualified.CYCLES}']
        command += [f"-D{macro}=32'h{symbols[symbol]:08x}" for macro,symbol in gl.SYMBOLS.items()]
        row.update(status='COMPILING_ACTUAL_ACK_MAPPED_BOOT',sources=pins,rom_manifest=rom)
        common.save(output/'result.json',row)
        compiled=alu.execute(command+files,output,'compile');row['compile']=compiled
        protocol.validate_compile_log(compiled['returncode'],(output/'compile.log').read_text())
        row.update(status='COMPILED_READY_FOR_ACK_FOUR_STATE_BOOT',compiled_simulation=pin(work/'sim.vvp'),
                   compiled_simulation_path=str(work/'sim.vvp'),
                   boot_command=list(map(str,[tools/'bin/vvp','-i',work/'sim.vvp','+flash0='+str(firmware/'flash0.hex')])))
        for path,expected in pins.items():common.verify_file(Path(path),expected)
        verify_input_trees(snapshot,lock,bundle,bootlock,row)
    except BaseException as error:
        row.update(status='FAILED_PRESERVED',error=f'{type(error).__name__}: {error}')
        raise
    finally:finish(output,row)


def boot_run(output):
    cloud_only();row=json.loads((output/'result.json').read_text())
    try:
        require(row['status']=='COMPILED_READY_FOR_ACK_FOUR_STATE_BOOT','Wrong boot startup state')
        verify_outputs(output,row)
        require(row['actual_core_prerequisite']['producer']==PROTOCOL_PRODUCER and
                row['cycle_bound']==qualified.CYCLES,'Boot prerequisite or cycle bound changed')
        for name,expected in row['sources'].items():common.verify_file(Path(name),expected)
        common.verify_file(Path(row['compiled_simulation_path']),row['compiled_simulation'])
        command=row['boot_command']
        require(command[1:3]==['-i',row['compiled_simulation_path']] and len(command)==4
                and command[3]=='+flash0='+str(output/'firmware/flash0.hex'),'Boot command differs')
        common.verify_file(Path(command[0]),row['runtime']['tools']['vvp'])
        row['status']='RUNNING_ACK_FOUR_STATE_BOOT_AND_MBIST';common.save(output/'result.json',row)
        progress=output/'progress';progress.mkdir()
        env=os.environ.copy()
        for key in ('GH_TOKEN','GITHUB_TOKEN','PYTHONPATH','PYTHONHOME'):env.pop(key,None)
        start=time.monotonic()
        with (output/'boot.log').open('x') as log:
            child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                text=True,bufsize=1,env=env,stdin=subprocess.DEVNULL)
            for line in child.stdout:
                log.write(line);log.flush();print(line,end='',flush=True)
                match=re.search(r'LOGICROM_GL progress cycles=(\d+)',line)
                if match:
                    cycle=int(match[1]);record=dict(cycle=cycle,elapsed_s=time.monotonic()-start,
                        raw_marker=line.rstrip(),log_prefix=pin(output/'boot.log'),compiled_simulation=row['compiled_simulation'])
                    target=progress/f'cycle-{cycle:07d}.json'
                    require(not target.exists(),'Repeated native cycle marker')
                    common.save(target,record)
            code=child.wait()
        row['boot_execution']=dict(command=command,returncode=code,elapsed_s=time.monotonic()-start)
        common.save(output/'boot-execution.json',row['boot_execution'])
        for name,expected in row['sources'].items():common.verify_file(Path(name),expected)
        common.verify_file(Path(row['compiled_simulation_path']),row['compiled_simulation'])
        common.verify_file(Path(command[0]),row['runtime']['tools']['vvp'])
        require(qualified.passed_boot(code,(output/'boot.log').read_text()),'Full ACK SoC MBIST/28-check boot failed')
        row.update(status=BOOT_STATUS,scope='Finite four-state mapped SoC boot, exact native cells and immutable C10 loader/flash; '
                   'system and Ethernet power-on MBIST plus 28 checks. No SDF, exhaustive refinement, adoption or timing acceptance.')
    except BaseException as error:
        row.update(status='FAILED_PRESERVED',error=f'{type(error).__name__}: {error}')
        raise
    finally:finish(output,row)


def start_boot(output):
    cloud_only()
    row=json.loads((output/'result.json').read_text());verify_outputs(output,row)
    require(row['status']=='COMPILED_READY_FOR_ACK_FOUR_STATE_BOOT' and not (output/'launch.json').exists(),
            'Boot worker already launched or not compiled')
    command=[sys.executable,'-B',str(Path(__file__).resolve()),'_boot-worker','--output',str(output)]
    launch_worker(output,command)


def launch_worker(output,command):
    """Detach without an elapsed watchdog; record Linux PID birth identity."""
    env=os.environ.copy()
    for key in ('GH_TOKEN','GITHUB_TOKEN','PYTHONPATH','PYTHONHOME'):env.pop(key,None)
    with (output/'worker.log').open('xb') as log:
        child=subprocess.Popen(command,stdin=subprocess.DEVNULL,stdout=log,stderr=subprocess.STDOUT,
            start_new_session=True,close_fds=True,env=env)
    # Linux may briefly expose an empty cmdline while exec installs the image.
    # Observe this transition only; no signal or worker runtime limit is used.
    identity=None
    for _ in range(50):
        identity=process.snapshot(child.pid)
        if identity is None or identity['state']=='Z' or identity['command']==command:break
        time.sleep(.01)
    require(identity is not None or (output/'worker-final.json').is_file(),'Boot worker vanished without a final receipt')
    require(identity is None or identity['state']=='Z' or identity['command']==command,
            'Boot worker command identity differs')
    common.save(output/'launch.json',dict(command=command,pid=child.pid,
        identity=identity,recorded=common.now()))
    return child


def worker(output):
    code=0
    try:boot_run(output)
    except BaseException as error:
        code=1;print(f'{type(error).__name__}: {error}',file=sys.stderr,flush=True)
    common.save(output/'worker-final.json',dict(returncode=code,result=pin(output/'result.json'),recorded=common.now()))
    return code


def observation(output):
    terminal=output/'worker-final.json'
    if terminal.is_file():
        record=json.loads(terminal.read_text())
        common.verify_file(output/'result.json',record['result'])
        return dict(terminal=True,returncode=record['returncode'],
                    status=json.loads((output/'result.json').read_text())['status'])
    # PID + kernel birth stamp are checked; no signal or native deadline is used.
    return common.observation(output)


def wait(output,seconds=None,github_output=None):
    require(seconds is None or (math.isfinite(seconds) and seconds>=0),'Invalid observation interval')
    start=time.monotonic()
    while True:
        row=observation(output)
        if row['terminal'] or (seconds is not None and time.monotonic()-start>=seconds):
            row.update(recorded=common.now(),worker_was_not_signaled=True)
            common.save(output/'observer.json',row)
            if github_output:
                with github_output.open('a') as sink:sink.write('terminal='+str(row['terminal']).lower()+'\n')
            print(json.dumps(row));return row
        time.sleep(min(15,max(0,seconds-(time.monotonic()-start))) if seconds is not None else 15)


def capture(output,destination):
    require(not destination.resolve().is_relative_to(output.resolve()),'Snapshot must be outside live output')
    destination=common.fresh_directory(destination)
    observed=observation(output);copied={}
    # Only compact fixed-prefix logs and completed receipt files. A snapshot is
    # immutable observation, never a replacement for the final validation.
    paths=[output/n for n in ('result.json','launch.json','observer.json','worker-final.json','boot.log','worker.log')]
    paths+=sorted((output/'progress').glob('*.json'))
    for path in paths:
        if not path.exists():continue
        require(path.is_file() and not path.is_symlink(),'Unsafe progress file')
        relative=str(path.relative_to(output));target=destination/relative;target.parent.mkdir(parents=True,exist_ok=True)
        with path.open('rb') as source,target.open('xb') as sink:
            remaining=os.fstat(source.fileno()).st_size
            require(remaining<=16*1024**2,'Compact snapshot file budget exceeded')
            while remaining:
                chunk=source.read(min(remaining,1024**2));require(chunk,'Truncated open snapshot source')
                sink.write(chunk);remaining-=len(chunk)
        copied[relative]=pin(target)
    common.save(destination/'snapshot.json',dict(schema=1,status='IMMUTABLE_PARTIAL_OBSERVATION_NOT_ACCEPTANCE',
        recorded=common.now(),observation=observed,files=copied,worker_was_not_signaled=True,
        candidate_adopted=False,timing_accepted=False))


def validate_boot(output):
    row=json.loads((output/'result.json').read_text());verify_outputs(output,row)
    final=json.loads((output/'worker-final.json').read_text())
    common.verify_file(output/'result.json',final['result'])
    require(final['returncode']==0 and row['status']==BOOT_STATUS,'Native boot incomplete or failed')
    require(qualified.passed_boot(row['boot_execution']['returncode'],(output/'boot.log').read_text()),
            'Completed boot markers absent')
    return row


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=('synthesis-map','boot-prepare','boot-start','_boot-worker',
                                       'wait','capture','validate-boot'))
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--work',type=Path);parser.add_argument('--mapped',type=Path)
    parser.add_argument('--variant',choices=('original','candidate'))
    parser.add_argument('--memory',choices=('vendor','independent'))
    parser.add_argument('--seconds',type=float);parser.add_argument('--github-output',type=Path)
    parser.add_argument('--destination',type=Path)
    args=parser.parse_args();output=args.output.resolve()
    if args.phase in ('synthesis-map','boot-prepare'):
        if args.work is None:parser.error('--work required')
        if args.phase=='synthesis-map':synthesize_and_map(output,args.work.resolve())
        elif args.mapped is None:parser.error('--mapped required')
        else:boot_prepare(output,args.work.resolve(),args.variant,args.memory,args.mapped)
    elif args.phase=='boot-start':start_boot(output)
    elif args.phase=='_boot-worker':sys.exit(worker(output))
    elif args.phase=='wait':wait(output,args.seconds,args.github_output)
    elif args.phase=='capture':
        if args.destination is None:parser.error('--destination required')
        capture(output,args.destination.resolve())
    else:validate_boot(output)


if __name__=='__main__':main()
