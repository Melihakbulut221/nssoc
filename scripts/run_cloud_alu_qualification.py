#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Consume completed C10 ALU synthesis; map exact SRAMs and run paired gate boot.

No synthesis, source adoption, ODB substitution or mapped-equivalence waiver.
Four-state gate simulation includes the real power-on MBIST and unchanged ROM.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tarfile
import time

sys.dont_write_bytecode = True
import bootstrap_oss
import run_cloud_alu_prefix as alu
import run_cloud_eco_logic_proof as artifact
import run_cloud_timing_experiment as common

ROOT = Path(__file__).resolve().parents[1]
LOCK = 'hw/soc/pnr/alu-qualification-input.lock.json'
PRODUCER = dict(run_id=36998734236, source_commit='b4387d7dc2436f0b223be17f93310b883c7344c1',
                artifact_id=11223062019, artifact_name='alu-prefix-synthesis-1', bytes=10989784,
                sha256='bc8345496dbcee984b9497eb6d3fd0d39b287a38e6d1e16d795c713bc11f5871',
                url='https://github.com/Melihakbulut221/nssoc/releases/download/evidence-20260927-chip-io/'
                    'closure-alu-prefix-36998734236-20261002.zip')
EXPECTED_NETLISTS = dict(original='5d05a3bc48cdd8c92dd51e61f1cff81f52e7ffcb973c2a8256f21b6648857fd8',
                        candidate='ff0fa54dac1855c21c43e3c463042ff21eefa3be65f8481ba79701742c5f796c')
STANDARD = 'pdk/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib'
SOURCES = ('scripts/run_cloud_alu_qualification.py', 'scripts/run_cloud_alu_prefix.py',
           'scripts/prepare_alu_prefix.py', 'scripts/run_cloud_eco_logic_proof.py',
           'scripts/run_cloud_timing_experiment.py', 'scripts/bootstrap_oss.py',
           '.github/workflows/timing-alu-qualification.yml', LOCK, alu.LOCK, alu.MANIFEST)
CYCLES = 3_000_000  # Measured C10 MBIST alone takes 983,048 cycles; old boot limit was 1M.
require = alu.require
pin = alu.pin


def restore_inputs(lock, destination):
    common.verify_file(ROOT/lock['archive']['path'], lock['archive'])
    destination.mkdir()
    seen = set()
    with tarfile.open(ROOT/lock['archive']['path'], 'r:xz') as source:
        for member in source:
            name = str(common.safe_relative(member.name))
            require(member.isfile() and not member.issparse() and name not in seen
                    and name in lock['files'] and member.size == lock['files'][name]['bytes'],
                    'Unsafe qualification snapshot')
            path = destination/name
            path.parent.mkdir(parents=True, exist_ok=True)
            with source.extractfile(member) as incoming, path.open('xb') as outgoing:
                shutil.copyfileobj(incoming, outgoing)
            common.verify_file(path, lock['files'][name])
            path.chmod(0o444)
            seen.add(name)
    require(seen == set(lock['files']), 'Incomplete qualification snapshot')
    for name, expected in lock['tracked_sources'].items():
        require(lock['files']['repo/'+name] == expected, 'Snapshot tracked pin differs')
        common.verify_file(ROOT/name, expected)
    require(lock['loader_sha256'] == '729a8e1c199925b8a75e982704955e5cdc63a7bbff9cc2546b73ac6c5c6c788f'
            and lock['rom_sha256'] == '66428964f4fa90fda733288ac4b8e88267f7f1205f5f551beed2b0c049fe6582',
            'Current C10 loader/ROM identity changed')


def verify_outputs(directory, row):
    actual = {str(p.relative_to(directory)) for p in directory.rglob('*') if p.is_file()}
    require(actual == set(row['outputs']) | {'result.json'}, 'Artifact file inventory differs')
    for name, expected in row['outputs'].items():
        common.safe_relative(name)
        common.verify_file(directory/name, expected)
    for name, expected in row['methods'].items():
        common.verify_file(directory/'methods'/name, expected)
        raw = artifact.git_bytes(row['github_source_commit'], name)
        require(dict(bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest()) == expected,
                'Method is not its captured Git source: '+name)


