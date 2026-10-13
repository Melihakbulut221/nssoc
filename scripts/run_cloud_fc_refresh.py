#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Hasan Melih Akbulut
# SPDX-License-Identifier: Apache-2.0
"""Prove an exact source-bound FC refresh-counter priority partition."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import subprocess

SOURCE_SHA = '599755ec5824cdea24379dbac7de7eff20cb5dd738cc4f4fd2767c8ddf73b904'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def candidate(source):
    assert hashlib.sha256(source.encode()).hexdigest() == SOURCE_SHA
    clear = '                        if(frame_phase==2) refresh_count<=0;'
    increment = '            if(!training_i && refresh<REFRESH_CYCLES) refresh_count<=refresh+1;'
    for statement in (clear, increment, 'refresh_count<=REFRESH_CYCLES;'):
        assert source.count(statement) == 1
        source = source.replace(statement, '')
    assert source.count('refresh_count<=0;') == 2
    source = source.replace('refresh_count<=0;', '')
    anchor = '    always @(posedge clk_i or negedge rst_ni) begin'
    assert source.count(anchor) == 1
    partition = """    // Same-cycle priority and exact counter state; no timer or latency change.
    // Counter control is separate from byte CRC/snapshot/arbiter update logic.
    wire refresh_clear = active && tx_ready_i && index==5 &&
                         frame_class==2 && frame_phase==2;
    wire refresh_force_limit = !active && !training_i && phase==1 &&
                               second_triplet && peer_init2_seen_i;
    always @(posedge clk_i or negedge rst_ni) begin
        if(!rst_ni) refresh_count<=0;
        else if(!link_up_i || refresh_clear) refresh_count<=0;
        else if(refresh_force_limit) refresh_count<=REFRESH_CYCLES;
        else if(!training_i && refresh<REFRESH_CYCLES) refresh_count<=refresh+1;
    end
"""
    return source.replace(anchor, partition + anchor)


def verify(source, crc, out):
    source, crc, out = Path(source), Path(crc), Path(out)
    assert sha(source) == SOURCE_SHA
    out.mkdir(parents=True, exist_ok=False)
    before = {str(p): sha(p) for p in (source, crc)}
    altered = candidate(source.read_text())
    target = out / 'soc_pcie_fc_tx.v'
    target.write_text(altered)
    shutil.copyfile(crc, out / 'crc.v')
    yosys = shutil.which('yosys')
    assert yosys
    record = dict(status='RUNNING', source_sha256=SOURCE_SHA,
                  candidate_path=str(target), candidate_sha256=sha(target),
                  inputs=before, helper_sha256=sha(__file__), proofs=[],
                  runtime=subprocess.check_output([yosys, '-V'], text=True).strip(),
                  scope='Exact FC module outputs and counter/state equality. Explicit clocks and asynchronous reset; no observation mask, state abstraction or changed refresh period. Full parent/SoC timing not implied.')

    def save():
        (out / 'result.json').write_text(json.dumps(record, indent=2) + '\n')

    save()
    try:
        for value, negative in [(n, False) for n in (0, 1, 2, 127, 128, 255, 1024, 2147483647, -1)] + [(128, True)]:
            label = str(value) + ('-wrong-clear' if negative else '')
            directory = out / label
            directory.mkdir()
            gate = altered
            if negative:
                assert gate.count('frame_class==2 && frame_phase==2') == 1
                gate = gate.replace('frame_class==2 && frame_phase==2',
                                    'frame_class==2 && frame_phase!=2')
            for name, text in [('gold', source.read_text()), ('gate', gate)]:
                if value < 0:
                    # Native chparam rejects a leading-minus token. Let the
                    # Verilog frontend elaborate the original signed integer.
                    parameter = 'parameter integer REFRESH_CYCLES=128'
                    assert text.count(parameter) == 1
                    text = text.replace(parameter, 'parameter integer REFRESH_CYCLES=' + str(value))
                anchor = 'module soc_pcie_fc_tx #('
                assert text.count(anchor) == 1
                (directory / (name + '.v')).write_text(text.replace(anchor, 'module ' + name + ' #('))
            script = '\n'.join([
                'read_verilog -sv ../crc.v gold.v gate.v',
                ('chparam -set REFRESH_CYCLES ' + str(value) + ' gold') if value >= 0 else '# signed negative default in Verilog',
                ('chparam -set REFRESH_CYCLES ' + str(value) + ' gate') if value >= 0 else '# signed negative default in Verilog',
                'proc', 'flatten', 'memory_map', 'opt', 'clk2fflogic', 'opt',
                'write_json elaborated.json',
                'equiv_make gold gate equiv', 'hierarchy -top equiv',
                'equiv_simple', 'equiv_induct -seq 4', 'equiv_status -assert', ''])
            (directory / 'proof.ys').write_text(script)
            with (directory / 'proof.log').open('x') as log:
                result = subprocess.run([yosys, '-s', 'proof.ys'], cwd=directory,
                                        stdout=log, stderr=subprocess.STDOUT)
            log = (directory / 'proof.log').read_text()
            elaborated = json.loads((directory / 'elaborated.json').read_text())['modules']
            parameter_bits = {name: elaborated[name]['parameter_default_values']['REFRESH_CYCLES'] for name in ('gold','gate')}
            counter_widths = {name: len(elaborated[name]['netnames']['refresh_count']['bits']) for name in ('gold','gate')}
            assert all(len(bits)==32 and int(bits,2)==(value & 0xffffffff) for bits in parameter_bits.values())
            expected_width = 32 if value < 0 else max(1,value.bit_length())
            assert set(counter_widths.values()) == {expected_width}
            counts = re.findall(r'Of those cells (\d+) are proven and (\d+) are unproven', log)
            passed = result.returncode == 0 and len(counts) == 1 and int(counts[0][0]) > 0 and int(counts[0][1]) == 0 and 'Equivalence successfully proven!' in log
            rejected = result.returncode != 0 and bool(counts) and int(counts[-1][1]) > 0
            record['proofs'].append(dict(refresh_cycles=value, negative=negative,
                returncode=result.returncode, passed=passed, negative_rejected=rejected,
                equiv_counts=counts, parameter_bits=parameter_bits, counter_widths=counter_widths, log_sha256=sha(directory / 'proof.log'),
                script_sha256=sha(directory / 'proof.ys')))
            save()
            assert rejected if negative else passed, label
        assert before == {str(p): sha(p) for p in (source, crc)}
        assert sha(target) == record['candidate_sha256']
        record['status'] = 'PASS_MODULE_REFRESH_PARTITION_EQUIVALENCE_NOT_TIMING'
    except BaseException as error:
        record.update(status='FAIL_OR_ERROR', error=repr(error))
        raise
    finally:
        save()
    return target, record