def verify_producer(directory):
    row = json.loads((directory/'result.json').read_text())
    require(row['github_source_commit'] == PRODUCER['source_commit'] and row['status'] ==
            'MATCHED_C10_SYNTHESIS_COMPLETE_REQUIRES_FUNCTIONAL_AND_PHYSICAL_PROOF',
            'Incomplete or wrong ALU synthesis producer')
    verify_outputs(directory, row)
    require(row['profile'] == alu.PROFILE and row['phase_requested'] == 'synthesis', 'Wrong producer profile')
    require(all(row[k] is False for k in ('candidate_adopted', 'timing_accepted',
                                        'manufacturing_approval', 'full_soc_functional_accepted')),
            'Producer acceptance scope differs')
    original = (directory/'prepared/original.v').read_bytes()
    candidate, negative = alu.prefix.prepare(original)
    require(candidate == (directory/'prepared/candidate.v').read_bytes() and
            negative == (directory/'prepared/negative.v').read_bytes(), 'Prepared ALU differs')
    cases = row['proof_cases']
    require([c['name'] for c in cases] == ['candidate', 'negative'], 'Missing native proof/control')
    for case in cases:
        log = directory/(case['name']+'-proof.log')
        common.verify_file(log, case['log'])
        alu.validate_proof_log(case['returncode'], log.read_text(), case['name'] == 'negative')
    for name, expected in EXPECTED_NETLISTS.items():
        require(row['synthesis'][name]['execution']['returncode'] == 0 and
                row['synthesis'][name]['netlist']['sha256'] == expected, 'Producer netlist differs')
        common.verify_file(directory/('synthesis-'+name)/'soc_top.netlist.v', row['synthesis'][name]['netlist'])
    require(row['baseline_reproduction']['observed']['sha256'] == EXPECTED_NETLISTS['original']
            == row['baseline_reproduction']['expected_sha256'], 'Original C10 reproduction absent')
    lock = json.loads((ROOT/alu.LOCK).read_text())
    require(row['source_snapshot'] == lock['archive'] and row['current_tracked_sources_verified'] ==
            lock['tracked_sources'], 'C10 synthesis snapshot contract differs')
    require(row['synthesis_runtime']['yosys']['sha256'] == lock['synthesis_yosys_sha256'] and
            row['synthesis_runtime']['archive_sha256'] == bootstrap_oss.ARCHIVE_SHA256,
            'Producer synthesis runtime differs')
    require(row['runtime'] == json.loads((ROOT/alu.MANIFEST).read_text())['runtime'],
            'Producer formal runtime differs')
    return row


def get_producer(work, output, bundle):
    # Preserve originally verified metadata. The byte-identical release copy
    # remains usable when the Actions artifact itself expires.
    run = json.loads((bundle/'provenance/producer-run.json').read_text())
    info = json.loads((bundle/'provenance/producer-artifact.json').read_text())['artifacts'][0]
    artifact.validate_metadata(PRODUCER, run, info)
    for name, value in [('producer-run', run), ('producer-artifact', info)]:
        common.save(output/(name+'.json'), value)
    archive = work/'producer.zip'
    common.download(PRODUCER, archive)
    directory = work/'producer'
    artifact.extract_zip(archive, directory)
    row = verify_producer(directory)
    common.save(output/'producer-result.json', row)
    return directory, row


def mapping_recipe(template, netlist, output, bundle, snapshot, lock):
    root = lock['original_repo']
    source = root+'/hw/soc/out/timing-repair2-20260927'
    replacements = {
        source+'/synthesis-pipeline/soc_top.netlist.v': str(netlist),
        source+'/replacement-map-pipeline': str(output),
        source+'/synthesis-pipeline/abc.constr': str(snapshot/'repo'/Path(
            lock['original_synthesis']).relative_to(root)/'abc.constr'),
        lock['original_pdk']+'/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib': str(snapshot/STANDARD),
        root+'/hw/soc/out/external-review-20260919/route-closure-20260923/sram-chip-integration/independent_bb.v':
            str(bundle/'models/independent_bb.v'),
        root+'/hw/soc/techmap/independent_sram_map.v': str(bundle/'repo/hw/soc/techmap/independent_sram_map.v'),
    }
    for master in ('RM_IHPSG13_1P_2048x64_c2_bm_bist', 'RM_IHPSG13_2P_256x16_c2_bm_bist'):
        suffix='/hw/soc/pnr/'+master+'_bb.v'
        replacements[root+suffix] = str(bundle/'repo'/suffix.lstrip('/'))
    require(template.count(source+'/synthesis-pipeline/soc_top.netlist.v') == 1, 'Ambiguous map input')
    expression='|'.join(re.escape(p) for p in sorted(replacements, key=len, reverse=True))
    return re.sub(expression, lambda m: replacements[m.group()], template)


def mapping_contract(before, after, physical):
    """Preserve every existing nonmemory pin equation, not just a cell census."""
    native = {n:c for n,c in before['cells'].items() if c['type'].startswith('RM_')}
    require(len(native) == 20 and sum(c['type']=='RM_IHPSG13_1P_2048x64_c2_bm_bist' for c in native.values()) == 4
            and sum(c['type']=='RM_IHPSG13_2P_256x16_c2_bm_bist' for c in native.values()) == 16,
            'Expected exact 4 SP +16 DP vendor macros')
    for name, cell in native.items():
        p=cell['connections']
        width = 16 if '2P_' in cell['type'] else 64
        require(p['A_BIST_EN'] == ['0'] and len(p['A_BM']) == width and
                all(len(set(p['A_BM'][b:b+8])) == 1 for b in range(0,width,8)),
                'Vendor BIST or byte mask contract changed: '+name)
        if width == 16:
            require(p['B_BIST_EN'] == ['0'] and p['A_DLY'] == p['B_DLY'] == ['0']
                    and p['A_BM'] == p['B_BM'] == ['1']*16, 'DP SRAM contract changed: '+name)
    mapping = {x:x for x in ('0','1','x','z')}
    for name, net in before['netnames'].items():
        if name not in after['netnames']:
            continue
        other = after['netnames'][name]['bits']
        require(len(other) == len(net['bits']), 'Named net width changed')
        for old, new in zip(net['bits'], other):
            require(old not in mapping or mapping[old] == new, 'Inconsistent retained net mapping')
            mapping[old]=new
    for name, old in before['cells'].items():
        if name in native:
            continue
        new = after['cells'].get(name)
        require(new is not None and old['type'] == new['type'] and old.get('parameters') == new.get('parameters')
                and set(old['connections']) == set(new['connections']), 'Retained cell changed: '+name)
        for port, bits in old['connections'].items():
            require([mapping[b] for b in bits] == new['connections'][port], 'Retained cell equation changed: '+name+'/'+port)
    require(set(before['ports']) == set(after['ports']), 'Top ports changed')
    for name, port in before['ports'].items():
        require(port['direction'] == after['ports'][name]['direction'] and
                [mapping[b] for b in port['bits']] == after['ports'][name]['bits'], 'Top port changed: '+name)
    expected = {name:master for master,entry in physical['MACROS'].items() for name in entry['instances']}
    actual = {name:c['type'] for name,c in after['cells'].items() if c['type'] in physical['MACROS']}
    require(set(physical['MACROS']) == {'SP6TSRAM512x64','DP8TSRAMDP256x16'} and
            actual == expected and len(actual) == 32 and
            sum(x=='SP6TSRAM512x64' for x in actual.values()) == 16,
            '32 exact physical macro identities differ')
    require(not any(c['type'].startswith('RM_') for c in after['cells'].values()), 'Vendor SRAM retained')
    return dict(retained_nonmemory_cells=len(before['cells'])-20,
                top_ports=len(before['ports']), macros=actual,
                scope='SRAM replacement only; retained existing cell pin equations, masks and interfaces. '
                      'This does not prove original core versus prefix core or SRAM transistor behavior.')


def prepare_boot_bench(text, memory):
    require(memory in ('vendor','independent'), 'Unknown SRAM model selection')
    if memory == 'independent':
        start = text.index('  function [31:0] ram_word;')
        stop = text.index('  endfunction', start)+len('  endfunction')
        old = text[start:stop]
        require(old.count('i_SRAM_1P_behavioral_bm_bist.memory') == 4, 'RAM observation source differs')
        rows = ['  function [31:0] ram_word;', '    input [31:0] addr;', '    reg [12:0] widx;',
                '    reg [63:0] row;', '    begin', '      widx = addr[14:2];', '      case (widx[12:11])']
        for bank in range(4):
            rows += [f"        2'd{bank}: begin", '          case(widx[10:9])']
            for tile in range(4):
                rows.append(f"            2'd{tile}: row = dut.\\u_ram.g_ram_2048x64_ecc.u_b{bank}.bank_adapter.bank[{tile}].mem .mem[widx[8:0]];")
            rows += ['          endcase', '        end']
        rows += ['      endcase', '      ram_word = row[31:0];', '    end', '  endfunction']
        text = text[:start]+'\n'.join(rows)+text[stop:]
    marker='  integer finished=0;'
    require(text.count(marker) == 1 and text.count('$display("LOGICROM_GL PASS checks=28");') == 1,
            'Boot bench completion contract changed')
    monitor='''  reg qualification_mbist_seen=0;
  always @(negedge clk) if(rst_n) begin
    if(dut.mbist_failed_o === 1'b1) $fatal(1,"Mapped MBIST failed");
    if(dut.mbist_done_o === 1'b1 && !qualification_mbist_seen) begin
      if(dut.eth_mbist_done_o !== 2'b11 || dut.eth_mbist_failed_o !== 2'b00)
        $fatal(1,"Mapped Ethernet MBIST completion failed");
      qualification_mbist_seen=1;
      $display("QUALIFICATION_MBIST PASS cycles=%0d",cycles);
      $fflush();
    end
  end
'''
    text=text.replace(marker,monitor+marker)
    text=text.replace('$display("LOGICROM_GL PASS checks=28");', '''if(!qualification_mbist_seen || dut.mbist_done_o !== 1'b1 ||
       dut.mbist_busy_o !== 1'b0 || dut.mbist_failed_o !== 1'b0 ||
       dut.eth_mbist_done_o !== 2'b11 || dut.eth_mbist_failed_o !== 2'b00)
      $fatal(1,"Mapped boot did not preserve successful power-on MBIST");
    $display("LOGICROM_GL PASS checks=28");''')
    return text


def passed_boot(code, text):
    return (code == 0 and len(re.findall(r'(?m)^QUALIFICATION_MBIST PASS cycles=\d+$',text)) == 1
            and len(re.findall(r'(?m)^LOGICROM_GL PASS checks=28$',text)) == 1
            and re.search(r'(?im)(?:\bFATAL:|\bERROR:|Assertion failed|%Fatal|%Error)',text) is None)


def module(path, name):
    spec=importlib.util.spec_from_file_location(name,path)
    mod=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def prepare(output, work):
    require(os.environ.get('GITHUB_ACTIONS') == 'true', 'Full map/boot work is cloud-only')
    output=common.fresh_directory(output)
    work=common.fresh_directory(work)
    row=dict(schema=1,status='PREPARING',github_source_commit=os.environ['GITHUB_SHA'],
             producer=PRODUCER,candidate_adopted=False,timing_accepted=False,
             manufacturing_approval=False,mapped_core_equivalence_accepted=False,
             full_soc_functional_accepted=False,methods={})
    common.save(output/'result.json',row)
    try:
        for name in SOURCES:
            target=output/'methods'/name
            target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/name,target)
            row['methods'][name]=pin(target)
        lock=json.loads((ROOT/LOCK).read_text())
        bundle=work/'inputs'
        restore_inputs(lock,bundle)
        producer, source=get_producer(work,output,bundle)
        row.update(qualification_inputs=lock['archive'],producer_status=source['status'])
        toolroot=bootstrap_oss.install(work/'oss-cad-suite')
        for name,key in [('yosys','synthesis_yosys_sha256'),('iverilog','iverilog_sha256'),('vvp','vvp_sha256')]:
            expected=(json.loads((ROOT/alu.LOCK).read_text()) if name=='yosys' else lock)[key]
            require(common.sha(toolroot/'bin'/name)==expected,'Native tool differs: '+name)
        row['runtime']=dict(archive_sha256=bootstrap_oss.ARCHIVE_SHA256,archive_bytes=bootstrap_oss.ARCHIVE_SIZE,
                            tools={n:pin(toolroot/'bin'/n) for n in ('yosys','iverilog','vvp')})
        return output,work,row,lock,bundle,producer,toolroot
    except Exception as error:
        row.update(status='FAILED_PRESERVED',error=f'{type(error).__name__}: {error}')
        finish(output,row)
        raise


def finish(output,row):
    row['outputs']={str(p.relative_to(output)):pin(p) for p in sorted(output.rglob('*'))
                    if p.is_file() and p!=output/'result.json'}
    common.save(output/'result.json',row)


def map_run(output,work):
    output,work,row,lock,bundle,producer,toolroot=prepare(output,work)
    try:
        synlock=alu.validate_lock(json.loads((ROOT/alu.LOCK).read_text()))
        snapshot=work/'c10-synthesis-inputs'
        alu.restore(ROOT/synlock['archive']['path'],snapshot,synlock)
        physical=json.loads((bundle/'physical-config.json').read_text())
        manifest=json.loads((ROOT/alu.MANIFEST).read_text())
        common.verify_file(bundle/'physical-config.json',manifest['files'][manifest['config']])
        row.update(status='MAPPING_EXACT_SRAM_CONTRACTS',mapping={})
        for name in ('original','candidate'):
            out=output/name
            out.mkdir()
            script=out/'map.ys'
            script.write_text(mapping_recipe((bundle/'recipe/original-map.ys').read_text(),
                producer/('synthesis-'+name)/'soc_top.netlist.v',out,bundle,snapshot,synlock))
            common.save(output/'result.json',row)
            execution=alu.execute([toolroot/'bin/yosys','-s',script],out,'mapping')
            require(execution['returncode']==0,'SRAM mapping native failure: '+name)
            before=json.loads((out/'before.json').read_text())['modules']['soc_top']
            after=json.loads((out/'after.json').read_text())['modules']['soc_top']
            checks=mapping_contract(before,after,physical)
            del before,after
            net=pin(out/'soc_top.netlist.v')
            row['mapping'][name]=dict(execution=execution,checks=checks,netlist=net,recipe=pin(script))
            common.save(output/'result.json',row)
            if name=='original':
                require(net['sha256']==lock['original_mapping_sha256'],
                        'Original SRAM mapping did not reproduce exact13dd615d C10 replacement netlist')
        for name,expected in lock['files'].items():common.verify_file(bundle/name,expected)
        row['status']='PASS_REPRODUCED_ORIGINAL_AND_CANDIDATE_32_SRAM_MAPPING_ONLY'
        row['next_required']=['Paired four-state boot/MBIST', 'Separate original/candidate mapped equivalence',
                              'Fresh placement/CTS/routing under original constraints']
    except Exception as error:
        row.update(status='FAILED_PRESERVED',error=f'{type(error).__name__}: {error}')
        raise
    finally:
        finish(output,row)


def boot_prepare(output,work,name,memory,mapped):
    output,work,row,lock,bundle,producer,toolroot=prepare(output,work)
    try:
        require(name in EXPECTED_NETLISTS and memory in ('vendor','independent'),'Unknown boot case')
        row.update(variant=name,memory=memory,status='PREPARING_EXACT_MAPPED_BOOT',cycle_bound=CYCLES)
        gl=module(ROOT/'hw/soc/flow/sim_logic_boot_gl.py','qualification_gl')
        generator=module(ROOT/'hw/soc/flow/gen_logic_boot_rom.py','qualification_rom')
        firmware=output/'firmware'
        shutil.copytree(bundle/'firmware',firmware)
        rom=generator.generate(firmware/'test_soc.bin',firmware/'boot-rom')
        require(rom['rtl_sha256']==lock['rom_sha256'] and rom['image_sha256']==lock['loader_sha256']
                and rom==json.loads((bundle/'c10-rom/manifest.json').read_text()),'Regenerated C10 ROM differs')
        # Read-only generic ELF symbol decoding by nm; the ELF itself is hash pinned.
        nm=shutil.which('nm')
        require(nm is not None,'ELF symbol reader unavailable')
        symbols=gl.read_symbols(nm,firmware/'app.elf')
        row['symbols']=symbols
        row['nm']=dict(path=nm,**pin(Path(nm)),version=subprocess.check_output([nm,'--version'],text=True).splitlines()[0])
        version=subprocess.run([str(toolroot/'bin/iverilog'),'-V'],capture_output=True,text=True,check=True).stdout
        require(re.search(r'Icarus Verilog version (?:1[3-9]|[2-9]\d)',version),'Icarus>=13 required')
        (output/'iverilog-version.log').write_text(version)
        gate=gl.check_native_cell('iverilog',str(toolroot/'bin/iverilog'),bundle/'models/sg13g2_stdcell.v',output/'native-cell-gate')
        row['native_cell_gate']=gate
        require(gate['passed'],'Native standard-cell gate failed')
        source=producer/('synthesis-'+name)/'soc_top.netlist.v'
        models=[bundle/'models'/n for n in gl.SRAM_MODELS]
        if memory=='independent':
            require(mapped is not None,'Independent boot requires completed mapping artifact')
            mapped=mapped.resolve()
            mapping=json.loads((mapped/'result.json').read_text())
            verify_outputs(mapped,mapping)
            require(mapping['github_source_commit']==os.environ['GITHUB_SHA'] and mapping['producer']==PRODUCER
                    and mapping['status']=='PASS_REPRODUCED_ORIGINAL_AND_CANDIDATE_32_SRAM_MAPPING_ONLY',
                    'Mapping artifact source/status differs')
            require(mapping['mapping']['original']['netlist']['sha256']==lock['original_mapping_sha256'],
                    'Mapping original reproduction missing')
            source=mapped/name/'soc_top.netlist.v'
            common.verify_file(source,mapping['mapping'][name]['netlist'])
            common.save(output/'mapping-result.json',mapping)
            models=[bundle/'models/sp.v',bundle/'models/dp.v']
        bench=output/'tb_qualification_boot.v'
        bench.write_text(prepare_boot_bench((bundle/'repo/hw/soc/tb/tb_soc_logic_boot_gl.v').read_text(),memory))
        files=[bench,source,bundle/'repo/hw/soc/tb/flash_w25q128jv.v',bundle/'models/sg13g2_stdcell.v',*models]
        pins={str(p):pin(p) for p in [*files,firmware/'app.elf',firmware/'flash0.hex',firmware/'test_soc.bin']}
        command=[toolroot/'bin/iverilog','-g2005-sv','-s','tb_logicrom_gl','-o',work/'sim.vvp',
                 '-DFUNCTIONAL',f'-DTIMEOUT_CYCLES={CYCLES}']
        command += [f"-D{macro}=32'h{symbols[symbol]:08x}" for macro,symbol in gl.SYMBOLS.items()]
        row.update(status='COMPILING_ACTUAL_MAPPED_BOOT',sources=pins,rom_manifest=rom)
        common.save(output/'result.json',row)
        compile_result=alu.execute(command+files,output,'compile')
        row['compile']=compile_result
        require(compile_result['returncode']==0,'Actual mapped boot compilation failed')
        executable=pin(work/'sim.vvp')
        row.update(status='COMPILED_READY_FOR_FOUR_STATE_BOOT',compiled_simulation=executable,
                   compiled_simulation_path=str(work/'sim.vvp'),
                   boot_command=list(map(str,[toolroot/'bin/vvp','-i',work/'sim.vvp',
                                             '+flash0='+str(firmware/'flash0.hex')])))
        for path,expected in pins.items():common.verify_file(Path(path),expected)
    except Exception as error:
        row.update(status='FAILED_PRESERVED',error=f'{type(error).__name__}: {error}')
        raise
    finally:
        finish(output,row)


def boot_resume(output):
    """Stream real progress after the completed compile-stage artifact is saved."""
    require(os.environ.get('GITHUB_ACTIONS')=='true','Full boot work is cloud-only')
    row=json.loads((output/'result.json').read_text())
    try:
        require(row['github_source_commit']==os.environ['GITHUB_SHA'] and
                row['status']=='COMPILED_READY_FOR_FOUR_STATE_BOOT','Wrong boot startup checkpoint')
        verify_outputs(output,row)
        require(row['producer']==PRODUCER and row['cycle_bound']==CYCLES,'Boot contract changed')
        for path,expected in row['sources'].items():common.verify_file(Path(path),expected)
        common.verify_file(Path(row['compiled_simulation_path']),row['compiled_simulation'])
        command=row['boot_command']
        require(command[1:3]==['-i',row['compiled_simulation_path']] and len(command)==4
                and command[3]=='+flash0='+str(output/'firmware/flash0.hex'),
                'Compiled simulation command differs')
        common.verify_file(Path(command[0]),row['runtime']['tools']['vvp'])
        row['status']='RUNNING_FOUR_STATE_BOOT_AND_POWER_ON_MBIST'
        common.save(output/'result.json',row)
        progress=output/'progress'
        progress.mkdir()
        env=os.environ.copy()
        for key in ('GH_TOKEN','GITHUB_TOKEN','PYTHONPATH','PYTHONHOME'):env.pop(key,None)
        start=time.monotonic()
        # The benchmark emits and flushes cycle markers every10,000 cycles.
        # Tee complete native output to the artifact and the live Actions log.
        with (output/'boot.log').open('x') as log:
            child=subprocess.Popen(command,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,
                                   text=True,bufsize=1,env=env,stdin=subprocess.DEVNULL)
            for line in child.stdout:
                log.write(line)
                log.flush()
                print(line,end='',flush=True)
                match=re.search(r'LOGICROM_GL progress cycles=(\d+)',line)
                if match:
                    cycle=int(match[1])
                    observation=dict(cycle=cycle,elapsed_s=time.monotonic()-start,
                        raw_marker=line.rstrip(),log_prefix=pin(output/'boot.log'),
                        compiled_simulation=row['compiled_simulation'])
                    with (progress/f'cycle-{cycle:07d}.json').open('x') as sink:
                        sink.write(json.dumps(observation,indent=2)+'\n')
            code=child.wait()
        row['boot_execution']=dict(command=command,returncode=code,elapsed_s=time.monotonic()-start)
        common.save(output/'boot-execution.json',row['boot_execution'])
        for path,expected in row['sources'].items():common.verify_file(Path(path),expected)
        common.verify_file(Path(row['compiled_simulation_path']),row['compiled_simulation'])
        require(passed_boot(code,(output/'boot.log').read_text()),'Mapped MBIST/28-check boot failed')
        row.update(status='PASS_FOUR_STATE_MAPPED_BOOT_AND_POWER_ON_MBIST_ONLY',
                   scope='Real mapped SoC, unchanged loader/flash, native IHP cells, four-state Icarus; '
                         'successful system/Ethernet power-on MBIST and28 firmware checks. '
                         'No ROM/RAM preload, SDF, mapped equivalence, analog SRAM or timing acceptance.')
    except Exception as error:
        row.update(status='FAILED_PRESERVED',error=f'{type(error).__name__}: {error}')
        raise
    finally:
        finish(output,row)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase',choices=('map','boot-prepare','boot-run'))
    parser.add_argument('--variant',choices=('original','candidate'))
    parser.add_argument('--memory',choices=('vendor','independent'))
    parser.add_argument('--mapped',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--work',type=Path)
    args=parser.parse_args()
    if args.phase=='boot-run':boot_resume(args.output.resolve())
    elif args.work is None:parser.error('--work is required for preparation')
    elif args.phase=='map':map_run(args.output.resolve(),args.work.resolve())
    else:boot_prepare(args.output.resolve(),args.work.resolve(),args.variant,args.memory,args.mapped)


if __name__=='__main__':main()
